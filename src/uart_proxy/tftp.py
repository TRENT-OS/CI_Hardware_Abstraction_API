import asyncio
import os
import pathlib
import subprocess

# ===============================================================================
# TFTP BOOT
# ===============================================================================


class TFTP:
    def __init__(self, tftp_folder="/tftpboot/"):
        self.tftp_folder = tftp_folder
        self.trentos_image_name = "os_image.elf"

    reply = {}

    @staticmethod
    def __check_xinetd_status():
        try:
            output = subprocess.check_output(["systemctl", "status", "xinetd"]).decode(
                "utf-8"
            )
        except Exception as e:
            return f"Failed to retrieve status due to: {e}"
        if all(substr in output for substr in ("Active: active", "Loaded: loaded")):
            return "service runnning"
        return "service not running"

    @staticmethod
    def __xinet_tftp_service_status():
        xinetd_config = "/etc/xinetd.d/tftp"
        if not os.path.exists(xinetd_config):
            return "Error config does not exist"

        with open(xinetd_config, "r") as file:
            data = file.read()

        inner_data = data[data.find("{") + 1 : data.find("}")].strip()
        key_value_pairs = [line.strip().split("=") for line in inner_data.split("\n")]
        return {key.strip(): value.strip() for key, value in key_value_pairs}

    def status(self, device: str):
        return {
            "xinetd": self.__check_xinetd_status(),
            "xinet_tftp_config": self.__xinet_tftp_service_status(),
            "tftp_folder": {
                "tftp/": os.path.exists(pathlib.Path(self.tftp_folder)),
                "device/": os.path.exists(pathlib.Path(self.tftp_folder) / device),
                "trentos_image": os.path.exists(
                    pathlib.Path(self.tftp_folder) / device / self.trentos_image_name
                ),
            },
        }

    def __validate_file(self, filename):
        return filename != self.trentos_image_name

    async def upload(self, device, file):
        if self.__validate_file(file.filename):
            return (422, "The uploaded file is not the TRENTOS executable expected")

        if not os.path.exists(pathlib.Path(self.tftp_folder) / device):
            os.makedirs(pathlib.Path(self.tftp_folder) / device)

        file_location = (
            pathlib.Path(self.tftp_folder) / device / self.trentos_image_name
        )
        try:
            with open(file_location, "wb") as tftp_file:
                tftp_file.write(await file.read())
            return (200, "Upload successfull")
        except Exception as e:
            print(f"Exception during file processing occured: {e}")
            return (500, "Saving file saved due to server error")

    def delete(self, device):
        file_location = (
            pathlib.Path(self.tftp_folder) / device / self.trentos_image_name
        )
        try:
            os.remove(file_location)
            return (200, "File deleted succesfully")
        except Exception as e:
            print(f"Exception during file processing occured: {e}")
            return (500, "Saving file saved due to server error")
