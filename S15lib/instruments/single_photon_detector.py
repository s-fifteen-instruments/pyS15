import time
from . import serial_connection


class SinglePhotonDetector(object):
    """
    """

    DEVICE_IDENTIFIER = 'SPD'

    def __init__(self, device_path: str = ''):
        if device_path == '':
            device_path = (serial_connection.search_for_serial_devices(
                self.DEVICE_IDENTIFIER))[0]
            print('Connected to', device_path)
        self._com = serial_connection.SerialConnection(device_path)

    def identity(self) -> str:
        # self._com.write(b'*IDN?\r\n')
        return self._com._getresponse_1l('*idn?')

    def help(self) -> str:
        print(self._com.help())

    def save_settings(self) -> str:
        return self._com._getresponse_1l('save')

    @property
    def hvolt(self) -> float:
        return float(self._com._getresponse_1l('hvolt?'))

    @hvolt.setter
    def hvolt(self, value: float):
        self._com.write(f'hvolt {value}\r\n'.encode())

    @property
    def time(self) -> float:
        return float(self._com._getresponse_1l('time?'))

    @time.setter
    def time(self, value: float):
        '''Sets counting time duration

        value (float): duration in ms
        '''
        self._com.write(f'time {value}\r\n'.encode())

    def counts(self) -> int:
        return int(self._com._getresponse_1l('counts?', timeout=1.1))

    @property
    def temperature(self) -> float:
        return float(self._com._getresponse_1l('temp?'))

    @temperature.setter
    def temperature(self, value: float):
        self._com.write('settemp {value}')
