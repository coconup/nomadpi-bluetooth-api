import logging

from utils import bytes_to_int, int_to_bytes, crc16_modbus
from adapters.base_solar_charge_controller import BaseSolarChargeController
from ble.client import Device

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

class RenogyRoverMppt(BaseSolarChargeController, Device):
    notify_char_uuid = "0000fff1-0000-1000-8000-00805f9b34fb"
    write_char_uuid = "0000ffd1-0000-1000-8000-00805f9b34fb"

    commands = [
        { 'name': 'device_info', 'command': 12, 'words': 8 },
        { 'name': 'charging_info', 'command': 256, 'words': 34 },
        { 'name': 'battery_type', 'command': 57348, 'words': 1 }
    ]

    def __init__(self, mac_address):
        BaseSolarChargeController.__init__(self)
        Device.__init__(
            self,
            mac_address=mac_address,
            notify_uuid=self.notify_char_uuid,
            write_uuid=self.write_char_uuid
        )

    def renogy_command(self, command, words):                             
        data = None                                
        if command != None and words != None:
            data = [255, 3]
            data += int_to_bytes(command)
            data += int_to_bytes(words)
            data += crc16_modbus(bytes(data))
        return data

    def execute(self, commands):
        parsed_commands = [self.renogy_command(cmd['command'], cmd['words']) for cmd in commands]
        super().execute(parsed_commands)

    def parse_result(self):
        for result in self.data:
            command = next((cmd for cmd in self.commands if cmd['words'] * 2 + 5 == len(result)), None)
            if command['name'] == 'device_info':
                self.parse_device_info(result)
            elif command['name'] == 'charging_info':
                self.parse_chargin_info(result)
            elif command['name'] == 'battery_type':
                self.parse_battery_type(result)

    def parse_device_info(self, bs):
        self.model = (bs[3:17]).decode('utf-8').strip()

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

def get_info(mac_address):
    mppt = RenogyRoverMppt(mac_address)
    mppt.execute(mppt.commands)
    mppt.parse_result()
    return mppt.to_json()

def main():
    mac_address = '84:c6:92:13:c0:f4'
    data = get_info(mac_address)
    print(data)

if __name__ == '__main__':
    main()
