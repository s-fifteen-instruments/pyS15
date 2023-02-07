cimport cython
import numpy as np
cimport numpy as np

DTYPE = np.int
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

@cython.boundscheck(False)  # turn off bounds-checking
@cython.wraparound(False)   # turn off negative index wrapping
@cython.nonecheck(False)
def _cond_delta_loop(double [:] t1 not None,
                     double [:] t2 not None,
                     double [:] t3 not None,
                     int bins,
                     double bin_width,
                     int l_t1, 
                     int l_t2,
                     int l_t3):

    cdef np.ndarray histogram_a = np.zeros(bins, dtype=DTYPE)
    cdef np.ndarray histogram_b = np.zeros(bins, dtype=DTYPE)
    cdef np.ndarray histogram_c = np.zeros(bins, dtype=DTYPE)
    cdef int idx = 0
    cdef int idx2 = 0
    cdef int idx3 = 0
    cdef int idx4 = 0
    cdef int n, m, it_a ,it_b, it_c
    cdef double c, b, a, k
    cdef double max_range = bins * bin_width
    for it_a in range(l_t1):
        a = t1[it_a]
        n = 0
        m = 0
        idx = idx2
        idx3 = idx4
        while True:
            if (idx + n) >= l_t2:
                break
            b = t2[idx + n]
            n += 1
            if b < a:
                idx2 = idx + n
                continue
            else:
                k = b - a
                if not k >= max_range:
                    histogram_a[int(k // bin_width)] += 1
                else:
                    continue
                if (idx3 + m) >= l_t2:
                    break
                c = t3[idx3 + m]
                m += 1
                if c < a:
                    idx4 = idx3 + m 
                    continue
                else:
                    k = c - a
                    if not k >= max_range:
                        histogram_b[int(k // bin_width)] += 1
                    else:
                        continue
                    k = b - a 
                    if not k >= max_range:
                        histogram_c[int(k // bin_width)] += 1
                    else:
                        break
    return histogram_a, histogram_b, histogram_c


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
    return _delta_loop(t1, t2, bins, bin_width_ns, l_t1, l_t2)

def cond_delta_loop(t1,
        t2,
        t3,
        bins: int = 500,
        bin_width_ns: float = 2):
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
    cdef int l_t3 = len(t3)
    return _cond_delta_loop(t1, t2, t3, bins, bin_width_ns, l_t1, l_t2, l_t3)
