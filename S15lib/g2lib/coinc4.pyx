# 4-fold coincidence counting in Cython
# Justin, 2024-12-12
#
# Compile with the directives 'boundscheck=False' and 'wraparound=False'

# distutils: language=c++

from libcpp.pair cimport pair
from libcpp.queue cimport queue

ctypedef unsigned long long ull
ctypedef unsigned int uint
ctypedef pair[ull,uint] event2

cdef extern from *:
    """
    typedef unsigned long long ull;
    using event = std::pair<ull,uint>;
    using pq = std::priority_queue<event, std::vector<event>, std::greater<event>>;
    """
    cdef cppclass pq:
        pq() except +
        bint empty()
        void pop()
        void push(event2)
        event2& top()

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

cpdef int count_4coinc_indiv(ull[:] ts1, ull[:] ts2, ull[:] ts3, ull[:] ts4, int coincw_ns):
    """Returns number of 4-fold coincidences within coincidence window.

    Similar to 'count_4coinc', with the exception of the timestamps in separated
    channels to facilitate either delay compensation. This has time complexity of
    O(N log k) with k number of timestamp arrays. Each timestamp array must already be
    in increasing sorted order, otherwise this function produces gibberish.

    Args:
        ts1 (np.array[uint64]): Timestamp values from channel 1
        ts2 (np.array[uint64]): Timestamp values from channel 2
        ts3 (np.array[uint64]): Timestamp values from channel 3
        ts4 (np.array[uint64]): Timestamp values from channel 4
        coincw_ns (int): Width of coincidence window, in ns

    Note:
        This function takes 79ms per 1M timestamp events on a 2GHz Ryzen 4600GE, so about
        30% of the execution speed of 'count_4coinc'.
    """
    cdef int i, j, total = 0
    cdef ull t
    cdef uint p = 0
    cdef int[4] ch_counts = [0, 0, 0, 0]
    cdef queue[event] window

    cdef int[4] ch_idxs = [1, 1, 1, 1]
    cdef int[4] ch_max_idxs = [len(ts1), len(ts2), len(ts3), len(ts4)]
    cdef pq stream

    # Populate first timestamps
    cdef event2 tp
    stream.push([ts1[0], 0])
    stream.push([ts2[0], 1])
    stream.push([ts3[0], 2])
    stream.push([ts4[0], 3])

    while not stream.empty():

        # Get next nearest event from stream
        tp = stream.top()
        stream.pop()
        t = tp.first
        p = tp.second
        i = ch_idxs[p]

        # Replenish stream from timestamp inputs
        if i != ch_max_idxs[p]:
            if p == 0:  # let Cython optimize as switch
                target = ts1
            elif p == 1:
                target = ts2
            elif p == 2:
                target = ts3
            else:
                target = ts4

            tp.first = target[i]
            tp.second = p
            stream.push(tp)
            ch_idxs[p] = i + 1

        # Flush all invalid events that fall outside or
        # at the boundary of the coincidence window
        cutoff = t - coincw_ns
        while not window.empty() and window.front().t <= cutoff:
            _p = window.front().p
            window.pop()
            ch_counts[_p] -= 1

        # Count and add coincidences
        total += get_window4coincs(ch_counts, p)
        ch_counts[p] += 1
        window.push([t, p])

    return total


"""
Manual delay code to delay and merge individual channels, for cross-comparison
between 'count_4coinc' and 'count_4coinc_indiv'.

def channel2pattern(channel):
    return (1 << (channel-1))

def delay(ts, ps, channel, delay=1000, inplace=False):
    if not inplace:
        ps = ps.copy()

    # Extract channel timestamps and apply delay
    mask = (ps & channel2pattern(channel)).astype(bool)
    nts = ts[mask] - delay

    # Remove existing channel events
    ps[mask] &= (0b1111 - channel2pattern(channel))
    mask = (ps == 0)
    if not inplace:
        ts = np.delete(ts, mask)  # remove empty timestamps
        ps = np.delete(ps, mask)
    else:
        _ts = np.delete(ts, mask)
        _ps = np.delete(ps, mask)
        del ts, ps
        ts = _ts
        ps = _ps

    # Add new events - existing timestamps
    mask = np.isin(ts, nts, assume_unique=True)
    ps[mask] |= channel2pattern(channel)  # update pattern

    # Add new events - new timestamps
    nts = nts[np.isin(nts, ts, invert=True, assume_unique=True)]
    target = np.searchsorted(ts, nts)
    ts = np.insert(ts, target, nts)
    ps = np.insert(ps, target, channel2pattern(channel))
    return ts, ps
"""
