import serial


from tty_usb import TTY_USB


uart0 = TTY_USB.find_device(
    serial   = None,
    usb_path = '1-2'
)

port = serial.Serial(
    port = uart0.device,
    baudrate = 115200,
    bytesize = serial.serialutil.EIGHTBITS,
    parity   = serial.serialutil.PARITY_NONE,
    stopbits = serial.serialutil.STOPBITS_ONE,
    timeout  = 0.5,
)

while 1:
    print(port.readline())



