#
# Copyright (C) 2024, HENSOLDT Cyber GmbH
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# For commercial licensing, contact: info.cyber@hensoldt.net
#

import json
import base64
import asyncio
import os
from fastapi import (
    FastAPI,
    HTTPException,
    File,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse

import requests

from .tftp import TFTP
from .uart import LogUart, DataUart


# ===============================================================================
# Hardware
# ===============================================================================




class Device:
    def __init__(self, device, config):
        self.__device = device
        self.__config = config
        self.name = device["name"]
        self.poe_id = device["poe_id"]
        self.uart = LogUart(
            self.name, device["uart"]["serialid"], device["uart"]["usb_path"]
        )
        self.has_data_uart = "data_uart" in device

    def print_info(self):
        power_state = "Error" if (ps := self.power_state()) is None else ps
        return {
            **self.__device,
            "reading": self.uart.is_reading(),
            "power_state": power_state,
        }

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
            verify=False,
        )

    def power_on(self):
        return self.__switch_power_set("auto-on").ok

    def power_off(self):
        return self.__switch_power_set("off").ok

    async def data_uart(self, websocket):
        if not self.has_data_uart:
            print(
                f"Data Uart not configured for {self.name}, websocket connection failed."
            )
            await websocket.close(
                code=4002, reason="A data uart is not configured for this device"
            )
            return

        print("Opening Data Uart for ", self.name)

        data_uart = DataUart(
            self.__device,
            self.__device["data_uart"]["serialid"],
            self.__device["data_uart"]["usb_path"],
        )
        await data_uart.open_port()

        async def uart_callback(data):
            print("Received Data from Uart: ", data)
            await websocket.send_text(data)

        # Uart read loops, this will run until the websocket disconnects
        uart_read_task = asyncio.create_task(data_uart.read(uart_callback))

        print("Entering data uart read loop for ", self.name)

        try:
            while True:
                print("Waiting for data from WS...")
                data = await websocket.receive_text()

                print("Received Data from WS: ", data)
                await data_uart.write(data)

        except WebSocketDisconnect:
            print(f"Data Uart Websocket disconnected for {self.name} disconnected.")
        except Exception as e:
            print(f"Unexpected error in handling data Uart websocket: {e}")
        finally:
            uart_read_task.cancel()
            try:
                await uart_read_task
            except asyncio.CancelledError:
                pass
            # await websocket.close(code=1006)

    @staticmethod
    def get_device(device):
        if device not in devices:
            raise HTTPException(status_code=404, detail="Device not found")
        return devices[device]


# ===============================================================================
# Config
# ===============================================================================

config = None

class Config:
    def __init__(self, config_file):
        if not os.path.exists(config_file):
            print(f"ERROR: Config file at {config_file} not found")
            exit(-1)

        with open(config_file, "r") as file:
            self.config = json.load(file)
            self.ip = self.config["ip"]
            self.port = self.config["port"]

    async def get_devices(self):
        return {dev["name"]: Device(dev, self.config) for dev in self.config["devices"]}

    # Returns a safe copy of the config without credentials
    def get_clean_config(self):
        return {
            **self.config,
            "poe_switch": {**self.config["poe_switch"], "password": "********"},
        }


def init_config(config_file="/etc/uart_proxy.json"):
    global config
    config = Config(config_file)


def get_config():
    if config is None:
        init_config()
    return config


# ===============================================================================
# Api Code
# ===============================================================================

app = FastAPI()
devices = None
tftp = TFTP()


@app.on_event("startup")
async def startup_event():
    global devices
    devices = await get_config().get_devices()


@app.get("/{device}/info")
async def device_info(device: str):
    Device.get_device(device)
    info = {**devices[device].print_info(), "tftp": tftp.status(device)}
    print(info)
    return JSONResponse(content=info)


@app.get("/config")
async def get_loaded_config():
    return JSONResponse(content=config.get_clean_config())


## Power
@app.post("/{device}/power/state")
async def device_power_state(device: str):
    dev = Device.get_device(device)

    power_state = dev.power_state()

    if power_state is None:
        raise HTTPException(
            status_code=502, detail="Retrieving information from switch failed"
        )
    return power_state


@app.post("/{device}/power/on")
async def device_power_on(device: str):
    dev = Device.get_device(device)

    if not dev.power_on():
        raise HTTPException(status_code=502, detail="Request to switch failed")


@app.post("/{device}/power/off")
async def device_power_off(device: str):
    dev = Device.get_device(device)
    if not dev.power_off():
        raise HTTPException(status_code=502, detail="Request to switch failed")


## Uart
@app.get("/{device}/uart/state")
async def device_uart_state(device: str):
    dev = Device.get_device(device)
    return str(dev.uart.is_reading())


@app.post("/{device}/uart/enable")
async def device_uart_enable(device: str):
    dev = Device.get_device(device)
    await dev.uart.start_reading()


@app.post("/{device}/uart/disable")
async def device_uart_disable(device: str):
    dev = Device.get_device(device)
    dev.uart.stop_reading()


@app.get("/{device}/uart/readline")
async def device_uart_readline(device: str):
    dev = Device.get_device(device)
    if not dev.uart.is_reading():
        raise HTTPException(status_code=412, detail="Uart not started")

    if dev.uart.queue.empty():
        raise HTTPException(status_code=202, detail="No data in the queue")

    return base64.b64encode(await dev.uart.queue.get())


## Data UART
@app.get("/{device}/data_uart/available")
async def device_data_uart_state(device: str):
    return Device.get_device(device).has_data_uart


@app.websocket("/{device}/data_uart/connect")
async def device_data_uart_connect(device: str, websocket: WebSocket):
    print("Websocket api triggered ", device)
    try:
        await websocket.accept()
        await Device.get_device(device).data_uart(websocket)
    except WebSocketDisconnect:
        print(f"Websocket for {device} disconnected.")


## TFTP
@app.get("/{device}/tftp/state")
async def device_tftp_state(device: str):
    return JSONResponse(content=tftp.status(device))


@app.post("/{device}/tftp/upload")
async def device_tftp_upload(device: str, file: UploadFile = File(...)):
    error_code, error_msg = await tftp.upload(device, file)
    if error_code != 200:
        raise HTTPException(status_code=error_code, detail=error_msg)


@app.delete("/{device}/tftp/delete")
async def device_tftp_delete(device: str):
    tftp.delete(device)


@app.on_event("shutdown")
async def shutdown_event():
    print("shutting down")
    [dev.join_thread() for dev in devices.values()]
    print("all threads joined.")
