#!/usr/bin/env python3
"""Simple script to continuously feed pair source optimization statistics

Python port of 'inst_efficiency.sh' functionality written in CQT.
Supports reading of singles, pairs, and other miscellaneous features.
Interface via CLI only, to avoid unnecessary GUI dependencies.

Supports usage of 'inst_efficiency.py' both as a script,
as well as an importable library for specific function usage, e.g. 'read_log'.

Configuration files can be supplied according to parser specification, which
can be viewed by supplying the '--help' flag.

Usage:

    1. View available configuration options

       ./inst_efficiency.py --help


    2. TTL input pulses with 2s integration time

       ./inst_efficiency.py singles \
           -U /dev/ioboards/usbtmst1 \
           -S /home/sfifteen/programs/usbtmst4/apps/readevents7 \
           --threshvolt 1 \
           --integration_time 2


    3. Search for pairs between detector channels 1 and 2, over +/-250ns,
       showing histogram of coincidences for each dataset

       ./inst_efficiency.py pairs -qH --channel_start 1 --channel_stop 2


    4. Calculate total pairs located at +118ns delay, within a 2ns-wide
       coincidence window spanning +117ns to +118ns, with only 20 bins

       ./inst_efficiency.py pairs -q --peak 118 --left=-1 --right=0 --bins 20


    5. Log measurements into a file

       ./inst_efficiency.py pairs -q --logging pair_measurements


    6. Save configuration from (4) into default config file

       ./inst_efficiency.py pairs -q --peak 118 -L=-1 -R 0 --bins 20 \
           --save ./inst_efficiency.py.default.conf


    7. Load multiple configuration

       > cat ./inst_efficiency.py.default.conf
       bins = 10
       peak = 200

       > cat ./asympair
       peak = 118
       integration_time = 2

       # Output yields 'bins=10', 'peak=118', 'integration_time=3'
       ./inst_efficiency.py pairs -c asympair --time 3


Author:
    Justin, 2022-12-01

Note:
    Configuration specification follows the philosophy of ConfigArgParse[1].
    Previous idea to use extensible sections (via overriding of profiles),
    but its utility typically only applies up to three layers, in increasing
    precedence, i.e.

        1. Default (platform-specific, e.g. TTL inputs)
        2. Profile (setup-specific, e.g. specific delays)
        3. Sub-profile (setup-specific variations, e.g. longer integration)

    This can be mapped into the respective ConfigArgParse input methods:

        1. Default configuration file (i.e. 'inst_efficiency.py.default.conf')
        2. Specified configuration file (via '--config' option)
        3. Command line arguments, with highest precedence

References:
    [1] https://github.com/bw2/ConfigArgParse
"""

import datetime as dt
import logging
import pathlib
import re
import sys
import time
from itertools import product

import configargparse
import numpy as np
import tqdm

from S15lib.g2lib import g2lib as g2
from S15lib.instruments import LCRDriver, TimestampTDC2

# Constants
INT_MIN = np.iinfo(np.int64).min  # indicate invalid value in int64 array
RE_ANSIESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Colorama
COLORAMA_IMPORTED = False
try:
    import colorama

    COLORAMA_IMPORTED = True
    try:
        colorama.just_fix_windows_console()
        COLORAMA_INIT = False
    except AttributeError:
        colorama.init()
        COLORAMA_INIT = True
except ModuleNotFoundError:
    pass  # colorama does not exist, disable coloring


