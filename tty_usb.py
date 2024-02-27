import os
import pathlib


#-------------------------------------------------------------------------------
# implement "@class_or_instancemethod" attribute for methods
class class_or_instance_method(classmethod):

    def __get__(self, instance, type_):

        descr_get = super().__get__ if instance is None \
                    else self.__func__.__get__

        return descr_get(instance, type_)



class TTY_USB():

    #---------------------------------------------------------------------------
    def __init__(self, device, vid, pid, serial, usb_path, driver):
        self.device   = device
        self.vid      = vid
        self.pid      = pid
        self.serial   = serial
        self.usb_path = usb_path
        self.driver   = driver


    #---------------------------------------------------------------------------
    @class_or_instance_method
    def get_device_list(self_or_cls):

        dev_list = []

        base_folder = '/sys/class/tty'
        for dev in sorted(os.listdir(base_folder)):

            if not dev.startswith('ttyUSB'):
                continue

            dev_fqn = os.path.join(base_folder, dev)
            # each item in the folder is a symlink
            linked_dev = os.path.realpath(dev_fqn)
            # 1-4.2.2.1:1.0 -> 1-4.2.2.1
            usb_path = pathlib.Path(linked_dev).parts[-4].split(':',1)[0]

            usb_dev = os.path.join('/sys/bus/usb/devices', usb_path)

            def get_id_from_file(dn, id_file):
                id_file_fqn = os.path.join(dn, id_file)
                if not os.path.exists(id_file_fqn): return None
                with open(id_file_fqn) as f: return f.read().strip()

            vid = get_id_from_file(usb_dev, 'idVendor')
            pid = get_id_from_file(usb_dev, 'idProduct')
            serial = get_id_from_file(usb_dev, 'serial')

            # <item>/device/driver is also symlink
            driver = os.path.basename(
                        os.path.realpath(
                            os.path.join(dev_fqn, 'device/driver')))

            device = TTY_USB(
                        f'/dev/{dev}',
                        vid,
                        pid,
                        serial,
                        usb_path,
                        driver)

            dev_list.append(device)

        return dev_list


    #---------------------------------------------------------------------------
    @class_or_instance_method
    def get_and_print_device_list(self_or_cls):

        print('USB/serial adapter list')
        dev_list = self_or_cls.get_device_list()
        for dev in dev_list:
            sn = f's/n {dev.serial}' if dev.serial else '[no s/n]'
            print(f'  {dev.device} is {dev.vid}:{dev.pid} {sn} at {dev.usb_path}, driver {dev.driver}')

        return dev_list


    #---------------------------------------------------------------------------
    @class_or_instance_method
    def find_device(self_or_cls, serial = None, usb_path = None):

        dev_list = self_or_cls.get_and_print_device_list()
        print(dev_list)

        print(f'opening {usb_path}, {serial}')

        my_device = None

        if serial is not None:
            for dev in dev_list:
                print(f"serial comparison: {dev.serial} : {serial}")
                if (dev.serial == serial):
                    my_device = dev
                    break

        if usb_path is not None:
            for dev in dev_list:
                print(f"serial comparison: {dev.usb_path} : {usb_path}")
                if (dev.usb_path == usb_path):
                    my_device = dev
                    break

        #else:
        #    raise Exception('must specify device, serial and/or USB path')

        if not my_device:
            raise Exception('device not found')

        if usb_path and (usb_path != my_device.usb_path):
            raise Exception(f'USB path different, expected {usb_path}, got {my_device.usb_path}')

        if serial and (serial != my_device.serial):
            raise Exception(f'serial different, expected {serial}, got {my_device.serial}')

        sn = f's/n {dev.serial}' if dev.serial else '[no s/n]'
        usb_path = my_device.usb_path or '[None]'
        print(f'using {my_device.device} ({sn}, USB path {usb_path})')

        return my_device
