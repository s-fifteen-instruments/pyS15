#!/usr/bin/env python3
# S-Fifteen Instruments, 2022-12-01
# Simple script to continuously feed pair source optimization statistics
#
# Python port of 'inst_efficiency.sh' from CQT
#
# Example:
# ./inst_efficiency.py
#
# Obtained histogram:
#       0       0       0       0      13     170     289     412
#     441     509     474     482     493     483     498     446
#     620   11089   57358    1836     654     495     411     401
#     554     601     562     564     435     336     693     714
#     546     416     423     510     619     629     496     417
# Maximum 57358 @ index 18
#
#    TIME   PAIRS     ACC SINGLE1 SINGLE2    EFF1    EFF2 EFF_AVG
#  181533   49405 10937.3  602536  451915    10.9     8.2     9.5
#  181537   48641 10762.8  591921  446168    10.9     8.2     9.5
#  181541   48976 10786.3  597189  449125    10.9     8.2     9.5
#  181544   48692 10737.5  593972  444109    11.0     8.2     9.5
#  181550   48503 10707.9  592597  445542    10.9     8.2     9.4
#  181555   49083 10873.9  602213  452347    10.9     8.2     9.4
#  181601   49146 10863.2  602124  452245    10.9     8.2     9.4
#  181607   48976 10877.5  604058  450367    10.9     8.1     9.4
#  181613   48998 10851.1  601716  452697    10.8     8.1     9.4

import datetime as dt

import numpy as np

from S15lib.g2lib import g2lib as g2
from S15lib.instruments import TimestampTDC2

timestamp = TimestampTDC2(
    readevents_path="/home/belgianwit/projects/qkd_asyktp/bin/readevents7",
    outfile_path="/tmp/quick_timestamp",
)

# Set coincidence window
WINDOW_START = 18
WINDOW_STOP = 21
BIN_WIDTH = 2
BINS = 40


def print_fixedwidth(*values, width=7):
    """Prints right-aligned columns of fixed width."""
    line = " ".join([f"{str(value): >7s}" for value in values])
    print(line)


def monitor():
    """Prints out pair source statistics."""
    i = 0
    window_size = WINDOW_STOP - WINDOW_START + 1
    acc_start = (BINS - WINDOW_STOP) // 2  # location to compute accidentals
    is_initialized = False
    while True:

        # Invoke timestamp data recording
        timestamp._call_with_duration(["-a1", "-X"])

        # Extract g2 histogram and other data
        data = g2.g2_extr(
            "/tmp/quick_timestamp",
            channel_start=0,
            channel_stop=3,
            highres_tscard=True,
            bin_width=BIN_WIDTH,
            bins=BINS,
        )
        hist = data[0]

        # Visualize g2 histogram
        if not is_initialized:
            is_initialized = True
            a = np.array(hist, dtype=np.int64)
            print("\nObtained histogram:")
            [print_fixedwidth(*row) for row in a.reshape(-1, 8)]
            print(f"Maximum {max(a)} @ index {np.argmax(a)}\n")

        # Calculate statistics
        s1, s2 = data[2:4]
        acc = window_size * np.mean(hist[acc_start:])
        pairs = sum(hist[WINDOW_START : WINDOW_STOP + 1]) - acc
        e1 = 100 * pairs / s2
        e2 = 100 * pairs / s1
        eavg = 100 * pairs / (s1 * s2) ** 0.5

        # Print the header line after every 10 lines
        if i == 0:
            i = 10
            print_fixedwidth(
                "TIME", "PAIRS", "ACC", "SINGLE1", "SINGLE2", "EFF1", "EFF2", "EFF_AVG"
            )
        i -= 1

        # Print statistics
        print_fixedwidth(
            dt.datetime.now().strftime("%H%M%S"),
            int(pairs),
            round(acc, 1),
            int(s1),
            int(s2),
            round(e1, 1),
            round(e2, 1),
            round(eavg, 1),
        )


monitor()
