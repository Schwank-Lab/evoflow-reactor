import platform
import subprocess
import serial.tools.list_ports
import os
import tempfile


def find_pico_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Pico" in port.description or "Board" in port.description:
            return port.device
    return None


def ensure_tmp_dir():
    tmp_dir = tempfile.gettempdir()
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    return tmp_dir


if __name__ == "__main__":
    port = find_pico_port()
    if port is None:
        print("Could not find the pico attached.")
    else:
        tmp_dir = ensure_tmp_dir()
        file_path = os.path.join(tmp_dir, "pico_port.txt")
        print(f"Pico is found at port: {port}")
        with open(file_path, "w") as f:
            f.write(port)
        print(f"Copy/Paste (Run) the following command: 'export PICO_PORT={port}'")
