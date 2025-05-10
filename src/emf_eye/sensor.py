
class Sensor:
    """ Base sensor class for all sensors """
    def __init__(self, name):
        self.name = name

    def read(self):
        """ Read the sensor value """
        raise NotImplementedError("Subclass must implement abstract method")

    def __str__(self):
        return f"{self.name}: {self.read()}"

