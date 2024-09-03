#
# Copyright (C) 2024, HENSOLDT Cyber GmbH
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# For commercial licensing, contact: info.cyber@hensoldt.net
#


import asyncio
from enum import Enum

import serial
import serial_asyncio
from fastapi import HTTPException

from .tty_usb import TTY_USB


class UART_STATE(Enum):
    UNINITIALIZED = 0
    ERROR = 1
    INIT_FAILED = 2
    CONNECTED = 3
    RECEIVING = 4


class Uart:
    def __init__(self, device: str, serial: str, usb_path: str):
        self.reader, self.writer = None, None
        self.device = device
        self.serial = serial
        self.usb_path = usb_path
        self.find_uart_device()

    def __del__(self):
        if self.writer is not None:
            self.writer.close()

    async def open_port(self):
        try:
            self.reader, self.writer = await serial_asyncio.open_serial_connection(
                url=self.uart.device,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            self.state = UART_STATE.CONNECTED
        except Exception as e:
            print(
                f"Exception occurred during opening of UART Device for {self.device}:\n{e}"
            )
            self.state = UART_STATE.ERROR

    def find_uart_device(self):
        try:
            self.uart = TTY_USB.find_device(self.serial, self.usb_path)
            self.state = UART_STATE.UNINITIALIZED
        except Exception as e:
            print(
                f"Exception occurred during initialization of UART Device for {self.device}:\n"
                f"Trying to initialize serialid: {self.serial} usb_path {self.usb_path}\n{e}"
            )
            self.state = UART_STATE.INIT_FAILED


class LogUart(Uart):
    def __init__(self, device: str, serial: str, usb_path: str):
        super().__init__(device, serial, usb_path)

        self.queue = asyncio.Queue()
        self.reading_state = asyncio.Event()

    async def read_from_uart(self):
        while True:
            await self.reading_state.wait()
            line = await self.reader.readline()
            if line:
                await self.queue.put(line)

    def is_reading(self):
        return self.reading_state.is_set()

    async def initialize_uart_reading(self):
        await self.open_port()
        asyncio.create_task(self.read_from_uart())

    async def start_reading(self):
        self.queue = asyncio.Queue() #Flush queue

        if self.state is UART_STATE.UNINITIALIZED:
            print("UART not initialized, trying initialization")
            await self.initialize_uart_reading()

        if self.state is UART_STATE.INIT_FAILED or self.state is UART_STATE.ERROR:
            print("UART initialization failed, exiting")
            raise HTTPException(
                status_code=500, detail="Failed to initialize UART Device"
            )

        self.reading_state.set()
        self.state = UART_STATE.RECEIVING

    def stop_reading(self):
        self.reading_state.clear()
        self.state = UART_STATE.CONNECTED


class DataUart(Uart):
    async def read(self, callback):
        while True:
            data = await self.reader.read(1)
            await callback(data)

    async def write(self, data):
        self.writer.write(data)
        await self.writer.drain()
