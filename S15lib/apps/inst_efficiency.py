#!/usr/bin/env python3
# S-Fifteen Instruments, 2022-12-01
# Simple script to continuously feed pair source optimization statistics
#
# Python port of 'inst_efficiency.sh' from CQT
#
# Example:
# ./inst_efficiency.py pairs --profile optimization -L logger
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

import argparse
import datetime as dt
import pathlib
import re
import sys
import time
from itertools import product

import numpy as np
import tqdm

from S15lib.g2lib import g2lib as g2
from S15lib.instruments import LCRDriver, TimestampTDC2

timestamp = TimestampTDC2(
    readevents_path="/home/qitlab/programs/drivers/usbtmst4/apps/readevents7",
    outfile_path="/tmp/quick_timestamp",
)

SETTINGS = {
    "50km": {
        "WINDOW_START": 10,
        "WINDOW_STOP": 11,
        "BIN_WIDTH": 1,
        "BINS_START": 246944,
        "BINS": 100,
    },
    "optimization": {
        "WINDOW_START": 2,
        "WINDOW_STOP": 4,
        "BIN_WIDTH": 1,
        "BINS_START": 38,
        "BINS": 12,
        "DARKCOUNTS_CH1": 5466 + 2600,
        "DARKCOUNTS_CH4": 150,
    },
}

# Constants
INT_MAX = np.iinfo(np.int64).max
INT_MIN = np.iinfo(np.int64).min

# Dynamically assigned constants
# Default configuration specified here
# Coincidence window
WINDOW_START = 0
WINDOW_STOP = 1
BIN_WIDTH = 1
BINS_START = 0
BINS = 1000

# Timestamp settings
INTEGRATION_TIME = 1
THRESHOLD = -0.4

# Dark count rates in cps, for efficiency calc.
DARKCOUNTS_CH1 = 0
DARKCOUNTS_CH2 = 0
DARKCOUNTS_CH3 = 0
DARKCOUNTS_CH4 = 0


def init_settings(profile):
    """Initialize script-wide settings.

    Must be executed first before running any functions in this script.

    This is used to dynamically set the timestamp and g(2) parameters
    so that profiles for different configurations can be quickly
    executed via the command line.

    For examples of which specific parameters are used, refer
    to the global SETTINGS dictionary.
    """
    settings = SETTINGS[profile]
    for param, value in settings.items():
        if param == "THRESHOLD":
            timestamp.threshold = value
        else:
            globals()[param] = value


def _request_filecomment(comment_cache=".inst_efficiency.comment") -> pathlib.Path:
    """Request for comments to append to logfile and returns path to logfile."""

    # If logging is enabled, request for filename
    # Search for any cached comments from previous runs
    path_comment = pathlib.Path(comment_cache)
    if path_comment.is_file():
        with open(path_comment, "r") as f:
            comment = f.read()
    else:
        comment = ""  # default

    # Request for new comment from user, reassign only if issued
    _comment = re.sub(" ", "_", input(f"Enter comment [{comment}]: "))
    if _comment:
        comment = _comment

    # Check writable to location
    path_logfile = _append_datetime_logfile(comment)
    with open(path_logfile, "a") as f:
        f.write("")
    with open(path_comment, "w") as f:
        f.write(comment)

    return path_logfile


def _append_datetime_logfile(comment):
    return dt.datetime.now().strftime(f"%Y%m%d_inst_efficiency_{comment}.log")


def print_fixedwidth(*values, width=7, out=None, pbar=None):
    """Prints right-aligned columns of fixed width."""
    line = " ".join(
        [f"{str(value) if value != INT_MIN else ' ': >7s}" for value in values]
    )
    if pbar:
        pbar.set_description(line)
    else:
        print(line)
    if out:
        with open(out, "a") as f:
            f.write(line + "\n")


#############
#  SCRIPTS  #
#############


