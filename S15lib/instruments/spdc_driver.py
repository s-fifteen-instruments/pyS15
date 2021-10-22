"""
TODO:
    Resolve the following bug in the firmware:
    >>> spdc.heater_voltage_limit = 3
    >>> spdc.heater_voltage = 2
    >>> spdc.heater_voltage_limit = 1
    >>> spdc.heater_voltage  # expected: 1.0
    2.0

    This in contrast to laser current:
    >>> spdc.laser_current_limit = 3
    >>> spdc.laser_current = 2
    >>> spdc.laser_current_limit = 1
    >>> spdc.laser_current  # expected: ~1.0
    0.952

    Bug occurs for peltier_voltage as well, independent on POWER setting.
    This bug does not occur with peltier/heater loops on.
"""

import time

import numpy as np  # for type checking with numpy types

from .serial_connection import SerialConnection


class SPDCDriver(object):
    """Python wrapper to communcate with SPDC board."""

    DEVICE_IDENTIFIER = "SPDC driver"

    def __init__(self, device_path: str = ""):
        if device_path == "":
            self._com = SerialConnection.connect_by_name(self.DEVICE_IDENTIFIER)
        else:
            self._com = SerialConnection(device_path)

    def help(self) -> None:
        self._com.print_help()

    @property
    def identity(self) -> str:
        return self._com.get_identity()

    def reset(self) -> None:
        """Resets the device."""
        self._com.writeline("*RST")

    def save_settings(self) -> str:
        """Save device settings into storage.

        Returns:
            Success message if save is successful.
        Note:
            Saving of settings typically take longer than 100ms. One second is a
            reasonable upper bound.
        """
        return self._com.getresponse("SAVE", timeout=1)

    def close(self) -> None:
        """Close connection to device."""
        self._com.close()

    @property
    def heater_loop(self) -> int:
        return int(self._com.getresponse("HLOOP?"))

    @heater_loop.setter
    def heater_loop(self, value: int):
        """Sets heater/crystal temperature loop (HLOOP) on/off.

        Heater voltage is automatically set to zero, which is not part of the
        device command set. Implemented because there is almost zero use case
        for a voltage hold after PID is switched off, except for debugging.
        Recommended to combine with `heater_voltage = 0` in scripts for visual
        consistency.

        Args:
            value: 0 to switch off, otherwise non-0 to switch on loop.
        Raises:
            ValueError: value is not a valid number.
        Note:
            See `heater_voltage` for rationale behind exception used.
        """
        if not isinstance(value, (int, np.integer)):
            raise ValueError(
                "Heater loop can only take integer values - "
                "off (value=0) or on (value!=0)."
            )
        if value == 0:
            self._com.writeline("HLOOP 0")  # holds HVOLT at current value
            self._com.writeline("HVOLT 0")
        else:  # value != 0
            self._com.writeline("HLOOP 1")

    @property
    def peltier_loop(self) -> int:
        return int(self._com.getresponse("PLOOP?"))

    @peltier_loop.setter
    def peltier_loop(self, value: int):
        """Sets peltier/laser temperature loop (PLOOP) on/off.

        Peltier voltage is automatically set to zero, which is not part of the
        device command set. Implemented because there is almost zero use case
        for a voltage hold after PID is switched off, except for debugging.
        Recommended to combine with `peltier_voltage = 0` in scripts for visual
        consistency.

        Args:
            value: 0 to switch off, otherwise non-0 to switch on loop.
        Raises:
            ValueError: value is not an integer.
        Note:
            See `heater_voltage` for rationale behind exception used.
        """
        if not isinstance(value, (int, np.integer)):
            raise ValueError(
                "Peltier loop can only take integer values - "
                "off (value=0) or on (value!=0)."
            )
        if value == 0:
            self._com.writeline("PLOOP 0")  # holds PVOLT at current value
            self._com.writeline("PVOLT 0")
        else:  # value != 0
            self._com.writeline("PLOOP 1")

    @property
    def heater_voltage(self) -> float:
        return float(self._com.getresponse("HVOLT?"))

    @heater_voltage.setter
    def heater_voltage(self, voltage: float) -> None:
        """Sets voltage across crystal heater, in volts.

        The set voltage should be non-negative and less than or equal to
        `heater_voltage_limit`.

        Raises:
            ValueError: `voltage` is not a valid number.
        Note:
            Outside of the allowable range, the driver itself will return an
            error message, otherwise there is no return value. This leaves
            three implementation options for the return value:

              - Allow the setter to forward the wrong command, and raise a
                ValueError if there is a device response. This incurs an additional
                read timeout for successful commands with no device response.
              - Allow the setter to fail silently (ignore response). This shaves
                off read timeout due to pre-emptive clearing of buffer, but
                users are left unaware of the failure unless explicitly checked.
              - Enforce the setter to check for bounding values from the get-go.
                Requires an additional attribute query, but shaves off the timeout
                as well. Risks hardcoding outdated values when firmware changes.

            At the moment the last option is preferable due to the mix of explicit
            failure and input sanitization. Replacing TypeError with ValueError
            to minimize the possible exceptions raised.
        """
        hlimit_low, hlimit_high = 0, self.heater_voltage_limit
        if not (
            isinstance(voltage, (int, float, np.number))
            and hlimit_low <= voltage <= hlimit_high
        ):
            raise ValueError(
                "Heater voltage can only take values between "
                + f"[{hlimit_low}, {hlimit_high}] V"
            )
        self._com.writeline(f"HVOLT {voltage:.3f}")

    @property
    def peltier_voltage(self) -> float:
        return float(self._com.getresponse("PVOLT?"))

    @peltier_voltage.setter
    def peltier_voltage(self, voltage: float) -> None:
        """Sets voltage across laser peltier, in volts.

        The set voltage should have magnitude less than or equal to
        `peltier_voltage_limit`.

        Raises:
            ValueError: `voltage` is not a valid number.
        Note:
            See `heater_voltage` notes for rationale behind input validation.
        """
        plimit = self.peltier_voltage_limit
        if not (
            isinstance(voltage, (int, float, np.number))
            and -plimit <= voltage <= plimit
        ):
            raise ValueError(
                "Peltier voltage can only take values between "
                + f"[{-plimit}, {plimit}] V"
            )
        self._com.writeline(f"PVOLT {voltage:.3f}")

    @property
    def heater_voltage_limit(self) -> float:
        return float(self._com.getresponse("HLIMIT?"))

    @heater_voltage_limit.setter
    def heater_voltage_limit(self, voltage: float) -> None:
        """Sets the crystal heater voltage limit, in volts.

        The voltage limit should be within [0, 10] V.

        Raises:
            ValueError: `voltage` is not a valid number.
        Note:
            See `heater_voltage` notes for rationale behind input validation.
        """
        hlimit_low, hlimit_high = 0, 10  # hardcoded based on firmware
        if not (
            isinstance(voltage, (int, float, np.number))
            and hlimit_low <= voltage <= hlimit_high
        ):
            raise ValueError(
                "Heater voltage limit can only take values between "
                + f"[{hlimit_low}, {hlimit_high}] V"
            )
        self._com.writeline(f"HLIMIT {voltage:.3f}")

    @property
    def peltier_voltage_limit(self) -> float:
        return float(self._com.getresponse("PLIMIT?"))

    @peltier_voltage_limit.setter
    def peltier_voltage_limit(self, voltage: float) -> None:
        """Sets the laser peltier voltage limit, in volts.

        Raises:
            ValueError: `voltage` is not a valid number.
        Note:
            See `heater_voltage` notes for rationale behind input validation.
        """
        plimit_low, plimit_high = 0, 2.5  # hardcoded based on firmware
        if not (
            isinstance(voltage, (int, float, np.number))
            and plimit_low <= voltage <= plimit_high
        ):
            raise ValueError(
                "Peltier voltage limit can only take values between "
                + f"[{plimit_low}, {plimit_high}] V"
            )
        self._com.writeline(f"PLIMIT {voltage:.3f}")

    @property
    def heater_temp(self) -> float:
        """Measures the instantaneous temperature near the crystal."""
        return float(self._com.getresponse("HTEMP?"))

    @heater_temp.setter
    def heater_temp(self, temperature: float):
        """Alias for `heater_temp_setpoint` setter, temperature in Celsius."""
        self.heater_temp_setpoint = temperature

    @property
    def heater_temp_setpoint(self) -> float:
        return float(self._com.getresponse("HSETTEMP?"))

    @heater_temp_setpoint.setter
    def heater_temp_setpoint(self, temperature: float) -> None:
        """Sets the target temperature of the crystal, in Celsius.

        Raises:
            ValueError: `temperature` is not a valid number.
        Note:
            See `heater_voltage` notes for rationale behind input validation.
        """
        htemp_low, htemp_high = 20, 100  # hardcoded based on firmware
        if not (
            isinstance(temperature, (int, float, np.number))
            and htemp_low <= temperature <= htemp_high
        ):
            raise ValueError(
                "Heater temperature setpoint can only take values between "
                + f"[{htemp_low}, {htemp_high}] °C"
            )
        self._com.writeline(f"HSETTEMP {temperature:.3f}")

    @property
    def peltier_temp(self) -> float:
        """Measures the instantaneous temperature near the laser."""
        return float(self._com.getresponse("PTEMP?"))

    @peltier_temp.setter
    def peltier_temp(self, temperature: float):
        """Alias for `peltier_temp_setpoint` setter, temperature in Celsius."""
        self.peltier_temp_setpoint = temperature

    @property
    def peltier_temp_setpoint(self) -> float:
        return float(self._com.getresponse("PSETTEMP?"))

    @peltier_temp_setpoint.setter
    def peltier_temp_setpoint(self, temperature: float) -> None:
        """Sets the target temperature of the laser, in Celsius.

        Raises:
            ValueError: `temperature` is not a valid number.
        Note:
            See `heater_voltage` notes for rationale behind input validation.
        """
        ptemp_low, ptemp_high = 20, 50  # hardcoded based on firmware
        if not (
            isinstance(temperature, (int, float, np.number))
            and ptemp_low <= temperature <= ptemp_high
        ):
            raise ValueError(
                "Peltier temperature setpoint can only take values between "
                + f"[{ptemp_low}, {ptemp_high}] °C"
            )
        self._com.writeline(f"PSETTEMP {temperature:.3f}")

    @property
    def pconstp(self) -> float:
        return float(self._com.getresponse("pconstp?"))

    @pconstp.setter
    def pconstp(self, value) -> float:
        cmd = "pconstp {}\r\n".format(value).encode()
        return self._com.write(cmd)

    @property
    def pconsti(self) -> float:
        return float(self._com.getresponse("pconsti?"))

    @pconsti.setter
    def pconsti(self, value) -> float:
        cmd = "pconsti {}\r\n".format(value).encode()
        return self._com.write(cmd)

    @property
    def hconstp(self) -> float:
        return float(self._com.getresponse("hconstp?"))

    @hconstp.setter
    def hconstp(self, value: float) -> float:
        cmd = "hconstp {}\r\n".format(value).encode()
        return self._com.write(cmd)

    @property
    def hconsti(self) -> float:
        return float(self._com.getresponse("hconsti?"))

    @hconsti.setter
    def hconsti(self, value: float) -> float:
        cmd = "hconsti {}\r\n".format(value).encode()
        return self._com.write(cmd)

    @property
    def laser_current(self) -> float:
        assert type(self._com) is SerialConnection
        return float(self._com.getresponse("lcurrent?"))

    @laser_current.setter
    def laser_current(self, current: int):
        assert type(self._com) is SerialConnection and (
            type(current) is float or type(current) is int
        )
        cmd = ("lcurrent {}\n".format(current)).encode()
        self._com.write(cmd)
        msg = self._com.readlines()
        if msg != []:
            print(msg)

    def laser_on(self, current: int):
        if self.laser_current == 0:
            self.peltier_temp = 25
            self._com.write(b"LCURRENT 0\n")
            cmd = "on\n".encode()
            self._com.write(b"on\n")
            # laser current ramp
            for i in range(1, current + 1):
                cmd = ("LCURRENT {}\n".format(i)).encode()
                self._com.write(cmd)
                time.sleep(0.05)
        else:
            print("Laser is on already.")

    def laser_off(self):
        if self.laser_current != 0:
            for i in range(int(self.laser_current), -1, -1):
                cmd = ("LCURRENT {}\n".format(i)).encode()
                # print(cmd)
                self._com.write(cmd)
                time.sleep(0.05)
        self._com.write("off\n".encode())

    @property
    def laser_current_limit(self) -> float:
        return float(self._com.getresponse("llimit?"))

    @laser_current_limit.setter
    def laser_current_limit(self, value: float) -> float:
        cmd = "llimit {}\r\n".format(value).encode()
        return self._com.write(cmd)
