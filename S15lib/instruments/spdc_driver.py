"""
Created on Mon Feb 9 2020
by Mathias Seidler
"""


from . import serial_connection
import time
import numpy as np


class SPDCDriver(object):
    """Module for communicating with the power meter"""

    DEVICE_IDENTIFIER = 'SPDC driver'

    def __init__(self, device_path: str=''):
        # if no path is indicated it tries to init the first power_meter device
        if device_path == '':
            device_path = (serial_connection.search_for_serial_devices(
                self.DEVICE_IDENTIFIER))[0]
            print('Connected to', device_path)
        self._com = serial_connection.SerialConnection(device_path)
        time.sleep(0.05)
        self.identity
        time.sleep(0.05)
        self.identity

    def reset(self):
        '''Resets the device.

        Returns:
            str -- Response of the device after.
        '''
        return self._com.write(b'*RST')

    def heater_loop_on(self):
        self._com.write(b'HLOOP 1\n')

    def heater_loop_off(self):
        self._com.write(b'HLOOP 0\n')

    def peltier_loop_on(self):
        self._com.write(b'PLOOP 1\n')

    def peltier_loop_off(self):
        self._com.write(b'PLOOP 0\n')

    @property
    def peltier_loop(self) -> float:
        return int(self._com._getresponse_1l('PLOOP?'))

    @property
    def heater_loop(self):
        return int(self._com._getresponse_1l('HLOOP?'))

    @property
    def laser_current(self) -> float:
        assert type(self._com) is serial_connection.SerialConnection
        return float(self._com._getresponse_1l('lcurrent?'))

    @laser_current.setter
    def laser_current(self, current: int):
        assert type(self._com) is serial_connection.SerialConnection and (
            type(current) is float or type(current) is int)
        cmd = ('lcurrent {}\n'.format(current)).encode()
        self._com.write(cmd)
        msg = self._com.readlines()
        if msg != []:
        	print(msg)

    def laser_on(self, current: int):
        if self.laser_current == 0:
            self.peltier_temp = 25
            self._com.write(b'LCURRENT 0\n')
            cmd = 'on\n'.encode()
            self._com.write(b'on\n')
            # laser current ramp
            for i in range(1, current + 1):
                cmd = ('LCURRENT {}\n'.format(i)).encode()
                self._com.write(cmd)
                time.sleep(0.05)
        else:
            print('Laser is on already.')

    def laser_off(self):
        if self.laser_current != 0:
            for i in range(int(self.laser_current), -1, -1):
                cmd = ('LCURRENT {}\n'.format(i)).encode()
                # print(cmd)
                self._com.write(cmd)
                time.sleep(0.05)
        self._com.write('off\n'.encode())

    @property
    def heater_temp(self) -> float:
        """Returns the temperature at the crystal.

        Returns:
            number -- Temperature at the crystal
        """
        assert type(self._com) is serial_connection.SerialConnection
        return float(self._com._getresponse_1l('HTEMP?'))

    @heater_temp.setter
    def heater_temp(self, temperature: float):
        '''Sets the temperature of the crystal heater


        Decorators:
                heater_temp.setter

        Arguments:
                temperature {float} -- set point for the heater temperature
        '''
        assert type(self._com) is serial_connection.SerialConnection
        # cmd_setPID = b'HCONSTP 0.13;HCONSTI 0.008\n'
        # self._com.write(cmd_setPID)
        now_temp = self.heater_temp
        # cmd = ('HSETTEMP {}\n'.format(now_temp)).encode()
        # self.heater_loop_on()
        if now_temp < temperature:
            for t in range(int(now_temp) + 1, int(temperature) + 1):
                cmd = ('HSETTEMP {}\n'.format(t)).encode()
                print(cmd)
                self._com.write(cmd)
                time.sleep(6)
        else:
            cmd = ('HSETTEMP {}\n'.format(temperature)).encode()
            print('lowering temp', cmd)
            self._com.write(cmd)

    @property
    def peltier_temp(self) -> float:
        """Measures the temperature close to the peltier, where the laser diode is cooled.

        Returns:
            number -- Current temperature of the peltier temp
        """
        assert type(self._com) is serial_connection.SerialConnection
        return float(self._com._getresponse_1l('PTEMP?'))

    @peltier_temp.setter
    def peltier_temp(self, temperature: float):
        assert temperature > 20 and temperature < 50
        assert type(self._com) is serial_connection.SerialConnection
        assert type(temperature) is float or type(temperature) is int
        # cmd_setPID = b'PCONSTP 0.1;PCONSTI 0.03\r\n'
        # self._com.write(cmd_setPID)
        cmd = ('PSETTEMP {}\r\n'.format(temperature)).encode()
        self._com.write(cmd)
        self.peltier_loop_on()  # switch feedback loop on

    @property
    def peltier_temp_setpoint(self) -> float:
        return float(self._com._getresponse_1l('psettemp?'))

    @property
    def heater_temp_setpoint(self) -> float:
        return float(self._com._getresponse_1l('hsettemp?'))

    @property
    def identity(self):
        return self._com._getresponse_1l('*idn?')

    def help(self):
        return self._com.help()

    def save_settings(self) -> str:
        return self._com._getresponse_1l('save')

    @property
    def pconstp(self) -> float:
        return float(self._com._getresponse_1l('pconstp?'))

    @pconstp.setter
    def pconstp(self, value) -> float:
        cmd = f'pconstp {value}\r\n'.encode()
        return self._com.write(cmd)

    @property
    def pconsti(self) -> float:
        return float(self._com._getresponse_1l('pconsti?'))

    @pconsti.setter
    def pconsti(self, value) -> float:
        cmd = f'pconsti {value}\r\n'.encode()
        return self._com.write(cmd)

    @property
    def hconstp(self) -> float:
        return float(self._com._getresponse_1l('hconstp?'))

    @hconstp.setter
    def hconstp(self, value: float) -> float:
        cmd = f'hconstp {value}\r\n'.encode()
        return self._com.write(cmd)

    @property
    def hconsti(self) -> float:
        return float(self._com._getresponse_1l('hconsti?'))

    @hconsti.setter
    def hconsti(self, value: float) -> float:
        cmd = f'hconsti {value}\r\n'.encode()
        return self._com.write(cmd)

    @property
    def laser_current_limit(self) -> float:
        return float(self._com._getresponse_1l('llimit?'))

    @laser_current_limit.setter
    def laser_current_limit(self, value: float) -> float:
        cmd = f'llimit {value}\r\n'.encode()
        return self._com.write(cmd)



if __name__ == '__main__':
    spdc_driver = SPDCDriver()
    start = time.time()
    print(spdc_driver.heater_temp)
    Dt = time.time() - start

    print("Waktu {}".format(Dt))