def monitor_pairs(enable_hist=False, logfile=None):
    """Prints out pair source statistics, between ch1 and ch4."""
    is_header_logged = False
    i = 0
    window_size = WINDOW_STOP - WINDOW_START + 1
    acc_start = max((BINS + WINDOW_STOP) // 2, 1)  # location to compute accidentals
    is_initialized = False
    while True:

        # Invoke timestamp data recording
        timestamp._call_with_duration(["-a1", "-X"], duration=INTEGRATION_TIME)

        # Extract g2 histogram and other data
        data = g2.g2_extr(
            "/tmp/quick_timestamp",
            channel_start=0,
            channel_stop=3,
            highres_tscard=True,
            bin_width=BIN_WIDTH,
            bins=BINS,
            min_range=BINS_START,
        )
        hist = data[0]
        s1, s2 = data[2:4]
        inttime = data[4] * 1e-9  # convert to units of seconds

        # TODO(Justin, 2022-12-08):
        #     Formalize the integration time check
        if inttime <= 0.75 * INTEGRATION_TIME:
            continue

        # Visualize g2 histogram
        HIST_ROWSIZE = 10
        if not is_initialized or enable_hist:
            is_initialized = True
            a = np.array(hist, dtype=np.int64)
            # Append NaN values until fits number of rows
            a = np.append(a, np.resize(INT_MIN, HIST_ROWSIZE - (a.size % HIST_ROWSIZE)))
            print("\nObtained histogram:")
            for row in a.reshape(-1, HIST_ROWSIZE):
                print_fixedwidth(*row)
            print(f"Maximum {max(a)} @ index {np.argmax(a)}\n")

        # Calculate statistics
        acc = window_size * np.mean(hist[acc_start:])
        pairs = sum(hist[WINDOW_START : WINDOW_STOP + 1]) - acc

        # Normalize to per unit second
        s1 = s1 / inttime - DARKCOUNTS_CH1  # timestamp data more precise
        s2 = s2 / inttime - DARKCOUNTS_CH4
        pairs = pairs / inttime
        acc = acc / inttime

        if s1 == 0 or s2 == 0:
            e1 = e2 = eavg = 0
        else:
            e1 = 100 * pairs / s2
            e2 = 100 * pairs / s1
            eavg = 100 * pairs / (s1 * s2) ** 0.5

        # Print the header line after every 10 lines
        if i == 0 or enable_hist:
            i = 10
            print_fixedwidth(
                "TIME",
                "ITIME",
                "PAIRS",
                "ACC",
                "SINGLE1",
                "SINGLE2",
                "EFF1",
                "EFF2",
                "EFF_AVG",
                out=logfile if not is_header_logged else None,
            )
            is_header_logged = True
        i -= 1

        # Print statistics
        print_fixedwidth(
            dt.datetime.now().strftime("%H%M%S"),
            round(inttime, 1),
            int(pairs),
            round(acc, 1),
            int(s1),
            int(s2),
            round(e1, 1),
            round(e2, 1),
            round(eavg, 1),
            out=logfile,
        )


def monitor_singles(enable_avg: bool = False):
    """Prints out singles statistics."""
    i = 0
    avg = np.array([0, 0, 0, 0])  # averaging facility, e.g. for measuring dark counts
    avg_iters = 0
    while True:

        # Invoke timestamp data recording
        counts = timestamp.get_counts(duration=INTEGRATION_TIME)
        counts = (
            counts[0] - DARKCOUNTS_CH1 * INTEGRATION_TIME,
            counts[1] - DARKCOUNTS_CH2 * INTEGRATION_TIME,
            counts[2] - DARKCOUNTS_CH3 * INTEGRATION_TIME,
            counts[3] - DARKCOUNTS_CH4 * INTEGRATION_TIME,
        )

        # Implement rolling average to avoid overflow
        if enable_avg:
            avg_iters += 1
            avg = (avg_iters - 1) / avg_iters * avg + np.array(counts) / avg_iters
            counts = np.round(avg, 1)

        # Print the header line after every 10 lines
        if i == 0:
            i = 10
            print_fixedwidth(
                "TIME",
                "CH1",
                "CH2",
                "CH3",
                "CH4",
                "TOTAL",
            )
        i -= 1

        # Print statistics
        print_fixedwidth(
            dt.datetime.now().strftime("%H%M%S"),
            *counts,
            round(sum(counts), 1),
        )


def scan_lcvr_singles():
    target = dt.datetime.now().strftime("%Y%m%d_%H%M%S_lcvrsingles.log")
    lcvr = LCRDriver(
        "/dev/serial/by-id/"
        "usb-Centre_for_Quantum_Technologies_Quad_LCD_driver_QLC-QO05-if00"
    )
    lcvr.all_channels_on()

    voltages = np.round(np.linspace(0.9, 5.5, 9), 3)
    combinations = product(voltages, repeat=4)

    pbar = tqdm.tqdm(combinations)
    for combination in pbar:

        # Set LCVR values
        lcvr.V1, lcvr.V2, lcvr.V3, lcvr.V4 = combination
        time.sleep(0.1)

        # Invoke timestamp data recording
        counts = timestamp.get_counts()
        counts = (
            counts[0],
            counts[1],
            counts[2],
            counts[3],
        )

        # Print statistics
        print_fixedwidth(
            dt.datetime.now().strftime("%H%M%S"),
            *combination,
            *counts,
            out=target,
            pbar=pbar,
        )


##########################
#  PRE-SCRIPT EXECUTION  #
##########################

# Store all program scripts
PROGRAMS = {
    "singles",
    "pairs",
    "lcvr",
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Continuous printing of timestamp statistics"
    )
    parser.add_argument(
        "--averaging",
        "-a",
        action="store_true",
        help="Change to averaging singles mode",
    )
    parser.add_argument(
        "--histogram",
        "-H",
        action="store_true",
        help="Enable histogram in pairs mode",
    )
    parser.add_argument(
        "--logging",
        "-L",
        nargs="?",
        action="store",
        const="unspecified",
        help="Log stuff",
    )
    parser.add_argument(
        "--profile",
        "-p",
        nargs="?",
        action="store",
        choices=list(SETTINGS.keys()),
        help="Specify detection profile",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Specify debug verbosity",
    )
    parser.add_argument("--silent", "-s", action="store_true", help="Suppress errors")
    parser.add_argument("script", choices=PROGRAMS, help="Script to run")

    # Do script only if arguments supplied
    # otherwise run as a normal script (for interactive mode)
    if len(sys.argv) > 1:
        args = parser.parse_args()
        if args.verbose:
            print(args)

        # Request for comments
        path_logfile = None
        if args.logging:

            # No arguments supplied, to query user manually
            if args.logging == "unspecified":
                path_logfile = _request_filecomment()

            # Comment for logfile supplied, use that
            else:
                path_logfile = _append_datetime_logfile(args.logging)

        # Set profile
        if args.profile:
            init_settings(args.profile)

        # Silence all errors/tracebacks
        if args.silent:
            sys.excepthook = lambda etype, e, tb: print()

        # Collect required arguments
        # TODO(Justin, 2022-12-14):
        #     Implement this dynamically without conflicting
        #     with mypy signature checks.
        program = args.script
        if program == "singles":
            monitor_singles(args.averaging)
        elif program == "pairs":
            monitor_pairs(args.histogram, path_logfile)
        elif program == "lcvr":
            scan_lcvr_singles()
