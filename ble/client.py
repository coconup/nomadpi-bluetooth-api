import os
import gatt
import logging 
import time
from threading import Timer

DISCOVERY_TIMEOUT = 5
READ_TIMEOUT = 5
CONNECT_TIMEOUT=5
RUN_TIMEOUT=20

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Device:
    def __init__(self, mac_address, notify_uuid, write_uuid):
        self.mac_address = mac_address
        self.manager = DeviceManager(adapter_name='hci0', mac_address=mac_address, alias=None)
        self.buffer = bytearray()
        self.data = []
        self.client = DeviceClient(
            manager=self.manager, 
            mac_address=mac_address,
            notify_uuid=notify_uuid,
            write_uuid=write_uuid,
            on_ready=self.on_ready_callback,
            on_data=self.on_data_callback,
            on_complete=self.on_complete_callback
        )
        self.on_data = None

    def on_ready_callback(self):
        self.client.process_next_command()

    def on_data_callback(self, value):
        logger.info(f"{self.mac_address} - Received data ${value}")
        self.on_data_received(value)

    def execute(self, commands):
        print(f"Executing commands {commands}")
        self.client.commands_queue = commands
        self.client.manager.discover()
        self.client.connect()
        self.client.manager.run()

    def on_data_received(self, data):
        self.buffer += data
        self.append_response(self.buffer, clear_buffer=True)

    def append_response(self, data, clear_buffer):
        logger.info(f'Appending response')
        self.data.append(data.copy())
        if clear_buffer:
            self.buffer.clear()
        self.client.process_next_command()

    def on_complete_callback(self):
        self.manager.stop()

class DeviceManager(gatt.DeviceManager):
    def __init__(self, adapter_name, mac_address, alias):
        super(). __init__(adapter_name)
        self.device_found = False
        self.mac_address = mac_address
        self.device_alias = alias
        self.run_timer = None

        if not self.is_adapter_powered:
            self.is_adapter_powered = True
        logger.info(f"{self.mac_address} - Adapter status - Powered: ".format(self.is_adapter_powered))

    def discover(self):
        discovering = True; wait = DISCOVERY_TIMEOUT; self.device_found = False; mac_address = self.mac_address.upper();

        logger.info(f"{self.mac_address} - Updating devices...")
        self.update_devices()
        logger.info(f"{self.mac_address} - Starting discovery...")
        self.start_discovery()

        while discovering:
            time.sleep(1)
            logger.info(f"{self.mac_address} - Devices found: %s", len(self.devices()))
            for dev in self.devices():
                if dev.mac_address != None and (dev.mac_address.upper() == mac_address or (dev.alias() and dev.alias().strip() == self.device_alias)) and discovering:
                    logger.info(f"{self.mac_address} - Found matching device %s => [%s]", dev.alias(), dev.mac_address)
                    discovering = False; self.device_found = True
            wait = wait -1
            if (wait <= 0):
                discovering = False
        self.stop_discovery()

    def run(self):
        # self.run_timer = Timer(RUN_TIMEOUT, self.on_run_timeout)
        # self.run_timer.start()
        super().run()

    def on_run_timeout(self):
        logger.info(f'Run timeout')
        self.stop()

    def stop(self):
        if self.run_timer:
            self.run_timer.cancel()
        logger.info(f'Stopping manager')
        super().stop()

