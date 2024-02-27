import asyncio
from bleak import BleakClient, BleakGATTCharacteristic
from utils import bytes_to_int

class JbdBt:
    UUID_RX = '0000ff01-0000-1000-8000-00805f9b34fb'
    UUID_TX = '0000ff02-0000-1000-8000-00805f9b34fb'

    def __init__(self, address):
        self.buffer = bytearray()
        self.address = address
        self.data = {}

    def jbd_command(self, command: int):
        return bytes([0xDD, 0xA5, command, 0x00, 0xFF, 0xFF - (command - 1), 0x77])

    def parse_metrics(self, result):
        mos_byte = bytes_to_int(result, 24, 1)
        num_cell = bytes_to_int(result, 25, 1)
        num_temp = bytes_to_int(result, 26, 1)

        return {
            'voltage':      bytes_to_int(result, 4, 2, scale=0.01),
            'current':     -bytes_to_int(result, 6, 2, scale=0.01, signed=True),
            'charge':       bytes_to_int(result, 7, 2, scale=0.01),
            'capacity':     bytes_to_int(result, 10, 2, scale=0.01),
            'num_cycles':   bytes_to_int(result, 12, 2, scale=0.01),
            'soc':          bytes_to_int(result, 23, 1),
            'temperatures': [
                (bytes_to_int(result, 27 + i * 2, 2, scale=0.1) - 273.1) for i in range(num_temp)
            ],
            'switches':     dict(
                discharge=mos_byte == 2 or mos_byte == 3,
                charge=mos_byte == 1 or mos_byte == 3,
            )
        }

    def parse_voltages(self, result):
        num_cell = int(bytes_to_int(result, 3, 1) / 2)
        voltages = [(bytes_to_int(result, 4 + 1 * 2, 2, scale=0.001)) for i in range(num_cell)]
        return voltages

    def save_result(self, command, result):
        if command == 0x03:
            self.data['metrics'] = self.parse_metrics(result)
        elif command == 0x04:
            self.data['voltages'] = self.parse_voltages(result)

    def notification_handler(self, sender: BleakGATTCharacteristic, data: bytearray):
        self.buffer += data
        if self.buffer.endswith(b'w'):
            command = self.buffer[1]
            self.save_result(command, self.buffer)
            self.buffer.clear()

    async def send_command(self, command):
        async with BleakClient(self.address) as client:
            await client.start_notify(self.UUID_RX, self.notification_handler)
            await client.write_gatt_char(self.UUID_TX, self.jbd_command(command))
            await asyncio.sleep(1)
            await client.stop_notify(self.UUID_RX)

async def get_info(mac_address):
    bms = JbdBt(mac_address)
    await bms.send_command(0x03)
    await bms.send_command(0x04)
    return bms.data

async def main():
    mac_address = 'A4:C1:38:0B:79:22'
    data = await get_info(mac_address)
    print(data)

if __name__ == '__main__':
    asyncio.run(main())