def style(text, fg=None, bg=None, style=None, clear=False, up=0):
    """Returns text with ANSI wrappers for each line.

    Special note on newlines, where lines are broken up to apply
    formatting on individual lines, excluding the newline character.

    Position of start of print can be controlled using the 'up' arg.

    Usage:
        >>> print(s("hello\nworld", fg="red", style="dim"))
        hello
        world
    """
    # Construct formatting
    fmt = ""
    for c, cls in zip((fg, bg), (colorama.Fore, colorama.Back)):
        if c:
            c = c.upper()
            if c.startswith("LIGHT"):
                c += "_EX"
            fmt += getattr(cls, c)
    if style:
        fmt += getattr(colorama.Style, style.upper())

    # Force clear lines
    if clear:
        fmt = colorama.ansi.clear_line() + fmt

    # Break by individual lines to apply formatting
    lines = str(text).split("\n")
    lines = [f"{fmt}{line}{colorama.Style.RESET_ALL}" for line in lines]
    text = "\n".join(lines)

    # Apply move and restore position
    # Assuming Cursor.DOWN will stop at bottom of current terminal printing
    # Non-positive numbers are treated strangely.
    if up > 0:
        text = colorama.Cursor.UP(up) + text + colorama.Cursor.DOWN(up)
    return text


def strip_ansi(text):
    return RE_ANSIESCAPE.sub("", text)


def len_ansi(text):
    """Returns length after removing ANSI codes."""
    return len(strip_ansi(text))


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


def print_fixedwidth(*values, width=7, out=None, pbar=None, end="\n"):
    """Prints right-aligned columns of fixed width.

    Note:
        The default column width of 7 is predicated on the fact that
        10 space-separated columns can be comfortably squeezed into a
        80-width terminal (with an extra buffer for newline depending
        on the shell).
    """
    row = []
    for value in values:
        if value == INT_MIN:
            row.append(" " * width)
        else:
            # Measure length with ANSI control chars removed
            value = str(value)
            slen = max(0, width - len_ansi(value))
            row.append(" " * slen + value)
    line = " ".join(row)

    if pbar:
        pbar.set_description(line)
    else:
        print(line, end=end)
    if out:
        line = " ".join(
            [
                f"{strip_ansi(str(value)) if value != INT_MIN else ' ': >{width}s}"
                for value in values
            ]
        )
        with open(out, "a") as f:
            f.write(line + "\n")


def read_log(filename: str, schema: list, merge: bool = False):
    """Parses a logfile into a dictionary of columns.

    Convenience method to read out logfiles generated by the script.
    This is not filename-aware (i.e. date and schema version is not
    extracted from the filename) since these are not rigorously
    set-in-stone yet.

    Args:
        filename: Filename of log file.
        schema: List of datatypes to parse each column in logfile.
        merge:
            Whether multiple logging runs in the same file should
            be merged into a single list, or as a list-of-lists.

    Note:
        This code assumes tokens in columns do not contain spaces,
        including headers.

    TODO(Justin):
        Consider usage of PEP557 dataclasses for type annotations.
        Change the argument type of filename to include Path-like objects.
        Implement non-merge functionality.
    """

    # Custom datatype
    def convert_time(s):
        """Converts time in HHMMSS format to datetime object.

        Note:
            The default date is 1 Jan 1900.
        """
        return dt.datetime.strptime(s, "%H%M%S")

    # Parse schema
    _maps = []
    for dtype in schema:
        # Parse special (hardcoded) types
        if isinstance(dtype, str):
            if dtype == "time":
                _map = convert_time
            else:
                raise ValueError(f"Unrecognized schema value - '{dtype}'")
        # Treat everything else as regular Python datatypes
        elif isinstance(dtype, type):
            _map = dtype
        else:
            raise ValueError(f"Unrecognized schema value - '{dtype}'")
        _maps.append(_map)

    # Read file
    is_header_logged = False
    _headers = []
    _data = []
    with open(filename, "r") as f:
        for row_str in f:
            # Squash all intermediate spaces
            row = re.sub(r"\s+", " ", row_str.strip()).split(" ")
            try:
                # Equivalent to Pandas's 'applymap'
                row = [f(v) for f, v in zip(_maps, row)]
                _data.append(row)
            except Exception:
                # If fails, assume is string header
                if not is_header_logged:
                    _headers = row
                    is_header_logged = True

    if not is_header_logged:
        raise ValueError("Logfile does not contain a header.")

    # Merge headers
    _data = np.array(list(zip(*_data)))  # type: ignore
    _items = tuple(zip(_headers, _data))  # type: ignore
    return dict(_items)


