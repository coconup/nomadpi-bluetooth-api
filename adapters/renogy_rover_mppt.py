import asyncio
from bleak import BleakClient, BleakGATTCharacteristic

from utils import bytes_to_int, int_to_bytes, crc16_modbus
from adapters.base_solar_charge_controller import BaseSolarChargeController

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

class RenogyRover(BaseSolarChargeController):
    UUID_RX = "0000fff1-0000-1000-8000-00805f9b34fb"
    UUID_TX = "0000ffd1-0000-1000-8000-00805f9b34fb"

    def __init__(self, address):
        super().__init__(address)
        self.commands_queue = []
        self.next_command = 0

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
        self.model = (bs[3:17]).decode('utf-8').strip()

    def parse_device_address(self, bs):
        self.device_address = bytes_to_int(bs, 4, 1)

    def parse_chargin_info(self, bs):
        self.battery_state_of_charge = bytes_to_int(bs, 3, 2)
        self.battery_voltage = bytes_to_int(bs, 5, 2, scale = 0.1)
        self.battery_current = bytes_to_int(bs, 7, 2, scale = 0.01)
        self.battery_temperature = bytes_to_int(bs, 10, 1)
        self.controller_temperature = bytes_to_int(bs, 9, 1)
        self.load_status = LOAD_STATE.get(bytes_to_int(bs, 67, 1) >> 7)
        self.load_voltage = bytes_to_int(bs, 11, 2, scale = 0.1)
        self.load_current = bytes_to_int(bs, 13, 2, scale = 0.01)
        self.load_power = bytes_to_int(bs, 15, 2)
        self.photovoltaic_voltage = bytes_to_int(bs, 17, 2, scale = 0.1) 
        self.photovoltaic_current = bytes_to_int(bs, 19, 2, scale = 0.01)
        self.photovoltaic_power = bytes_to_int(bs, 21, 2)
        # self.max_charging_power_today = bytes_to_int(bs, 33, 2)
        # self.max_discharging_power_today = bytes_to_int(bs, 35, 2)
        # self.charging_amp_hours_today = bytes_to_int(bs, 37, 2)
        # self.discharging_amp_hours_today = bytes_to_int(bs, 39, 2)
        # self.power_generation_today = bytes_to_int(bs, 41, 2)
        # self.power_consumption_today = bytes_to_int(bs, 43, 2)
        # self.power_generation_total = bytes_to_int(bs, 59, 4)
        self.charging_status = CHARGING_STATE.get(bytes_to_int(bs, 68, 1))

    def parse_battery_type(self, bs):
        self.battery_type = BATTERY_TYPE.get(bytes_to_int(bs, 3, 2))

    def notification_handler(self, sender: BleakGATTCharacteristic, data: bytearray):
        command = self.commands_queue[self.next_command]
        if command and (command['words'] * 2 + 5) == len(data):
            if command['command'] == 12:
                self.parse_device_info(data)
            elif command['command'] == 26:
                self.parse_device_address(data)
            elif command['command'] == 256:
                self.parse_chargin_info(data)
            elif command['command'] == 57348:
                self.parse_battery_type(data)
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
    mppt = RenogyRover(mac_address)
    mppt.add_command(12, 8)
    # bms.add_command(26, 1)
    mppt.add_command(256, 34)
    mppt.add_command(57348, 1)
    await mppt.execute_commands()
    return mppt.to_json()

async def main():
    mac_address = '84:c6:92:13:c0:f4'
    data = await get_info(mac_address)
    print(data)

if __name__ == '__main__':
    asyncio.run(main())
