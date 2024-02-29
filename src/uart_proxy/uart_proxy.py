#
# Copyright (C) 2024, HENSOLDT Cyber GmbH
# 
# SPDX-License-Identifier: GPL-2.0-or-later
#
# For commercial licensing, contact: info.cyber@hensoldt.net
#

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import serial
import os
import threading
import queue
import time
import base64
import requests

from .tty_usb import TTY_USB

import json


#===============================================================================
# Hardware
#===============================================================================

def read_from_uart_thread(dev):
    while True:
        if not dev.event.is_set():
            dev.event.wait()
            print("clear queue")
            dev.port.flush()
        if dev.finish_thread.is_set():
            dev.port.close()
            break
        line = dev.port.readline()
        if (len(line) == 0):
            # readline() encountered a timeout
            continue
        dev.queue.put(line)
        print(line)
        

class Device:
    def __init__(self, device, config):
        self.__device = device
        self.__config = config
        self.name = device["name"]
        self.serial = device["serialid"]
        self.poe_id = device["poe_id"]
        self.usb_path = device["usb_path"]
        self.uart = TTY_USB.find_device(self.serial, self.usb_path)
        
        self.open_port()
        
        self.queue = queue.Queue()
        
        self.event = threading.Event()
        self.finish_thread = threading.Event()

        self.init_thread()

    def open_port(self):
        self.port = serial.Serial(
                    port = self.uart.device,
                    baudrate = 115200,
                    bytesize = serial.serialutil.EIGHTBITS,
                    parity   = serial.serialutil.PARITY_NONE,
                    stopbits = serial.serialutil.STOPBITS_ONE,
                    timeout  = 5,
                )

    def init_thread(self):
        self.thread = threading.Thread(target=read_from_uart_thread, args=(self,))
        self.thread.start()
        

    def start_thread(self):
        self.event.set()

    def stop_thread(self):
        self.event.clear()
        while not self.queue.empty():
            self.queue.get()

    def join_thread(self):
        self.finish_thread.set()
        self.start_thread()
        self.thread.join()

    def print_info(self):
        power_state = "Error" if (ps := self.power_state()) is None else ps
        
        return { **self.__device, 
                 "reading": self.event.is_set(), 
                 "thread_running": not self.finish_thread.is_set(),
                 "power_state": power_state } 

    def power_state(self):
        poe = self.__config["poe_switch"]
        url = f"{poe['url']}/rest/interface/ethernet/poe"
        response = requests.get(url, auth=(poe["username"], poe["password"]))

        if not response.ok:
            return None

        json_res = json.loads(response.text)

        field = next((e for e in json_res if e.get("name") == self.poe_id), {})

        return field.get("poe-out")

    def __switch_power_set(self, mode: str):
        poe = self.__config["poe_switch"]
        url = f"{poe['url']}/rest/interface/ethernet/set"
        return requests.post(
                url, 
                auth=(poe["username"], poe["password"]),
                headers={"Content-Type": "application/json"},
                json={".id": self.poe_id, "poe-out": mode},
                verify=False
                )
        
    def power_on(self):
        return self.__switch_power_set("auto-on").ok


    def power_off(self):
        return self.__switch_power_set("off").ok
        
        

#===============================================================================
# Config
#===============================================================================

config = None

class Config:
    def __init__(self, config_file):
        if not os.path.exists(config_file):
            print(f"ERROR: Config file at {config_file} not found")
            exit(-1)
        
        with open(config_file, 'r') as file:
            self.config = json.load(file)
            self.ip     = self.config["ip"]
            self.port   = self.config["port"]

    def get_devices(self):
        return { dev["name"]: Device(dev, self.config) for dev in self.config["devices"] }

def init_config(config_file = "/etc/uart_proxy.json"):
    global config
    config = Config(config_file)

def get_config():
    if config is None:
        init_config()
    return config


#===============================================================================
# Api Code
#===============================================================================

app = FastAPI()
devices = None

@app.on_event("startup")
async def startup_event():
    global devices
    devices = get_config().get_devices()

@app.get("/{device}/info")
async def device_info(device: str):
    if device not in devices:
        raise HTTPException(status_code=404, detail="Device not found")
    return JSONResponse(content=devices[device].print_info())
        

@app.post("/{device}/power/state")
async def device_power_state(device: str):
    if device not in devices:
        raise HTTPException(status_code=404, detail="Device not found")
    dev = devices[device]
    power_state = dev.power_state()

    if power_state is None:
        raise HTTPException(status_code=502, detail="Retrieving information from switch failed")
    return power_state
    
  

@app.post("/{device}/power/on")
async def device_power_on(device: str):
    if device not in devices:
        raise HTTPException(status_code=404, detail="Device not found")

    dev = devices[device]
    if not dev.power_on():
        raise HTTPException(status_code=502, detail="Request to switch failed")
    


@app.post("/{device}/power/off")
async def device_power_off(device: str): 
    if device not in devices:
        raise HTTPException(status_code=404, detail="Device not found")

    dev = devices[device]
    if not dev.power_off():
        raise HTTPException(status_code=502, detail="Request to switch failed")
    

@app.get("/{device}/uart/state")
async def device_uart_state(device: str):
    if device not in devices:
        raise HTTPException(status_code=404, detail="Device not found")

    dev = devices[device]
    return str(dev.event.is_set())


@app.post("/{device}/uart/start")
async def device_uart_start(device: str):
    if device not in devices:
        raise HTTPException(status_code=404, detail="Device not found")

    dev = devices[device]
    dev.start_thread()


@app.post("/{device}/uart/stop")
async def device_uart_stop(device: str):
    if device not in devices:
        raise HTTPException(status_code=404, detail="Device not found")

    dev = devices[device]
    dev.stop_thread()


@app.get("/{device}/uart/readline")
async def device_uart_readline(device: str):
    if device not in devices:
        raise HTTPException(status_code=404, detail="Device not found")

    dev = devices[device]
    if not dev.event.is_set():
        raise HTTPException(status_code=412, detail="Uart not started")

    if dev.queue.empty():
        raise HTTPException(status_code=202, detail="No data in the queue")

    return base64.b64encode(dev.queue.get())

   
@app.on_event("shutdown")
async def shutdown_event():
    print("shutting down")
    [ dev.join_thread() for dev in devices.values() ]
    print("all threads joined.")
    
