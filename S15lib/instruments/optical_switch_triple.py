#!/usr/bin/env python3

"""
Triple Optical Multiplexer

"""
from . import serial_connection

MAX_PULSE_DURATION = 255


class TripleOpticalSwitch:
    """Module to use the Triple Optical Switch"""

    DEVICE_IDENTIFIER = "OMX1"

    def __init__(
        self,
        device_path=None,
        connections: list = [],
    ):
        if device_path is None:
            device_path = (
                serial_connection.search_for_serial_devices(self.DEVICE_IDENTIFIER)
            )[0]
            print("Connected to", device_path)
        self._device_path = device_path
        self._com = serial_connection.SerialConnection(device_path)
        self._identity = self._com.getresponse("*idn?")

    @property
    def route(self) -> tuple:
        """
        Returns the settings on the switches
        """
        return (self.switch_0, self.switch_1, self.switch_2)

    @route.setter
    def route(self, path: tuple = (0, 0, 0)):
        """
        High level routing based on path.
        """
        self.switch_0, self.switch_1, self.switch_2 = path
        return

    """ CDC properties """

    @property
    def single(self) -> int:
        """
        Returns position value of switch 1 (0 or 1),
        or error condition -1 for both closed, -2 for both open.
        """
        return int(self.ask("SINGLE?"))

    @single.setter
    def single(self, value: int) -> None:
        """
        sets switch 1 to value (0 or 1).
        """
        if value == 0 or value == 1:
            self.write(f"SINGLE {value}")
        else:
            print("Illegal value")

    @property
    def switch_0(self) -> int:
        """
        Returns position value of switch 0 (0 or 1),
        or error condition -1 for both closed, -2 for both open.
        """
        return int(self.ask("SWITCH? 0"))

    @switch_0.setter
    def switch_0(self, value: int) -> None:
        """
        sets channel 0 to value (0 or 1).
        """
        if value == 0 or value == 1:
            self.write(f"SWITCH 0 {value}")
        else:
            print("Illegal value")

    @property
    def switch_1(self) -> int:
        """
        Returns position value of switch 1 (0 or 1),
        or error condition -1 for both closed, -2 for both open.
        """
        return int(self.ask("SWITCH? 1"))

    @switch_1.setter
    def switch_1(self, value: int) -> None:
        """
        sets channel 1 to value (0 or 1).
        """
        if value == 0 or value == 1:
            self.write(f"SWITCH 1 {value}")
        else:
            print("Illegal value")

    @property
    def switch_2(self) -> int:
        """
        Returns position value of switch 2 (0 or 1),
        or error condition -1 for both closed, -2 for both open.
        """
        return int(self.ask("SWITCH? 2"))

    @switch_2.setter
    def switch_2(self, value: int) -> None:
        """
        sets channel 2 to value (0 or 1).
        """
        if value == 0 or value == 1:
            self.write(f"SWITCH 2 {value}")
        else:
            print("Illegal value")

    @property
    def millisec(self) -> float:
        """
        returns duration of switch pulse in milliseconds
        """
        return float(self.ask("MILLISEC?"))

    @millisec.setter
    def millisec(self, value) -> None:
        """
        sets duration of switch pulse in milliseconds
        """
        if value <= MAX_PULSE_DURATION:
            self.write(f"MILLISEC {value}")
        else:
            raise ValueError(
                f"Input argument of duration {value} exceeds \
                Maximum pulse duration of {MAX_PULSE_DURATION}"
            )

    @property
    def config(self) -> int:
        """
        returns drive coil polarity configuration
        """
        return int(self.ask("CONFIG?"))

    @config.setter
    def config(self, value: int) -> None:
        """
        Sets the drive coil polarity configuration of each switch.
        Bits 0..2 correspond to switches 1..3.
        """
        if value <= 7:
            self.write(f"CONFIG {value}\n")
        else:
            raise ValueError(f"Input argument of config {value} is invalid!")

    def ask(self, txt: str) -> str:
        return self._com.getresponse(txt + "\n").strip()

    def write(self, txt: str) -> None:
        self._com.write((txt + "\n").encode())
