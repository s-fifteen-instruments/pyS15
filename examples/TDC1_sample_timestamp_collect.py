# A short example python script to use S-Fifteen Instruments TDC1 for collecting
# timestamps from four input channels into python variables. t1—t4 will hold the
# timestamps (in ns) for 4 different channels respectively. From these timestamps, any
# processing can be done
import numpy as np

from S15lib.instruments import TimeStampTDC1

# channels patterns are defined as below in timestamp mode
ch1 = 1
ch2 = 2
ch3 = 4
ch4 = 8

ts = TimeStampTDC1()
ts.level = ts.TTL_LEVELS  # use ts.NIM_LEVELS for nim signals
"""
ts.threshold = 1.2  # use ts.threshold to set trigger levels other than
                    # NIM or TTL standards between -3.3V and 3.3V
"""
t, p = ts.get_timestamps(t_acq=1)
p_int = np.array([int(i, 2) for i in p])
t1 = t[p_int == ch1]
t2 = t[p_int == ch2]
t3 = t[p_int == ch3]
t4 = t[p_int == ch4]
