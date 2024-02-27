from fastapi import FastAPI
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
        if dev.finish_thread.is_set():
            break
        dev.queue.put("Item")  # Put an item into the queue
        print("Produced an item")
        #TODO: Clear queue and uart_fifo before continueing


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


class Config:
    def __init__(self, config_file = "config.json"):
        with open(config_file, 'r') as file:
            self.config = json.load(file)

    def get_devices(self):
        return [ Device(dev) for dev in self.config["uart_devices"] ]




if __name__ == "__main__":
    devices = Config().get_devices()

    rpi = devices[0]
    rpi.init_thread()
    rpi.start_thread()

    for _ in range(10):
        print(rpi.queue.get())

    rpi.stop_thread()

    print("sleeping...")
    time.sleep(5)

    rpi.start_thread()
    for _ in range(10):
        print(rpi.queue.get())
    
    rpi.stop_thread()

    rpi.join_thread()
    
    
    
    
    
    
    
        
