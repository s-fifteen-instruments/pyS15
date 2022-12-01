#!/usr/bin/env python3
# S-Fifteen Instruments, 2022-11-10
# Python wrapper for readevents7
#
# Wraps 'readevents7' that performs lower level calls, for easier integration
# with other Python scripts. To add mitigations against hangups or errors.
# Avoids reimplementation of 'readevents7'.
#
# Currently implemented only for Linux platforms: need to first implement the
# Windows driver.

import os
import pathlib
import subprocess
import time
from os.path import expanduser
from typing import List, Optional, Tuple, Union

import numpy as np
import psutil

from ..g2lib import parse_timestamps as parser


class TimestampTDC2:
    """Interfaces with timestamp7 device.

    Aligns with methods of TimeStampTDC1 class as much as possible.

    Current implementation flushes the output into file. This has the disadvantage
    of slow disk writes, but avoids potential memory full issues when collecting
    large amounts of data. To eventually port into an adaptive version depending on
    singles rate + integration time.

    Note:
        The naming of 'TimestampTDC2' instead of 'TimeStampTDC2' is intentional.
        Ought to eventually migrate 'TimeStampTDC1' to 'TimestampTDC1'.
    """

    DEFAULT_READEVENTS = "./readevents7"
    DEFAULT_OUTFILE = "/tmp/_TimestampTDC2_events.dat"

    def __init__(
        self, device_path: str = "", readevents_path: str = "", outfile_path: str = ""
    ):
        """Loads path to timestamp device and readevents interfacing code.

        Args:
            device_path: Optional, path to timestamp device.
            readevents_path: Optional, path to readevents.
            outfile_path: Optional, path to event cache on filesystem.
        """
        # If device path not specified, use default loaded by readevents
        self.device_path = device_path

        # Local directory fallback for readevents
        target = (
            readevents_path if readevents_path else TimestampTDC2.DEFAULT_READEVENTS
        )
        if pathlib.Path(target).is_file():
            self.readevents_path = target  # account for spaces in path

        # Otherwise direct user to either download precompiled binaries, or
        # or provide manual build instructions.
        # Note: Not a good practice to install software without prompting.
        else:
            raise FileNotFoundError(
                f"'readevents7' could not be found at specified path "
                f"'{readevents_path}'. [INSERT DOWNLOAD_INSTRUCTIONS]."
            )

        # Use default outfile if not specified
        self.outfile_path = (
            outfile_path if outfile_path else TimestampTDC2.DEFAULT_OUTFILE
        )

        # Other initialization parameters
        self._int_time = 1.0
        self._threshold_dacs = (768, 768, 768, 768)
        self._int_trig = False
        self._legacy = False
        self._mode = 2

    def _call(self, args: List[str], target_file: str = ""):
        """Convenience method to call underlying readevents.

        Need to close 'fd' object after calls. If file descriptor does not get
        excessive, still okay.

        Args:
            args: List of readevents arguments.
            target_file: Path to local storage to store timestamp event data.
        """
        command = [
            self.readevents_path,
            "-t",
            ",".join(map(str, self._threshold_dacs)),
            *args,
        ]
        if self.device_path:
            command.extend(["-U", self.device_path])

        if not target_file:
            target_file = self.outfile_path

        # TODO(Justin): Asynchronous manner?
        # TODO(Justin): Consider migration to psutil.Popen.
        # TODO(Justin): If method gets too long, consider a two-step prepare-call
        #               for more accurate timing.
        fd = os.open(target_file, os.O_WRONLY | os.O_TRUNC | os.O_CREAT)
        process = psutil.Popen(command, stdout=fd, stderr=subprocess.PIPE)
        return process, fd

    def _clear_buffer(self):
        """Convenience function to clear the buffer."""
        while True:
            fd = None
            try:
                process, fd = self._call(["-q1"])
                process.wait()
                break
            except Exception as e:
                raise RuntimeError(f"Call failed with {e.__class__.__name__}: {e}")
            finally:
                if fd:
                    os.close(fd)

    def _call_with_duration(
        self,
        args: List[str],
        target_file: str = "",
        duration: float = 1,
        max_retries: int = 3,
        clear_buffer: bool = True,
    ):
        """Run '_call' with automatic termination and output validity checks.

        Args:
            args: List of readevents arguments.
            target_file: Path to local storage to store timestamp event data.
            duration: Time before terminating process, in seconds.
            max_retries: Maximum retries to avoid error loop.
            clear_buffer: Attempts to clear buffer before executing call.
        """
        # TODO(Justin): Implement a better way to catch premature termination
        # e.g. when LUT lookup fails and readevents exits. As well as make the
        # timing output more precise.

        emsg = None
        for _ in range(max_retries):
            process = fd = None

            try:
                if clear_buffer:
                    self._clear_buffer()
                process, fd = self._call(args, target_file)
                end_time = time.time() + duration
                while time.time() <= end_time:
                    pass

            except Exception as e:
                raise RuntimeError(f"Call failed with {e.__class__.__name__}: {e}")

            finally:
                # Clean up
                if process:
                    process.terminate()
                    gone, alive = psutil.wait_procs([process], timeout=0.5)
                    for p in alive:
                        p.kill()
                if fd:
                    os.close(fd)

            # Check for stderr messages
            if process:
                emsg = process.stderr.read1(100)
                if emsg:
                    continue

            # TODO: Check for event hardcoded signatures

            # No errors detected
            break

        # No successful call completed
        else:
            if emsg:
                raise RuntimeError(
                    f"Call failed with readevents error '{emsg.decode().strip()}'"
                )

    @property
    def int_time(self) -> float:
        """Returns the integration time, in seconds.

        The timestamp itself does not store an integration time - this is controlled
        manually via the software wrapper.
        """
        return self._int_time

    @int_time.setter
    def int_time(self, value: float):
        """Sets the integration time, in seconds.

        Args:
            value: Integration time. Set to 0 for continuous running.
        """
        if value < 0:
            raise ValueError("Invalid integration time.")
        self._int_time = value

    def get_counts(self, duration=None) -> Tuple:
        """Returns the singles counts in each channel.

        Currently copies TimestampTDC1 implementation using a blocking while loop,
        but can rewrite into asynchronous variety.
        """
        duration = duration if duration else self.int_time
        self._call_with_duration(["-a1"], duration=duration)
        t, p = parser.read_a1(self.outfile_path, legacy=self._legacy)

        # TODO(Justin): Add checks on timestamp output validity
        t1 = t[p & 0b0001 != 0]
        t2 = t[p & 0b0010 != 0]
        t3 = t[p & 0b0100 != 0]
        t4 = t[p & 0b1000 != 0]
        return len(t1), len(t2), len(t3), len(t4)

    @staticmethod
    def _threshold_dac2volt(value: float):
        """Converts threshold value from DAC units to voltage."""
        return round((2.047 + 1.024) / 4095 * value - 1.024, 3)

    @staticmethod
    def _threshold_volt2dac(value: float):
        """Converts threshold value from voltage to DAC units.

        Note: In DAC units, 0 corresponds to -1.024V, 4095 corresponds to +2.047V.
        """
        return round((value + 1.024) * 4095 / (2.047 + 1.024))

    @property
    def threshold(self):
        """Returns threshold voltage for all four channels, in volts."""
        return tuple(map(TimestampTDC2._threshold_dac2volt, self._threshold_dacs))

    @threshold.setter
    def threshold(self, value: Union[float, Tuple[float, float, float, float]]):
        """Sets threshold voltage by converting into DAC units, for each channel.

        If 'value' is a single number, this value is broadcasted to all channels.
        Caps to [-1.024, 2.047]V.

        Args:
            value: Either a 4-tuple of voltages, or a single voltage.

        Note:
            Type handling for 'value' follows the convention followed by Scipy[1].

        References:
            [1] https://github.com/scipy/scipy/blob/d1684e067a12d7166119d455a9f78eecf9c2c6bb/scipy/optimize/_lsq/least_squares.py#L95
        """  # noqa

        def limit(voltage: float):
            """Applies hard cap to voltage values."""
            return min(2.047, max(-1.024, voltage))

        # Broadcast single values into a 4-tuple
        avalue = np.asarray(value, dtype=float)
        if avalue.ndim == 0:
            avalue = np.resize(avalue, 4)

        # Check for length of tuple
        if avalue.size != 4:
            raise ValueError("Only arrays of size 4 is allowed.")

        # Convert voltages into DAC values
        value_dac = (TimestampTDC2._threshold_volt2dac(limit(float(v))) for v in avalue)

        # Set threshold voltages
        # Result from tuple comprehension is Tuple[Any, ...], which yields type mismatch
        # Alternative to 'ignore' is to cast type:
        #     cast(Tuple[int, int, int, int], value_dac)
        self._threshold_dacs = value_dac  # type: ignore
        return

    def get_timestamps(self, duration: Optional[float] = None):
        """See parser.read_a1 doc."""
        duration = duration if duration else self.int_time
        self._call_with_duration(["-a1"], duration=duration)
        t, p = parser.read_a1(self.outfile_path, legacy=self._legacy)
        return t, p

    def begin_readevents(
        self,
        duration: Optional[float] = None,
        mode: Optional[int] = None,
        events: Optional[int] = 0,
    ):
        duration = duration if duration else self.int_time
        mode = mode if mode else self._mode
        events = events if events else 0
        if self._legacy:
            swap_opt = " -X"
        else:
            swap_opt = ""
        if events > 0:
            q_opt = " -q" + f"{events}"
        else:
            q_opt = ""
        if self._int_trig:
            j_opt = " -j"
        else:
            j_opt = ""
        mode_opt = f"-a{mode}"
        re_opts = " " + mode_opt + swap_opt + q_opt + j_opt
        file = " > " + self.outfile_path
        # Take data
        os.system("timeout " + str(duration) + " " + READEVENTS_PROG + re_opts + file)
        return


DEVICE_PATH = "/dev/ioboards/usbtmst0"
READEVENTS_PROG = expanduser("~") + "/programs/usbtmst4/apps/readevents7"
t = TimestampTDC2(
    DEVICE_PATH,
    READEVENTS_PROG,
)
# args = ["-a2", "-q100"]
# p,pid = t._call(args)
# time.sleep(2)
# p.terminate()
