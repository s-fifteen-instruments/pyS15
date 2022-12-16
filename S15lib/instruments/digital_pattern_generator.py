import re
import time

import numpy as np  # for type checking with numpy types

from .serial_connection import SerialConnection

COMMENT_PATTERN = re.compile(r"(#.*)?\n?", re.MULTILINE)
status_bits = dict(
    {"tablestat": 0x00F, "inlines": 0x0F0, "clk": 0x100, "pll": 0x200, "level": 0x400}
)


class PattGen(object):
    """Python wrapper to communcate with DPG1 board."""

    DEVICE_IDENTIFIER = "DPG1"

    def __init__(self, device_path: str = "", level: str = "NIM"):
        if device_path == "":
            self._com = SerialConnection.connect_by_name(self.DEVICE_IDENTIFIER)
        else:
            self._com = SerialConnection(device_path)
        self._clk = False

        # for k, v in status_bits.items():
        #    setattr(self, k, v)
        # self.status()

    @property
    def level(self):
        """Set type of incoming pulses"""
        return self._level

    @level.setter
    def level(self, value: str):
        if value.lower() == "nim":
            self.write_only("NIM")
            self._level = "NIM"
        elif value.lower() == "ttl":
            self.write_only("TTL")
            self._level = "TTL"
        else:
            print("Accepted input is a string and either 'TTL' or 'NIM'")

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
        print(self._com.get_help())
        return

    @property
    def identity(self) -> str:
        return self._com.get_identity()

    def reset(self) -> None:
        """Resets the device."""
        self._com.writeline("*RST")

    def close(self) -> None:
        """Close connection to device."""
        self._com.close()

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
        # hlimit_low, hlimit_high = 0, self.heater_voltage_limit
        # self._raise_if_oob(voltage, hlimit_low, hlimit_high, "Heater voltage", "V")
        # self._com.writeline(f"HVOLT {voltage:.3f}")

    @property
    def status(self) -> int:
        """
        Returns the status of the pattern generator
        status_bits = dict({'tablestat' : 0x00f,
                 'inlines' : 0x0f0,
                 'clk' : 0x100,
                 'pll' : 0x200,
                 'level' : 0x400})

        """
        self._status = int(self._com.getresponse("STATUS?"))
        self.tablestat = self._status & 0x00F
        self.inlines = self._status & 0x0F0
        self.clk = True if self._status & 0x100 else False
        self.pll = "LOCKED" if self._status & 0x200 else "UNLOCKED"
        self.level = "TTL" if self._status & 0x400 else "NIM"
        return self._status

    @property
    def clk(self) -> bool:
        return self._clk

    @clk.setter
    def clk(self, val: bool) -> bool:
        self._clk = val
        return self._clk

    @property
    def clock(self) -> str:
        """
        Reads the current clock setting.
        """
        val = int(self._com.getresponse("CLOCKSEL?"))
        clk_ok = self.clk
        if val == 0 and clk_ok:
            return "100MHz Auto reference, ext reference good"
        if val == 0:
            return "100MHz Auto reference, internal reference"
        elif val == 1 and clk_ok:
            return "100MHz force External reference, ext reference good"
        elif val == 1 and not clk_ok:
            return "100MHz force External reference, ext reference not good"
        elif val == 2:
            return "100MHZ force Internal reference"
        elif val == 3:
            return "External clock reference"
        else:
            raise ValueError("Clock should not return this value")

    @clock.setter
    def clock(self, value: str):
        """Set the clock source

        Args:
            sets the clock source. 0: 100MHz autoref, 1: 100MHz ext ref
          2: 100MHz internal ref, 3: External clock directly

            value (str): 0: 100MHz autoselect clock, 1: 100MHz external clock,
                         2: 100MHz internal clock, 3:
        """
        self.write_only("CLOCKSEL {}".format(value))

    def strip_comments(self, code):
        out = []
        for line in code:
            out.append(COMMENT_PATTERN.sub("", line))
        return out

    def cleanup_string(self, code):
        out = []
        for line in code:
            clean = " ".join(line.split())
            clean = clean.replace(",", " ")
            clean = clean.lower()
            out.append(clean)
        return out

    def hex_to_dec(self, line: list):
        """Converts hex beginning with 0x to decimal"""
        dec_line = []
        dec_out = []
        for j in line:
            for i in j.split(" "):
                if i.startswith("0x"):
                    dec_line.append(f"{int(i,16)}")
                elif i.isdecimal():
                    dec_line.append(f"{int(i)}")
                else:
                    dec_line.append(i)
            dec_out.append(" ".join(dec_line))
            dec_line = []
        return dec_out

    def read_word_file(self, filepath):
        """Opens a word/pattern file and writes it to the DPG
        Eats both hex and decimal. No checking for correctness done.
        """
        with open(filepath, "r") as fd:
            tables = self.strip_comments(fd.readlines())
            tables = self.cleanup_string(tables)
            tables = self.hex_to_dec(tables)
            self.writeDPG(tables)
        return tables

    def writeDPG(self, table):
        """Writes into DPG"""
        for line in table:
            line = line + ";"
            self._com.write(line.encode())
        print("tables loaded.")

    def write_only(self, cmd):
        """Write something but don't care about any response"""
        self._com.write((cmd + "\r\n").encode())
        self._com.readlines()
        time.sleep(0.1)
