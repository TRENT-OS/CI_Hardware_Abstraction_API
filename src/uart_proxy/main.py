#!/usr/bin/python3

#
# Copyright (C) 2024, HENSOLDT Cyber GmbH
# 
# SPDX-License-Identifier: GPL-2.0-or-later
#
# For commercial licensing, contact: info.cyber@hensoldt.net
#

import argparse

import uvicorn

 
from .uart_proxy import app, get_config, init_config
from .tty_usb import TTY_USB


def get_argument_parser():
    parser = argparse.ArgumentParser(
        description="Uart proxy"
        "provide uart read access via an API"
    )
    parser.add_argument(
        "--configfile",
        "-c",
        help="Path to server configuration file",
        required=False,
    )
    parser.add_argument(
        "--devices",
        "-d",
        action="store_true",
        help="Print all available devices found"
    )
    return parser
 
 
def main():
    parser = get_argument_parser()
    args = parser.parse_args()
    if args.devices:
        TTY_USB.get_and_print_device_list()
        exit(0)

    print("Load Server Configuration")
    if args.configfile:
        init_config(args.configfile)
    else:
        init_config()
    print("Starting Webserver!")
    config = get_config()
    uvicorn.run(app=app, host=config.ip, port=config.port, log_level="info")
 
 
if __name__ == "__main__":
    main()
