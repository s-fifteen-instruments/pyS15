#!/usr/bin/env python3

"""
USB mini counter based on FPGA

Collection of functions to simplify the integration of the USB counter in
Python scripts.
"""

import glob
import numpy as np
import subprocess
from typing import Tuple

import time

from ..g2lib import g2lib


from os.path import exists, expanduser
from tempfile import NamedTemporaryFile

from . import serial_connection

READEVENTS_PROG = expanduser("~") + "/programs/usbcntfpga/apps/readevents4a"


def pattern_to_channel(pattern):
    if pattern == 4:
        return 3
    elif pattern == 8:
        return 4
    elif pattern == 1 or pattern == 2 or pattern == 0:
        return pattern


class TimeStampTDC1(object):
    """
    The usb counter is seen as an object through this class,
    inherited from the generic serial one.
    """
    DEVICE_IDENTIFIER = 'TDC1'

    def __init__(self, device_path=None,
                 integration_time=1000,
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
        self._com = serial_connection.SerialConnection(device_path)
        self._prog = READEVENTS_PROG
        if exists(self._prog):
            self._use_native_timestamps_acq = False
        else:
            self._use_native_timestamps_acq = True
        self._com.write(b'*rst\r\n')
        self._com.readlines()
        self._com.write(b'mode?\r\n')
        self._com.readline()
        self.mode = mode
        self.level = level
        self.int_time = integration_time

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
        self._int_time = int(self._com._getresponse_1l('TIME?'))
        return self._int_time / 1000

    @int_time.setter
    def int_time(self, value: float):
        value *= 1000
        if value < 1:
            print('Invalid integration time.')
        else:
            self._com.write('time {:d};time?\r\n'.format(int(value)).encode())
            self._int_time = int(self._com.readline().decode().strip())

    def get_counts(self):
        """
        Return the actual number of count read from the device buffer.
        :return: a three-element array
        :rtype: {int}
        """
        # self.mode = 'singles'
        return [int(x)
                for x
                in self._com._getresponse_1l('singles;counts?', self._int_time + 0.05).split()]

    @property
    def mode(self):
        self._mode = int(self._com._getresponse_1l('MODE?'))
        if self._mode == 0:
            return 'singles'
        if self._mode == 1:
            return 'pairs'
        if self._mode == 2:
            return 'timestamp'

    @mode.setter
    def mode(self, value):
        if value.lower() == 'singles':
            self._mode = 0
            self._com.write(b'singles\r\n')
        if value.lower() == 'pairs':
            self._mode = 1
            self._com.write(b'pairs\r\n')
        if value.lower() == 'timestamp':
            self._mode = 3
            self._com.write(b'timestamp\r\n')
        time.sleep(0.1)

    @property
    def level(self):
        """ Set the kind of pulses to count"""
        return self._com._getresponse_1l('LEVEL?')

    @level.setter
    def level(self, value):
        if value.lower() == 'nim':
            self._com.write(b'NIM\r\n')
        elif value.lower() == 'ttl':
            self._com.write(b'TTL\r\n')
        else:
            print('Acceptable input is either \'TTL\' or \'NIM\'')
        time.sleep(0.1)

    @property
    def clock(self):
        """ Choice of clock"""
        return self._com._getresponse_1l('REFCLK?')

    @clock.setter
    def clock(self, value):
        self._com.write('REFCLK {}\r\n'.format(value).encode())

    """ Functions for the timestamp mode"""

    def _timestamp_acq(self, t_acq, out_file_buffer):
        """ Write the binary output to a buffer"""
        if self._mode != 3:
            self.mode = 'timestamp'
        # for short acquisition times (<65 s) we can reply on the FPGA timer
        if t_acq > 65:
            self._timestamp_acq_LT(t_acq, out_file_buffer)
        else:
            self._timestamp_acq_ST(t_acq, out_file_buffer)

    def _timestamp_acq_LT(self, t_acq, out_file_buffer):
        """ Write the binary output to a buffer for total measurement
        times longer than 65 seconds"""
        p1 = subprocess.Popen([self._prog,
                               '-U', self._device_path,
                               '-a', '1',
                               '-g', '{}'.format(int(0)),
                               '-X'],
                              stdout=out_file_buffer,
                              stderr=subprocess.PIPE)
        time.sleep(t_acq)
        p1.kill()

    def _timestamp_acq_ST(self, t_acq, out_file_buffer):
        """ Write the binary output to a buffer for total measurement
        times longer than 65 seconds"""
        subprocess.check_call([self._prog,
                               '-U', self._device_path,
                               '-a', '1',
                               '-g', '{}'.format(int(t_acq * 1000)),
                               '-X'],
                              stdout=out_file_buffer,
                              stderr=subprocess.PIPE)

    def timestamp_acq(self, t_acq, out_file):
        """ Write the binary output to a file"""
        with open(out_file, 'wb') as of:
            self._timestamp_acq(t_acq, of)


    def get_timestamps(self, t_acq: float=1, level: str= 'NIM') -> Tuple[list, list]:
        '''Acquires timestamps and returns 2 lists. The first one containing the time and the second
        the event channel. 

        Keyword Arguments:
            t_acq {float} -- Duration of the the timestamp acquisition in seconds (default: {1})
        '''
        buffer = self._com._stream_response_into_buffer(
            '*RST;INPKT;' + level + ';time ' + str(t_acq * 1000) + ';timestamp;counts?', t_acq + 0.1)

        # buffer contains the timestamp information in binary.
        # We need to convert them into time and identify the event channel.
        # each timestamp is 32 bits long.
        ts_list = []
        event_channel_list = []
        ts_length = 32 / 8  # bits
        periode_duration = 2**28 * 2  # in nano seconds
        periode_counter = 0

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
            prev_ts = time_stamp
            # prev_pattern = pattern
            if (pattern & 0x10) == 0:
                ts_list.append(time_stamp + periode_duration * periode_count)
                event_channel_list.append(pattern_to_channel(pattern & 0xf))

        ts_list = np.array(ts_list) * 2
        event_channel_list = np.array(event_channel_list)
        return ts_list, event_channel_list

    def count_g2(self, t_acq: float, bin_width: int=2, bins: int=500, ch_start:int=1, ch_stop:int=2, ch_stop_delay:float=0):
        """Returns pairs and singles counts from usbcounter timestamp data.

        Computes g2 between channels 1 and 2 of timestamp
        and sum the coincidences within specified window

        :param t_acq: acquisition time in seconds
        :type t_acq: float
        :returns: ch_start counts, ch_stop counts, actual acquistion time
        :rtype: {int, int, int, float, float}
        """

        # open a temporary file to store the processed g2
        if self._use_native_timestamps_acq is False:
            with NamedTemporaryFile() as f_raw:
                self._timestamp_acq(t_acq, f_raw)
                f_raw.seek(0)
                g2, t_bins, s1, s2, time_total = g2lib.g2_extr(f_raw.name,
                                                               bins=bins,
                                                               bin_width=bin_width,
                                                               channel_start=ch_start,
                                                               channel_stop=ch_stop,
                                                               c_stop_delay=ch_stop_delay)
            # calculates the pairs from the processed g2
            # pairs = np.sum(g2 * self._mask_coinc)

            # estimates accidentals for the integration time-window
            # acc = np.sum(g2 * self._mask_acc) * self._acc_corr
            return {'channel1': s1, 
                    'channel2': s2, 
                    'total_time': time_total}, t_bins, g2
        else:
            print('use python readevents')
            bins = 500
            bin_width = 2
            t, channel = self.get_timestamps(t_acq)
            # print(channel)
            t_ch1 = t[channel == ch_start]
            t_ch2 = t[channel == ch_stop]
            histo = g2lib.delta_loop(
                t_ch1, t_ch2 + ch_stop_delay, bins=bins, bin_width=bin_width)
            total_time = t[-1]
            return {'channel1': len(t_ch1),
                    'channel2': len(t_ch2),
                    'total_time': total_time}, np.arange(0, bins * bin_width, bin_width), histo


if __name__ == '__main__':
    fpga = TimeStampTDC1()

    # record events for 1s and store it in test.raw
    fpga.timestamp_acq(1, 'test.raw')

    # generates the conincidence histogram from data stored in test.raw
    histogram, dt, s1, s2, time_total = g2lib.g2_extr('test.raw', 1000, 2000)
    print(s1, s2, time_total)

    # Counts singles, pairs, coincidences, and estimates accidentals
    fpga.binwidth = 16
    fpga.maxbins = 500
    fpga.range = [48, 54]
    fpga.acc_range = [100, 300]
    output = fpga.counts(5)
    print(output)
    rate1 = output['channel1'] / output['total_time']
    rate2 = output['channel2'] / output['total_time']
    print('rate ch1: {0:.3e} counts/s\n'
          'rate ch2: {1:.3e} counts/s'.format(rate1, rate2))
