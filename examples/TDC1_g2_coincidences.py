# A sample Python script to collect timestamps from 2 input channels and perform a g2
# time correlation histogram (with set integration time and time delay) between them.

from S15lib.instruments import TimeStampTDC1

ch1 = 1
ch2 = 2
ch3 = 3
ch4 = 4

ts = TimeStampTDC1()
ts.level = ts.TTL_LEVELS  # use ts.NIM_LEVELS for nim signals
t_acq = 0.5  # 0.5 sec acquisition time
bin_width = 2  # 2ns time correlation bin width
bins = 40  # number of bins in the g2 histogram output
ch_stop_delay = 2  # time delay added to channel stop in ns
ch_start = ch1  # first input channel selected for g2
ch_stop = ch4  # second input channel selected for g2

c = ts.count_g2(
    t_acq=t_acq,
    bin_width=bin_width,
    bins=bins,
    ch_stop_delay=ch_stop_delay,
    ch_start=ch_start,
    ch_stop=ch_stop,
)

histo = c["histogram"]
time_ax = c["time_bins"]
