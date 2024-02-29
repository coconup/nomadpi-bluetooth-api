class BaseBattery:
    def __init__(self):
        self.voltage = None
        self.cells_voltage = None
        self.cells_count = None
        self.current_load = None
        self.power_load = None
        self.remaining_capacity = None
        self.total_capacity = None
        self.cycles_count = None
        self.state_of_charge = None
        self.temperatures = None

    def to_json(self):
        data = {
            'voltage': {
                'total': self.voltage,
                'cells': self.cells_voltage,
            },
            'cells_count': self.cells_count or None,
            'current_load': self.current_load,
            'power_load': self.power_load,
            'capacity': {
                'remaining': self.remaining_capacity,
                'total': self.total_capacity,
            },
            'cycles_count': self.cycles_count,
            'state_of_charge': self.state_of_charge,
            'temperatures': self.temperatures
        }

        return data