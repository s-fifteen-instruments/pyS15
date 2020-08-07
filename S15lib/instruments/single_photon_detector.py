import time
from . import serial_connection


class SinglePhotonDetector(object):
    """
    """

    DEVICE_IDENTIFIER = 'SPD'

    def __init__(self, device_path: str=''):
        if device_path == '':
            device_path = (serial_connection.search_for_serial_devices(
                self.DEVICE_IDENTIFIER))[0]
            print('Connected to', device_path)
        self._com = serial_connection.SerialConnection(device_path)
        # setvolt 0 1.5; interpol 0 2; setspeed 0 170; zero 0; on 0

    
    def identity(self) -> str:
        # self._com.write(b'*IDN?\r\n')
        return self._getresponse_1l('*idn?')

    def help(self) -> str:
        print(self._com.help())

    @property
    def hvolt(self) -> str:
        return float(self._com._getresponse_1l('hvolt?'))

    @hvolt.setter
    def hvolt(self, value: float):
        self._com.write(f'hvolt {value}\r\n'.encode())

    def counts(self) -> int:
        return int(self._com._getresponse_1l('counts?', timeout = 1.1))

    @property
    def temperature(self) -> str:
        return float(self._com._getresponse_1l('temp?'))

    @temperature.setter
    def temperature(self, value: float):
        self._com.write('settemp {value}')