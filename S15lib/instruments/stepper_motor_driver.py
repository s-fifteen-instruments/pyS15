import time
from . import serial_connection


class StepperMotorDriver(object):
    """
    Controls stepper motors.
    """

    DEVICE_IDENTIFIER = 'SMD'

    def __init__(self, device_path: str=''):
        if device_path == '':
            device_path = (serial_connection.search_for_serial_devices(
                self.DEVICE_IDENTIFIER))[0]
            print('Connected to', device_path)
        self._com = serial_connection.SerialConnection(device_path)
        # setvolt 0 1.5; interpol 0 2; setspeed 0 170; zero 0; on 0

    def init_motor(self, channel: int):
        self._com.write(f'setvolt {channel} 1.5; interpol {channel} 2; setspeed {channel} 170; zero {channel}; on {channel}\r\n'.encode())
        self._com.write(f'setvolt {channel} 1.5; interpol {channel} 2; setspeed {channel} 170; zero {channel}; on {channel}\r\n'.encode())

    def identity(self) -> str:
        # self._com.write(b'*IDN?\r\n')
        return self._getresponse_1l('*idn?')

    def help(self) -> str:
        print(self._com.help())

    def on(self, channel: int):
        """
        Locks the magnet in the stepper motor
        """
        self._com.write('on {0}\r\n'.format(channel).encode('ascii'))
        self._com.write('on {0}\r\n'.format(channel).encode('ascii'))

    def off(self, channel: int):
        """
        Unlocks the magnet in the stepper motor
        """
        self._com.write('off {0}\r\n'.format(channel).encode('ascii'))
        self._com.write('off {0}\r\n'.format(channel).encode('ascii'))


    def go(self, channel: int, position: int):
        """
        Go to absolute position
        """
        self._com.write('go {0} {1}\r\n'.format(channel, position).encode('ascii'))
        self._com.write('go {0} {1}\r\n'.format(channel, position).encode('ascii'))

    # def set_voltage(self, channel, voltage):
    #     self._com.write('setvolt {0} {1};'.format(channel, voltage).encode('ascii'))

    def get_position(self, channel: int) -> int:
        # self._com.write('pos? {};'.format(channel).encode('ascii'))
        pos1 = int(self._com._getresponse_1l('pos?'))
        pos2 = int(self._com._getresponse_1l('pos?'))
        if pos1 == pos2:
            return pos2

    def zero(self, channel: int):
        """
        Sets current position as zero
        """
        self._com.write('zero {}\r\n'.format(channel).encode('ascii'))
        self._com.write('zero {}\r\n'.format(channel).encode('ascii'))

    def go_wait(self, channel: int, position: int):
        """
        Send the move command to the motor and polls the motor position
        until the motor reaches the desired position.

        :param position: desired position in steps
        """
        self.go(channel, position)
        while self.get_position(channel) != position:
            time.sleep(.005)
