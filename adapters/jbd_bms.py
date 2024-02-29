import logging
import time

from utils import bytes_to_int
from adapters.base_battery import BaseBattery
from ble.client import Device

class JbdBms(Device, BaseBattery):
    notify_char_uuid = "0000ff01-0000-1000-8000-00805f9b34fb"
    write_char_uuid = "0000ff02-0000-1000-8000-00805f9b34fb"

    def __init__(self, mac_address):
        BaseBattery.__init__(self)
        Device.__init__(
            self,
            mac_address=mac_address,
            notify_uuid=self.notify_char_uuid,
            write_uuid=self.write_char_uuid
        )

    def on_ready_callback(self):
        print(f"Sending sample command")
        self.client.characteristic_write_value(self.jbd_command(0x01))
        time.sleep(1)
        super().on_ready_callback()

    def on_data_received(self, data):
        self.buffer += data
        if self.buffer.endswith(b'w'):
            command = self.buffer[1]
            self.append_response(self.buffer, clear_buffer=True)

    def jbd_command(self, command: int):
        return bytes([0xDD, 0xA5, command, 0x00, 0xFF, 0xFF - (command - 1), 0x77])

    def execute(self, commands):
        parsed_commands = [self.jbd_command(command) for command in commands]
        self.commands = parsed_commands
        super().execute(parsed_commands)

    def parse_result(self):
        for result in self.data:
            command = result[1]
            if command == 0x03:
                self.parse_metrics(result)
            elif command == 0x04:
                self.parse_voltages(result)

    def parse_metrics(self, result):
        mos_byte = bytes_to_int(result, 24, 1)
        num_cell = bytes_to_int(result, 25, 1)
        num_temp = bytes_to_int(result, 26, 1)

        self.voltage = bytes_to_int(result, 4, 2, scale=0.01)
        self.cells_count = num_cell
        self.current_load = -bytes_to_int(result, 6, 2, scale=0.01, signed=True)
        self.remaining_capacity = bytes_to_int(result, 8, 2, scale=0.01)
        self.total_capacity = bytes_to_int(result, 10, 2, scale=0.01)
        self.cycles_count = bytes_to_int(result, 12, 2, scale=0.01)
        self.state_of_charge = bytes_to_int(result, 23, 1)
        self.temperatures = [
            (bytes_to_int(result, 27 + i * 2, 2, scale=0.1) - 273.1) for i in range(num_temp)
        ]
        self.power_load = self.current_load * self.voltage

    def parse_voltages(self, result):
        num_cell = int(bytes_to_int(result, 3, 1) / 2)
        voltages = [(bytes_to_int(result, 4 + 1 * 2, 2, scale=0.001)) for i in range(num_cell)]

        self.cells_voltage = voltages
        self.cells_count = num_cell

def get_info(mac_address):
    bms = JbdBms(mac_address)
    bms.execute([0x03, 0x04])
    bms.parse_result()
    return bms.to_json()

def main():
    mac_address = 'A4:C1:38:0B:79:22'
    data = get_info(mac_address)
    print(data)

if __name__ == '__main__':
    main()
