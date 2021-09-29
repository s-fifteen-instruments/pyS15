#!/usr/bin/env python3

"""
USB mini counter based on FPGA

Collection of functions to simplify the integration of the USB counter in
Python scripts.
"""

import os
import glob
import numpy as np
import subprocess
from typing import Tuple, List

import serial
import serial.tools.list_ports
import time
import multiprocessing
import csv

from ..g2lib import g2lib


from os.path import exists, expanduser
from tempfile import NamedTemporaryFile

from . import serial_connection

READEVENTS_PROG = expanduser("~") + "/programs/usbcntfpga/apps/readevents4a"
TTL = 'TTL'
NIM = 'NIM'

def pattern_to_channel(pattern):
    if pattern == 4:
        return 3
    elif pattern == 8:
        return 4
    elif pattern == 1 or pattern == 2 or pattern == 0:
        return pattern

def channel_to_pattern(channel):
    return int(2**(channel-1))

# class Threading(object):
#     """ Threading example class
#     The run() method will be started and it will run in the background
#     until the application exits.
#     ref: http://sebastiandahlgren.se/2014/06/27/running-a-method-as-a-background-thread-in-python/
#     """

#     def __init__(self, interval=1):
#         """ Constructor
#         :type interval: int
#         :param interval: Check interval, in seconds
#         """
#         self.interval = interval

#         thread = threading.Thread(target=self.run, args=())
#         thread.daemon = True                            # Daemonize thread
#         thread.start()                                  # Start the execution

#     def run(self):
#         """ Method that runs forever """
#         while True:
#             # Do something
#             print('Doing something imporant in the background')

#             time.sleep(self.interval)

