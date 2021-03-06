"""
Created on 8 July 2020
by Chin Chean Lim, Mathias Seidler
"""

from . import serial_connection
# import time


class LCRDriver(object):
    """Module for communicating with the liquid crystal variable phase retarder"""

    DEVICE_IDENTIFIER = 'LCD cell driver'

    def __init__(self, device_path=''):
        # if no path is indicated it tries to init the first power_meter device
        if device_path == '':
            device_path = (serial_connection.search_for_serial_devices(
                self.DEVICE_IDENTIFIER))[0]
            print('Connected to', device_path)
        self._com = serial_connection.SerialConnection(device_path)

    def reset(self):
        '''Resets the device.

        Returns:
            str -- Response of the device after.
        '''
        return self._com.write(b'*RST')

    def all_channels_on(self):
        self._com.write(b'ON\r\n')
        self._com.write(b'DARK\r\n')
        self._com.write(b'FREQ 2000\r\n')

    def set_voltage(self, channel: int, voltage: float):
        if voltage < 10 and voltage >= 0:
            self._com.write((f'AMPLITUDE {channel} {voltage}\r\n').encode())
        else:
            raise Exception('Voltage to high')

    def read_voltage(self, channel: int):
        cmd = 'AMP? ' + str(channel)
        return self._com._getresponse(cmd)

    @property
    def V1(self):
        return self._com._getresponse_1l('AMP? 1')

    @V1.setter
    def V1(self, V1):
        self._com.write((f'AMPLITUDE 1 {V1}\r\n').encode())

    @property
    def V2(self):
        return self._com._getresponse_1l('AMP? 2')

    @V2.setter
    def V2(self, value):
        self._com.write((f'AMPLITUDE 2 {value}\r\n').encode())

    @property
    def V3(self):
        return self._com._getresponse_1l('AMP? 3')

    @V3.setter
    def V3(self, value):
        self._com.write((f'AMPLITUDE 3 {value}\r\n').encode())

    @property
    def V4(self):
        return self._com._getresponse_1l('AMP? 4')

    @V4.setter
    def V4(self, value):
        self._com.write((f'AMPLITUDE 4 {value}\r\n').encode())

    @property
    def identity(self):
        return self._com._getresponse_1l('*idn?')

    def help(self):
        return self._com.help()
