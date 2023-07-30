#!/usr/bin/env python3

import typing
from typing import List, Optional, Union

import numpy as np
import pyximport

pyximport.install(language_level=3)

try:
    from S15lib.g2lib.delta import cond_delta_loop

    cflag = True
except ImportError:
    print("Unable to import Cython conditional g2 module, using native option")

    def _cond_delta_loop(t1, t2, t3, bins, bin_width, l_t1, l_t2, l_t3):
        histogram_ba = np.zeros(bins, dtype=float)
        histogram_ca = np.zeros(bins, dtype=float)
        histogram_bc = np.zeros(bins, dtype=float)
        histogram_cb = np.zeros(bins, dtype=float)
        idx = 0
        idx2 = 0
        idx3 = 0
        idx4 = 0
        max_range = bins * bin_width
        # List while checking t2 first before t3
        for it_a in range(l_t1):
            a = t1[it_a]  # current t1
            idx = idx2  # set t2 pos to start
            for it_b in range(l_t2):
                if (it_b + idx) >= l_t2:  # protect against buffer overflow
                    break
                b = t2[it_b + idx]  # get t2 based on start and list index
                if b < a:  # t2 still smaller than t1
                    idx2 = (  # Store index of t2 for next t1.
                        idx + it_b  # Don't need to start from the first one again.
                    )
                    continue  # go to next in the t2 list
                else:  # t2 larger than t1
                    idx3 = idx4  # set t3 pos to start
                    for it_c in range(l_t3):  # go through t3 list
                        if (it_c + idx3) >= l_t3:
                            break
                        c = t3[it_c + idx3]  # get t3 based on start and list index
                        if c < a:  # similar to
                            idx4 = idx3 + it_c
                            continue
                        else:
                            k = c - b
                            if k < 0 or k >= max_range:
                                break
                            histogram_cb[int(k // bin_width)] += 1
                    k = b - a
                    if k >= max_range:
                        break
                    histogram_ba[int(k // bin_width)] += 1
        # List while checking t3 first before t2
        idx2 = 0
        idx4 = 0
        for it_a in range(l_t1):
            a = t1[it_a]
            idx = idx2
            for it_c in range(l_t3):
                if (it_c + idx) >= l_t3:
                    break
                c = t3[it_c + idx]
                if c < a:
                    idx2 = idx + it_c
                    continue
                else:
                    idx3 = idx4
                    for it_b in range(l_t2):
                        if (it_b + idx3) >= l_t2:
                            break
                        b = t2[it_b + idx3]
                        if b < a:
                            idx4 = idx3 + it_b
                            continue
                        else:
                            k = b - c
                            if k < 0 or k >= max_range:
                                break
                            histogram_bc[int(k // bin_width)] += 1
                    k = c - a
                    if k >= max_range:
                        break
                    histogram_ca[int(k // bin_width)] += 1
        return histogram_ba, histogram_ca, histogram_cb, histogram_bc

    def cond_delta_loop(t1, t2, t3, bins: int = 500, bin_width_ns: float = 2):
        """Returns time difference histogram from the given lists (t1, t2, t3) with
           timestamps. List t1 contains the heralding times and t2, t3 the signal times.
           Correlated t2, t3 events should arrive after t1 events, since this function
           does not look for correlated events before t1 events.
        Args:
            t1 (List[float]): heralding times.
            t2 (List[float]): Start/Stop times.
            t3 (List[float]): Start/Stop times.
            bins (int, optional): Number of histogram bins. Defaults to 500 bins.
            bin_width_ns (float, optional): Bin width in nano seconds. Defaults to 2 ns.
        Returns:
            List[int]: Time difference histogram between t2 and t1.
            List[int]: Time difference histogram between t3 and t1.
            List[int]: Time difference histogram between t3 and t2 given a .
            List[int]: Time difference histogram.
        """
        l_t1 = len(t1)
        l_t2 = len(t2)
        l_t3 = len(t3)
        return _cond_delta_loop(t1, t2, t3, bins, bin_width_ns, l_t1, l_t2, l_t3)


# Indicates success import of Cython g2 script
CFLAG = False
try:
    from S15lib.g2lib.delta import delta_loop

    CFLAG = True
except ImportError:
    # print('delta.so module not found, using native option')
    def delta_loop(
        t1: List[float], t2: List[float], bins: int = 500, bin_width_ns: float = 2
    ) -> List[int]:
        """Returns time difference histogram from two given lists (t1, t2) containing
           timestamps. List t1 contains the start times and t2 the stop times.
           Correlated t2 events should arrive after t1 events, since this function
           does not look for correlated events before t1 events.

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


def _data_extractor(filename: str, highres_tscard: bool = False):
    """Reads raw timestamp into time and patterns vectors

    Args:
        filename (str): a python file object open in binary mode
        highres_tscard (bool, optional): Flag for the 4ps time resolution card

    Returns:
        (numpy.ndarray(float), numpy.ndarray(uint32)):
          Two vectors: timestamps, corresponding pattern
    """

    with open(filename, "rb") as f:
        data = np.fromfile(file=f, dtype="=I").reshape(-1, 2)
        if highres_tscard:
            t = ((np.uint64(data[:, 0]) << 22) + (data[:, 1] >> 10)) / 256.0
        else:
            t = ((np.uint64(data[:, 0]) << 17) + (data[:, 1] >> 15)) / 8.0
        p = data[:, 1] & 0xF
        return t, p


def cond_g2_extr():
    """Unimplemented yet. Use cond_delta_loop() directly"""
    cond_delta_loop()
    return


def g2_extr(
    filename: str,
    bins: int = 100,
    bin_width: float = 2,
    min_range: int = 0,
    channel_start: int = 0,
    channel_stop: int = 1,
    c_stop_delay: int = 0,
    highres_tscard: bool = False,
    normalise: bool = False,
):
    """Generates G2 histogram from a raw timestamp file

    Args:
        filename (str): timestamp file containing raw data
        bins (int, optional):
            Number of bins for the coincidence histogram. Defaults to 100.
        bin_width (float, optional):
            Bin width of coincidence histogram in nanoseconds. Defaults to 2.
        min_range (int, optional):
            Lower range of correlation in nanoseconds. Defaults to 0.
        channel_start (int, optional): Channel of start events. Defaults to 0.
        channel_stop (int, optional): Channel of stop events. Defaults to 1.
        c_stop_delay (int, optional):
            Adds time (in nanoseconds) to the stop channel time stamps. Defaults to 0.
        highres_tscard (bool, optional):
            Setting for timestamp cards with higher time resolution. Defaults to False.
        normalise (bool, optional):
            Setting to normalise the g2 with N1*N2*dT/T . Defaults to False.

    Raises:
        ValueError: When channel is not between 0 - 3.
            (0: channel 1, 1: channel 2, 2: channel 3, 3: channel 4)

    Returns:
        [int], [float], int, int, int:
            histogram, time differences, events in channel_start,
            events in channel_stop, time at last event
    """

    if channel_start not in range(4):
        raise ValueError("Selected start channel not in range")
    if channel_stop not in range(4):
        raise ValueError("Selected stop channel not in range")
    t, p = _data_extractor(filename, highres_tscard)
    # t1 = t[(p & (0b1 << channel_start)) == (0b1 << channel_start)]
    t1 = t[p == (0b1 << channel_start)]
    # t2 = t[(p & (0b1 << channel_stop)) == (0b1 << channel_stop)]
    t2 = t[p == (0b1 << channel_stop)]

    hist = delta_loop(
        t1, t2 - min_range + c_stop_delay, bins=bins, bin_width_ns=bin_width
    )
    try:
        t_max = t[-1] - t[0]
        if normalise:
            N = len(t1) * len(t2) / t_max * bin_width
            hist = hist / N
    except IndexError:
        t_max = 0
        if normalise:
            print("Unable to normalise, intergration time error")
    dt = np.arange(0, bins * bin_width, bin_width)
    return hist, dt + min_range, len(t1), len(t2), t_max


def peak_finder(
    t1_series: List[float],
    t2_series: List[float],
    t_resolution: float,
    buffer_length: int,
):
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


@typing.no_type_check
def histogram(
    alice: list,
    bob: list,
    duration: Union[float, tuple[float, float]],
    resolution: float = 1,
    center: float = 0.0,
    statistics: bool = False,
    window: Optional[Union[float, tuple[float, float]]] = None,
):
    """Returns the coincidence histogram and corresponding (left-edge) bin timings.

    This is a convenience function for commonly used routines when extracting
    information from a coincidence measurement. This wraps the 'delta_loop'
    function.

    'duration' specifies the minimum window of the histogram, in nanoseconds.
    If 'duration' is a number, the duration is distributed evenly across the 'center'
    time, otherwise 'duration' is a 2-tuple of offsets from the 'center'. The end
    offset is inclusive, i.e. there will be an extra rightmost bin.

    'window' specifies the minimum window of the expected signal in the histogram,
    in nanoseconds. Functionally similar to 'duration', but applied to the signal
    instead. Used only if 'statistics' is True. If 'window' is not supplied, the
    window size is assumed to be half the histogram duration, centered at 'center'.

    If 'statistics' is True, then a third argument containing relevant statistical
    properties will be returned.

    Args:
        alice: First (earlier) set of timestamps.
        bob: Second (later) set of timestamps.
        duration: Minimum window for histogram, in ns.
        resolution: Size of each timing bin for histogram, in ns.
        center: Center of the histogram/signal, in ns.
        statistics: Whether statistics should be computed.
        window: Minimum window for signal in histogram, in ns.

    Examples:

        >>> a = [1,2,52]; b = [2,52]
        >>> def _viz(args):
        ...     if len(args) > 2:
        ...         print(f"Significance: {args[2]['significance']}")
        ...         return
        ...     bins = np.array(args[1]);          hist = np.array(args[0])
        ...     bins = bins[np.flatnonzero(hist)]; hist = hist[hist != 0]
        ...     return list(zip(bins, hist))

        ###################
        #  Regular usage  #
        ###################

        >>> _viz(histogram(a, b, duration=100))
        [(-50.0, 1), (0.0, 2), (1.0, 1), (50.0, 1)]
        >>> _viz(histogram(a, b, duration=(-1, 50), resolution=1))
        [(0.0, 2), (1.0, 1), (50.0, 1)]

        ###################
        #  Adjust center  #
        ###################

        >>> _viz(histogram(a, b, duration=50, resolution=2, center=-25))
        [(-51.0, 1), (-1.0, 2), (1.0, 1)]
        >>> _viz(histogram(a, b, duration=50, resolution=2, center=-26))
        [(-50.0, 1), (0.0, 3)]
        >>> _viz(histogram(a, b, duration=(-50, 0), resolution=2))  # alternate usage
        [(-50.0, 1), (0.0, 3)]

        #######################
        #  Obtain statistics  #
        #######################

        >>> _viz(histogram(a, b, duration=100, statistics=True, window=50))
        Significance: 10.002
        >>> _viz(histogram(a, b, duration=100, statistics=True))
        Significance: 10.002
        >>> _viz(histogram(a, b, duration=100, statistics=True, window=(0, 1)))
        Significance: 14.072

    Bugs:
        Currently insensitive to the sign of the numbers in 'duration' and 'window',
            when specified as a 2-tuple, i.e. 'left' is always assumed to the left of
            the center.
    """
    # Convert timestamps into ndarrays for vectorization
    alice = np.array(alice, dtype=np.float64)
    bob = np.array(bob, dtype=np.float64)

    # Extract duration information and align start time
    try:
        left, right = duration
        duration = right - left
    except TypeError:
        left = right = duration / 2  # split between both sides equally

    num_bins_left = int(
        np.ceil(np.abs(left) / resolution)
    )  # ensure left/right bins cover at least duration
    num_bins_right = int(np.ceil(np.abs(right) / resolution))
    num_bins = (
        num_bins_left + num_bins_right + 1
    )  # +1 to accomodate an additional rightmost bin

    # Compute histogram
    time_offset = np.float64(center) - num_bins_left * resolution
    hist = delta_loop(alice, bob - time_offset, num_bins, resolution)
    bins = time_offset + np.arange(num_bins) * resolution
    bins = np.round(
        bins, 8
    )  # correct for floating errors, up to 1/256 ns (i.e. 8 decimals)

    # Early termination if no need to calculate statistics
    if not statistics:
        return hist, bins

    # Obtain coincidence window to identify signal
    stats = {}
    left = right = None
    if window is not None:
        try:
            left, right = window  # relative to center
        except TypeError:
            left = -window / 2  # defaults to balanced left and right
            right = window / 2

    # If still missing, need to guess window, i.e. half the total duration
    # split between each side of the center, but still bounded by full window
    if left is None:
        left = -duration / 4
    if right is None:
        right = duration / 4

    num_windowbins_left = int(np.ceil(np.abs(left) / resolution))
    num_windowbins_right = int(np.ceil(np.abs(right) / resolution))
    bin_offset_left = num_bins_left - min(num_windowbins_left, num_bins_left)
    bin_offset_right = num_bins_left + min(num_windowbins_right, num_bins_right)

    # Extract signal
    signal = hist[bin_offset_left : bin_offset_right + 1]
    background = np.hstack((hist[:bin_offset_left], hist[bin_offset_right + 1 :]))

    # Populate statistics
    stats = {
        "signal": signal,
        "background": background,
        "max": np.inf,
        "mean": 0,
        "stdev": 0,
        "total": 0,
        "significance": np.inf,
        "significance2": np.inf,
    }
    if len(background) != 0:
        stats["mean"] = np.mean(background)
        stats["stdev"] = np.std(background)
    if len(signal) != 0:
        stats["max"] = max(signal)
        stats["total"] = sum(signal) - len(signal) * stats["mean"]
    if stats["stdev"] != 0:
        stats["significance"] = round(
            (stats["max"] - stats["mean"]) / stats["stdev"], 3
        )  # single point
        stats["significance2"] = round(
            stats["total"] / stats["stdev"], 3
        )  # area under signal

    return hist, bins, stats


if __name__ == "__main__":
    filename = "./test.raw"
    _data_extractor(filename)
    # import timeit
    # g2_time = timeit.timeit('g2_extr(filename)', number=100, globals=globals())
    # print(g2_time / 100)