class TimeStampTDC1(object):
    """
    The usb counter is seen as an object through this class,
    inherited from the generic serial one.
    """
    DEVICE_IDENTIFIER = 'TDC1'
    TTL_LEVELS = 'TTL'
    NIM_LEVELS = 'NIM'

    def __init__(self, device_path=None,
                 integration_time=1,
                 mode='singles',
                 level='NIM'):
        """
        Function to initialize the counter device.
        It requires the full path to the serial device as arguments,
        otherwise it will
        initialize the first counter found in the system
        """
        if device_path is None:
            device_path = (serial_connection.search_for_serial_devices(
                self.DEVICE_IDENTIFIER))[0]
            print('Connected to', device_path)
        self._device_path = device_path
        # self._com = serial_connection.SerialConnection(device_path)
        self._com = serial.Serial(device_path, timeout=0.1)
        self._com.write(b'\r\n')
        self._com.readlines()
        self.mode = mode
        self.level = level
        self.int_time = integration_time
        self.accumulate_timestamps = False # flag for timestamp accumulation service
        self.accumulated_timestamps_filename = "timestamps.raw" # binary file where timestamps are stored
        time.sleep(0.2)

    @property
    def int_time(self):
        """
        Controls the integration time set in the counter

        :getter: returns integration time in seconds
        :setter: Set integration
        :param value: integration time in seconds
        :type value: int
        :returns: integration time in seconds
        :rtype: int
        """
        self._com.write(b'time?\r\n')
        return int(self._com.readline())

    @int_time.setter
    def int_time(self, value: float):
        value *= 1000
        if value < 1:
            print('Invalid integration time.')
        else:
            self._com.write('time {:d};'.format(int(value)).encode())
            self._com.readlines()

    def get_counts(self, duration_seconds: int = None) -> Tuple:
        """[summary]

        Args:
            duration_seconds (int, optional): [description]. Defaults to None.

        Returns:
            List: [description]
        """
        self._com.timeout = 0.05
        if duration_seconds is None:
            duration_seconds = self.int_time
        else:
            self.int_time = duration_seconds
        self._com.timeout = duration_seconds

        self._com.write(b'singles;counts?\r\n')

        t_start = time.time()
        while True:
            if self._com.inWaiting() > 0:
                break
            if time.time() > (t_start + duration_seconds + 0.1):
                print(time.time() - t_start)
                raise serial.SerialTimeoutException('Command timeout')


        counts = self._com.readline()
        self._com.timeout = 0.05
        return tuple([int(i) for i in counts.split()])

    @property
    def mode(self):
        # mode = int(self._com.getresponse('MODE?'))
        self._com.write(b'mode?\r\n')
        mode = int(self._com.readline())
        if mode == 0:
            return 'singles'
        if mode == 1:
            return 'pairs'
        if mode == 3:
            return 'timestamp'

    @mode.setter
    def mode(self, value):
        if value.lower() == 'singles':
            self.write_only('singles')
        if value.lower() == 'pairs':
            self.write_only('pairs')
        if value.lower() == 'timestamp':
            self.write_only('timestamp')

    def write_only(self, cmd):
        self._com.write((cmd + '\r\n').encode())
        self._com.readlines()
        time.sleep(0.1)

    @property
    def level(self):
        """ Set type of incoming pulses"""
        self._com.write(b'level?\r\n')
        return self._com.readline()
        # return self._com.getresponse('LEVEL?')

    @level.setter
    def level(self, value: str):
        if value.lower() == 'nim':
            self.write_only('NIM')
        elif value.lower() == 'ttl':
            self.write_only('TTL')
        else:
            print('Accepted input is a string and either \'TTL\' or \'NIM\'')
        # time.sleep(0.1)

    @property
    def threshold(self):
        """Returns the threshold level"""
        return self.level

    @threshold.setter
    def threshold(self, value: float):
        """Sets the the threshold the input pulse needs to exceed to trigger an event.

        Args:
            value (float): threshold value in volts can be negative or positive
        """
        if value < 0:
            self.write_only('NEG {}'.format(value))
        else:
            self.write_only('POS {}'.format(value))

    @property
    def clock(self) -> str:
        """ Choice of clock"""
        self._com.write('REFCLK?\r\n')
        return self._com.readline()

    @clock.setter
    def clock(self, value: str):
        """Set the clock source internel or external

        Args:
            value (str): 0 autoselect clock, 1 force external clock, 2 force internal clock reference
        """
        self.write_only('REFCLK {}'.format(value).encode())

    def _stream_response_into_buffer(self, cmd: str, acq_time: float) -> bytes:
        """Streams data from the timestamp unit into a buffer.

        Args:
            cmd (str): Executes the given command to start the stream.
            acq_time (float): Reads data for acq_time seconds.

        Returns:
            bytes: Returns the raw data.
        """
        # this function bypass the termination character (since there is none for timestamp mode),
        # streams data from device for the integration time.

        # Stream data for acq_time seconds into a buffer
        ts_list = []
        time0 = time.time()
        self._com.write((cmd + '\r\n').encode())
        while ((time.time() - time0) <= acq_time):
            ts_list.append(self._com.read((1 << 20)*4))
        self._com.write(b'abort\r\n')
        self._com.readlines()
        return b''.join(ts_list)

    def get_counts_and_coincidences(self, t_acq: float =1) -> Tuple[int, int , int, int, int, int, int, int]:
        """Counts single events and coinciding events in channel pairs.

        Args:
            t_acq (float, optional): Time duration to count events in seperated channels and coinciding events in 2 channels. Defaults to 1.

        Returns:
            Tuple[int, int , int, int, int, int, int, int]: Events ch1, ch2, ch3, ch4; Coincidences: ch1-ch3, ch1-ch4, ch2-ch3, ch2-ch4
        """
        self.mode = 'pairs'
        self._com.readlines() # empties buffer

        if t_acq is None:
            t_acq = self.int_time
        else:
            self.int_time = t_acq
        self._com.timeout = t_acq

        self._com.write(b'pairs;counts?\r\n')
        t_start = time.time()
        while True:
            if self._com.inWaiting() > 0:
                break
            if time.time() > (t_start + t_acq + 0.1):
                print(time.time() - t_start)
                raise serial.SerialTimeoutException('Command timeout')
        singlesAndPairs = self._com.readline()
        self._com.timeout = 1
        return tuple([int(i) for i in singlesAndPairs.split()])

    def get_timestamps(self, t_acq: float = 1) -> Tuple[List[float], List[str]]:
        """Acquires timestamps and returns 2 lists. The first one containing the time and the second
        the event channel.

        Args:
            t_acq (float, optional): Duration of the the timestamp acquisition in seconds. Defaults to 1.

        Returns:
            Tuple[List[float], List[str]]: Returns the event times in ns and the corresponding event channel.
                                           The channel are returned as string where a 1 indicates the trigger channel.
                                           For example an event in channel 2 would correspond to "0010".
                                           Two coinciding events in channel 3 and 4 correspond to "1100"
        """
        self.mode = 'singles'
        level = float(self.level.split()[0])
        level_str = 'NEG' if level < 0 else "POS"
        self._com.readlines() # empties buffer
        # t_acq_for_cmd = t_acq if t_acq < 65 else 0
        cmd_str = 'INPKT;{} {};time {};timestamp;counts?;'.format(
            level_str, level, (t_acq if t_acq < 65 else 0) * 1000)
        buffer = self._stream_response_into_buffer(cmd_str, t_acq + 0.1)
        # '*RST;INPKT;' + level + ';time ' + str(t_acq * 1000) + ';timestamp;counts?', t_acq + 0.1)

        # buffer contains the timestamp information in binary.
        # Now convert them into time and identify the event channel.
        # Each timestamp is 32 bits long.
        bytes_hex = buffer[::-1].hex()
        ts_word_list = [int(bytes_hex[i:i + 8], 16)
                        for i in range(0, len(bytes_hex), 8)][::-1]

        ts_list = []
        event_channel_list = []
        periode_count = 0
        periode_duration = 1 << 27
        prev_ts = -1
        for ts_word in ts_word_list:
            time_stamp = ts_word >> 5
            pattern = ts_word & 0x1f
            if prev_ts != -1 and time_stamp < prev_ts:
                periode_count += 1
                # print(periode_count)
            prev_ts = time_stamp
            if (pattern & 0x10) == 0:
                ts_list.append(time_stamp + periode_duration * periode_count)
                event_channel_list.append('{0:04b}'.format(pattern & 0xf))

        ts_list = np.array(ts_list) * 2
        event_channel_list = event_channel_list

        return ts_list, event_channel_list

    def count_g2(self, t_acq: float, bin_width: int = 2, bins: int = 500,
                 ch_start: int = 1, ch_stop: int = 2,
                 ch_stop_delay: float = 0):
        """
        Returns pairs and singles counts from usbcounter timestamp data.

        Computes g2 between channels 1 and 2 of timestamp
        and sum the coincidences within specified window

        :param t_acq: acquisition time in seconds
        :type t_acq: float
        :returns: ch_start counts, ch_stop counts, actual acquistion time, time bin array, histogram
        :rtype: {int, int, int, float, float}

        Notes
        -----
        Actual acquisition time is obtained from the returned timestamps. This might differ slightly from the
        acquisition time passed to the timestamp device in the arguments of this function. If there are no counts
        in a given timespan, no timestamps are obtained. In this case, t_acq is taken to be the actual acquisition time.
        """

        t, channel = self.get_timestamps(t_acq)

        """
        OLDER CODE:
        """
        # channel = np.array([pattern_to_channel(int(i, 2)) for i in channel])
        # t_ch1 = t[channel == ch_start]
        # t_ch2 = t[channel == ch_stop]

        """
        NEWER CODE:
        convert string expression of channel elements to a number, and mask it against desired channels
        the mask ensures that timestamp events that arrive at the channels within one time resolution is still registered.
        """
        t_ch1 = t[[int(ch,2) & channel_to_pattern(ch_start) != 0 for ch in channel]]
        t_ch2 = t[[int(ch,2) & channel_to_pattern(ch_stop) != 0 for ch in channel]]
        histo = g2lib.delta_loop(
            t_ch1, t_ch2 + ch_stop_delay, bins=bins, bin_width_ns=bin_width)
        total_time = t[-1] if len(t)>0 else t_acq
        return {'channel1': len(t_ch1),
                'channel2': len(t_ch2),
                'total_time': total_time, 'time_bins': np.arange(0, bins * bin_width, bin_width), 'histogram': histo}

    def help(self):
        """
        Prints device help text
        """
        self._com.write(b'help\r\n')
        [print(k) for k in self._com.readlines()]

    def _continuous_stream_timestamps_to_file(self, filename: str):
        """
        Indefinitely streams timestamps to a file
        WARNING: ensure there is sufficient disk space: 32 bits x total events required
        """
        self.mode = 'singles'
        level = float(self.level.split()[0])
        level_str = 'NEG' if level < 0 else "POS"
        self._com.readlines() # empties buffer
        # t_acq_for_cmd = t_acq if t_acq < 65 else 0
        cmd_str = 'INPKT;{} {};time {};timestamp;counts?;'.format(
            level_str, level, 0)
        self._com.write((cmd_str + '\r\n').encode())

        while True:
            buffer = self._com.read((1 << 20)*4)
            with open(filename,'ab+') as f:
                f.write(buffer)
            f.close()

    def start_continuous_stream_timestamps_to_file(self):
        """
        Starts the timestamp streaming service to file in the brackground
        """
        if os.path.exists(self.accumulated_timestamps_filename):
          os.remove(self.accumulated_timestamps_filename) # remove previous accumulation file for a fresh start
        else:
          pass
        self.accumulate_timestamps = True
        self.proc = multiprocessing.Process(target=self._continuous_stream_timestamps_to_file,args=(self.accumulated_timestamps_filename,))
        self.proc.daemon = True                            # Daemonize thread
        self.proc.start()                                  # Start the execution

    def stop_continuous_stream_timestamps_to_file(self):
        """
        Stops the timestamp streaming service to file in the brackground
        """
        self.accumulate_timestamps = False
        self.proc.terminate()
        time.sleep(0.5)
        self.proc.close()
        self._com.write(b'abort\r\n')
        self._com.readlines()

    def read_timestamps_bin(self, binary_stream):
        """
        Reads the timestamps accumulated in a binary sequence
        Returns:
            Tuple[List[float], List[str]]: Returns the event times in ns and the corresponding event channel.
                                           The channel are returned as string where a 1 indicates the trigger channel.
                                           For example an event in channel 2 would correspond to "0010".
                                           Two coinciding events in channel 3 and 4 correspond to "1100"
        """
        bytes_hex = binary_stream[::-1].hex()
        ts_word_list = [int(bytes_hex[i:i + 8], 16)
                                for i in range(0, len(bytes_hex), 8)][::-1]

        ts_list = []
        event_channel_list = []
        periode_count = 0
        periode_duration = 1 << 27
        prev_ts = -1
        for ts_word in ts_word_list:
            time_stamp = ts_word >> 5
            pattern = ts_word & 0x1f
            if prev_ts != -1 and time_stamp < prev_ts:
                periode_count += 1
        #         print(periode_count)
            prev_ts = time_stamp
            if (pattern & 0x10) == 0:
                ts_list.append(time_stamp + periode_duration * periode_count)
                event_channel_list.append('{0:04b}'.format(pattern & 0xf))

        ts_list = np.array(ts_list) * 2
        event_channel_list = event_channel_list
        return ts_list, event_channel_list

    def read_timestamps_from_file(self):
        """
        Reads the timestamps accumulated in a binary file
        """
        with open(self.accumulated_timestamps_filename,"rb") as f:
            lines = f.read()
        f.close()
        return self.read_timestamps_bin(lines)

    def read_timestamps_from_file_as_dict(self):
        """
        Reads the timestamps accumulated in a binary file
        Returns dictionary where timestamps['channel i'] is the timestamp array in nsec for the ith channel
        """
        timestamps = {}
        times, channels = self.read_timestamps_from_file() # channels may involve coincidence signatures such as '0101'
        for channel in range(1,5,1): # iterate through channel numbers 1, 2, 3, 4
            timestamps['channel {}'.format(channel)] = times[[int(ch,2) & channel_to_pattern(channel) != 0 for ch in channels]]
        return timestamps

    def real_time_processing(self):
        """
        Real-time processes the timestamps that are saved in the background.
        Grabs a number of lines of timestamps to process (defined as a section): since reading from a file is time-consuming, we grab a couple at a go.
        """
        lines_per_section = int(1e6) # reads these number of timestamp events at a time
        with open("timestamps.raw","rb") as f:
            times = np.array([])
            while not eof:
                lines = f.read(4*lines_per_section) # reads a section-worth = 4 bytes (32-bits) x lines per section
                t,c = counter.read_timestamps_bin(lines) # returns time-ordered list

                try:
                    curr_section_first_ts = t[0] # grabs the first timestanp of the section
                except:
                    time.sleep(0.1) # wait a while for data to come in
                if curr_section_first_ts < prev_section_last_ts: # compares the first timestamp of the section to the last timestamp of the previous section
                    t = np.array(t) + np.ceil((prev_section_last_ts - curr_section_first_ts)/periode_duration)*periode_duration # make up for rollover
                prev_section_last_ts = t[-1] # update previous section timestamps

                """
                INSERT WHATEVER REAL TIME PROCESS HERE
                """
                # example:
                times = np.append(times,t) # builds a list of times if needed: comment out if you don't need to accumulate e.g. when building a g2
        f.close()
