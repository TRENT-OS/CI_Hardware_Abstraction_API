#
# Copyright (C) 2024, HENSOLDT Cyber GmbH
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# For commercial licensing, contact: info.cyber@hensoldt.net
#


import sys
import asyncio
import threading
from websockets.client import connect


async def recv(websocket):
    while True:
        message = await websocket.recv()
        print(f"< {message}")


async def send(websocket, loop):
    while True:
        message = await loop.run_in_executor(None, input, "> ")
        await websocket.send(message)


async def ws_loop():
    uri = f"ws://192.168.88.4:8000/{sys.argv[1]}/data_uart/connect"
    async with connect(uri) as websocket:
        recv_task = asyncio.create_task(recv(websocket))
        send_task = asyncio.create_task(send(websocket, asyncio.get_running_loop()))
        await asyncio.gather(recv_task, send_task)


if __name__ == "__main__":
    asyncio.run(ws_loop())
