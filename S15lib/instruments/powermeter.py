"""
Created on Mon Feb 9 2020
by Mathias Seidler
"""

import glob
from . import serial_connection
import time
import numpy as np
from typing import Tuple


"""
Responsivity (A/W) table for Hamamatsu S5107.
"""
wl = [351.1, 390.0, 404., 405., 425., 532., 632.8,
      660., 702., 761., 770., 776., 780., 795.,
      808., 810., 850., 1064.]

eff = [0.149, 0.156, 0.1753, 0.1766, 0.1991, 0.3198, 0.4376,
       0.4681, 0.5131, 0.5718, 0.5802, 0.5863, 0.59, 0.6027,
       0.6155, 0.6179, 0.6508, 0.3519]

eff_err = [0.002682, 0.003588, 0.00154264, 0.00155408, 0.00109505,
           0.00153504, 0.00188168, 0.00182559, 0.0020524, 0.00268746,
           0.00237882, 0.0023452, 0.002419, 0.00265188, 0.0025851,
           0.00259518, 0.00247304, 0.0063342]

"""
Responsivity (A/W) table for Thorlabs FDG50, which is a germanium photo diode.
This table was provided by Thorlabs and represents typical values.
These values can vary slightly as they depend on reverse bias voltage, temperature, and production lot.
"""
wl_FDG50 = [800., 810., 820., 830., 840., 850., 860., 870., 880.,
            890., 900., 910., 920., 930., 940., 950., 960., 970.,
            980., 990., 1000., 1010., 1020., 1030., 1040., 1050., 1060.,
            1070., 1080., 1090., 1100., 1110., 1120., 1130., 1140., 1150.,
            1160., 1170., 1180., 1190., 1200., 1210., 1220., 1230., 1240.,
            1250., 1260., 1270., 1280., 1290., 1300., 1310., 1320., 1330.,
            1340., 1350., 1360., 1370., 1380., 1390., 1400., 1410., 1420.,
            1430., 1440., 1450., 1460., 1470., 1480., 1490., 1500., 1510.,
            1520., 1530., 1540., 1550., 1560., 1570., 1580., 1590., 1600.,
            1610., 1620., 1630., 1640., 1650., 1660., 1670., 1680., 1690.,
            1700., 1710., 1720., 1730., 1740., 1750., 1760., 1770., 1780.,
            1790., 1800.]

responsivity_FDG50 = [0.22508, 0.24665, 0.26523, 0.26213, 0.26513, 0.27525, 0.29272,
                      0.30612, 0.29395, 0.29197, 0.31639, 0.34314, 0.33874, 0.35345,
                      0.36875, 0.375, 0.3837, 0.39427, 0.41518, 0.42412, 0.43576,
                      0.43922, 0.45196, 0.46431, 0.4764, 0.48833, 0.49845, 0.51611,
                      0.52045, 0.5321, 0.54247, 0.54571, 0.55472, 0.5618, 0.56882,
                      0.5811, 0.58872, 0.60078, 0.60694, 0.6187, 0.62561, 0.63318,
                      0.64138, 0.64911, 0.65293, 0.65686, 0.66692, 0.67623, 0.68537,
                      0.69418, 0.71071, 0.70957, 0.71724, 0.72821, 0.72881, 0.73514,
                      0.73725, 0.70826, 0.74667, 0.72364, 0.74545, 0.75398, 0.76239,
                      0.78291, 0.78974, 0.8, 0.82617, 0.81905, 0.82667, 0.83774,
                      0.84074, 0.85138, 0.85405, 0.87207, 0.87857, 0.87788, 0.86667,
                      0.8386, 0.78947, 0.7193, 0.64561, 0.59115, 0.54513, 0.51071,
                      0.48288, 0.45018, 0.42606, 0.40636, 0.37981, 0.35736, 0.33524,
                      0.31423, 0.29608, 0.2788, 0.25818, 0.24016, 0.22004, 0.20042,
                      0.18139, 0.16173, 0.14279]


def volt2power_HamamatsuS5107(volt: float, wave_length: float, resistance: float) -> float:
    alpha = np.interp(wave_length, wl, eff)
    return volt / resistance / alpha


def volt2power_FDG50(volt: float, wave_length: float, resistance: float) -> float:
    '''
    Voltage to optical power conversion for Thorlabs FDG50
    '''
    alpha = np.interp(wave_length, wl_FDG50, responsivity_FDG50)
    return volt / resistance / alpha


class PowerMeter():
    """Module to use the power meter"""

    DEVICE_IDENTIFIER = 'OPM'

    def __init__(self, device_path: str='', resistors: list=[1e6, 1 / (1 / 110e3 + 1 / 1e6), 10e3, 1e3, 20]):
        # if no path is indicated it tries to init the first power_meter device
        self._resistors = resistors
        if device_path == '':
            device_path = (serial_connection.search_for_serial_devices(
                self.DEVICE_IDENTIFIER))[0]
            print('Connected to', device_path)
        self._device_path = device_path
        self._com = serial_connection.SerialConnection(device_path)
        self._identity = self._com.getresponse('*idn?')
        # check for diode type in the device identifier
        if 'OPMGE' in self._identity:
        	self._volt2power = volt2power_FDG50
        elif 'OPM' in self._identity:
        	self._volt2power = volt2power_HamamatsuS5107


    def reset(self):
        '''Resets the device.

        Returns:
            str -- Response of the device after.
        '''
        return self._com.getresponse(b'*RST')

    def get_voltage(self):
        """Returns the voltage accross the resistor.

        Returns:
            number -- Voltage in V
        """
        assert type(self._com) is serial_connection.SerialConnection
        return float(self._com.getresponse('VOLT?'))

    def get_power(self, wave_length: int) -> float:
        """Get optical power (Watts).

        It automatically selects the correct range.

        Keyword Arguments:
            wave_length {number} -- Wave length of the light in nm

        Returns:
            (number) -- optical power in Watt

        Raises:
            Exception -- Raises an exception when the optical power is higher than the device can measure (A higher resistor may be necessary).
        """
        assert wave_length > 350 and wave_length < 1801
        volt = 0
        range = self.range
        while True:
            volt = self.get_voltage()
            if volt > 2.45:
                if range == 5:
                    raise Exception('Optical power out of range')
                else:
                    self.range = range = range + 1
            elif volt < 0.01:
                if range == 1:
                    break
                else:
                    self.range = range = range - 1
            else:
                break
        return self._volt2power(volt, wave_length, self._resistors[range - 1])

    def get_avg_power(self, wave_length: float, samples: int=10) -> Tuple[float, float]:
        """Returns the mean and the standard deviation of the optical power
            after sampling it for "samples" times.

        Keyword Arguments:
            samples (number) -- number of samples to average from (default: 10)
            wave_length (number) -- wave length of the light in nm 

        Returns:
            (number, number) -- mean and standard deviation of optical power
        """
        avg_value = []
        for _ in range(samples):
            avg_value.append(self.get_power(wave_length))
        return np.mean(avg_value), np.std(avg_value)

    @property
    def range(self) -> int:
        return int(self._com.getresponse('RANGE?'))

    @range.setter
    def range(self, value: int):
        cmd = ('RANGE {}\n'.format(value)).encode()
        self._com.write(cmd)

    @property
    def identity(self) -> str:
        return self._identity


    def help(self) -> str:
        return self._com.help()


if __name__ == '__main__':
    powermeter = PowerMeter()
    start = time.time()
    print(powermeter.get_voltage())
    Dt = time.time() - start

    print("Waktu {}".format(Dt))
