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

    @staticmethod
    def _raise_if_oob(value, low, high, propname, propunits):
        """Raises ValueError if value is invalid / out of bounds (oob).

        Note:
            See `heater_voltage` notes for rationale behind input validation
            and exception used.
        """
        if not (isinstance(value, (int, float, np.number)) and low <= value <= high):
            raise ValueError(
                f"{propname} can only take values between [{low}, {high}] {propunits}"
            )

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

    def heater_loop_on(self):
        """Switches on the crystal heater temperature PID loop.

        Note:
            The `HLOOP 1` command is encapsulated within the `heater_loop_on()`
            subroutine, since it is usually compounded with the power command.
            See `heater_loop_off()`.
        """
        self._com.writeline("HLOOP 1")
        self._power_on_heater_peltier()

    def heater_loop_off(self):
        """Switches off the crystal heater temperature PID loop.

        Note:
            Heater voltage is automatically set to zero, which is not part of the
            device command set, and hence is implemented as a method instead of
            a `heater_loop` setter. This avoids the cognitive inconsistency
            between `heater_loop = 0` and `HLOOP 0`.

            Implemented because there is likely no use case
            for a voltage hold after PID is switched off, except for debugging.
        """
        self._com.writeline("HLOOP 0")  # holds voltage at current value
        self.heater_voltage = 0
        if not self.peltier_loop:  # switch off power only if peltier loop also off
            self._power_off_heater_peltier()

    @property
    def peltier_loop(self) -> int:
        return int(self._com.getresponse("PLOOP?"))

    def peltier_loop_on(self):
        """Switches on the laser peltier temperature PID loop.

        Note:
            See `heater_loop_on()`.
        """
        self._com.writeline("PLOOP 1")
        self._power_on_heater_peltier()

    def peltier_loop_off(self):
        """Switches off the laser peltier temperature PID loop.

        Note:
            See `peltier_loop_off()`.
        """
        self._com.writeline("PLOOP 0")  # holds voltage at current value
        self.peltier_voltage = 0
        if not self.heater_loop:  # switch off power only if heater loop also off
            self._power_off_heater_peltier()

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
        self._raise_if_oob(voltage, hlimit_low, hlimit_high, "Heater voltage", "V")
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
        """
        plimit = self.peltier_voltage_limit
        self._raise_if_oob(voltage, -plimit, plimit, "Peltier voltage", "V")
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
        """
        hlimit_low, hlimit_high = 0, 10  # hardcoded based on firmware
        self._raise_if_oob(
            voltage, hlimit_low, hlimit_high, "Heater voltage limit", "V"
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
        """
        plimit_low, plimit_high = 0, 2.5  # hardcoded based on firmware
        self._raise_if_oob(
            voltage, plimit_low, plimit_high, "Peltier voltage limit", "V"
        )
        self._com.writeline(f"PLIMIT {voltage:.3f}")

    @property
    def heater_temp(self) -> float:
        """Measures the instantaneous temperature near the crystal."""
        return float(self._com.getresponse("HTEMP?"))

    @heater_temp.setter
    def heater_temp(self, temp: float):
        """Alias for `heater_temp_setpoint` setter, temp in Celsius."""
        self.heater_temp_setpoint = temp

    @property
    def heater_temp_setpoint(self) -> float:
        return float(self._com.getresponse("HSETTEMP?"))

    @heater_temp_setpoint.setter
    def heater_temp_setpoint(self, temp: float) -> None:
        """Sets the target temperature of the crystal, in Celsius.

        Raises:
            ValueError: `temp` is not a valid number.
        """
        htemp_low, htemp_high = 20, 100  # hardcoded based on firmware
        self._raise_if_oob(temp, htemp_low, htemp_high, "Heater temp setpoint", "°C")
        self._com.writeline(f"HSETTEMP {temp:.3f}")

    @property
    def heater_temp_rate(self) -> float:
        return float(self._com.getresponse("HRATE?"))

    @heater_temp_rate.setter
    def heater_temp_rate(self, rate: float) -> None:
        """Sets the heater temperature ramp rate, in K/s.

        Two separate and distinct heating profiles are used depending on the
        value of `rate`. If `rate` is set at 0, the change in heater temp setpoint
        will be instantaneous. Otherwise, the heater setpoint will ramp up/down
        linearly, starting from the previous value when `rate` > 0.

        Raises:
            ValueError: `rate` is not a valid number.
        Note:
            Strongly related to `heater_temp_target`, which determines the
            instantaneous time-varying heater setpoint.
        """
        hrate_low, hrate_high = 0.0, 1.0  # hardcoded based on firmware
        self._raise_if_oob(rate, hrate_low, hrate_high, "Heater temp ramp", "K/s")
        self._com.writeline(f"HRATE {rate:.3f}")

    @property
    def heater_temp_target(self) -> float:
        return float(self._com.getresponse("HTARGET?"))

    @property
    def peltier_temp(self) -> float:
        """Measures the instantaneous temperature near the laser."""
        return float(self._com.getresponse("PTEMP?"))

    @peltier_temp.setter
    def peltier_temp(self, temp: float):
        """Alias for `peltier_temp_setpoint` setter, temp in Celsius."""
        self.peltier_temp_setpoint = temp

    @property
    def peltier_temp_setpoint(self) -> float:
        return float(self._com.getresponse("PSETTEMP?"))

    @peltier_temp_setpoint.setter
    def peltier_temp_setpoint(self, temp: float) -> None:
        """Sets the target temperature of the laser, in Celsius.

        Raises:
            ValueError: `temp` is not a valid number.
        """
        ptemp_low, ptemp_high = 20, 50  # hardcoded based on firmware
        self._raise_if_oob(temp, ptemp_low, ptemp_high, "Peltier temp setpoint", "°C")
        self._com.writeline(f"PSETTEMP {temp:.3f}")

    @property
    def hconstp(self) -> float:
        return float(self._com.getresponse("HCONSTP?"))

    @hconstp.setter
    def hconstp(self, constant: float) -> None:
        """Sets the proportional control constant for crystal heater, in V/K."""
        hconstp_low, hconstp_high = 0, 10  # hardcoded based on firmware
        self._raise_if_oob(
            constant, hconstp_low, hconstp_high, "Heater P constant", "V/K"
        )
        self._com.writeline(f"HCONSTP {constant:.3f}")

    @property
    def hconsti(self) -> float:
        return float(self._com.getresponse("HCONSTI?"))

    @hconsti.setter
    def hconsti(self, constant: float) -> None:
        """Sets the integral control constant for crystal heater, in V/(Ks)."""
        hconsti_low, hconsti_high = 0, 10  # hardcoded based on firmware
        self._raise_if_oob(
            constant, hconsti_low, hconsti_high, "Heater I constant", "V/(Ks)"
        )
        self._com.writeline(f"HCONSTI {constant:.3f}")

    @property
    def hconstd(self) -> float:
        return float(self._com.getresponse("HCONSTD?"))

    @hconstd.setter
    def hconstd(self, constant: float) -> None:
        """Sets the derivative control constant for crystal heater, in Vs/K."""
        hconstd_low, hconstd_high = 0, 10  # hardcoded based on firmware
        self._raise_if_oob(
            constant, hconstd_low, hconstd_high, "Heater D constant", "Vs/K"
        )
        self._com.writeline(f"HCONSTD {constant:.3f}")

    @property
    def pconstp(self) -> float:
        return float(self._com.getresponse("PCONSTP?"))

    @pconstp.setter
    def pconstp(self, constant: float) -> None:
        """Sets the proportional control constant for laser peltier, in V/K."""
        pconstp_low, pconstp_high = 0, 10  # hardcoded based on firmware
        self._raise_if_oob(
            constant, pconstp_low, pconstp_high, "Peltier P constant", "V/K"
        )
        self._com.writeline(f"PCONSTP {constant:.3f}")

    @property
    def pconsti(self) -> float:
        return float(self._com.getresponse("PCONSTI?"))

    @pconsti.setter
    def pconsti(self, constant: float) -> None:
        """Sets the integral control constant for laser peltier, in V/(Ks)."""
        pconsti_low, pconsti_high = 0, 10  # hardcoded based on firmware
        self._raise_if_oob(
            constant, pconsti_low, pconsti_high, "Peltier I constant", "V/(Ks)"
        )
        self._com.writeline(f"PCONSTI {constant:.3f}")

    @property
    def pconstd(self) -> float:
        return float(self._com.getresponse("PCONSTD?"))

    @pconstd.setter
    def pconstd(self, constant: float) -> None:
        """Sets the derivative control constant for laser peltier, in Vs/K."""
        pconstd_low, pconstd_high = 0, 10  # hardcoded based on firmware
        self._raise_if_oob(
            constant, pconstd_low, pconstd_high, "Peltier D constant", "Vs/K"
        )
        self._com.writeline(f"PCONSTD {constant:.3f}")

    @property
    def laser_current(self) -> float:
        return float(self._com.getresponse("LCURRENT?"))

    @laser_current.setter
    def laser_current(self, current: float) -> None:
        """Sets the laser current, in mA.

        Note that `SPDCDriver.power` needs to be 1 or 3 for lasing to begin.

        Raises:
            ValueError: `current` is not a valid number.
        """
        lcurrent_low, lcurrent_high = 0, self.laser_current_limit
        self._raise_if_oob(current, lcurrent_low, lcurrent_high, "Laser current", "mA")
        self._com.writeline(f"LCURRENT {current:.3f}")

    @property
    def laser_current_limit(self) -> float:
        return float(self._com.getresponse("LLIMIT?"))

    @laser_current_limit.setter
    def laser_current_limit(self, current: float) -> None:
        """Sets the laser current limit, in mA.

        Raises:
            ValueError: `current` is not a valid number.
        """
        llimit_low, llimit_high = 0, 97  # hardcoded based on firmware
        self._raise_if_oob(
            current, llimit_low, llimit_high, "Laser current limit", "mA"
        )
        self._com.writeline(f"LLIMIT {current:.3f}")

    def laser_on(self, current: float):
        """Switches on laser.

        The lasing current ramp used is 1mA/50ms.

        Raises:
            ValueError: `current` is not a valid number.
            RuntimeError: Laser is already switched on.
        Note:
            The `ON` command are encapsulated within `laser_on()` instead of
            provisioning a standalone command, to prevent accidental laser
            delivery while it is switched off. Use case of `ON` is almost
            always tied to a laser ramp up.
        """
        lcurrent_low, lcurrent_high = 0, self.laser_current_limit
        self._raise_if_oob(current, lcurrent_low, lcurrent_high, "Laser current", "mA")
        if self.laser_current != 0:
            raise RuntimeError(
                "Laser is already switched on - use `SPDCDriver.laser_current` to"
                "change the current"
            )

        # Switch on laser only, ignoring heater/peltier
        self._power_on_laser()
        self._com.writeline("ON")

        # Ramp laser current
        for c in np.arange(0, current, 1):
            self.laser_current = c
            time.sleep(0.05)  # ~5 seconds
        self.laser_current = current  # target current

    def laser_off(self):
        """Switches off the laser."""
        # Ramp laser current
        for c in np.arange(self.laser_current, 0, -1):
            self.laser_current = c
            time.sleep(0.05)
        self.laser_current = 0

        # Switch off laser only, ignoring heater/peltier
        self._com.writeline("OFF")
        self._power_off_laser()

    @property
    def power(self) -> int:
        return int(self._com.getresponse("POWER?"))

    @power.setter
    def power(self, value: int) -> None:
        """Sets power converter enable lines on board.

        Args:
            value: Takes the following integer values,
                0 (0b00) - all lines disabled
                1 (0b01) - enable heater/peltier power lines only
                2 (0b10) - enable laser power lines only
                3 (0b11) - all lines enabled
        Raises:
            ValueError: value is not a valid number.
        """
        if not (isinstance(value, (int, np.integer)) and 0 <= value <= 3):
            raise ValueError("Power can only take integer values (0, 1, 2, 3)")
        self._com.writeline(f"POWER {value}")

    def _power_on_heater_peltier(self) -> None:
        self.power = {0: 2, 1: 3, 2: 2, 3: 3}[self.power]

    def _power_off_heater_peltier(self) -> None:
        self.power = {0: 0, 1: 1, 2: 0, 3: 1}[self.power]

    def _power_on_laser(self) -> None:
        self.power = {0: 1, 1: 1, 2: 3, 3: 3}[self.power]

    def _power_off_laser(self) -> None:
        self.power = {0: 0, 1: 0, 2: 2, 3: 2}[self.power]
