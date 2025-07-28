"""
This script generates outputs on 2 channel of the DPG to simulate some g2 statistics.
To do this, we exploit the fact that the histogram bins will be much larger than the
step size of the pulses (10ns) so that we can fit more pulses in one bin.

The output is a Mermaid syntax file that will be sent to the DPG_Mermaid_parser.py to
generate a .dpatt file for the Digital Pattern Generator DPG1
"""

from numpy import abs, exp, linspace, round

c1_nim = 0
c2_nim = 2
c1_ttl = 8
c2_ttl = 9
span = 100_000  # 105us
center = 50_000  # 50us
time_const = 35_000  # 20us
histogram_binsize = 21
bin_width = int(span / (histogram_binsize - 1))
peak_counts = 10
peak_counts2 = 5
outfile = "out_anti_bunch.txt"
outfile2 = "out_bunch.txt"


def bunching(x, x0=center, tau_c=time_const):
    return 1 + exp(-2 * abs(x - x0) / tau_c)


def anti_bunching(x, x0=center, tau_c=time_const):
    return 1 - exp(-2 * abs(x - x0) / tau_c)


fn = anti_bunching
fn2 = bunching
x = linspace(0, span, histogram_binsize)
y_counts = round(fn(x) * peak_counts)
y2_counts = round(fn2(x) * peak_counts2)

top_mermaid_string = """flowchart TD
    %%control block for settings of DPG
    %%Settings accepted are {CLOCK}, {evars}, {ivars}, {auxout}, {auxconfig}
    %% {dacconfig}, {inlevel}, {version}, {dacstatic}, {startaddress}, {inthresh}
    control[ivars
    ivars 10, 100
    version 64bit
    ]

    %%sequential blocks
    seq1[ #single
"""

top_seq_string = f"10ns chan {c1_nim} {c1_ttl}\n10ns chan\n"
new_str = ""
current_time = 20
for i, val in enumerate(y_counts.astype(int)):
    bin_i = i * bin_width
    bin_f = (i + 1) * bin_width
    while val > 0:
        new_str += f"10ns chan {c2_nim} {c2_ttl}\n10ns chan\n"
        current_time += 20
        val -= 1
        if current_time > bin_f:
            print(f"point {i} is larger than bin")
    balance = int(bin_f - current_time)
    new_str += f"{balance}ns chan\n"
    current_time += balance

new_str += "    ]\n\n"

end_str = "seq1-->seq1\n"

with open(outfile, "w") as f:
    f.write(top_mermaid_string)
    f.write(top_seq_string)
    f.write(new_str)
    f.write(end_str)

new_str = ""
current_time = 20
for i, val in enumerate(y2_counts.astype(int)):
    bin_i = i * bin_width
    bin_f = (i + 1) * bin_width
    while val > 0:
        new_str += f"10ns chan {c2_nim} {c2_ttl}\n10ns chan\n"
        current_time += 20
        val -= 1
        if current_time > bin_f:
            print(f"point {i} is larger than bin")
    balance = int(bin_f - current_time)
    new_str += f"{balance}ns chan\n"
    current_time += balance

new_str += "    ]\n\n"
with open(outfile2, "w") as f:
    f.write(top_mermaid_string)
    f.write(top_seq_string)
    f.write(new_str)
    f.write(end_str)
