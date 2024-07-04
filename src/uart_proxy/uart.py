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


class UART:
    def __init__(self, device: str, serial: str, usb_path: str):
        self.device = device
        self.serial = serial
        self.usb_path = usb_path
        self.queue = asyncio.Queue()
        self.reading_state = asyncio.Event()
        self.find_uart_device()
        self.port = None

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

    async def open_port(self):
        try:
            self.port, _ = await serial_asyncio.open_serial_connection(
                url=self.uart.device,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            asyncio.create_task(self.read_from_uart())
            self.state = UART_STATE.CONNECTED
        except Exception as e:
            print(
                f"Exception occurred during opening of UART Device for {self.device}:\n{e}"
            )
            self.state = UART_STATE.ERROR

    async def read_from_uart(self):
        while True:
            print("Awaiting data event to be true")
            await self.reading_state.wait()
            print("Reading from UART")
            line = await self.port.readline()
            if line:
                await self.queue.put(line)
                print(line)

    def is_reading(self):
        return self.reading_state.is_set()

    async def start_reading(self):
        if self.state is UART_STATE.UNINITIALIZED:
            await self.open_port()

        if self.state is UART_STATE.INIT_FAILED or self.state is UART_STATE.ERROR:
            raise HTTPException(
                status_code=500, detail="Failed to initialize UART Device"
            )
        self.reading_state.set()
        self.state = UART_STATE.RECEIVING

    def stop_reading(self):
        self.reading_state.clear()
        self.state = UART_STATE.CONNECTED


class DataUart:
    def __init__(self, device, config):
        pass
