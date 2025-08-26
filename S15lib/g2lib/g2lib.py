#!/usr/bin/env python3

import typing
import warnings
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

import numpy as np
from fpfind.lib.parse_timestamps import read_a1

# Indicates success import of Cython g2 script
CFLAG = False
try:
    from S15lib.g2lib.delta import cond_delta_loop, delta_loop

    CFLAG = True
except ImportError:
    warnings.warn("Unable to import Cython conditional g2 module, using native option")

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
        RuntimeError: When no timestamps events are in specified channels.

    Returns:
        [int], [float], int, int, int:
            histogram, time differences, events in channel_start,
            events in channel_stop, time at last event
    """

    if channel_start not in range(4):
        raise ValueError("Selected start channel not in range")
    if channel_stop not in range(4):
        raise ValueError("Selected stop channel not in range")

    if highres_tscard:
        t, p = read_a1(filename, legacy=True, ignore_rollover=True)
    else:
        t, p = _data_extractor(filename, highres_tscard)

    t1 = t[(p & (1 << channel_start)).astype(bool)].astype(np.float64)
    t2 = t[(p & (1 << channel_stop)).astype(bool)].astype(np.float64)
    if t1.size == 0 and t2.size == 0:
        raise RuntimeError(
            "No timestamp events recorded in channels "
            f"{channel_start+1} and {channel_stop+1}."
        )

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


@dataclass
class PeakStatistics:
    signal: list
    background: list

    @property
    def max(self):
        if len(self.signal) == 0:
            return None
        return np.max(self.signal)

    @property
    def mean(self):
        if len(self.background) == 0:
            return None
        return np.mean(self.background)

    @property
    def stdev(self):
        if len(self.background) == 0:
            return None
        return np.std(self.background)

    @property
    def total(self):
        if len(self.signal) == 0:
            return None
        return sum(self.signal) - len(self.signal) * self.mean

    @property
    def significance(self):
        if self.stdev == 0:
            return None
        return round((self.max - self.mean) / self.stdev, 3)

    @property
    def significance_raw(self):
        if self.stdev == 0:
            return None
        full = np.hstack(self.signal, self.background)
        return (np.max(full) - np.mean(full)) / np.std(full)

    @property
    def significance2(self):
        if self.stdev == 0:
            return None
        # Estimate stdev after grouping in bins of 'len(signal)'
        length = (len(self.background) // len(self.signal)) * len(self.signal)
        if length == 0:
            return None
        rebinned = np.sum(
            self.background[:length].reshape(-1, len(self.signal)), axis=1
        )
        stdev = np.std(rebinned)
        if stdev == 0:
            return None
        return round(self.total / stdev, 3)

    @property
    def g2(self):
        if self.mean == 0:
            return None
        return self.max / self.mean


@typing.no_type_check
def histogram(
    alice: list,
    bob: list,
    duration: Union[float, Tuple[float, float]],
    resolution: float = 1,
    center: float = 0.0,
    statistics: bool = False,
    window: Optional[Union[float, Tuple[float, float]]] = None,
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
    stats = PeakStatistics(signal, background)
    return hist, bins, stats


def get_statistics(
    hist: list,
    resolution: Optional[float] = None,
    center: Optional[float] = None,
    window: float = 0.0,
):
    """Returns statistics of histogram, after performing cross-correlation.

    Args:
        hist: Timing histogram to analyze.
        resolution: Resolution of the histogram.
        center: Timing center of the peak, if known beforehand.
        window: Desired timing window width to exclude from background mean calculation.
    """
    # Fallback to simple statistics, if not other arguments supplied
    if resolution is None:
        if center is None:
            return PeakStatistics(hist, hist)
        else:
            raise ValueError("Resolution must be supplied if 'center' is supplied.")

    # Guess non-negative center bin position, assuming aligned at zero
    if center is None:
        bin_center = np.argmax(hist)
    else:
        bin_center = np.abs(center) // resolution
        if center < 0:
            bin_center = len(hist) - bin_center

    # Retrieve size of symmetrical window
    num_windowbins_onesided = int(np.ceil(window / 2 / resolution))
    bin_offset_left = max(0, bin_center - num_windowbins_onesided)
    bin_offset_right = min(len(hist), bin_center + num_windowbins_onesided)

    # Avoid tails of the cross-correlation by taking only half of the spectrum
    # Use-case when same timestamp is used to obtain histogram, resulting in deadtime
    bin_offset_left_bg = bin_offset_left // 2
    bin_offset_right_bg = (len(hist) + bin_offset_right) // 2

    # Retrieve signal
    signal = hist[bin_offset_left : bin_offset_right + 1]
    background = np.hstack(
        (
            hist[bin_offset_left_bg:bin_offset_left],
            hist[bin_offset_right + 1 : bin_offset_right_bg + 1],
        )
    )
    return PeakStatistics(signal, background)


@typing.no_type_check
def generate_fft(
    arr: list,
    num_bins: int,
    time_res: float,
    acq_start: Optional[float] = None,
    duration: Optional[float] = None,
):
    """Returns the FFT and frequency resolution for the set of timestamps.

    Assumes the inputs are real-valued, i.e. the FFT output is symmetrical.

    Args:
        arr: The timestamp series.
        num_bins: The number of bins in the time/frequency domain.
        bin_size: The size of each timing bin, in ns.
        acq_start: The starting time, relative to the first timestamp, in s.
        duration: The duration to capture for the FFT, in ns.

    Note:
        This function is technically not cacheable due to the mutability of
        np.ndarray.
    """
    import scipy  # nested in function

    acq_start = arr[0] if acq_start is None else acq_start * 1e9
    duration = arr[-1] - arr[0] if duration is None else duration * 1e9

    new_arr = arr[np.where((arr >= acq_start) & (arr < (acq_start + duration)))]
    bin_arr = np.bincount(
        np.int64((new_arr // time_res) % num_bins), minlength=num_bins
    )
    return scipy.fft.rfft(bin_arr)


def get_xcorr(afft: list, bfft: list, filter: Optional[list] = None):
    """Returns the cross-correlation.

    Note:
        The conjugation operation on an FFT is essentially a time-reversal
        operation on the original time-series data.
    """
    import scipy  # nested in function

    fft = np.conjugate(afft) * bfft
    if filter is not None:
        fft = fft * filter
    result = scipy.fft.irfft(fft)
    return np.abs(result)


def histogram_fft(
    alice: list,
    bob: list,
    num_bins: int,
    num_wraps: int = 1,
    resolution: float = 1,
    acq_start: Optional[float] = None,
    filter: Optional[list] = None,
    statistics: bool = False,
    center: Optional[float] = None,
    window: float = 0.0,
):
    """Returns the cross-correlation histogram.

    Args:
        acq_start: Starting timing, relative to first common timestamp.
        filter: Optional filter in frequency-space.
    """
    if not isinstance(num_wraps, (int, np.integer)):
        warnings.warn(
            "Number of wraps is not an integer - "
            "statistical significance will be lower."
        )

    duration = num_wraps * num_bins * resolution
    first_timestamp = max(alice[0], bob[0])
    last_timestamp = min(alice[-1], bob[-1])
    if first_timestamp + duration > last_timestamp:
        warnings.warn(
            f"Desired duration of timestamps ({duration} ns) "
            f"exceeds available data ({last_timestamp - first_timestamp} ns)."
        )

    # Normalize timestamps
    alice -= first_timestamp
    bob -= first_timestamp

    # Generate FFT
    afft = generate_fft(alice, num_bins, resolution, acq_start, duration)
    bfft = generate_fft(bob, num_bins, resolution, acq_start, duration)
    result = get_xcorr(afft, bfft, filter)
    bins = np.arange(num_bins) * resolution
    if statistics:
        return result, bins, get_statistics(result, resolution, center, window)
    return result, bins


if __name__ == "__main__":
    filename = "./test.raw"
    _data_extractor(filename)
    # import timeit
    # g2_time = timeit.timeit('g2_extr(filename)', number=100, globals=globals())
    # print(g2_time / 100)
