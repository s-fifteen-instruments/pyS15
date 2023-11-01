cimport cython
import numpy as np
cimport numpy as np

# distutils: define_macros=NPY_NO_DEPRECATED_API=NPY_1_7_API_VERSION
DTYPE = np.int64
ctypedef np.int_t DTYPE_t

@cython.boundscheck(False)  # turn off bounds-checking
@cython.wraparound(False)   # turn off negative index wrapping
@cython.nonecheck(False)
def _delta_loop(double [:] t1 not None,
                double [:] t2 not None,
                int bins,
                double bin_width,
                int l_t1,
                int l_t2):

    cdef np.ndarray histogram = np.zeros(bins, dtype=DTYPE)
    cdef int idx = 0
    cdef int idx2 = 0
    cdef int n, it_b, it_c
    cdef double c, b, k
    cdef double max_range = bins * bin_width
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
                histogram[int(k // bin_width)] += 1
    return histogram

@cython.wraparound(False)   # turn off negative index wrapping
def _cond_delta_loop(double [:] t1 not None,
                     double [:] t2 not None,
                     double [:] t3 not None,
                     int bins,
                     double bin_width,
                     int l_t1,
                     int l_t2,
                     int l_t3):

    cdef np.ndarray histogram_ba = np.zeros(bins, dtype=DTYPE)
    cdef np.ndarray histogram_ca = np.zeros(bins, dtype=DTYPE)
    cdef np.ndarray histogram_bc = np.zeros(bins, dtype=DTYPE)
    cdef np.ndarray histogram_cb = np.zeros(bins, dtype=DTYPE)
    cdef int idx = 0
    cdef int idx2 = 0
    cdef int idx3 = 0
    cdef int idx4 = 0
    cdef int n, m, it_a ,it_b, it_c
    cdef double c, b, a, k
    cdef double max_range = bins * bin_width
    # List while checking t2 first before t3
    for it_a in range(l_t1):
        a = t1[it_a] # current t1
        idx = idx2 # set t2 pos to start
        for it_b in range(l_t2):
            if (it_b + idx) >= l_t2: # protect against buffer overflow
                break
            b = t2[it_b + idx] # get t2 based on start and list index
            if b < a: # t2 still smaller than t1
                idx2 = idx + it_b # store index of t2 for next t1. Don't need to start from the first one again.
                continue # go to next in the t2 list
            else: # t2 larger than t1
                idx3 = idx4 # set t3 pos to start
                for it_c in range(l_t3): # go through t3 list
                    if (it_c + idx3) >= l_t3:
                        break
                    c = t3[it_c + idx3] # get t3 based on start and list index
                    if c < a: # similar to b < a
                        idx4 = idx3 + it_c
                        continue
                    else:
                        k = c - b
                        if k < 0 or  k >= max_range:
                            break
                        histogram_cb[int(k // bin_width)] +=1
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
                        histogram_bc[int(k // bin_width)] +=1
                k = c - a
                if k >= max_range:
                    break
                histogram_ca[int(k // bin_width)] += 1
    return histogram_ba, histogram_ca, histogram_cb, histogram_bc


def delta_loop(t1,
        t2,
        bins: int = 500,
        bin_width_ns: float = 2
        ):
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
    cdef int l_t1 = len(t1)
    cdef int l_t2 = len(t2)
    if isinstance(t1[0],np.int64):
        t1 = np.float64(t1)
        t2 = np.float64(t2)
    return _delta_loop(t1, t2, bins, bin_width_ns, l_t1, l_t2)

def cond_delta_loop(t1,
        t2,
        t3,
        bins: int = 500,
        bin_width_ns: float = 2):
    """Returns time difference histogram from the given lists (t1, t2, t3) containing
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
    cdef int l_t1 = len(t1)
    cdef int l_t2 = len(t2)
    cdef int l_t3 = len(t3)
    return _cond_delta_loop(t1, t2, t3, bins, bin_width_ns, l_t1, l_t2, l_t3)


@cython.boundscheck(False)  # turn off bounds-checking
@cython.wraparound(False)   # turn off negative index wrapping
@cython.nonecheck(False)
def _delta_loop_ts(
    double [:] t1s not None,
    double [:] t2s not None,
    int bins_len,
    double bin_width,
    int t1s_len,
    int t2s_len,
):
    """See documentation for 'delta_loop_ts'."""

    # Define masks
    cdef np.ndarray mask1 = np.zeros(t1s_len, dtype=np.int32)
    cdef np.ndarray mask2 = np.zeros(t2s_len, dtype=np.int32)
    cdef np.ndarray histogram = np.zeros(bins_len, dtype=DTYPE)

    # Define looping variables
    cdef int t1_idx, t2_idx
    cdef int n, t2_idx0 = 0, t2_idx_left = 0
    cdef double t1, t2, dt
    cdef double window_size = bins_len * bin_width

    # Start loop
    for t1_idx in range(t1s_len):
        t1 = t1s[t1_idx]

        # Iterate starting from cached left bound
        n = -1
        t2_idx0 = t2_idx_left
        while True:
            n += 1

            t2_idx = t2_idx0 + n
            if t2_idx >= t2s_len:
                break  # no more valid timestamps

            t2 = t2s[t2_idx]
            if t2 < t1:
                t2_idx_left = t2_idx + 1
                continue  # outside left of window, cache

            dt = t2 - t1
            if dt >= window_size:
                break  # outside right of window, done

            # Store valid coincidence
            mask1[t1_idx] = 1
            mask2[t2_idx] = 1
            histogram[int(dt // bin_width)] += 1

    return histogram, mask1.astype(bool), mask2.astype(bool)

def delta_loop_ts(
    t1,
    t2,
    bins: int = 500,
    bin_width_ns: float = 2,
):
    """Returns histogram and masks for coincidences.

    This is essentially 'delta_loop', but collects the mask values
    for the coincidences as well. This is required to avoid stray
    background not arising from the heralding process, when building
    up the g(3) coincidences.

    In practice, the error from using 'cond_delta_loop' should be
    small due to the large timing separation between consecutive
    photon events in the same channel/detector.

    Args:
        t1: Timestamps of start events.
        t2: Timestamps of stop events.
        bins: Number of histogram bins for coincidence binning.
        bin_width_ns: Bin width, in nanoseconds.

    Returns:
        histogram: Histogram of coincidence window.
        mask1: Mask of t1 for coincidence timestamps.
        mask2: Mask of t2 for coincidence timestamps.

    Examples:
        >>> hist2, _, mask2 = delta_loop_ts(t1, t2, 20, 2)  # 40 ns window of 20 bins, left-aligned at 0
        >>> hist3, _, mask3 = delta_loop_ts(t1, t3, 20, 2)
        >>> hist, m2p, m3p = delta_loop_ts(t2[mask2], t3[mask3]+500, 500, 2)  # 1 us window, centered at 0
        >>> print(f"Trigger 1 rate: {len(t2[mask2])/len(t2)}")
        >>> print(f"Trigger 2 rate: {len(t3[mask3])/len(t3)}")
        >>> print(f"Heralding rate: {len(t2[mask2][m2p])/len(t2[mask2])}")

    TODO:
        Extend this in another function to automatically guess duration.
    """
    cdef int l_t1 = len(t1)
    cdef int l_t2 = len(t2)
    histogram, mask1, mask2 = _delta_loop_ts(t1, t2, bins, bin_width_ns, l_t1, l_t2)

    return histogram, mask1, mask2
