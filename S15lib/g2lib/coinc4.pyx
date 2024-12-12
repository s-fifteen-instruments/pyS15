# 4-fold coincidence counting in Cython
# Justin, 2024-12-12
#
# Compile with the directives 'boundscheck=False' and 'wraparound=False'

# distutils: language=c++
from libcpp.queue cimport queue

ctypedef unsigned long long ull
ctypedef unsigned int uint

cdef struct s_event:
    ull t
    uint p
ctypedef s_event event

cdef int get_window4coincs(int[4] counts, int idx) noexcept:
    """Returns number of coincidences given an event in channel 'idx'.

    The idea is conceptually simple: given a set of counts per channel
    already in the coincidence window, adding a new event in channel 'idx'
    forms new coincidences with every other event in channels other than
    'idx', which is basically the total number of combinations.

    Note:
        Cython optimizes the if-elif chain away as a switch statement.
    """
    if idx == 0:
        return counts[1] * counts[2] * counts[3]
    elif idx == 1:
        return counts[0] * counts[2] * counts[3]
    elif idx == 2:
        return counts[0] * counts[1] * counts[3]
    else:
        return counts[0] * counts[1] * counts[2]

cpdef int count_4coinc(ull[:] ts, uint[:] ps, int coincw_ns):
    """Returns number of 4-fold coincidences within coincidence window.

    The time complexity of this algorithm is O(N) amortized in the number of
    timestamps. This relies on collecting all timestamps within a coincidence window,
    and tracking the number of events per channel for O(1) coincidence counting.

    The format of 'ts' and 'ps' matches exactly that returned by
    'fpfind.lib.parse_timestamps.read_al(fractional=False, resolution=TSRES.NS1)',
    so no additional type casting is necessary. Note that resolutions smaller
    than 1 ns is not supported.

    Args:
        ts (np.array[uint64]): Timestamp values
        ps (np.array[uint32]): Detection pattern values
        coincw_ns (int): Width of coincidence window, in ns

    Note:
        This function takes 23ms per 1M timestamp events on a 2GHz Ryzen 4600GE.

        A computation bottleneck arises from parsing the timestamps (outside of this
        function) since this relies on the 'a1' files having already being parsed by
        the 'read_a1' Python function. This is designed so that timing delays and
        detection patterns can be arbitrary adjusted using numpy in Python.
    """
    cdef int i, j, total = 0, length = len(ts)
    cdef ull t
    cdef uint p
    cdef int[4] ch_counts = [0, 0, 0, 0]
    cdef queue[event] window
    for j in range(length):
        t = ts[j]
        p = ps[j]

        # Flush all invalid events that fall outside or
        # at the boundary of the coincidence window
        cutoff = t - coincw_ns
        while not window.empty() and window.front().t <= cutoff:
            _p = window.front().p
            window.pop()
            for i in range(4):
                if _p & (1 << i) != 0:
                    ch_counts[i] -= 1

        # Count and add coincidences
        for i in range(4):
            if p & (1 << i) != 0:
                total += get_window4coincs(ch_counts, i)
                ch_counts[i] += 1
        window.push([t, p])
    return total

