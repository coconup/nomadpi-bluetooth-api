import asyncio
from bleak import BleakClient, BleakGATTCharacteristic
from utils import bytes_to_int, int_to_bytes, crc16_modbus

CHARGING_STATE = {
    0: 'deactivated',
    1: 'activated',
    2: 'mppt',
    3: 'equalizing',
    4: 'boost',
    5: 'floating',
    6: 'current limiting'
}

LOAD_STATE = {
  0: 'off',
  1: 'on'
}

BATTERY_TYPE = {
    1: 'open',
    2: 'sealed',
    3: 'gel',
    4: 'lithium',
    5: 'custom'
}

class RenogyRover:
    UUID_RX = "0000fff1-0000-1000-8000-00805f9b34fb"
    UUID_TX = "0000ffd1-0000-1000-8000-00805f9b34fb"

    def __init__(self, address):
        self.address = address
        self.commands_queue = []
        self.next_command = 0
        self.data = {}

    def create_generic_read_request(self, device_id, function, regAddr, readWrd):                             
        data = None                                
        if regAddr != None and readWrd != None:
            data = []
            data.append(device_id)
            data.append(function)
            data += int_to_bytes(regAddr)
            data += int_to_bytes(readWrd)
            data += crc16_modbus(bytes(data))
        return data

    def parse_device_info(self, bs):
        data = {}
        data['model'] = (bs[3:17]).decode('utf-8').strip()
        return data

    def parse_device_address(self, bs):
        data = {}
        data['device_id'] = bytes_to_int(bs, 4, 1)
        return data

    def parse_chargin_info(self, bs):
        data = {
            'battery_percentage': bytes_to_int(bs, 3, 2),
            'battery_voltage': bytes_to_int(bs, 5, 2, scale = 0.1),
            'battery_current': bytes_to_int(bs, 7, 2, scale = 0.01),
            'battery_temperature': bytes_to_int(bs, 10, 1),
            'controller_temperature': bytes_to_int(bs, 9, 1),
            'load_status': LOAD_STATE.get(bytes_to_int(bs, 67, 1) >> 7),
            'load_voltage': bytes_to_int(bs, 11, 2, scale = 0.1),
            'load_current': bytes_to_int(bs, 13, 2, scale = 0.01),
            'load_power': bytes_to_int(bs, 15, 2),
            'pv_voltage': bytes_to_int(bs, 17, 2, scale = 0.1) ,
            'pv_current': bytes_to_int(bs, 19, 2, scale = 0.01),
            'pv_power': bytes_to_int(bs, 21, 2),
            'max_charging_power_today': bytes_to_int(bs, 33, 2),
            'max_discharging_power_today': bytes_to_int(bs, 35, 2),
            'charging_amp_hours_today': bytes_to_int(bs, 37, 2),
            'discharging_amp_hours_today': bytes_to_int(bs, 39, 2),
            'power_generation_today': bytes_to_int(bs, 41, 2),
            'power_consumption_today': bytes_to_int(bs, 43, 2),
            'power_generation_total': bytes_to_int(bs, 59, 4),
            'charging_status': CHARGING_STATE.get(bytes_to_int(bs, 68, 1)),
        }
        return data

    def parse_battery_type(self, bs):
        data = {}
        data['battery_type'] = BATTERY_TYPE.get(bytes_to_int(bs, 3, 2))
        return data

    def notification_handler(self, sender: BleakGATTCharacteristic, data: bytearray):
        command = self.commands_queue[self.next_command]
        if command and (command['words'] * 2 + 5) == len(data):
            if command['command'] == 12:
                self.data['device_info'] = self.parse_device_info(data)
            elif command['command'] == 26:
                self.data['device_address'] = self.parse_device_address(data)
            elif command['command'] == 256:
                self.data['metrics'] = self.parse_chargin_info(data)
            elif command['command'] == 57348:
                self.data['battery_type'] = self.parse_battery_type(data)
            self.next_command += 1

    def add_command(self, command, words):
        self.commands_queue.append(dict(command=command, words=words))

    async def execute_commands(self):
        async with BleakClient(self.address) as client:
            await client.start_notify(self.UUID_RX, self.notification_handler)

            for item in self.commands_queue:
                request = self.create_generic_read_request(255, 3, item['command'], item['words']) 
                await client.write_gatt_char(self.UUID_TX, request)
    
            await asyncio.sleep(1)
            await client.stop_notify(self.UUID_RX)

async def get_info(mac_address):
    bms = RenogyRover(mac_address)
    bms.add_command(12, 8)
    # bms.add_command(26, 1)
    bms.add_command(256, 34)
    bms.add_command(57348, 1)
    await bms.execute_commands()
    return bms.data

async def main():
    mac_address = '84:c6:92:13:c0:f4'
    data = await get_info(mac_address)
    print(data)

if __name__ == '__main__':
    asyncio.run(main())
