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
        self._com.write(b';')
        self._com._getresponse_1l('*idn?')

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


    def set_voltage(self, channel, voltage):
        if voltage < 10 and voltage >= 0:
            self._com.write((f'AMPLITUDE {channel} {voltage}\r\n').encode())
        else:
            raise Exception('Voltage to high')

    def read_voltage(self, channel):
        cmd = 'AMP? ' + str(channel)
        return self._com._getresponse(cmd)

    @property
    def identity(self):
        return self._com._getresponse_1l('*idn?')

    def help(self):
        return self._com.help()
