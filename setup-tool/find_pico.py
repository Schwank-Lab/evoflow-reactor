import serial.tools.list_ports

def find_pico_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Pico" in port.description or "Board" in port.description:
            return port.device
    return None


if __name__ == '__main__': 
    port = find_pico_port()
    if port is None: 
        print('Could not find the pico attached.')
    else: 
        print(f'Pico is found at port:\n{port}')
        with open('./pico_port.txt', 'w') as f: 
            f.write(port)