#############
#  SCRIPTS  #
#############

# Collect program names
PROGRAMS = {}


def _collect_as_script(alias=None):
    """Decorator to dynamically collect functions for use as scripts."""

    def collector(f):
        nonlocal alias
        if alias is None:
            alias = f.__name__
        PROGRAMS[alias] = f
        return f

    return collector


def read_pairs(params):
    """Compute single pass pair statistics.

    Note:
        Parameter dictionary passed instead of directly into kwargs, since:
            1. Minimize dependency with parser argument names
            2. Functions in the stack can reuse arguments,
               e.g. monitor_pairs -> read_pairs
    """

    # Unpack arguments into aliases
    bin_width = params["bin_width"]
    bins = params["bins"]
    peak = params["peak"]
    roffset = params["window_right_offset"]
    loffset = params["window_left_offset"]
    duration = params["integration_time"]
    darkcounts = [
        params["darkcount_ch1"],
        params["darkcount_ch2"],
        params["darkcount_ch3"],
        params["darkcount_ch4"],
    ]
    channel_start = params["channel_start"] - 1
    channel_stop = params["channel_stop"] - 1
    timestamp = params["timestamp"]

    darkcount_start = darkcounts[channel_start]
    darkcount_stop = darkcounts[channel_stop]
    window_size = roffset - loffset + 1
    acc_start = max(bins // 2, 1)  # location to compute accidentals
    while True:

        # Invoke timestamp data recording
        timestamp._call_with_duration(["-a1", "-X"], duration=duration)

        # Extract g2 histogram and other data
        data = g2.g2_extr(
            "/tmp/quick_timestamp",
            channel_start=channel_start,
            channel_stop=channel_stop,
            highres_tscard=True,
            bin_width=bin_width,
            bins=bins,
            # Include window at position 1
            min_range=peak + loffset - 1,
        )
        hist = data[0]
        s1, s2 = data[2:4]
        inttime = data[4] * 1e-9  # convert to units of seconds

        # Integration time check for data validity
        if not (0.75 < inttime / duration < 2):
            continue

        # Calculate statistics
        acc = window_size * np.mean(hist[acc_start:])
        pairs = sum(hist[1 : 1 + window_size]) - acc

        # Normalize to per unit second
        s1 = s1 / inttime - darkcount_start  # timestamp data more precise
        s2 = s2 / inttime - darkcount_stop
        pairs = pairs / inttime
        acc = acc / inttime

        if s1 == 0 or s2 == 0:
            e1 = e2 = eavg = 0
        else:
            e1 = 100 * pairs / s2
            e2 = 100 * pairs / s1
            eavg = 100 * pairs / (s1 * s2) ** 0.5

        # Single datapoint collection completed
        break

    return hist, inttime, pairs, acc, s1, s2, e1, e2, eavg


@_collect_as_script("pairs_once")
def print_pairs(params):
    """Pretty printed variant of 'read_pairs', showing pairs, acc, singles."""
    _, _, pairs, acc, s1, s2, _, _, _ = read_pairs(params)
    print_fixedwidth(
        round(pairs, 1),
        round(acc, 1),
        int(s1),
        int(s2),
        width=0,
    )


@_collect_as_script("pairs")
def monitor_pairs(params):
    """Prints out pair source statistics, between ch1 and ch4."""
    # Unpack arguments into aliases
    peak = params["peak"]
    roffset = params["window_right_offset"]
    loffset = params["window_left_offset"]
    enable_hist = params.get("histogram", False)
    disable_hist = params.get("no_histogram", False)
    logfile = params.get("logfile", None)

    is_header_logged = False
    i = 0
    is_initialized = False
    prev = None
    longterm_data = {"count": 0, "inttime": 0, "pairs": 0, "acc": 0, "s1": 0, "s2": 0}
    while True:

        hist, inttime, pairs, acc, s1, s2, e1, e2, eavg = read_pairs(params)

        # Visualize g2 histogram
        HIST_ROWSIZE = 10
        if not is_initialized or enable_hist:
            is_initialized = True
            a = np.array(hist, dtype=np.int64)
            # Append NaN values until fits number of rows
            a = np.append(a, np.resize(INT_MIN, HIST_ROWSIZE - (a.size % HIST_ROWSIZE)))
            if not disable_hist:
                print("\nObtained histogram:")
                for row in a.reshape(-1, HIST_ROWSIZE):
                    print_fixedwidth(*row)
            peakvalue = max(a)
            peakargmax = np.argmax(a)
            peakpos = peakargmax + peak + loffset - 1
            print(f"Maximum {peakvalue} @ index {peakpos}")

            # Display current window as well
            window_size = roffset - loffset + 1
            print(f"Current window: {list(hist[1:window_size+1])}")

            # Display likely window
            likely_window = [peakvalue]
            likely_left = None
            likely_right = None
            acc_bin = acc / window_size
            # Scan below
            i = 0
            while True:
                i += 1
                pos = peakargmax - i
                value = a[pos]
                if value > 2 * acc_bin:
                    likely_window = [value] + likely_window
                else:
                    likely_left = -(i - 1)
                    break
            i = 0
            while True:
                i += 1
                pos = peakargmax + i
                value = a[pos]
                if value > 2 * acc_bin:
                    likely_window = likely_window + [value]
                else:
                    likely_right = i - 1
                    break
            print(
                "Likely window: "
                f"{list(a[likely_left+peakargmax:likely_right+1+peakargmax])}"
            )
            print(
                f"Args: --peak={peakpos} --left={likely_left} --right={likely_right}\n"
            )

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
            style(dt.datetime.now().strftime("%H%M%S"), style="dim"),
            round(inttime, 1),
            style(int(pairs), style="bright"),
            round(acc, 1),
            style(int(s1), fg="yellow", style="bright"),
            style(int(s2), fg="green", style="bright"),
            round(e1, 1),
            round(e2, 1),
            style(round(eavg, 1), fg="cyan", style="bright"),
            out=logfile,
        )

        # Print long-term statistics, only if value supplied
        if params["averaging_time"] > 0:
            # Update first
            longterm_data["count"] += 1
            longterm_data["inttime"] += inttime
            longterm_data["pairs"] += pairs
            longterm_data["acc"] += acc
            longterm_data["s1"] += s1
            longterm_data["s2"] += s2

            # Cache long term results if reach threshold
            if longterm_data["inttime"] >= params["averaging_time"]:
                counts = longterm_data["count"]
                inttime = longterm_data["inttime"]
                p = longterm_data["pairs"] / counts
                acc = longterm_data["acc"] / counts
                s1 = longterm_data["s1"] / counts
                s2 = longterm_data["s2"] / counts
                prev = (
                    dt.datetime.now().strftime("%H%M%S"),
                    round(inttime, 1),
                    style(int(round(p, 0)), fg="red", style="bright"),
                    round(acc, 1),
                    int(round(s1, 0)),
                    int(round(s2, 0)),
                    round(100 * p / s2, 1),
                    round(100 * p / s1, 1),
                    style(
                        round(100 * p / (s1 * s2) ** 0.5, 1), fg="red", style="bright"
                    ),
                )
                longterm_data = {
                    "count": 0,
                    "inttime": 0,
                    "pairs": 0,
                    "acc": 0,
                    "s1": 0,
                    "s2": 0,
                }

            # Print if exists
            if prev:
                print_fixedwidth(*prev, end="\r")


