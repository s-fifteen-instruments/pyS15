#!/usr/bin/env python3

from typing import List

import numpy as np

try:
    from .delta import delta_loop
    cflag = True
except ImportError:
    # print('delta.so module not found, using native option')
    def delta_loop(t1: List[float], t2: List[float], bins: int = 500, bin_width_ns: float = 2) -> List[int]:
        """Returns time difference histogram from two given lists (t1, t2) containing timestamps.
           List t1 contains the start times and t2 the stop times. 
           Correlated t2 events should arrive after t1 events, since this function does not look for correlated events before t1 events.

        Args:
            t1 (List[float]): Start times.
            t2 (List[float]): Stop times.
            bins (int, optional): Number of histogram bins. Defaults to 500 bins.
            bin_width_ns (float, optional): Bin width in nano seconds. Defaults to 2 ns.

        Returns:
            List[int]: Time difference histogram.
        """
        histogram = np.zeros(bins)
        idx = 0
        idx2 = 0
        l_t1 = len(t1)
        l_t2 = len(t2)
        max_range = bins * bin_width_ns
        for it_b in range(l_t1):
            b = t1[it_b]
            n = 0
            idx = idx2
            while True:
                if (idx + n) >= l_t2:
                    break
                c = t2[idx + n]
                n += 1
                if c < b:
                    idx2 = idx + n
                    continue
                else:
                    k = c - b
                    if k >= max_range:
                        break
                    histogram[int(k // bin_width_ns)] += 1
        return histogram


def _data_extractor(filename: str, highres_tscard: bool=False):
    """Reads raw timestamp into time and patterns vectors

    Args:
        filename (str): a python file object open in binary mode
        highres_tscard (bool, optional): Flag for the 4ps time resolution card

    Returns:
        (numpy.ndarray(float), numpy.ndarray(uint32)): Two vectors: timestamps, corresponding pattern
    """

    with open(filename, 'rb') as f:
        data = np.fromfile(file=f, dtype='=I').reshape(-1, 2)
        if highres_tscard:
            t = ((np.uint64(data[:, 0]) << 22) + (data[:, 1] >> 10)) / 256.
        else:
            t = ((np.uint64(data[:, 0]) << 17) + (data[:, 1] >> 15)) / 8.
        p = data[:, 1] & 0xf
        return t, p


def g2_extr(filename: str, bins: int=100, bin_width: float=2, min_range: int=0,
            channel_start: int=0, channel_stop: int=1, c_stop_delay: int=0, highres_tscard: bool=False):
    """Generates G2 histogram from a raw timestamp file

    Args:
        filename (str): timestamp file containing raw data
        bins (int, optional): Number of bins for the coincidence histogram. Defaults to 100.
        bin_width (float, optional): Bin width of coincidence histogram in nanoseconds. Defaults to 2.
        min_range (int, optional): Lower range of correlation in nanoseconds. Defaults to 0.
        channel_start (int, optional): Channel of start events. Defaults to 0.
        channel_stop (int, optional): Channel of stop events. Defaults to 1.
        c_stop_delay (int, optional): Adds time (in nanoseconds) to the stop channel time stamps. Defaults to 0.
        highres_tscard (bool, optional): Setting for timestamp cards with higher time resolution. Defaults to False.

    Raises:
        ValueError: When channel is not between 0 - 3. (0: channel 1, 1: channel 2, 2: channel 3, 3: channel 4)

    Returns:
        [int], [float], int, int, int: histogram, time differences, events in channel_start, events in channel_stop, time at last event
    """

    if channel_start not in range(4):
        raise ValueError('Selected start channel not in range')
    if channel_stop not in range(4):
        raise ValueError('Selected stop channel not in range')
    t, p = _data_extractor(filename, highres_tscard)
    # t1 = t[(p & (0b1 << channel_start)) == (0b1 << channel_start)]
    t1 = t[p == (0b1 << channel_start)]
    # t2 = t[(p & (0b1 << channel_stop)) == (0b1 << channel_stop)]
    t2 = t[p == (0b1 << channel_stop)]

    hist = delta_loop(t1, t2 - min_range + c_stop_delay, bins=bins,
                      bin_width_ns=bin_width)
    try:
        t_max = t[-1] - t[0]
    except IndexError:
        t_max = 0
    dt = np.arange(0, bins * bin_width, bin_width)
    return hist, dt + min_range, len(t1), len(t2), t_max


def peak_finder(t1_series: List[float], t2_series: List[float], t_resolution: float, buffer_length: int):
    def resample_and_fold_t(time_series, dt, samples):
        new_signal = np.zeros(samples)
        for i in time_series:
            sample_nr = int(i / dt) % samples
            new_signal[sample_nr] += 1
        return new_signal
    n = 2**buffer_length
    t1_series = resample_and_fold_t(t1_series, t_resolution, n)
    t2_series = resample_and_fold_t(t2_series, t_resolution, n)
    t1_fft = np.fft.fft(t1_series)
    t2_fft = np.fft.fft(t2_series)
    convolution = np.fft.ifft(np.multiply(np.conj(t1_fft), t2_fft))
    t_array = np.arange(0, n * t_resolution, t_resolution)
    idx_max = np.argmax(convolution)
    return t_array[idx_max], convolution, t_array



if __name__ == '__main__':
    import timeit
    filename = './test.raw'
    _data_extractor(filename)
    # g2_time = timeit.timeit('g2_extr(filename)', number=100, globals=globals())
    # print(g2_time / 100)
