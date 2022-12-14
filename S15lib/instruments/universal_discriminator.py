"""
Created on 5th Dec 2022
Settings are set via dictionaries with 2 elements for inputs channels 0: and 1:
    and 4 elements for output channels 0A: 1A: 0B: 1B:

    Examples:
        >>> ud = UniversalDiscriminator()
        >>> ud.inputthreshold = {0:-0.8, 1:0.8} # Sets threshold voltage to -9.8 on ch 0 and 0.8 on ch 1
        >>> ud.inputpolarity({0:1, 1:0}) # Sets input polarity to be negative on ch 0 and positive on ch 1
        >>> ud.ouputpolarity({"0A": 0 , "1A": 1, "0B" : 0, "1B" : 1}) # s
        >>> ud.outmode() # Sets variety of outmode in the 4 outputs.
        >>> ud.inputdelay({0:0, 1:0})

"""

from . import serial_connection

ref_in_dict = {0: 0, 1: 1}
ref_out_dict = {"0A": 0, "1A": 1, "0B": 2, "1B": 3}


class UniversalDiscriminator:
    """Module to use the Universarl Discriminator with 2 inputs and 4 outputs"""

    DEVICE_IDENTIFIER = "UD"

    def __init__(
        self,
        device_path: str = "",
    ):
        # if no path is indicated it tries to init the first device
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
        self._com.write("*RST\n".encode())

    @property
    def inputthreshold(self) -> dict:
        """
        Queries threshold from threshvolt register.

        """
        out = {0: 0, 1: 0}
        step_n = 0.0000979
        step_p = step_n

        for ch in [0, 1]:
            cmd = ("CONFIG {}\n".format((ch))).encode()
            retval = self._readword(cmd)
            if retval & 0x8000:  # negative threshold
                out[ch] = round(((retval & 0x7FFF) - 0x8000) * step_n, 3)
            else:
                out[ch] = round(retval * step_p, 3)
        return out

    @inputthreshold.setter
    def inputthreshold(self, vol: dict = {0: -0.8, 1: 1.2}):
        """
        Sets input polarity of channels 0 or 1.
        vol: -2 -> 2
        """
        n = 2
        if len(vol) < n:
            for key in ref_in_dict.keys():
                if not vol.get(key):
                    vol[key] = -0.8
                    print(f"Filling missing elements in dict {key} with -0.8")

        for key in vol.keys():
            cmd = ("THRESHOLD {} {}\n".format(ref_in_dict[key], vol[key])).encode()
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
    #            retval = self._readword(cmd)
    #            out.append(retval & 0x1)
    #        return out
    #
    #    @inputpolarity.setter
    def inputpolarity(self, pol: dict = {0: 1, 1: 0}):
        """
        Sets input polarity of channels 0 or 1.
        pol: 0 -> Positive
             1 -> Negative
        """
        n = 2
        if len(pol) < n:
            for key in ref_in_dict.keys():
                if not pol.get(key):
                    pol[key] = 0
                    print(f"Filling missing elements in dict {key} with 0")

        for key in pol.keys():
            cmd = ("POLARITY {} {}\n".format(ref_in_dict[key], pol[key])).encode()
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
    #            retval = self._readword(cmd)
    #            out.append((retval & 0x6) >> 1)
    #        return out
    #
    #    @outputpolarity.setter
    def outputpolarity(self, pol: dict = ref_out_dict):
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
        n = 4
        if len(pol) < n:
            for key in ref_out_dict.keys():
                if not pol.get(key):
                    pol[key] = 0
                    print(f"Filling missing elements in dict {key} with 0")

        for key in pol.keys():
            cmd = ("OUTLEVEL {} {}\n".format(ref_out_dict[key], pol[key])).encode()
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
    #            retval = self._readword(cmd)
    #            out.append((retval & 0x18) >> 3)
    #
    #        return out
    #
    #    @outmode.setter
    def outmode(self, mode: dict = ref_out_dict):
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
        n = 4
        if len(mode) < n:
            for key in ref_out_dict.keys():
                if not mode.get(key):
                    mode[key] = 0
                    print(f"Filling missing elements in dict {key} with 0")

        for key in mode.keys():
            cmd = ("OUTMODE {} {}\n".format(ref_out_dict[key], mode[key])).encode()
            self._com.write(cmd)

    #    @property
    #    def inputdelay(self):
    #        """
    #        Queries delay from config register.
    #        """
    #        out = []
    #        for ch in [0, 1]:
    #            cmd = ("CONFIG {}\n".format((ch + 2) << 4)).encode()
    #            retval = self._readword(cmd)
    #            out.append((retval & 0x1F00) >> 8)
    #        return out
    #
    #    @inputdelay.setter
    def inputdelay(self, delay: dict = {0: 0, 1: 0}):
        """
        Sets input delay of channels 0 or 1.
        delay: 0 --> 31
        """
        n = 2
        if len(delay) < n:
            for key in ref_in_dict.keys():
                if not delay.get(key):
                    delay[key] = 0
                    print(f"Filling missing elements in dict {key} with 0")

        for key in delay.keys():
            cmd = ("DELAY {} {}\n".format(ref_in_dict[key], delay[key])).encode()
            self._com.write(cmd)

    @property
    def identity(self) -> str:
        return self._identity

    def help(self):
        print(self._com.get_help())
        return

    def _readword(self, cmd) -> int:
        """Reads the config from FPGA. Currently only works on Config 0 and 1 for threshold registers"""
        self._com.write(cmd)
        retval = self._com.getresponse("READW?;").strip()
        return int(retval, 10)
