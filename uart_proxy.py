from fastapi import FastAPI, HTTPException
import serial
import threading
import queue
import time
from tty_usb import TTY_USB

import json


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
        dev.queue.put(line)
        print(line)
        

class Device:
    def __init__(self, device):
        self.name = device["name"]
        self.serial = device["serialid"]
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
                    timeout  = 0.5,
                )

    def init_thread(self):
        self.thread = threading.Thread(target=read_from_uart_thread, args=(self,))
        self.thread.start()
        

    def start_thread(self):
        self.event.set()

    def stop_thread(self):
        self.event.clear()

    def join_thread(self):
        self.finish_thread.set()
        self.start_thread()
        self.thread.join()

    def print_info(self):
        info = f"Name: {self.name}\n"
        info += f"Serial ID: {self.serial}\n"
        info += f"USB Path: {self.usb_path}\n"
        # Add more information as needed
        return info        

#===============================================================================
# Config
#===============================================================================

config = None

class Config:
    def __init__(self, config_file):
        with open(config_file, 'r') as file:
            self.config = json.load(file)
            self.ip     = self.config["ip"]
            self.port   = self.config["port"]

    def get_devices(self):
        return { dev["name"]: Device(dev) for dev in self.config["uart_devices"] }

def init_config(config_file = "config.json"):
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
    return devices[device].print_info()
        

@app.post("/{device}/start")
async def device_start(device: str):
    if device not in devices:
        raise HTTPException(status_code=404, detail="Device not found")

    dev = devices[device]
    dev.start_thread()


@app.post("/{device}/stop")
async def device_stop(device: str):
    if device not in devices:
        raise HTTPException(status_code=404, detail="Device not found")

    dev = devices[device]
    dev.stop_thread()


@app.get("/{device}/readline")
async def device_readline(device: str):
    if device not in devices:
        raise HTTPException(status_code=404, detail="Device not found")

    dev = devices[device]
    if not dev.event.is_set():
        raise HTTPException(status_code=412, detail="Uart not started")

    if dev.queue.empty():
        raise HTTPException(status_code=202, detail="No data in the queue")

    return dev.queue.get()
    
@app.on_event("shutdown")
async def shutdown_event():
    print("shutting down")
    [ dev.join_thread() for dev in devices.values() ]
    print("all threads joined.")
    