@_collect_as_script("singles")
def monitor_singles(params):
    """Prints out singles statistics."""
    # Unpack arguments into aliases
    duration = params["integration_time"]
    darkcount_ch1 = params["darkcount_ch1"]
    darkcount_ch2 = params["darkcount_ch2"]
    darkcount_ch3 = params["darkcount_ch3"]
    darkcount_ch4 = params["darkcount_ch4"]
    timestamp = params["timestamp"]
    logfile = params.get("logfile", None)
    enable_avg = params.get("averaging", False)

    is_header_logged = False
    i = 0
    avg = np.array([0, 0, 0, 0])  # averaging facility, e.g. for measuring dark counts
    avg_iters = 0
    while True:

        # Invoke timestamp data recording
        data = timestamp.get_counts(
            duration=duration,
            return_actual_duration=True,
        )
        counts = data[:4]
        inttime = data[4]

        # Rough integration time check
        if not (0.75 < inttime / duration < 2):
            continue
        if any(np.array(counts) < 0):
            continue

        counts = (
            counts[0] - darkcount_ch1 * inttime,
            counts[1] - darkcount_ch2 * inttime,
            counts[2] - darkcount_ch3 * inttime,
            counts[3] - darkcount_ch4 * inttime,
        )
        counts = np.array(counts)
        # VAHD
        # counts = counts/ np.array([1,1.057,0.788,0.631])
        # VDHA
        # counts = counts/ np.array([1,0.631,0.788,1.057])

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
                out=logfile if not is_header_logged else None,
            )
            is_header_logged = True
        i -= 1

        # Print statistics
        print_fixedwidth(
            style(dt.datetime.now().strftime("%H%M%S"), style="dim"),
            *list(map(int, counts)),
            style(int(sum(counts)), style="bright"),
            out=logfile,
        )


