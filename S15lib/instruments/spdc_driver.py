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
            value: 0 to switch off, otherwise non-0 to switch on.
        Raises:
            TypeError: value is not an integer.
        """
        if not isinstance(value, (int, np.integer)):
            raise TypeError(
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
            value: 0 to switch off, otherwise non-0 to switch on.
        Raises:
            TypeError: value is not an integer.
        """
        if not isinstance(value, (int, np.integer)):
            raise TypeError(
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
    def heater_voltage(self, voltage: float):
        """Sets voltage across crystal heater.

        This value must be less than or equal to HLIMIT to take effect, otherwise the
        command will fail silently.

        Raises:
            TypeError: voltage is not a non-negative number
        """
        if not isinstance(voltage, (int, float, np.number)) or voltage < 0:
            raise TypeError("Heater voltage can only take non-negative values.")
        self._com.writeline(f"HVOLT {voltage:.3f}")

    @property
    def peltier_voltage(self) -> float:
        return float(self._com.getresponse("PVOLT?"))

    @peltier_voltage.setter
    def peltier_voltage(self, voltage: float):
        """Sets voltage across laser peltier.

        This value must be within [-PLIMIT, PLIMIT] to take effect, otherwise the
        command will fail silently.

        Raises:
            TypeError: voltage is not a number
        """
        if not isinstance(voltage, (int, float, np.number)):
            raise TypeError("Peltier voltage can only take real values.")
        self._com.writeline(f"PVOLT {voltage:.3f}")

    @property
    def heater_voltage_limit(self) -> float:
        return float(self._com.getresponse("HLIMIT?"))

    @heater_voltage_limit.setter
    def heater_voltage_limit(self, voltage: float) -> None:
        """Sets the crystal heater voltage limit.

        If voltage limit is out of allowable range, the device responds with
        an error message as feedback, otherwise no feedback is provided.
        The input buffer is cleared pre-emptively.

        Args:
            voltage: Heater voltage limit, in volts
        Raises:
            TypeError: voltage is not a non-negative number
        """
        if not isinstance(voltage, (int, float, np.number)) or voltage < 0:
            raise TypeError("Heater voltage limit can only take non-negative values.")
        self._com.getresponse(f"HLIMIT {voltage:.3f}")

    @property
    def peltier_voltage_limit(self) -> float:
        return float(self._com.getresponse("PLIMIT?"))

    @peltier_voltage_limit.setter
    def peltier_voltage_limit(self, voltage: float) -> None:
        """Sets the laser peltier voltage limit.

        If voltage limit is out of allowable range, the device responds with
        an error message as feedback, otherwise no feedback is provided.
        The input buffer is cleared pre-emptively.

        Args:
            voltage: Peltier voltage limit, in volts
        Raises:
            TypeError: voltage is not a non-negative number
        """
        if not isinstance(voltage, (int, float, np.number)) or voltage < 0:
            raise TypeError("Peltier voltage limit can only take non-negative values.")
        self._com.getresponse(f"PLIMIT {voltage:.3f}")

    @property
    def heater_temp(self) -> float:
        """Measures the instantaneous temperature near the crystal."""
        return float(self._com.getresponse("HTEMP?"))

    @heater_temp.setter
    def heater_temp(self, temperature: float):
        """Alias for @heater_temp_setpoint.setter."""
        self.heater_temp_setpoint = temperature

    @property
    def heater_temp_setpoint(self) -> float:
        return float(self._com.getresponse("HSETTEMP?"))

    @heater_temp_setpoint.setter
    def heater_temp_setpoint(self, temperature: float) -> None:
        """Sets the target temperature of the crystal.

        The temperature setpoint must be within [20,100] to take effect, otherwise the
        command will fail silently - the input buffer is cleared pre-emptively.

        Args:
            temperature: Setpoint for the crystal temperature
        """
        if not isinstance(temperature, (int, float, np.number)) or temperature < 0:
            raise TypeError("Heater setpoint can only take non-negative values.")
        self._com.getresponse(f"HSETTEMP {temperature:.3f}")

    @property
    def peltier_temp(self) -> float:
        """Measures the instantaneous temperature near the laser."""
        return float(self._com.getresponse("PTEMP?"))

    @peltier_temp.setter
    def peltier_temp(self, temperature: float):
        """Alias for @peltier_temp_setpoint.setter."""
        self.peltier_temp_setpoint = temperature

    @property
    def peltier_temp_setpoint(self) -> float:
        return float(self._com.getresponse("PSETTEMP?"))

    @peltier_temp_setpoint.setter
    def peltier_temp_setpoint(self, temperature: float) -> None:
        """Sets the target temperature of the laser.

        The temperature setpoint must be within [20,50] to take effect, otherwise the
        command will fail silently - the input buffer is cleared pre-emptively.

        Args:
            temperature: Setpoint for the laser temperature
        """
        if not isinstance(temperature, (int, float, np.number)) or temperature < 0:
            raise TypeError("Peltier setpoint can only take non-negative values.")
        self._com.getresponse(f"PSETTEMP {temperature:.3f}")

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
