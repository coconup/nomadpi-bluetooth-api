class BaseSolarChargeController:
    def __init__(self):
        self.model = None
        self.charging_status = None
        self.controller_temperature = None
        self.photovoltaic_current = None
        self.photovoltaic_power = None
        self.photovoltaic_voltage = None
        self.load_current = None
        self.load_power = None
        self.load_voltage = None
        self.load_status = None
        self.battery_type = None
        self.battery_temperature = None
        self.battery_voltage = None
        self.battery_current = None
        self.battery_state_of_charge = None

    def to_json(self):
        data = {
            'model': self.model,
            'charging_status': self.charging_status,
            'controller_temperature': self.controller_temperature,
            'photovoltaic': {
                'current': self.photovoltaic_current,
                'power': self.photovoltaic_power,
                'voltage': self.photovoltaic_voltage
            },
            'load': {
                'current': self.load_current,
                'power': self.load_power,
                'status': self.load_status,
                'voltage': self.load_voltage
            },
            'battery': {
                'temperature': self.battery_temperature,
                'type': self.battery_type,
                'voltage': self.battery_voltage,
                'current': self.battery_current,
                'state_of_charge': self.battery_state_of_charge,
            }
        }

        return data