@_collect_as_script("lcvr")
def scan_lcvr_singles(params):
    timestamp = params["timestamp"]
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

# Enumerate data processing arguments
ARGUMENTS = [
    "bin_width",
    "bins",
    "peak",
    "window_left_offset",
    "window_right_offset",
    "integration_time",
    "averaging_time",
    "darkcount_ch1",
    "darkcount_ch2",
    "darkcount_ch3",
    "darkcount_ch4",
    "channel_start",
    "channel_stop",
]

if __name__ == "__main__":
    # Request python-black linter to avoid parsing, for readability
    # fmt: off
    parser = configargparse.ArgumentParser(
        default_config_files=["./inst_efficiency.py.default.conf"],
        description="Continuous printing of timestamp statistics"
    )

    # Parser-level arguments
    # ConfigArgParse does not support multiple configuration files for same argument
    # Workaround by adding additional argument with similar argument name to supply
    # any secondary configuration, i.e. "-c" and "-C" both supplies configuration
    parser.add_argument(
        "--config", "-c", is_config_file_arg=True,
        help="Configuration file")
    parser.add_argument(
        "--save", is_write_out_config_file_arg=True,
        help="Save configuration as file, and immediately exits program")

    # Script-level arguments
    parser.add_argument(
        "--averaging", "-a", action="store_true",
        help="Change to averaging singles mode")
    parser.add_argument(
        "--histogram", "-H", action="store_true",
        help="Enable histogram in pairs mode")
    parser.add_argument(
        "--no-histogram", action="store_true",
        help="Disable histogram in pairs mode. Overrides other histogram options.")
    parser.add_argument(
        "--logging", "-l", nargs="?", action="store", const="unspecified",
        help="Log stuff")
    parser.add_argument(
        "--verbose", "-v", action="count", default=0,
        help="Specify debug verbosity")
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress errors, does not block logging")
    parser.add_argument(
        "script", choices=PROGRAMS,
        help="Script to run")

    # Device-level argument
    parser.add_argument(
        "--device_path", "-U", default="/dev/ioboards/usbtmst0",
        help="Path to timestamp device")
    parser.add_argument(
        "--readevents_path", "-S",
        default="/home/qitlab/programs/drivers/usbtmst4/apps/readevents7",
        help="Path to readevents binary")
    parser.add_argument(
        "--outfile_path", "-O", default="/tmp/quick_timestamp",
        help="Path to temporary file for timestamp storage")
    parser.add_argument(
        "--threshvolt", "-t", type=float, default="-0.4",
        help="Pulse trigger level for each detector channel, comma-delimited")
    parser.add_argument(
        "--fast", "-f", action="store_true",
        help="Enable fast event readout mode, i.e. 32-bit wide events. Only for TDC2.")

    # Data processing arguments
    parser.add_argument(
        "--bin_width", "--width", "-W", type=float, default=1,
        help="Size of time bin, in nanoseconds")
    parser.add_argument(
        "--bins", "-B", type=int, default=500,
        help="Number of coincidence bins, in units of 'bin_width'")
    parser.add_argument(
        "--peak", "--window-center", "-M", type=int, default=-250,
        help="Absolute bin location of coincidence window, in units of 'bin_width'")
    parser.add_argument(
        "--window_left_offset", "--left", "-L", type=int, default=0,
        help="Left boundary of coincidence window relative to window middle")
    parser.add_argument(
        "--window_right_offset", "--right", "-R", type=int, default=0,
        help="Right boundary of coincidence window relative to window middle")
    parser.add_argument(
        "--integration_time", "--time", "-T", type=float, default=1.0,
        help="Integration time for timestamp, in seconds")
    parser.add_argument(
        "--averaging_time", "--atime", type=float, default=0.0,
        help="Auxiliary long-term integration time, in seconds")
    parser.add_argument(
        "--darkcount_ch1", "--ch1", "-1", type=float, default=0.0,
        help="Dark count level for detector channel 1, in counts/second")
    parser.add_argument(
        "--darkcount_ch2", "--ch2", "-2", type=float, default=0.0,
        help="Dark count level for detector channel 1, in counts/second")
    parser.add_argument(
        "--darkcount_ch3", "--ch3", "-3", type=float, default=0.0,
        help="Dark count level for detector channel 1, in counts/second")
    parser.add_argument(
        "--darkcount_ch4", "--ch4", "-4", type=float, default=0.0,
        help="Dark count level for detector channel 1, in counts/second")
    parser.add_argument(
        "--channel_start", "--start", type=int, default=1,
        help="Reference timestamp channel for calculating time delay offset")
    parser.add_argument(
        "--channel_stop", "--stop", type=int, default=4,
        help="Target timestamp channel for calculating time delay offset")
    parser.add_argument(
        "--color", action="store_true",
        help="Add preset color highlighting to text in stdout")
    # Reenable python-black linter
    # fmt: on

    # Do script only if arguments supplied
    # otherwise run as a normal script (for interactive mode)
    if len(sys.argv) > 1:
        args = parser.parse_args()

        # Set program logging verbosity
        levels = [
            logging.CRITICAL,
            logging.WARNING,
            logging.INFO,
            logging.DEBUG,
        ]
        logging.basicConfig(
            level=levels[min(args.verbose, 3)],
            format="{asctime} {levelname}: {message}",
            style="{",
        )
        logging.debug("Arguments: %s", args)

        # Request for comments
        path_logfile = None
        if args.logging:

            # No arguments supplied, to query user manually
            if args.logging == "unspecified":
                path_logfile = _request_filecomment()

            # Comment for logfile supplied, use that
            else:
                path_logfile = _append_datetime_logfile(args.logging)

        # Silence all errors/tracebacks
        if args.quiet:
            sys.excepthook = lambda etype, e, tb: print()

        # Disable color if not explicitly enabled
        if not args.color or not COLORAMA_IMPORTED:
            style = lambda text, *args, **kwargs: text  # noqa

        # Initialize timestamp
        timestamp = TimestampTDC2(
            device_path=args.device_path,
            readevents_path=args.readevents_path,
            outfile_path=args.outfile_path,
        )
        timestamp.threshold = args.threshvolt
        timestamp.fast = args.fast

        # Collect required arguments
        params = dict([(k, getattr(args, k, None)) for k in ARGUMENTS])
        params["logfile"] = path_logfile
        params["histogram"] = args.histogram
        params["no_histogram"] = args.no_histogram
        params["averaging"] = args.averaging
        params["timestamp"] = timestamp

        # Call script
        PROGRAMS[args.script](params)
