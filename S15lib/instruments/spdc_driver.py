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

    def reset(self):
        """Resets the device."""
        self._com.writeline("*RST")

    @property
    def heater_loop(self) -> int:
        return int(self._com.getresponse("HLOOP?"))

    @heater_loop.setter
    def heater_loop(self, value: int):
        """Sets heater/crystal temperature loop (HLOOP) on/off.

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
    def peltier_voltage_limit(self) -> float:
        return float(self._com.getresponse("plimit?"))

    @peltier_voltage_limit.setter
    def peltier_voltage_limit(self, voltage: float):
        self._com.writeline(f"plimit {voltage}")

    @property
    def heater_voltage(self) -> float:
        return float(self._com.getresponse("hvolt?"))

    @property
    def peltier_voltage(self) -> float:
        return float(self._com.getresponse("pvolt?"))

    @property
    def heater_voltage_limit(self) -> float:
        return float(self._com.getresponse("hlimit?"))

    @heater_voltage_limit.setter
    def heater_voltage_limit(self, voltage: float):
        self._com.write("hlimit {}".format(voltage).encode())

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
    def heater_temp(self) -> float:
        """Returns the temperature at the crystal.

        Returns:
            number -- Temperature at the crystal
        """
        assert type(self._com) is SerialConnection
        return float(self._com.getresponse("HTEMP?"))

    @heater_temp.setter
    def heater_temp(self, temperature: float):
        """Sets the temperature of the crystal heater


        Decorators:
                heater_temp.setter

        Arguments:
                temperature {float} -- set point for the heater temperature
        """
        assert type(self._com) is SerialConnection
        now_temp = self.heater_temp
        if now_temp < temperature:
            # Perform precautionary stepping during heating
            for t in range(int(now_temp) + 1, int(temperature) + 1):
                cmd = ("HSETTEMP {}\n".format(t)).encode()
                self._com.write(cmd)
                time.sleep(6)
            # Enable floating point setpoint
            if int(temperature) != temperature:
                cmd = ("HSETTEMP {:.3f}\n".format(temperature)).encode()
                self._com.write(cmd)
        else:
            cmd = ("HSETTEMP {}\n".format(temperature)).encode()
            self._com.write(cmd)

    @property
    def peltier_temp(self) -> float:
        """Measures the temperature close to the peltier, where the laser diode is cooled.

        Returns:
            number -- Current temperature of the peltier temp
        """
        assert type(self._com) is SerialConnection
        return float(self._com.getresponse("PTEMP?"))

    @peltier_temp.setter
    def peltier_temp(self, temperature: float):
        assert temperature > 20 and temperature < 50
        assert type(self._com) is SerialConnection
        assert type(temperature) is float or type(temperature) is int
        # cmd_setPID = b'PCONSTP 0.1;PCONSTI 0.03\r\n'
        # self._com.write(cmd_setPID)
        cmd = ("PSETTEMP {}\r\n".format(temperature)).encode()
        self._com.write(cmd)
        self.peltier_loop_on()  # switch feedback loop on

    @property
    def peltier_temp_setpoint(self) -> float:
        return float(self._com.getresponse("psettemp?"))

    @property
    def heater_temp_setpoint(self) -> float:
        return float(self._com.getresponse("hsettemp?"))

    @property
    def identity(self):
        return self._com.get_identity()

    def help(self):
        self._com.print_help()

    def save_settings(self) -> str:
        return self._com.getresponse("save")

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
    def laser_current_limit(self) -> float:
        return float(self._com.getresponse("llimit?"))

    @laser_current_limit.setter
    def laser_current_limit(self, value: float) -> float:
        cmd = "llimit {}\r\n".format(value).encode()
        return self._com.write(cmd)
