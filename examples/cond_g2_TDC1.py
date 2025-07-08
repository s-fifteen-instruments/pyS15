"""
This is an example script to collect a triggered/conditional g2 using 3 channels of
S-Fifteen Instruments Timestamp TDC1.

The trigger is connected to input 1 while the g2 is done between channels 2 and 3.
The delays between channel 2(3) and 1 is noted in t2_delay(t3_delay).

A g2 histogram with bins(51) of bin_width_ns(2) is calculated
First plot shows the normal histograms of the 4 time-correlation between channels
- 1 and 2
- 1 and 3
- 2 and 3 given a trigger in 1
- 3 and 2 given a trigger in 1

The last plot is the calculated normalised conditional g2.
ref.: Coherence measures for heralded single-photon sources
      https://doi.org/10.48550/arXiv.0807.1725

"""
import matplotlib.pyplot as plt
import numpy as np

from S15lib.g2lib import g2lib as g2
from S15lib.instruments import TimestampTDC1

int_time = 1

filename = "./data/dat.dat"
ts = TimestampTDC1()
t, p = ts.get_timestamps(int_time, legacy=True)
p = np.array(p)
pat1 = "0001"
pat2 = "0010"
pat3 = "0100"

t1 = t[p == pat1]
t2 = t[p == pat2]
t3 = t[p == pat3]

integration_time_ns = t[-1] - t[0]
bins = 51
bins_plot = 21
bin_width_ns = 2
center = bins // 2 * bin_width_ns
t2_delay = 21
t3_delay = 1
x = np.linspace(0, (bins - 1) * bin_width_ns, bins) - (bins // 2) * bin_width_ns
h12 = g2.delta_loop(
    t1,
    t2 - t2_delay + center,
    bins=bins,
    bin_width_ns=bin_width_ns,
)
h13 = g2.delta_loop(
    t1,
    t3 - t3_delay + center,
    bins=bins,
    bin_width_ns=bin_width_ns,
)
h123 = g2.cond_delta_loop(
    t1,
    t2 - t2_delay + center,
    t3 - t3_delay + center,
    bins=bins,
    bin_width_ns=bin_width_ns,
)

x2 = (
    np.linspace(0, (2 * bins - 2) * bin_width_ns, 2 * bins - 1)
    - (bins - 1) * bin_width_ns
)

h12_R2 = len(t1) * len(t2) / integration_time_ns * bin_width_ns
h13_R2 = len(t1) * len(t3) / integration_time_ns * bin_width_ns
h12_norm = h12 / h12_R2
h13_norm = h13 / h13_R2
plt.plot(
    x,
    h12_norm,
    label="g12",
)
plt.plot(
    x,
    h13_norm,
    label="g13",
)
plt.plot(
    x,
    h123[2],
    label="g23|1",
)
plt.plot(
    x,
    h123[3],
    label="g32|1",
)

plt.legend()
plt.show()

coinc_window = 4
c0 = -coinc_window / 2
c1 = coinc_window / 2
N = len(t1)
t_plot = (
    np.linspace(0, (bins_plot - 1) * bin_width_ns, bins_plot)
    - (bins_plot // 2) * bin_width_ns
)
norm_int = np.zeros(np.size(t_plot))
norm_int_err = np.zeros(np.size(t_plot))
fixed_idx = np.logical_and(x >= c0, x < c1)
g_si1f = h123[0][fixed_idx]
g_si2f = h123[1][fixed_idx]
for i in range(len(t_plot)):
    offset = t_plot[i]
    idx = np.logical_and(x >= offset + c0, x < offset + c1)
    g_si2 = h123[1][idx]
    offset = -t_plot[i]
    idx = np.logical_and(x >= offset + c0, x < offset + c1)
    g_si1 = h123[0][idx]
    # norm_int[i] = np.sum([g_si1f * g_si2])/(bin_width_ns)*4
    norm_int[i] = np.sum([g_si1f * g_si2, g_si2f * g_si1]) / (bin_width_ns) * 2
    norm_int_err[i] = np.sum(g_si1f**2 * g_si2 + g_si2**2 * g_si1f)

idx = np.logical_and(x >= t_plot[0], x <= t_plot[-1])
G_si1i2 = h123[3][idx]
G_si1i2_err = np.sqrt(G_si1i2)

g_2cond = G_si1i2 * N / norm_int
g_2cond_err = np.sqrt(
    (G_si1i2_err / norm_int) ** 2 + (G_si1i2_err * norm_int_err / (norm_int**2) ** 2)
)

plt.plot(t_plot, g_2cond, label="g_2cond")
plt.legend()
plt.xlabel("Delay(ns)")
plt.ylabel("g2")
# plt.savefig(filename + '.pdf')
plt.show()
