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
import subprocess
import pathlib
import time
from typing import List, Tuple, Union

import psutil

import parse_timestamps as parser

class TimestampTDC7:
    """Interfaces with timestamp7 device.

    Aligns with methods of TimestampTDC1 class as much as possible.
    
    Current implementation flushes the output into file. This has the disadvantage
    of slow disk writes, but avoids potential memory full issues when collecting
    large amounts of data. To eventually port into an adaptive version depending on
    singles rate + integration time. 
    """

    DEFAULT_READEVENTS = "./readevents7"
    DEFAULT_OUTFILE = "/tmp/_TimestampTDC7_events.dat"
    
    def __init__(self, device_path: str = "", readevents_path: str = ""):
        """Loads path to timestamp device and readevents interfacing code.

        Args:
            readevents_path: Optional, path to readevents.
        """
        # If device path not specified, use default loaded by readevents
        self.device_path = device_path

        # Local directory fallback for readevents
        target = readevents_path if readevents_path else TimestampTDC7.DEFAULT_READEVENTS
        if pathlib.Path(target).is_file():
            self.readevents_path = target  # account for spaces in path
        
        # Otherwise direct user to either download precompiled binaries, or
        # or provide manual build instructions. Note: Not a good practice to install software
        # without prompting.
        else:
            raise FileNotFoundError(
                f"'readevents7' could not be found at specified path '{target_path}'. "
                "[INSERT DOWNLOAD_INSTRUCTIONS]."
            )

        # Other initialization parameters
        self._int_time = 1
        self._threshold_dacs = [768, 768, 768, 768]
            
    def _call(self, args: List[str], target_file: str = ""):
        """Convenience method to call underlying readevents.

        Need to close 'fd' object after calls. If file descriptor does not get excessive,
        still okay.
        
        Args:
            args: List of readevents arguments.
            target_file: Path to local storage to store timestamp event data.
        """
        command = [
            self.readevents_path,
            "-t", ",".join(map(str, self._threshold_dacs)),
            *args,
        ]
        if self.device_path:
            command.extend(["-U", self.device_path])

        if not target_file:
            target_file = TimestampTDC7.DEFAULT_OUTFILE
        
        # TODO(Justin): Asynchronous manner?
        # TODO(Justin): Consider migration to psutil.Popen.
        # TODO(Justin): If method gets too long, consider a two-step prepare-call
        #               for more accurate timing.
        fd = os.open(target_file, os.O_WRONLY | os.O_TRUNC | os.O_CREAT)
        process = psutil.Popen(command, stdout=fd, stderr=subprocess.PIPE)
        return process, fd

    def _call_with_duration(
            self,
            args: List[str],
            target_file: str = "",
            duration: float = 1,
            max_retries: int = 3,
        ):
        """Run '_call' with automatic termination and output validity checks.

        Args:
            duration: Time before terminating process, in seconds.
            max_retries: Maximum retries to avoid error loop.
        """
        # TODO(Justin): Implement a better way to catch premature termination
        # e.g. when LUT lookup fails and readevents exits. As well as make the
        # timing output more precise.
        
        emsg = None
        for i in range(max_retries):
            process = fd = None

            try:
                process, fd = self._call(args, target_file)
                end_time = time.time() + duration
                while time.time() <= end_time: pass

            except Exception as e:
                raise RuntimeError(
                    f"Call failed with {e.__class__.__name__}: {e}"
                )
            
            finally:
                # Clean up
                if process:
                    process.terminate()
                    gone, alive = psutil.wait_procs([process], timeout=0.5)
                    for p in alive: p.kill()
                    os.close(fd)

            # Check for stderr messages
            if process:
                emsg = process.stderr.read1(100)
                if emsg: continue

            # TODO: Check for event hardcoded signatures
            
            # No errors detected
            break
        
        # No successful call completed
        else:
            raise RuntimeError(f"Call failed with readevents error '{emsg.decode().strip()}'")


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

    def get_counts(self, duration = None) -> Tuple:
        """Returns the singles counts in each channel.
        
        Currently copies TimestampTDC1 implementation using a blocking while loop,
        but can rewrite into asynchronous variety.
        """
        duration = duration if duration else self.int_time
        self._call_with_duration(["-a1"], duration=duration)
        t, p = parser.read_a1(TimestampTDC7.DEFAULT_OUTFILE, legacy=False)

        # TODO(Justin): Add checks on timestamp output validity
        t1 = t[p & 0b0001 != 0]
        t2 = t[p & 0b0010 != 0]
        t3 = t[p & 0b0100 != 0]
        t4 = t[p & 0b1000 != 0]
        return len(t1), len(t2), len(t3), len(t4)
    
    @staticmethod
    def _threshold_dac2volt(value: float):
        """Converts threshold value from DAC units to voltage."""
        return round((2.047+1.024)/4095 * value - 1.024, 3)

    @staticmethod
    def _threshold_volt2dac(value: float):
        """Converts threshold value from voltage to DAC units.

        Note: In DAC units, 0 corresponds to -1.024V, 4095 corresponds to +2.047V.
        """
        return round((value+1.024) * 4095/(2.047+1.024))
        
    @property
    def threshold(self):
        """Returns threshold voltage for all four channels, in volts."""
        return tuple(map(TimestampTDC7._threshold_dac2volt, self._threshold_dacs))
    
    @threshold.setter
    def threshold(self, value: Union[float, Tuple[float]]):
        """Sets threshold voltage by converting into DAC units, for each channel.

        If 'value' is a single number, this value is broadcasted to all channels.
        Caps to [-1.024, 2.047]V.

        Args:
            value: Either a 4-tuple of voltages, or a single voltage.
        """
        limit = lambda v: min(2.047, max(-1.024, v))

        # Attempt to parse as simple float
        try:
            value = float(value)
            value_dac = TimestampTDC7._threshold_volt2dac(limit(value))
            self._threshold_dacs = [value_dac]*4
            return
        except TypeError:
            pass

        # Attempt to parse as list
        try:
            if len(value) != 4: raise
            value = tuple(map(lambda v: limit(float(v)), value))
            value_dac = tuple(map(TimestampTDC7._threshold_volt2dac, value))
            self._threshold_dacs = value_dac
            return
        
        # Everything else didn't work
        except:
            raise ValueError(f"'{value}' is not a valid argument to threshold().")

    def get_timestamps(self, duration: float = None):
        """See parser.read_a1 doc."""
        duration = duration if duration else self.int_time
        self._call_with_duration(["-a1"], duration=duration)
        t, p = parser.read_a1(TimestampTDC7.DEFAULT_OUTFILE, legacy=False)
        return t, p


t = TimestampTDC7(
    "/dev/ioboards/usbtmst0",
    "/home/qitlab/programs/usbtmst4/apps/readevents7",
)
# args = ["-a2", "-q100"]
# t.call(args)
