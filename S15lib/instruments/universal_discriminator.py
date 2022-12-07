"""
Created on 5th Dec 2022
"""

import time
from typing import Tuple

import numpy as np

from . import serial_connection


class UniversalDiscriminator:
    """Module to use the power meter"""

    DEVICE_IDENTIFIER = "UD"

    def __init__(
        self,
        device_path: str = "",
    ):
        # if no path is indicated it tries to init the first power_meter device
        if device_path == "":
            device_path = (
                serial_connection.search_for_serial_devices(self.DEVICE_IDENTIFIER)
            )[0]
            print("Connected to", device_path)
        self._device_path = device_path
        self._com = serial_connection.SerialConnection(device_path)
        self._identity = self._com.getresponse("*idn?")

    def reset(self):
        """Resets the device.

        Returns:
            str -- Response of the device after.
        """
        return self._com.getresponse(b"*RST")

    #    @property
    #    def inputthreshold(self):
    #        """
    #        Queries threshold from threshvolt register.
    #        """
    #        out = []
    #        full_range = 6.6
    #        offset = -3.3
    #        for ch in [0, 1]:
    #            cmd = ("CONFIG {}\n".format((ch) << 1)).encode()
    #            self._com.write(cmd)
    #            retval = self._com.getresponse(b"READW?")
    #            out.append(retval / (1 << 16) * full_range + offset)
    #
    #        return out
    #
    #    @inputthreshold.setter
    def inputthreshold(self, ch, vol):
        """
        Sets input polarity of channels 0 or 1.
        vol: -2 -> 2
        """
        cmd = ("THRESHOLD {} {}\n".format(ch, vol)).encode()
        self._com.write(cmd)

    #    @property
    #    def inputpolarity(self):
    #        """
    #        Queries polarity from config register.
    #        0: positive
    #        1: negative
    #        """
    #        out = []
    #        for ch in [0, 1]:
    #            cmd = ("CONFIG {}\n".format((ch + 2) << 4)).encode()
    #            self._com.write(cmd)
    #            retval = self._com.getresponse(b"READW?")
    #            out.append(retval & 0x1)
    #        return out
    #
    #    @inputpolarity.setter
    def inputpolarity(self, ch, pol):
        """
        Sets input polarity of channels 0 or 1.
        pol: 0 -> Positive
             1 -> Negative
        """
        cmd = ("POLARITY {} {}\n".format(ch, pol)).encode()
        self._com.write(cmd)

    #    @property
    #    def outputpolarity(self):
    #        """
    #        Queries polarity from config register.
    #        0: NIM on A and B
    #        1: TTL on A and NIM on B
    #        2: NIM on A and TTL on B
    #        3: TTL on A and B
    #        """
    #        out = []
    #        for ch in [0, 1]:
    #            cmd = ("CONFIG {}\n".format((ch + 2) << 4)).encode()
    #            self._com.write(cmd)
    #            retval = self._com.getresponse(b"READW?")
    #            (retval & 0x6) >> 1
    #        return out
    #
    #    @outputpolarity.setter
    def outputpolarity(self, ch, pol):
        """
        Sets output polarity of channels 0A/B or 1A/B.
        ch:
            0: 0A
            1: 1A
            2: 0B
            3: 1B
        pol:
            0: NIM
            1: TTL
        """
        cmd = ("OUTLEVEL {} {}\n".format(ch, pol)).encode()
        self._com.write(cmd)

    #    @property
    #    def outmode(self) -> int:
    #        """
    #        Queries outmode from config register.
    #        0: Direct discriminator output
    #        1: Combinatorical leading edge generation
    #        2: Triggered flip-flop with reset by delayed discriminator signal
    #        3: TBD
    #        """
    #        out = []
    #        for ch in [0, 1]:
    #            cmd = ("CONFIG {}\n".format((ch + 2) << 4)).encode()
    #            self._com.write(cmd)
    #            retval = self._com.getresponse(b"READW?")
    #            out.append((retval & 0x18) >> 3)
    #
    #        return out
    #
    #    @outmode.setter
    def outmode(self, ch, mode):
        """
        Sets output polarity of channels 0A/B or 1A/B.
        ch:
            0: 0A
            1: 1A
            2: 0B
            3: 1B
        mode:
            0: direct comparator
            1: logic differentiation
            2: set/reset output
            3: TBD.
        """
        cmd = ("OUTMODE {} {}\n".format(ch, mode)).encode()
        self._com.write(cmd)

    #    @property
    #    def inputdelay(self):
    #        """
    #        Queries delay from config register.
    #        """
    #        out = []
    #        for ch in [0, 1]:
    #            cmd = ("CONFIG {}\n".format((ch + 2) << 4)).encode()
    #            self._com.write(cmd)
    #            retval = self._com.getresponse(b"READW?")
    #            out.append((retval & 0x1F00) >> 8)
    #        return out
    #
    #    @inputdelay.setter
    def inputdelay(self, ch, delay):
        """
        Sets input delay of channels 0 or 1.
        delay: 0 --> 31
        """
        cmd = ("DELAY {} {}\n".format(ch, delay)).encode()
        self._com.write(cmd)

    @property
    def identity(self) -> str:
        return self._identity

    def help(self) -> str:
        print(self._com.get_help())
        return
