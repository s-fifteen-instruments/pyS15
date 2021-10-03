import time

from . import serial_connection


class SinglePhotonDetector(object):
    """ """

    DEVICE_IDENTIFIER = "SPD"

    def __init__(self, device_path: str = ""):
        if device_path == "":
            device_path = (
                serial_connection.search_for_serial_devices(self.DEVICE_IDENTIFIER)
            )[0]
            print("Connected to", device_path)
        self._com = serial_connection.SerialConnection(device_path)

    def identity(self) -> str:
        # self._com.write(b'*IDN?\r\n')
        return self._com.getresponse("*idn?")

    def help(self) -> str:
        print(self._com.help())

    def save_settings(self) -> str:
        return self._com.getresponse("save")

    @property
    def hvolt(self) -> float:
        return float(self._com.getresponse("hvolt?"))

    @hvolt.setter
    def hvolt(self, value: float):
        self._com.write("hvolt {}\r\n".format(value).encode())
        time.sleep(0.1)

    @property
    def threshvolt(self) -> float:
        return float(self._com.getresponse("threshvolt?"))

    @threshvolt.setter
    def threshvolt(self, value: float):
        self._com.write("threshvolt {}\r\n".format(value).encode())

    @property
    def constp(self) -> float:
        return float(self._com.getresponse("constp?"))

    @constp.setter
    def constp(self, value: float):
        self._com.write("constp {}\r\n".format(value).encode())

    @property
    def consti(self) -> float:
        return float(self._com.getresponse("consti?"))

    @consti.setter
    def consti(self, value: float):
        self._com.write("consti {}\r\n".format(value).encode())

    @property
    def loop(self) -> int:
        return int(self._com.getresponse("loop?"))

    @loop.setter
    def loop(self, value: int):
        self._com.write("loop {}\r\n".format(value).encode())

    @property
    def pvolt(self) -> float:
        return float(self._com.getresponse("pvolt?"))

    @pvolt.setter
    def pvolt(self, value: float):
        self._com.write("pvolt {}\r\n".format(value).encode())

    def temp_stabilization_on(self):
        self.loop = 1

    def temp_stabilization_off(self):
        self.loop = 0

    @property
    def time(self) -> float:
        return float(self._com.getresponse("time?"))

    @time.setter
    def time(self, value: float):
        """Sets counting time duration

        value (float): duration in ms
        """
        self._com.write("time {}\r\n".format(value).encode())

    def counts(self, counting_time_sec: float = 1) -> int:
        """Returns counts detected on the detector within the given counting time.
        Default of 1 second."""
        self.time = counting_time_sec * 1000
        return int(self._com.getresponse("counts?", timeout=counting_time_sec + 0.1))

    @property
    def temperature(self) -> float:
        return float(self._com.getresponse("temp?"))

    @temperature.setter
    def temperature(self, value: float):
        self._com.write("settemp {}\r\n".format(value).encode())

    @property
    def settemperature(self) -> float:
        return float(self._com.getresponse("settemp?"))

    @settemperature.setter
    def settemperature(self, value: float):
        self.temperature = value

    @property
    def delay(self) -> int:
        return float(self._com.getresponse("delay?"))

    @delay.setter
    def delay(self, value: int):
        self._com.write("delay {}\r\n".format(value).encode())