class DeviceClient(gatt.Device):
    def __init__(self, mac_address, manager, on_ready, on_data, on_complete, notify_uuid, write_uuid, on_connect_fail=None):
        super(). __init__(mac_address=mac_address, manager=manager)
        self.data_callback = on_data
        self.on_ready_callback = on_ready
        self.on_complete_callback = on_complete
        self.connect_fail_callback = on_connect_fail
        self.notify_char_uuid = notify_uuid
        self.write_char_uuid = write_uuid
        self.write_characteristic = None
        self.notify_characteristic = None
        self.read_timer = None
        self.connect_timer = None
        self.disconnect_timer = None
        self.commands_queue = None
        self.command_index = 0
        self.ready = False

    def cancel_timers(self):
        if self.connect_timer:
            self.connect_timer.cancel()
        if self.read_timer:
            self.read_timer.cancel()
        if self.disconnect_timer:
            self.disconnect_timer.cancel()

    def connect(self):
        logger.info(f'Connecting')
        self.connect_timer = Timer(CONNECT_TIMEOUT, self.on_connect_timeout)
        self.connect_timer.start()
        super().connect()

    def on_connect_timeout(self):
        logger.info(f'Connect timeout')
        self.disconnect()

    def connect_succeeded(self):
        if self.connect_timer:
            self.connect_timer.cancel()
        super().connect_succeeded()
        logger.info(f"{self.mac_address} - [%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        # super().connect_failed(error)
        # logger.info(f"{self.mac_address} - Connection failed {error}")
        # if self.connect_fail_callback:
        #     self.connect_fail_callback(error)

        os._exit(os.EX_OK)

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        logger.info(f"{self.mac_address} - [%s] Disconnected" % (self.mac_address))
        self.cancel_timers()
        self.on_complete_callback()

    def services_resolved(self):
        super().services_resolved()

        logger.info(f"{self.mac_address} - [%s] Resolved services" % (self.mac_address))
        characteristics = [c for service in self.services for c in service.characteristics]
        self.notify_characteristic = next((c for c in characteristics if c.uuid == self.notify_char_uuid), None)
        self.write_characteristic = next((c for c in characteristics if c.uuid == self.write_char_uuid), None)

        if not self.notify_characteristic or not self.write_characteristic:
            logger.info(f"{self.mac_address} - Could not find characteristics {self.notify_char_uuid} and {self.write_char_uuid}")
            self.disconnect()
            return

        logger.info(f"{self.mac_address} - Enabling notifications from characteristic {self.notify_characteristic.uuid}")
        self.notify_characteristic.enable_notifications()

        time.sleep(0.5)
            
    def process_next_command(self):
        if self.command_index == len(self.commands_queue):
            self.disconnect()
        else:
            logger.info(f'Processing next command')
            command = self.commands_queue[self.command_index]
            self.command_index += 1
            logger.info(f"{self.mac_address} - Sending data {command} to characteristic {self.write_characteristic.uuid}")
            self.characteristic_write_value(command)

    def descriptor_read_value_failed(self, descriptor, error):
        logger.info(f'descriptor_value_failed')

    def characteristic_enable_notifications_succeeded(self, characteristic):
        logger.info(f'characteristic_enable_notifications_succeeded')
        time.sleep(1)
        self.read_timer = Timer(READ_TIMEOUT, self.on_read_timeout)
        self.read_timer.start()
        if not self.ready:
            self.ready = True
            self.on_ready_callback()

    def characteristic_enable_notifications_failed(self, characteristic, error):
        logger.info(f'characteristic_enable_notifications_failed')

    def characteristic_value_updated(self, characteristic, value):
        super().characteristic_value_updated(characteristic, value)
        if characteristic.uuid == self.notify_char_uuid:
            self.data_callback(value)

    def characteristic_write_value(self, value):
        self.write_characteristic.write_value(value)
        self.writing = value

    def characteristic_write_value_succeeded(self, characteristic):
        super().characteristic_write_value_succeeded(characteristic)
        logger.info(f'characteristic_write_value_succeeded')
        self.writing = False

    def characteristic_write_value_failed(self, characteristic, error):
        super().characteristic_write_value_failed(characteristic, error)
        logger.info(f'characteristic_write_value_failed {error}')
        if error == "In Progress" and self.writing is not False:
            time.sleep(0.1)
            self.characteristic_write_value(self.writing, characteristic)
        else:
            self.writing = False

    def alias(self):
        alias = super().alias()
        if alias:
            return alias.strip()
        return None

    def on_read_timeout(self):
        logger.info(f'Read timeout')
        self.disconnect()

    def exit(self):
        logger.info(f'Exiting')
        self.command_index = 0
        self.cancel_timers()

    def disconnect(self):
        logger.info(f'Disconnecting')
        self.exit()

        try:
            is_connected = super().is_connected()
        except Exception as e:
            is_connected = False

        if is_connected:
            logger.info(f"{self.mac_address} - Exit: Disconnecting device: %s [%s]", self.alias(), self.mac_address)
            super().disconnect()
            self.disconnect_timer = Timer(CONNECT_TIMEOUT, self.disconnect_succeeded)
            self.disconnect_timer.start()
