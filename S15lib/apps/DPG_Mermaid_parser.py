import re
import warnings
from math import ceil
from typing import Dict

import configargparse


# === UnitConverter ===
class UnitConverter:
    """
    Centralized utilities for frequency and time unit conversions.

    Supported frequency units: MHz, kHz, Hz.
    Supported time units: ms, us, ns.

    Example:
        >>> UnitConverter.freq(10, 'kHz')
        10000
        >>> UnitConverter.time(5, 'us')
        5000
    """

    freq_units = {"mhz": 1_000_000, "khz": 1_000, "hz": 1}
    time_units = {"ms": 1_000_000, "us": 1_000, "ns": 1}

    @staticmethod
    def freq(value, unit):
        """
        Convert frequency value and unit to Hz.

        Args:
            value (int): Frequency value.
            unit (str): Frequency unit ('MHz', 'kHz', 'Hz').

        Returns:
            int: Frequency in Hz.

        Raises:
            ValueError: If unit is not supported.
        """
        unit = unit.lower()
        if unit not in UnitConverter.freq_units:
            raise ValueError(f"Unknown frequency unit: {unit}")
        return int(value) * UnitConverter.freq_units[unit]

    @staticmethod
    def time(value, unit):
        """Convert time with unit (e.g. 5, 'us') to ns."""
        unit = unit.lower()
        if unit not in UnitConverter.time_units:
            raise ValueError(f"Unknown time unit: {unit}")
        return int(value) * UnitConverter.time_units[unit]

    @staticmethod
    def parse_value_unit(s: str):
        """Split '10ms' into ('10','ms'), or raise ValueError."""
        match = re.match(r"(\d+)([a-zA-Z]+)", s.strip())
        if match:
            return match.groups()
        raise ValueError(f"Cannot parse value and unit from '{s}'")


BLOCK_PATTERN_SINGLE = re.compile(r"^(\w+)\s*\[(.+)\]$")
BLOCK_PATTERN_BEGIN = re.compile(r"^(\w+)\s*\[(.*)$")
LOOP_PATTERN_SINGLE = re.compile(r"^subgraph\s*(\w+)\s*\[(.+)\]$")
LOOP_PATTERN_BEGIN = re.compile(r"^subgraph\s*(\w+)\s*\[(.*)$")
LOGIC_PATTERN = re.compile(r"^(\w+)\s*-->\s*(\|\w+\|)?\s*(\w+)$")


class MermaidParser:
    """
    Parses a Mermaid-like syntax file defining digital pattern generator blocks and
    their logical connections.

    Args:
        file_path (str): Path to the Mermaid-like input file.

    Attributes:
        blocks (dict): Maps block IDs to their content strings.
        logic (list): List of tuples representing logical connections between
                      blocks, e.g., (block_start, block_end, condition).

    Example:
        Input file format:
            blockA [ content ]
            blockB [ more content ]
            blockA --> blockB

        Usage:
            parser = MermaidParser("input.txt")
            parser.parse()
            blocks = parser.get_blocks()
            logic = parser.get_logic()
    """

    def __init__(self, file_path):
        """
        Initialize the MermaidParser with the input file path.

        Args:
            file_path (str): Path to the input file to parse.
        """
        self.file_path = file_path
        self.blocks = {}
        self.logic = []

    def parse(self):
        """
        Parse the input file, populating 'blocks' and 'logic' attributes.
        Handles single-line blocks, multi-line blocks,
        loop blocks, and logic connections.
        """
        with open(self.file_path, "r") as file:
            lines = file.readlines()

        self.current_block_id = None
        self.current_block_lines = []
        in_block = False
        in_loop = False

        for line in lines:
            line = line.strip()
            if self.ignore_comments(line):
                continue

            if self.get_single_line_block(line):
                continue

            # Single-line loop block
            if self.get_single_loop_block(line):
                in_loop = True
                continue

            # Start Loop block
            if not in_loop:
                if self.start_loop_block(line):
                    in_loop = True
                    in_block = True
                    continue

            # Multiline loop block continuation
            if in_loop and in_block:
                if self.end_of_line(line):
                    self.block_join(line)
                    in_block = False
                else:
                    self.block_append(line)
                continue

            # Loop block contents
            if in_loop:
                if self.end_of_loop(line):
                    self.block_join(line)
                    in_loop = False
                else:
                    self.block_append(line)
                continue

            # Start of a multiline block
            if not in_block:
                if self.start_multi_block(line):
                    in_block = True
                    continue

            # Multiline continuation
            if in_block:
                if self.end_of_line(line):
                    self.block_join(line)
                    in_block = False
                else:
                    self.block_append(line)
                continue

            # Logic connections
            self.match_logic(line)

    def start_loop_block(self, line):
        """
        Detect the start of a multi-line loop block.

        Args:
            line (str): Line to check.

        Returns:
            bool: True if a loop block begins here, else False.
        """
        return self.match_block(line, LOOP_PATTERN_BEGIN)

    def start_multi_block(self, line):
        """
        Detect the start of a multi-line block.

        Args:
            line (str): Line to check.

        Returns:
            bool: True if a multi-line block begins here, else False.
        """
        return self.match_block(line, BLOCK_PATTERN_BEGIN)

    def match_block(self, line, pattern):
        """
        Generic helper to match a line against a block start pattern.

        Args:
            line (str): The line to check.
            pattern (re.Pattern): Compiled regex pattern.

        Returns:
            bool: True if a block match is found, else False.
        """
        start_match = pattern.match(line)
        if start_match and not line.endswith("]"):
            self.current_block_id, first_line = start_match.groups()
            self.current_block_lines = [first_line]
            return True

    def end_of_loop(self, line):
        """
        Check if a line marks the end of a loop block.

        Args:
            line (str): The line to check.

        Returns:
            bool: True if this is an 'end' line.
        """
        if line.startswith("end"):
            return True
        else:
            return False

    def get_single_loop_block(self, line):
        """
        Parse a single-line loop block.

        Args:
            line (str): The line to check.

        Returns:
            bool: True if a single-line loop block is found and added.
        """
        match = LOOP_PATTERN_SINGLE.match(line)
        if match:
            block_id, content = match.groups()
            self.current_block_id = block_id
            self.current_block_lines = [content]
            return True

    def end_of_line(self, line):
        """
        Check if a line marks the end of a block (i.e., ends with ']').

        Args:
            line (str): The line to check.

        Returns:
            bool: True if the line ends a block.
        """
        if line.endswith("]"):
            return True
        else:
            return False

    def block_join(self, line):
        """
        Join lines to complete a multi-line block and add it to blocks.

        Args:
            line (str): The final line of the block.
        """
        self.current_block_lines.append(line[:-1])
        self.blocks[self.current_block_id] = "\n".join(self.current_block_lines).strip()
        return

    def block_append(self, line):
        """
        Append a line to the current block being parsed.

        Args:
            line (str): The line to append.
        """
        self.current_block_lines.append(line)
        return

    def match_logic(self, line):
        """
        Parse a line for logical connections between blocks and update logic.
            e.g:
            key1 --> key2
            key1 --> |key3| key2
        Args:
            line (str): The line to check.

        """
        logic_match = LOGIC_PATTERN.match(line)
        if logic_match:
            if logic_match.lastindex == 3:  # Has 3 information
                self.logic.append(
                    (logic_match.group(1), logic_match.group(3), logic_match.group(2))
                )
            else:
                self.logic.append((logic_match.group(1), logic_match.group(2)))

    def ignore_comments(self, line):
        """
        Parses line and remove comments, empty line or flowchart keyword

        Args:
            line (str): The line to check.

        Returns:
            bool: True if the line should be ignored.
        """
        mermaid_comment = "%%"
        if not line or line.startswith("flowchart") or line.startswith(mermaid_comment):
            return True
        else:
            return False

    def get_single_line_block(self, line):
        """
        Parses line  and looks for single line block
        block_id [ content ]

        Args:
            line (str): The line to check.

        Returns:
            bool: True if a single-line block is found and added.
        """
        match = BLOCK_PATTERN_SINGLE.match(line)
        if match:
            block_id, content = match.groups()
            self.blocks[block_id] = content.strip()
            return True
        else:
            return False

    def get_blocks(self):
        """
        Get the parsed blocks.

        Returns:
            dict: The blocks dictionary.
        """
        return self.blocks

    def get_logic(self):
        """
        Get the parsed logic connections.

        Returns:
            list: The logic list.
        """
        return self.logic


class Block(MermaidParser):
    """
    Base class for representing a block in the pattern generator.

    This class provides common functionalities for parsing block content,
    handling comments, and extracting channel, DAC, and time information.
    Specific block types (Control, Sequence, Trigger, Loop, Branch)
    inherit from this class.

    Args:
        block_id (str): The unique identifier for the block.
        content (str): The raw string content of the block.
    """

    def __init__(self, block_id, content):
        """
        Initializes a Block instance.

        Args:
            block_id (str): The unique identifier for the block.
            content (str): The raw string content of the block.
        """
        self.block_id = block_id
        self.content = content
        self.first_row = None
        self.last_row = None
        self.written = False

    def split_comments(self, line):
        """
        Splits a line into its content and an optional comment part.

        Comments are expected to start with '#'.

        Args:
            line (str): The input line.

        Returns:
            tuple: A tuple containing the line content (str) and the comment (str).
                   If no comment is found, the comment string is empty.
        """
        text = line.split("#", 1)
        if len(text) > 1:
            line = text[0]
            comment = "#" + text[1]
        else:
            line = text[0]
            comment = ""
        return line, comment

    def get_cols(self, line):
        """
        Splits a line into columns based on delimiters (',', ' ', '\t')
        and handles comments.

        Args:
            line (str): The input line.

        Returns:
            list: A list of strings, where each string is a column.
                  Comments are appended as the last element if present.
        """
        line, comment = self.split_comments(line)
        delimiter = ",| |\t"
        line = line.lower()
        cols = list(filter(None, re.split(delimiter, line)))
        if comment:
            cols.append(comment)
        return cols

    def chan_on(self, chan_string):
        """
        Parses a channel string and returns a list of active channel numbers.

        The string can contain individual numbers or ranges (e.g., "1-3").
        Example: "0 2-4 7" -> [0, 2, 3, 4, 7]

        Args:
            chan_string (str): The string defining active channels.

        Returns:
            list: A sorted list of unique active channel integers.
        """
        chan_list = []
        for part in self.get_cols(chan_string):
            if "-" in part:
                start, end = map(int, part.split("-"))
                chan_list.extend(range(start, end + 1))
            else:
                chan_list.append(int(part))
        return list(set(chan_list))  # remove duplicate

    def dac_update(self, dac_string):
        """
        Parses a DAC string and returns a dictionary of DAC channel-value pairs.

        Format: "ch:val ch:val ..."
        Values can be integers or float voltages (which are converted to 16-bit).
        Example: "0:100 1:2.5V" -> {0: 100, 1: <16-bit value for 2.5V>}

        Args:
            dac_string (str): The string defining DAC updates.

        Returns:
            dict: A dictionary mapping DAC channel numbers (int) to their values (int).
        """
        dac_list = []
        dac_value = []
        for part in self.get_cols(dac_string):
            ch, val = part.split(":")
            dac_list.append(int(ch))
            if val.isdigit():
                dac_value.append(int(val))
            else:
                val = self.volt_to_16bit(float(val))
                dac_value.append(val)
        return dict(zip(dac_list, dac_value))

    def parse_contents(self):
        """
        Splits the raw block content into a list of lines.

        Returns:
            list: A list of strings, where each string is a line from the block content.
        """
        return self.content.split("\n")

    def is_comment(self, line):
        """
        Checks if a given line is a comment line (starts with '#').

        Args:
            line (str): The input line.

        Returns:
            bool: True if the line is a comment, False otherwise.
        """
        if line.strip().startswith("#"):
            return True
        else:
            return False

    def eat_space_between_units(self, list_str):
        """
        Merges numerical values with their units if they are separated by space.

        Example: ["10", "ms"] -> ["10ms"]

        Args:
            list_str (list): A list of strings (columns).

        Returns:
            list: The modified list with values and units merged.
        """
        t = [x in UnitConverter.time_units for x in list_str]
        f = [x in UnitConverter.freq_units for x in list_str]
        for i, x in enumerate(t):
            if x:
                list_str[i - 1] += list_str[i]
                list_str.pop(i)

        for i, x in enumerate(f):
            if x:
                list_str[i - 1] += list_str[i]
                list_str.pop(i)

        return list_str

    def get_dac(self, cols):
        """
        Extracts DAC information from a list of columns.

        Expects the first column to be 'dac' (case-insensitive).

        Args:
            cols (list): A list of strings representing columns from a line.

        Returns:
            tuple: A tuple containing:
                - dac_updates (dict): DAC channel-value pairs.
                - comments (str): Any comments found on the line.
                - remaining_cols (list): The columns remaining after DAC parsing.
        """
        assert cols[0].lower() == "dac", "Keyword missing"
        line = ",".join(cols[1:])
        line, comments = self.split_comments(line)
        cols = []
        return self.dac_update(line), comments, cols

    def volt_to_16bit(self, val):
        """
        Converts a voltage value to its 16-bit representation.

        Args:
            val (float): The voltage value (between -10.3V and 10.3V).

        Returns:
            int: The 16-bit integer representation of the voltage.

        Raises:
            AssertionError: If the voltage is out of range or conversion is unexpected.
        """
        slope = 0.00031433585
        if val > 10.3 or val < -10.3:
            assert "DAC float value out of range. -10.3 < V < 10.3"
        elif val > 0:
            ret_val = int(val / slope)
        elif val < 0:
            ret_val = int(0xFFFF + int(val / slope))
        else:
            ret_val = 0
        assert ret_val >= 0 and ret_val < 65535, "Something strange"
        return ret_val

    def set_dac(self, line):
        """
        Placeholder method for setting DAC values.
        Currently not implemented.

        Args:
            line (list): A list of strings representing parts of a DAC command.
        """
        self.dac = self.dac_update(line)

    def get_chan(self, cols):
        """
        Extracts active channel information from a list of columns.

        Expects the first column to be 'chan' (case-insensitive).
        Can optionally be followed by 'dac' information.

        Args:
            cols (list): A list of strings representing columns from a line.

        Returns:
            tuple: A tuple containing:
                - active_channels (list): A list of active channel numbers.
                - comments (str): Any comments found on the line.
                - remaining_cols (list): Columns related to DAC or empty if none.
        """
        assert cols[0].lower() == "chan", "Keyword missing"
        try:
            dac_idx = cols.index("dac")
            line = ",".join(cols[1:dac_idx])
            comments = ""
            cols = cols[dac_idx:]
        except ValueError:
            line = ",".join(cols[1:])  # without dac,
            cols = []
        line, comments = self.split_comments(line)
        return self.chan_on(line), comments, cols

    def set_chan(self, line):
        """
        Sets the active channels for the block.

        Args:
            line (list): A list of strings representing channel information.
                         These are joined and parsed by `chan_on`.
        """
        self.chan = self.chan_on(",".join(line))

    def set_exinput(self, line):
        """
        Sets the external input channel used by the block.

        The input channel must be one of 'e1', 'e2', 'e3', or 'e4'.
        This method sets `self.external_input` to the integer part (1, 2, 3, or 4).

        Args:
            line (list): A list of strings, where the first element is the
                         external input designator (e.g., "e1").

        Raises:
            AssertionError: If the input designator is not valid.
        """
        part = line[0]
        assert part in ["e1", "e2", "e3", "e4"]
        self.external_input = int(part[1:])

    def assert_grammar(self, key, grammar):
        """
        Checks if a given key is present in the expected grammar.

        Args:
            key (str): The keyword to check.
            grammar (list or dict): A collection of valid keywords.

        Raises:
            ValueError: If the key is not found in the grammar.
        """
        if key not in grammar:
            raise ValueError(f"{key} doesn't match syntax")

    def get_time(self, cols):
        """
        Extracts time information (value and unit) from columns and
        converts to nanoseconds.

        Time can be specified as "value_unit" (e.g., "10ns") or
        "value unit" (e.g., "10 ns").

        Args:
            cols (list): A list of strings representing columns. The time information
                         is expected at the beginning of this list.

        Returns:
            tuple: A tuple containing:
                - time_ns (int): The time value in nanoseconds.
                - remaining_cols (list): The columns remaining after time parsing.
        """
        try:
            value, unit = UnitConverter.parse_value_unit(cols[0])
            cols.pop(0)
        except ValueError:
            value = cols[0]
            unit = cols[1]
            cols.pop(0)
            cols.pop(0)
        finally:
            time = UnitConverter.time(value, unit)
        return time, cols


class ControlBlock(Block):
    """
    Represents a 'control' block in the pattern generator.

    This block defines global configuration settings for the pattern generator,
    such as clock frequency, variable initial values, DAC configurations, etc.

    Args:
        block_id (str): The unique identifier for the block (e.g., "control").
        content (str): The raw string content of the control block.
    """

    def __init__(self, block_id, content):
        """
        Initializes a ControlBlock instance with default values and grammar.
        """
        super().__init__(block_id, content)
        self.block_type = "control"
        self.auxconfig = 0
        self.start_address = 0  # Default to 0
        self.ivars = [0, 0, 0, 0]  # Default to 0
        self.evars = [0, 0, 0, 0]  # Default to 0
        self.auxline_pol = 0  # Set to NIM by default
        self.clock_select = 0  # auto by default
        self.level = 0  # Set to NIM by default
        self.dacconfig = 0  # Set to static by default
        self.patgen_128bit = False  # Set to 64bit version by default
        self.dacs = [0, 0, 0, 0, 0, 0, 0, 0]  # Static DAC values
        self.inthreshold = 59000  # Nim by default
        self.clock = 100_000_000  # Default to 100MHz clock
        self.timestep = 10  # Default to 10 ns

        self.auxselect = {"normal": 0, "delayed": 1, "main": 2, "ref": 3}
        self.clockselect = {"auto": 0, "external": 1, "internal": 2, "direct": 3}
        self.dacselect = {"static": 0, "single": 1, "half": 2, "full": 3}
        self.control_grammar = [
            "clock",
            "evars",
            "ivars",
            "auxout",
            "dacconfig",
            "version",
            "inlevel",
            "auxconfig",
            "startaddress",
            "dacstatic",
        ]

    def process_control(self):
        """
        Parses the content of the control block and sets the configuration attributes.

        Iterates through each line of the block content, identifies the control
        command, and calls the appropriate setter method.
        """
        for line in self.parse_contents():
            cols = self.get_cols(line)
            first_col = cols[0]
            next_cols = cols[1:]
            self.assert_grammar(first_col, self.control_grammar)
            # Python 3.10+ match/case equivalent:
            # match first_col:
            #     case "clock": self.set_clock(next_cols)
            #     case "evars": self.set_evars(next_cols)
            #     ...
            if first_col == self.control_grammar[0]:  # clock
                self.set_clock(next_cols)
            elif first_col == self.control_grammar[1]:  # evars
                self.set_evars(next_cols)
            elif first_col == self.control_grammar[2]:  # ivars
                self.set_ivars(next_cols)
            elif first_col == self.control_grammar[3]:  # auxout
                self.set_auxline_polarity(next_cols)
            elif first_col == self.control_grammar[4]:  # dacconfig
                self.set_DACconfig(next_cols)
            elif first_col == self.control_grammar[5]:  # version
                self.set_patgenversion(next_cols)
            elif first_col == self.control_grammar[6]:  # inlevel
                self.set_external_input_polarity(next_cols)
            elif first_col == self.control_grammar[7]:  # auxconfig
                self.set_auxconfig(next_cols)
            elif first_col == self.control_grammar[8]:  # startaddress
                self.set_startaddress(next_cols)
            elif first_col == self.control_grammar[9]:  # dacstatic
                self.set_staticDAC(next_cols)

    def set_clock(self, clock_cols):
        """
        Sets the clock frequency and selection mode.

        Args:
            clock_cols (list): Columns containing clock information.
                               Example: ["100mhz", "auto"]

        Raises:
            AssertionError: If clock frequency is too high or settings are inconsistent.
        """
        clock_cols = self.eat_space_between_units(clock_cols)
        for i, part in enumerate(clock_cols):
            if i == 0:  # Clock value and unit
                value, unit = UnitConverter.parse_value_unit(part)
                self.clock = UnitConverter.freq(value, unit)
                assert self.clock <= 100_000_000, "Clock frequency too large"
                self.timestep = int(1e9 / self.clock)  # ns
        if i == 1:  # Clock select
            assert part in self.clockselect.keys(), "Undefined clock select"
            self.clock_select = self.clockselect.get(part)
        else:
            self.clock_select = 0  # auto by default
        if self.clock_select != 3:  # direct mode allows any clock
            assert (
                self.clock == 100_000_000
            ), "Clock select and clock freq don't agree for non-direct modes"

    def set_evars(self, evars_cols):
        """
        Sets the initial values for external variables (evars).

        Args:
            evars_cols (list): A list of up to 4 integer values for evars.

        Raises:
            AssertionError: If more than 4 evars are provided or a value overflows.
        """
        assert len(evars_cols) <= 4, "Too many external vars"
        for i, val in enumerate(evars_cols):
            val = int(val)
            assert val < 65536, "External variable overflow (must be < 65536)"
            self.evars[i] = val

    def set_ivars(self, ivars_cols):
        """
        Sets the initial values for internal variables (ivars).

        Args:
            ivars_cols (list): A list of up to 4 integer values for ivars.

        Raises:
            AssertionError: If more than 4 ivars are provided or a value overflows.
        """
        assert len(ivars_cols) <= 4, "Too many internal vars"
        for i, val in enumerate(ivars_cols):
            val = int(val)
            assert val < 65536, "Internal variable overflow (must be < 65536)"
            self.ivars[i] = val

    def set_auxconfig(self, aux_cols):
        """
        Sets the auxiliary output line configuration.

        Args:
            aux_cols (list): A list containing the auxline selection mode
                             (e.g., ["normal"], ["delayed"]).

        Raises:
            AssertionError: If the auxline selection mode is undefined.
        """
        part = aux_cols[0]
        assert part in self.auxselect.keys(), "Undefined auxline select"
        self.auxconfig = self.auxselect.get(part)

    def set_startaddress(self, aux_cols):
        """
        Sets the starting address for the pattern execution.

        Args:
            aux_cols (list): A list containing the start address (integer).

        Raises:
            AssertionError: If the start address is out of range (< 512).
        """
        part = int(aux_cols[0])
        assert part < 512, "Start address out of range (must be < 512)"
        self.start_address = part

    def set_auxline_polarity(self, aux_cols):
        """
        Sets the polarity for the auxiliary output line.

        Args:
            aux_cols (list): A list containing the polarity setting
                             ("0", "1", "nim", or "ttl").

        Raises:
            AssertionError: If the polarity setting is undefined.
        """
        part = aux_cols[0]
        assert part in ["0", "1", "nim", "ttl"], "Undefined auxout polarity"
        if part in ["0", "nim"]:
            self.auxline_pol = 0
        elif part in ["1", "ttl"]:
            self.auxline_pol = 1

    def set_external_input_polarity(self, aux_cols):
        """
        Sets the polarity for the external input level.

        Args:
            aux_cols (list): A list containing the polarity setting
                             ("0", "1", "nim", or "ttl").

        Raises:
            AssertionError: If the polarity setting is undefined.
        """
        part = aux_cols[0]
        assert part in ["0", "1", "nim", "ttl"], "Undefined external input polarity"
        if part in ["0", "nim"]:
            self.level = 0
        elif part in ["1", "ttl"]:
            self.level = 1

    def set_DACconfig(self, dac_config_cols):
        """
        Sets the DAC configuration mode.

        Args:
            dac_config_cols (list): A list containing the DAC configuration mode
                                    (e.g., ["static"], ["full"]).

        Raises:
            AssertionError: If the DAC configuration mode is undefined.
        """
        part = dac_config_cols[0]
        assert part in self.dacselect.keys(), f"Undefined DAC config: {part}"
        self.dacconfig = self.dacselect.get(part)

    def set_staticDAC(self, dac_vals):
        """
        Sets the static values for the DAC channels.

        These values are used if the `dacconfig` is 'static' or for DACs
        not actively updated in other modes.

        Args:
            dac_vals (list): A list of strings defining DAC channel-value pairs
                             (e.g., ["0:1.0V", "1:2000"]).
        """
        line = ",".join(dac_vals)
        dac_dict = self.dac_update(line)  # Uses Block.dac_update
        for dac_chan, val in dac_dict.items():
            self.dacs[dac_chan] = val

    def set_patgenversion(self, patgen_ver_cols):
        """
        Sets the pattern generator version (64-bit or 128-bit).

        This affects whether DAC functionality is available.

        Args:
            patgen_ver_cols (list): A list containing the version string
                                    ("64bit" or "128bit").

        Raises:
            AssertionError: If the version string is invalid.
        """
        part = patgen_ver_cols[0]
        assert part in ["128bit", "64bit"], f"Invalid pattern generator version: {part}"
        if part == "128bit":
            self.patgen_128bit = True
        elif part == "64bit":
            self.patgen_128bit = False

    def process(self):
        """
        Main processing method for the ControlBlock.
        Calls `process_control` to parse and apply settings.
        """
        self.process_control()


class SeqBlock(Block):
    """
    Represents a 'sequence' block in the pattern generator.

    A sequence block defines a series of steps, each with a duration,
    active digital channels, optional DAC updates, and optional use of
    internal variables (ivars) for looping/timing.

    The first line of a sequence block, if it's a comment, is taken as
    the sequence name.

    Attributes:
        block_type (str): Set to "sequence".
        last_step_is_loop (bool): True if the last step in the sequence uses an ivar.
        sequence_name (str): Name of the sequence (from the first comment line).
        sequence (list): A list of dictionaries, where each dictionary represents
                         a step in the sequence. Each step dict contains:
                         'time' (int): Duration in ns.
                         'chan' (list): Active digital channels.
                         'use_ivar' (int or None): Index of ivar used (0-3), or None.
                         'dac' (dict): DAC channel-value pairs.
                         'comments' (str): Comments for the step.
    """

    def __init__(self, block_id, content):
        """
        Initializes a SeqBlock instance.
        """
        super().__init__(block_id, content)
        self.block_type = "sequence"
        self.last_step_is_loop = False
        self.sequence_name = ""
        self.sequence = []

    def process_seq(self):
        """
        Parses the content of the sequence block to populate the `sequence` list.

        The first line, if a comment, sets `self.sequence_name`.
        Each subsequent line is parsed into a sequence step.
        """
        for i, line in enumerate(self.parse_contents()):
            if i == 0 and self.is_comment(line):
                self.sequence_name = line[1:].strip()  # Get name from comment
                continue
            cols = self.get_cols(line)
            self.add_seq_from_cols(cols)

    def add_seq_from_cols(self, cols):
        """
        Parses a list of columns (from a line) and adds a new step to `self.sequence`.

        Extracts time, ivar usage, channel information, and DAC updates.

        Args:
            cols (list): A list of strings representing columns from a sequence line.
        """
        time, cols = self.get_time(cols)
        use_ivar, cols = self.get_ivar(cols)  # Expects 'use_ivar <idx>' or nothing
        chan, comments1, cols = self.get_chan(cols)  # Expects 'chan <channels>'
        if cols:  # Remaining columns are assumed to be DAC info
            dac, comments2, cols = self.get_dac(cols)  # Expects 'dac <dac_updates>'
        else:
            dac = {}
            comments2 = ""
        self.sequence.append(
            {
                "time": time,
                "chan": chan,
                "use_ivar": use_ivar,
                "dac": dac,
                "comments": (comments1 + " " + comments2).strip(),
            }
        )

    def get_ivar(self, cols):
        """
        Extracts 'use_ivar' information from a list of columns.

        Looks for "use_ivar <index>" pattern. The index must be 0, 1, 2, or 3.

        Args:
            cols (list): A list of strings (columns).

        Returns:
            tuple: A tuple containing:
                - ivar_index (int or None): The ivar index (0-3) if found, else None.
                - remaining_cols (list): The columns after 'use_ivar' parsing.

        Raises:
            AssertionError: If 'use_ivar' is present but the index is invalid.
        """
        try:
            index = cols.index("use_ivar")
            ivar = int(cols[index + 1])
            cols.pop(index)  # remove 'use_ivar'
            cols.pop(index)  # remove index value
        except ValueError:  # 'use_ivar' not found
            ivar = None
        assert ivar in [None, 0, 1, 2, 3], f"Invalid ivar index: {ivar}"
        return ivar, cols

    def process(self):
        """
        Main processing method for the SeqBlock.
        Calls `process_seq` to parse the sequence definition.
        """
        self.process_seq()


class TriggerBlock(Block):
    """
    Represents a 'trigger' block in the pattern generator.

    A trigger block defines conditions based on an external input,
    event rate, or event count, and specifies subsequent blocks to
    execute based on success or failure of the trigger condition.

    The first line, if a comment, is taken as the trigger name.

    Attributes:
        block_type (str): Set to "trigger".
        trigger_name (str): Name of the trigger (from the first comment line).
        comment (list): List of comments found in the block.
        chan (list): Digital channels set when this block is active. (Set by `set_chan`)
        dac (list): DAC updates when this block is active. (Set by `get_dac`)
        rate (int): Trigger rate in Hz (if `rate` is defined).
        count (int): Trigger count (if `count` is defined).
        time_span (int): Time span in ns for count-based trigger.
        success (str): Block ID to jump to on trigger success.
        failure (str): Block ID to jump to on trigger failure.
        external_input (int): External input channel (1-4) used. (Set by `set_exinput`)
        rate_defined (bool): True if rate is used for triggering.
        count_defined (bool): True if count is used for triggering.
    """

    def __init__(self, block_id, content):
        """
        Initializes a TriggerBlock instance.
        """
        super().__init__(block_id, content)
        self.block_type = "trigger"
        self.trigger_name = ""
        self.comment = []
        self.chan = []  # Populated by set_chan
        self.dac = []  # Populated by get_dac
        self.rate_defined = None
        self.count_defined = None
        self.trigger_grammar = [
            "extinput",
            "chan",
            "rate",
            "count",
            "success",
            "failure",
            "dac",
        ]

    def process_trigger(self):
        """
        Parses the content of the trigger block to set its attributes.

        The first line, if a comment, sets `self.trigger_name`.
        Each subsequent line is parsed based on keywords defined in `trigger_grammar`.
        """
        for i, line in enumerate(self.parse_contents()):
            if self.is_comment(line) and i == 0:
                self.trigger_name = line[1:].strip()
                continue
            cols = self.get_cols(line)
            first_col = cols[0]
            next_cols = cols[1:]
            if next_cols and self.is_comment(
                next_cols[-1]
            ):  # Check if last part of next_cols is a comment
                self.comment.append(next_cols[-1])
            self.assert_grammar(first_col, self.trigger_grammar)

            if first_col == self.trigger_grammar[0]:  # extinput
                self.set_exinput(next_cols)  # Inherited from Block
            elif first_col == self.trigger_grammar[1]:  # chan
                self.set_chan(next_cols)  # Inherited from Block, sets self.chan
            elif first_col == self.trigger_grammar[2]:  # rate
                self.set_rate(next_cols)
            elif first_col == self.trigger_grammar[3]:  # count
                self.set_count(next_cols)
            elif first_col == self.trigger_grammar[4]:  # success
                self.set_success(next_cols)
            elif first_col == self.trigger_grammar[5]:  # failure
                self.set_failure(next_cols)
            elif first_col == self.trigger_grammar[6]:  # dac
                self.dac = self.set_dac(next_cols)  # Inherited from Block

    def set_rate(self, line):
        """
        Sets the trigger rate.

        Args:
            line (list): Columns defining the rate (e.g., ["100khz"]).

        Raises:
            Exception: If both rate and count are defined for the trigger.
        """
        line = self.eat_space_between_units(line)
        for i, part in enumerate(line):
            if i == 0:  # Rate value and unit
                value, unit = UnitConverter.parse_value_unit(part)
                self.rate = UnitConverter.freq(value, unit)
        if self.rate_defined is None and self.count_defined is None:
            self.rate_defined = True
        else:
            raise Exception("Use only RATE or COUNT, not both, for a trigger block.")

    def set_count(self, line):
        """
        Sets the trigger count over a specified time span.

        Args:
            line (list): Columns defining count and time span
                         (e.g., ["10", "in", "1ms"]).

        Raises:
            Exception: If both rate and count are defined for the trigger.
            ValueError: If count value is not an integer.
            AssertionError: If "in" keyword is missing.
        """
        line = self.eat_space_between_units(line)
        for i, part in enumerate(line):
            if i == 0:  # Count value
                try:
                    self.count = int(part)
                except ValueError:
                    raise ValueError("Count value should be an integer.")
            elif i == 1:  # "in" keyword
                assert (
                    part.lower() == "in"
                ), "Keyword 'in' missing for count definition."
            elif i == 2:  # Time span value and unit
                value, unit = UnitConverter.parse_value_unit(part)
                self.time_span = UnitConverter.time(value, unit)

        if self.rate_defined is None and self.count_defined is None:
            self.count_defined = True
        else:
            raise Exception("Use only RATE or COUNT, not both, for a trigger block.")

    def set_success(self, outcome):
        """
        Sets the block ID to jump to on trigger success.

        Args:
            outcome (list): A list containing the block ID string.
        """
        self.success = outcome[0]

    def set_failure(self, outcome):
        """
        Sets the block ID to jump to on trigger failure.

        Args:
            outcome (list): A list containing the block ID string.
        """
        self.failure = outcome[0]

    def check_consistent(self, success=None, failure=None):
        """
        Checks if the provided success/failure logic matches the block's settings.

        Used by the Translator to verify logic flow.

        Args:
            success (str, optional): Expected success block ID.
            failure (str, optional): Expected failure block ID.

        Raises:
            AssertionError: If the provided logic does not match the block's.
        """
        if success is not None:
            assert (
                success == self.success
            ), f"Success logic mismatch: expected {self.success}, got {success}"
        if failure is not None:
            assert (
                failure == self.failure
            ), f"Failure logic mismatch: expected {self.failure}, got {failure}"
        return

    def process(self):
        """
        Main processing method for the TriggerBlock.
        Calls `process_trigger` to parse the trigger definition.
        """
        self.process_trigger()


class LoopBlock(Block):
    """
    Represents a 'loop' block in the pattern generator.

    A loop block uses an internal variable (ivar) as a counter to repeat
    a sequence of other blocks or operations.

    The first line, if a comment, is taken as the loop name.
    The second line defines the ivar, its initial count, and optional
    channel/DAC settings for each iteration.
    Subsequent lines define the logic flow within the
    loop (connections to other blocks).

    Attributes:
        block_type (str): Set to "loop".
        loop_name (str): Name of the loop (from the first comment line).
        logic (list): Temporary list used by `match_logic`
                      (inherited from MermaidParser via Block).
                      Should be cleared or handled carefully if `match_logic`
                      is called directly.
        loop_logic (list): A list of logic connections (tuples) that form the
                           body of the loop. Each tuple is like:
                           (source_block_id, target_block_id, condition_str).
        counter_var (int): Index of the ivar used for counting (0-3).
        counter_val (int): Initial value for the ivar counter.
        loop_set (dict): Contains settings for each loop iteration:
                         'chan' (list): Active digital channels.
                         'use_ivar' (int): The `counter_var`.
                         'dac' (dict): DAC channel-value pairs.
                         'comments' (str): Comments for the loop setup line.
    """

    def __init__(self, block_id, content):
        """
        Initializes a LoopBlock instance.
        """
        super().__init__(block_id, content)
        self.block_type = "loop"
        self.loop_name = ""
        self.logic = []  # Inherited from MermaidParser, used by self.match_logic
        self.loop_logic = []  # Stores logic specific to this loop block

    def process_loop(self):
        """
        Parses the content of the loop block to set its attributes.

        - First line (if comment): sets `self.loop_name`.

        - Second line: parses ivar, count, and optional channel/DAC settings
          using `get_ivar` and `get_chan`/`get_dac`.

        - Subsequent lines: parse as logic connections using `add_logic_from_line`.
        """
        for i, line in enumerate(self.parse_contents()):
            if i == 0 and self.is_comment(line):
                self.loop_name = line[1:].strip()
                continue
            if i == 1:  # ivar setup line
                cols = self.get_cols(line)
                # get_ivar for LoopBlock is specific, not from SeqBlock
                self.counter_var, self.counter_val, cols = self.get_ivar(cols)
                chan, comments1, cols = self.get_chan(cols)
                if cols:
                    dac, comments2, cols = self.get_dac(cols)
                else:
                    dac = {}
                    comments2 = ""
                self.loop_set = {
                    "chan": chan,
                    "use_ivar": self.counter_var,  # Store which ivar is the counter
                    "dac": dac,
                    "comments": (comments1 + " " + comments2).strip(),
                }
            else:  # Logic lines within the loop
                self.add_logic_from_line(line)

    def add_logic_from_line(self, line):
        """
        Parses a line for a logic connection and adds it to `self.loop_logic`.

        Uses `self.match_logic` (inherited from MermaidParser via Block) which
        appends to `self.logic`. This method then moves the last added item
        from `self.logic` to `self.loop_logic`.

        Args:
            line (str): The line defining a logic connection.
        """
        self.match_logic(line)  # Appends to self.logic
        if len(self.logic) > 0:
            self.loop_logic.append(
                self.logic.pop()
            )  # Move from self.logic to self.loop_logic

    def get_ivar(self, cols):
        """
        Extracts ivar index and count value for the loop counter.

        Expects "ivar <index> <value>" followed by optional 'chan' or 'dac'.

        Args:
            cols (list): A list of strings (columns from the ivar setup line).

        Returns:
            tuple: A tuple containing:
                - ivar_index (int): The ivar index (0-3).
                - count_value (int): The initial count for the loop.
                - remaining_cols (list): Columns after ivar parsing (for chan/dac).

        Raises:
            AssertionError: If keyword 'ivar' is missing, index is invalid,
                            or value is out of bounds.
        """
        assert (
            cols[0].lower() == "ivar"
        ), "Wrong keyword, expected 'ivar' for loop setup."
        ivar = int(cols[1])
        assert ivar in [0, 1, 2, 3], "Counter ivar index must be 0, 1, 2, or 3."
        val = int(cols[2])
        assert val > 0 and val < 65536, "Counter value out of bounds (1-65535)."

        # Prepare remaining columns for further parsing (chan/dac)
        remaining_cols = cols[3:]
        return ivar, val, remaining_cols

    def process(self):
        """
        Main processing method for the LoopBlock.
        Calls `process_loop` to parse the loop definition.
        """
        self.process_loop()


class BranchBlock(Block):
    """
    Represents a 'branch' block in the pattern generator.

    A branch block makes a decision based on an external input's level (high or low)
    and jumps to a different block accordingly. It can also define a default
    timestep, digital channels, and DAC settings to apply while waiting for the input.

    The first line, if a comment, is taken as the branch name.

    Attributes:
        block_type (str): Set to "branch".
        branch_name (str): Name of the branch (from the first comment line).
        chan (list): Digital channels to set. (Populated by `get_chan`)
        dac (list): DAC updates. (Populated by `get_dac`)
        comment (list): List of comments found in the block.
        external_input (int): External input channel (1-4) used. (Set by `set_exinput`)
        high (str): Block ID to jump to if the external input is high.
        low (str): Block ID to jump to if the external input is low.
        timestep (int): Default time step in ns for this block, if specified.
    """

    def __init__(self, block_id, content):
        """
        Initializes a BranchBlock instance.
        """
        super().__init__(block_id, content)
        self.block_type = "branch"
        self.branch_name = ""
        self.chan = []  # Will be populated by get_chan if 'chan' keyword is present
        self.dac = []  # Will be populated by get_dac if 'dac' keyword is present
        self.comment = []  # Initialize comment list
        self.branch_grammar = ["extinput", "high", "low", "chan", "dac"]
        # timestep might be set directly if a line is just a time value

    def process_branch(self):
        """
        Parses the content of the branch block to set its attributes.

        The first line, if a comment, sets `self.branch_name`.
        Each subsequent line is parsed based on keywords in `branch_grammar`
        or as a direct time value.
        """
        for i, line in enumerate(self.parse_contents()):
            if self.is_comment(line) and i == 0:
                self.branch_name = line[1:].strip()
                continue
            cols = self.get_cols(line)
            if not cols:  # Skip empty lines
                continue

            if (
                len(cols) > 1 or cols[0].lower() in self.branch_grammar
            ):  # Keyword-based line
                first_col = cols[0].lower()
                next_cols = cols[1:]

                # Check for comments at the end of next_cols
                if next_cols and self.is_comment(next_cols[-1]):
                    self.comment.append(
                        next_cols.pop()
                    )  # Add comment and remove from next_cols

                self.assert_grammar(first_col, self.branch_grammar)

                if first_col == self.branch_grammar[0]:  # extinput
                    self.set_exinput(next_cols)  # Inherited from Block
                elif first_col == self.branch_grammar[1]:  # high
                    self.set_high(next_cols)
                elif first_col == self.branch_grammar[2]:  # low
                    self.set_low(next_cols)
                elif first_col == self.branch_grammar[3]:  # chan
                    self.set_chan(cols)  # Pass original cols
                elif first_col == self.branch_grammar[4]:  # dac
                    self.set_dac(cols)  # Pass original cols
            elif len(cols) == 1 or (
                len(cols) == 2 and UnitConverter.time_units.get(cols[1].lower())
            ):
                # Assumed to be a time definition line
                # e.g. "10ns" or "10 ns"
                try:
                    self.timestep, _ = self.get_time(cols)
                except ValueError:
                    # This might occur if the line is not a valid time format
                    # or an unrecognized single-word command.
                    raise ValueError(
                        f"Invalid line in branch block: '{line}'. "
                        + "Expected command or time value."
                    )
            else:
                # Fallback for lines that are not empty, not keyword-based, and not time
                # This case should ideally not be reached if grammar is complete.
                raise ValueError(f"Unrecognized line format in branch block: '{line}'")

    def set_high(self, outcome):
        """
        Sets the block ID to jump to if the external input is high.

        Args:
            outcome (list): A list containing the block ID string.
        """
        self.high = outcome[0]

    def set_low(self, outcome):
        """
        Sets the block ID to jump to if the external input is low.

        Args:
            outcome (list): A list containing the block ID string.
        """
        self.low = outcome[0]

    def check_consistent(self, high=None, low=None):
        """
        Checks if the provided high/low logic matches the block's settings.

        Used by the Translator to verify logic flow.

        Args:
            high (str, optional): Expected 'high' block ID.
            low (str, optional): Expected 'low' block ID.

        Raises:
            AssertionError: If the provided logic does not match the block's.
        """
        if high is not None:
            assert high == self.high, (
                f"High logic mismatch for branch {self.block_id}: "
                + f"expected {self.high}, got {high}"
            )
        if low is not None:
            assert low == self.low, (
                f"Low logic mismatch for branch {self.block_id}: "
                + f"expected {self.low}, got {low}"
            )
        return

    def process(self):
        """
        Main processing method for the BranchBlock.
        Calls `process_branch` to parse the branch definition.
        """
        self.process_branch()


class BlockFactory:
    """
    Factory to create block objects based on block name/id.
    Register block classes using BlockFactory.register().
    """

    _registry: Dict[str, Block] = {}

    @classmethod
    def register(cls, prefix, block_cls):
        """
        Registers a block class with a given prefix.

        The factory uses these registered classes to create block instances.
        The prefix is matched against the beginning of a block's ID (case-insensitive).

        Args:
            prefix (str): The prefix string to associate with the block class.
            block_cls (type): The block class (e.g., `ControlBlock`, `SeqBlock`).
        """
        cls._registry[prefix.lower()] = block_cls

    @classmethod
    def create(cls, block_id, content):
        """
        Creates a block instance based on its ID.

        It iterates through the registered block types and instantiates the
        first one whose prefix matches the beginning of the `block_id`.

        Args:
            block_id (str): The unique identifier of the block.
            content (str): The raw content of the block.

        Returns:
            Block: An instance of the appropriate subclass of `Block`.

        Raises:
            NotImplementedError: If no registered block type matches the `block_id`.
        """
        for prefix, block_cls in cls._registry.items():
            if block_id.lower().startswith(prefix):
                return block_cls(block_id, content)
        raise NotImplementedError(
            f"Block type for ID '{block_id}' not implemented or registered."
        )


BlockFactory.register("control", ControlBlock)
BlockFactory.register("seq", SeqBlock)
BlockFactory.register("trigger", TriggerBlock)
BlockFactory.register("loop", LoopBlock)
BlockFactory.register("branch", BranchBlock)


class Translator:
    """
    Translates parsed Mermaid-like block definitions into a hardware-specific
    pattern file format (.dpatt).

    The Translator takes a dictionary of parsed blocks and a list of logic
    connections, processes them, and generates the output file content.
    It handles:
    - Processing configuration from the 'control' block.
    - Preprocessing all other blocks to determine their size in pattern rows.
    - Assigning start and end row addresses to each block based on logic.
    - Generating the 'writew' lines for each block's functionality.
    - Writing the final .dpatt file.
    """

    def __init__(self, blocks, logic, filein, fileout, hex=True, verbose=False):
        """
        Initializes the Translator.

        Args:
            blocks (dict): Dictionary of block_id to raw block content string,
                           as returned by MermaidParser.get_blocks().
            logic (list): List of logic connection tuples
                          (source_id, target_id, condition_str),
                          as returned by MermaidParser.get_logic().
            filein (str): Name of the input Mermaid-like file (for logging).
            fileout (str): Path to the output .dpatt file.
            hex (bool): If True, output numerical values in hexadecimal (except time).
            verbose (bool): If True, include more detailed comments in the output file.
        """
        self.blocks = {}  # This will store processed Block objects
        self.hex = hex
        self.verbose = verbose
        self.logic = logic  # Overall program flow logic
        self.config_bits = 0
        self.param_register = []
        self.new_dpatt_str = ""  # String for the main pattern program
        self.dpatt_str = (
            f"#This file was generated by gen3.py using {filein}\n\n"  # Header  .dpatt
        )
        self.fileout = fileout

        # Create and process each block object
        for key, value in blocks.items():
            block_obj = BlockFactory.create(key, value)
            self.blocks[key] = block_obj  # Store the Block object instance
            block_obj.process()  # Call the block's specific process() method

        # Default configuration bits for initial setup
        PARAMETERWRITE = 8  # Bit 3: Write to parameter RAM
        ADDRESSRESET = 4  # Bit 2: Reset address counter on jump
        TABLERESET = 1  # Bit 0: Reset table pointer

        self.process_config()  # Process the 'control' block for global settings
        self.write_config(
            PARAMETERWRITE + ADDRESSRESET + TABLERESET
        )  # Write initial config word
        self.write_param()  # Write parameter register values

        self.preprocess_blocks()  # Calculate row requirements and assign addresses
        self.process_logic()  # Generate the 'writew' lines for the pattern
        self.write_out()  # Write everything to the output file

    def write_out(self):
        """
        Writes the generated .dpatt content to the output file.
        Appends a "run;" command at the end.
        """
        with open(self.fileout, "w") as f:
            f.write(self.dpatt_str)  # Header, config, params
            f.write(self.new_dpatt_str)  # Main pattern program
            f.write(f"\n\nconfig {self.config_bits}; #Release hold")
            # f.write("\n\nrun; #Run sequence")

    def preprocess_blocks(self):
        """
        Preprocesses all blocks to determine their required number of pattern rows
        and assigns `first_row` and `last_row` attributes to each block.

        This involves:
        1. Calculating `num_rows` for each non-control block via `determine_num_rows`.
        2. Iterating through the main program `logic` to lay out blocks sequentially
           in memory, assigning `first_row` and `last_row` for each block and
           any nested blocks (like within a loop).
        """
        # Go through blocks and determine rows needed for each
        for block_id, block_obj in self.blocks.items():
            if block_obj.block_type == "control":
                continue
            else:
                self.determine_num_rows(block_obj)

        # Go through main logic and determine start/end addresses of each block
        first_block_in_logic = True
        current_row_count = 0
        for block_start_id, block_end_id, condition in self.logic:
            start_block = self.blocks[block_start_id]

            if first_block_in_logic:
                start_block.first_row = 0
                current_row_count = start_block.first_row + start_block.num_rows
                start_block.last_row = current_row_count - 1
                first_block_in_logic = False
                continue

            # Assign rows for start_block if not already assigned
            if start_block.first_row is None:
                start_block.first_row = current_row_count
                current_row_count += start_block.num_rows
                start_block.last_row = current_row_count - 1
            elif start_block.last_row is None:  # Should be set if first_row is set
                current_row_count = start_block.first_row + start_block.num_rows
                start_block.last_row = current_row_count - 1

            end_block = self.blocks[block_end_id]
            if end_block.first_row is None:  # If end_block hasn't been placed yet
                end_block.first_row = current_row_count
                if end_block.block_type == "loop":
                    # Special handling for loops: account for setup rows and
                    #                             rows of nested blocks
                    current_row_count += 2  # For loop load var and decrement counter
                    for (
                        nested_block_start_id,
                        nested_block_end_id,
                        _,
                    ) in end_block.loop_logic:  # assume no nested loop
                        nested_block = self.blocks[nested_block_start_id]
                        if nested_block.first_row is None:
                            nested_block.first_row = current_row_count
                            current_row_count += nested_block.num_rows
                            nested_block.last_row = current_row_count - 1
                        if nested_block.last_row is None:
                            current_row_count = (
                                nested_block.first_row + nested_block.num_rows
                            )
                            nested_block.last_row = current_row_count - 1

                if end_block.block_type == "loop":
                    current_row_count += 2  # 2 for check and zero conndition address
                    end_block.last_row = current_row_count - 1
                else:
                    current_row_count += end_block.num_rows
                    end_block.last_row = current_row_count - 1

    def determine_num_rows(self, block):
        """
        Determines the number of hardware pattern rows required for a given block.

        Calls the appropriate `preprocess_<block_type>` method.

        Args:
            block (Block): The block object whose `num_rows` attribute will be set.
        """
        if block.block_type == "sequence":
            self.preprocess_seq(block)
        elif block.block_type == "trigger":
            self.preprocess_trigger(block)
        elif block.block_type == "loop":
            self.preprocess_loop(block)
        elif block.block_type == "branch":
            self.preprocess_branch(block)
        else:
            raise AssertionError(
                f"Unknown block type for row determination: {block.block_type}"
            )

    def preprocess_branch(self, block):
        """
        Calculates `num_rows` for a BranchBlock.
        A branch uses 1 row if its 'low' branch target is the immediately
        following block in the main logic; otherwise, it uses 2 rows.

        Args:
            block (BranchBlock): The branch block to process.
        """
        low_target_id = block.low
        block_id = block.block_id
        block.num_rows = 2  # Default to 2 rows
        # Check if the 'low' branch target immediately follow
        # this branch block in the main logic
        for i, (src, _, _) in enumerate(self.logic):
            if src == block_id:
                if i + 1 < len(self.logic):
                    next_block_in_logic_id = self.logic[i + 1][0]
                    if next_block_in_logic_id == low_target_id:
                        block.num_rows = 1
                        break
                # If it's the last block or next block isn't the low target,
                # it remains 2 rows.
                break

    def preprocess_trigger(self, block):
        """
        Sets `num_rows` for a TriggerBlock.
        Trigger blocks are allocated a fixed number of rows (currently 5)
        to accommodate various operations like loading variables, decrementing,
        and checking conditions.

        The 5 rows are typically for:
        1. Load evar (and ivar if needed for long time_span).
        2. Decrement ivar counter (if ivar used).
        3. Check non-zero ivar and branch (if ivar used).
        4. Check non-zero evar and branch to failure_row.
        5. Branch to success_row (if evar was zero).

        Args:
            block (TriggerBlock): The trigger block to process.
        """
        block.num_rows = 5

    def preprocess_loop(self, block):
        """
        Sets `num_rows` for a LoopBlock.
        Loop blocks are allocated a fixed number of rows (currently 4)
        for their control structure, plus rows for blocks inside the loop.
        The 4 rows are for:
        1. Load ivar (counter).
        2. Decrement ivar.
        3. Check ivar non-zero and branch to loop start.
        4. Branch to loop exit (when ivar is zero).
        Rows for blocks *inside* the loop are accounted for during the main
        `preprocess_blocks` logic traversal.

        Args:
            block (LoopBlock): The loop block to process.
        """
        # The num_rows for a loop block itself (control structure)
        block.num_rows = 4  # For load, decrement, check, and exit branching.
        # Rows for blocks *inside* the loop are added during the
        # main preprocess_blocks logic traversal.

    def preprocess_seq(self, block):
        """
        Calculates `num_rows` for a SeqBlock based on its sequence steps.
        Each step contributes rows depending on its duration and use of ivars.

        Args:
            block (SeqBlock): The sequence block to process.
        """
        rows = 0
        seq_len = len(block.sequence) - 1
        for j, step in enumerate(block.sequence):
            time = step["time"]
            ivar_idx = step["use_ivar"]  # Corrected from 'i' to 'ivar_idx' for clarity
            ivar_val = (
                self.ivars[ivar_idx] if ivar_idx is not None else None
            )  # Use self.ivars from control block

            if ivar_val:  # If an ivar is used for this step
                rows += 1  # For ivar load operation
                # Each full loop operation (decrement + check) takes 2 rows.
                # Effective time per full loop cycle = self.maxtimestep * 2 (approx)
                if (
                    time / self.maxtimestep / ivar_val / 2 <= 1
                ):  # Heuristic for simpler loop
                    rows += 2  # For one decrement and one check
                else:  # For longer durations requiring multiple decrement cycles
                    # per ivar load
                    rows += 2 + ceil(
                        time / self.maxtimestep / ivar_val
                    )  # Additional lines for extended time
                if j == seq_len:  # If this ivar-based step is the last in the sequence
                    rows += 1  # Add one more line for explicit jump if loop is last
                    block.last_step_is_loop = True
            elif (
                ceil(time / self.maxtimestep) < 1
            ):  # Single step, fits in one maxtimestep
                rows += 1  # For a single 'writew' line
            else:  # Step duration exceeds maxtimestep, requires multiple 'writew' lines
                additional_rows = ceil(time / self.maxtimestep)
                if additional_rows > 4:  # Warning for very long steps
                    warnings.warn(
                        f"Sequence step in '{block.block_id}' uses {additional_rows} "
                        + "rows. Consider using an ivar for better efficiency."
                    )
                rows += additional_rows
        block.num_rows = rows

    def process_logic(self):
        """
        Generates the main pattern program string (`self.new_dpatt_str`)
        by iterating through the `self.logic` flow and calling specific
        `process_<block_type>_logic` methods for each unwritten block.
        """
        # self.new_dpatt_str += (
        #    "\nholdaddr; ramprog;\n"  # Commands to prepare for pattern writing
        # )
        ADDRESSRESET = 4  # Bit 2: Reset address counter on jump
        TABLERESET = 1  # Bit 0: Reset table pointer
        self.write_config(
            ADDRESSRESET + TABLERESET
        )  # nominally writes config 5 unless other bits are set too
        self.pattern_row = self.param_register[0]  # Initialize current patt row number
        for block_start_id, block_end_id, condition_str in self.logic:
            start_block = self.blocks[block_start_id]
            # end_block might not always be a Block object if
            # it's a special target like 'loop_check'. For now, assume block_end_id
            # refers to a key in self.blocks for general cases. Specific logic
            # handlers (e.g., process_loop_logic) will manage special end targets.
            end_block = self.blocks.get(
                block_end_id
            )  # Use .get() for safety, handle None if needed

            if (
                start_block.written
            ):  # Skip if this block's pattern has already been generated
                continue

            # Dispatch to specific logic processors based on block type
            if start_block.block_type == "trigger":
                self.process_trigger_logic(start_block, end_block, condition_str)
            elif start_block.block_type == "sequence":
                self.process_seq_logic(
                    start_block, end_block
                )  # end_block is the next block after sequence
            elif start_block.block_type == "loop":
                self.process_loop_logic(
                    start_block, end_block
                )  # end_block is the block after loop finishes
            elif start_block.block_type == "branch":
                self.process_branch_logic(start_block, end_block, condition_str)

    def process_branch_logic(
        self, branch_block, end_block_unused, condition_str_unused
    ):
        """
        Generates 'writew' lines for a BranchBlock.

        Args:
            branch_block (BranchBlock): The branch block to process.
            end_block_unused: Typically the next block in main flow,
                              but branch logic uses internal high/low targets.
            condition_str_unused: Condition from main logic,
                                  not directly used here as branch has its own.
        """
        ext_chan_idx = branch_block.external_input  # 1-4
        dig_chan_settings = {"chan": branch_block.chan, "dac": branch_block.dac}
        time_for_check = (
            branch_block.timestep
            if hasattr(branch_block, "timestep")
            else self.timestep
        )  # Use block's time or default
        comment = f"Branch on ext input {ext_chan_idx}"

        # Address for 'high' and 'low' outcomes are determined by
        # the target blocks' first_row
        target_high_block = self.blocks[branch_block.high]
        target_low_block = self.blocks[branch_block.low]
        special_bcheck_address_high = target_high_block.first_row
        special_bcheck_address_low = target_low_block.first_row

        # Special command for branching: ((external_input_index + 3) << 12)
        # External inputs e1,e2,e3,e4 correspond to indices 0,1,2,3 for this calculation
        special_bcheck_command = (
            ext_chan_idx - 1 + 4
        ) << 12  # Adjust index for 0-based

        # Line 1: Check condition, go to 'high' address if input is high
        self.new_dpatt_str += self.writew_line(
            channels=dig_chan_settings,
            time=time_for_check,
            address={
                "address": special_bcheck_address_high,
                "special": special_bcheck_command,
                "cond": None,
            },
            comment=comment + f", if high go to {special_bcheck_address_high}",
        )

        # Line 2 (optional): Go to 'low' address if input was low
        # (fall-through from previous check)
        # This line is only needed if the 'low' target isn't
        # the immediately next line naturally.
        if branch_block.num_rows == 2:  # num_rows determined in preprocess_branch
            self.new_dpatt_str += self.writew_line(
                channels=dig_chan_settings,
                time=time_for_check,
                address={
                    "address": special_bcheck_address_low,  # Explicit jump to low targ
                    "special": None,  # No special command, just a goto
                    "cond": None,
                },
                comment=comment + f", if low go to {special_bcheck_address_low}",
            )
        branch_block.written = True

    def process_loop_logic(self, loop_block, after_loop_block):
        """
        Generates 'writew' lines for a LoopBlock and its contained logic.

        Args:
            loop_block (LoopBlock): The loop block to process.
            after_loop_block (Block): The block to jump to after the loop finishes.
        """
        self.new_dpatt_str += (
            f"\n# Loop Block: {loop_block.block_id} ({loop_block.loop_name})\n"
        )

        ivar_idx = loop_block.counter_var  # 0-3
        assert (
            self.ivars[ivar_idx] == loop_block.counter_val
        ), "Count in loop block doesn't match ivars in control block"
        dig_chan_settings = {
            "chan": loop_block.loop_set["chan"],
            "dac": loop_block.loop_set["dac"],
        }
        time_for_control_ops = (
            self.timestep
        )  # Use global minimum timestep for loop control
        loop_comment_base = loop_block.loop_set["comments"]

        # Special commands for ivar operations
        # Load: (1<<12) + ((1 << ivar_idx) << 4)
        # Dec : (1<<12) + ((1 << ivar_idx) << 8)
        # Check: ((12 + ivar_idx) << 12)
        special_load_ivar = (1 << 12) | ((1 << ivar_idx) << 4)
        special_decrement_ivar = (1 << 12) | ((1 << ivar_idx) << 8)
        special_check_ivar_nonzero = (12 + ivar_idx) << 12

        # 1. Load ivar (counter_var with its pre-set value from param_register)
        self.new_dpatt_str += self.writew_line(
            channels=dig_chan_settings,
            time=time_for_control_ops,
            address={
                "address": None,  # Address is next line
                "special": special_load_ivar,
                "cond": None,
            },
            comment=f"Load ivar {ivar_idx}. {loop_comment_base}",
        )

        # Mark the start of the loop body (for looping back if ivar is non-zero)
        loop_body_start_row = self.pattern_row

        # 2. Decrement ivar
        self.new_dpatt_str += self.writew_line(
            channels=dig_chan_settings,
            time=time_for_control_ops,
            address={
                "address": None,  # Address is next line
                "special": special_decrement_ivar,
                "cond": None,
            },
            comment=f"Decrement ivar {ivar_idx}. {loop_comment_base}",
        )

        # Process blocks inside the loop
        for nested_start_id, nested_end_id, nested_condition in loop_block.loop_logic:
            nested_start_block = self.blocks[nested_start_id]
            # nested_end_block needs careful handling:
            # If nested_end_id is 'loop_check', it means jump to the loop's own
            # check mechanism. Otherwise, it's a standard block ID.
            if nested_end_id == "loop_check":
                # Create a placeholder or use a specific mechanism
                # for 'loop_check' target. For now, the address for 'loop_check' will be
                # loop_block.last_row - 1 (the check ivar line). This means
                # process_trigger_logic etc. need to handle end.block_id == 'loop_check'
                # and use a pre-calculated target row (e.g. end.loop_check_row)
                class LoopCheckTarget:
                    pass  # Dummy class for type checking if needed

                nested_end_target = LoopCheckTarget()
                nested_end_target.block_id = "loop_check"
                # The actual target row for "loop_check" is
                # the 'special_check_ivar_nonzero' line
                nested_end_target.loop_check_row = (
                    loop_block.last_row - 1
                )  # loop_block.num_rows = 4, so this is 3rd row from its start
            else:
                nested_end_target = self.blocks[nested_end_id]

            # if nested_start_block.written:
            #    continue

            if nested_start_block.block_type == "trigger":
                self.process_trigger_logic(
                    nested_start_block, nested_end_target, nested_condition
                )
            elif nested_start_block.block_type == "sequence":
                self.process_seq_logic(nested_start_block, nested_end_target)
            elif nested_start_block.block_type == "branch":
                self.process_branch_logic(
                    nested_start_block, nested_end_target, nested_condition
                )
            # Note: Loops inside loops are not supported.
            # The block layout in preprocess_blocks should allocate space if declared.
            # However, generating nested loop control logic need more specific handling.

        # 3. Check ivar: if non-zero, jump to loop_body_start_row
        self.new_dpatt_str += self.writew_line(
            channels=dig_chan_settings,
            time=time_for_control_ops,
            address={
                "address": loop_body_start_row,  # Jump here if ivar non-zero
                "special": special_check_ivar_nonzero,
                "cond": None,
            },
            comment=f"Check ivar {ivar_idx}. If non-zero, "
            + f"goto row {loop_body_start_row}. {loop_comment_base}",
        )

        # 4. If ivar is zero (fall-through), jump to the block after the loop
        after_loop_target_row = (
            after_loop_block.first_row if after_loop_block else self.pattern_row + 1
        )  # Fall to next or specific target
        self.new_dpatt_str += self.writew_line(
            channels=dig_chan_settings,
            time=time_for_control_ops,
            address={
                "address": after_loop_target_row,
                "special": None,  # Simple goto
                "cond": None,
            },
            comment=f"Ivar {ivar_idx} is zero. Goto row "
            + f"{after_loop_target_row}. {loop_comment_base}",
        )
        loop_block.written = True

    def process_seq_logic(self, seq_block, next_block_after_seq):
        """
        Generates 'writew' lines for a SeqBlock.

        Args:
            seq_block (SeqBlock): The sequence block to process.
            next_block_after_seq (Block): The block to jump to after
                                          the sequence completes.
        """
        num_steps_in_seq = len(seq_block.sequence)
        self.new_dpatt_str += (
            f"\n# Sequence Block: {seq_block.block_id} ({seq_block.sequence_name})\n"
        )

        for i, step in enumerate(seq_block.sequence):
            time_ns = step["time"]
            ivar_idx = step["use_ivar"]  # 0-3 or None
            dig_chan_settings = {"chan": step["chan"], "dac": step["dac"]}
            step_comment = step["comments"]
            # ivar_val is the pre-loaded value in hardware for that ivar_idx
            ivar_val = self.ivars[ivar_idx] if ivar_idx is not None else None

            is_last_step = i == num_steps_in_seq - 1

            if ivar_val:  # Step uses an internal variable for timing/looping
                actual_time_ns = time_ns
                # If it's the last step of the sequence AND it's an ivar loop,
                # one timestep might be reserved for the final jump out of the sequence.
                if seq_block.last_step_is_loop and is_last_step:
                    actual_time_ns = time_ns - self.timestep

                # Special commands for ivar operations (same as in loop_block)
                special_load_ivar = (1 << 12) | ((1 << ivar_idx) << 4)
                special_decrement_ivar = (1 << 12) | ((1 << ivar_idx) << 8)
                special_check_ivar_nonzero = (12 + ivar_idx) << 12

                verbose_comment = ""
                if self.verbose:
                    verbose_comment = f" (ivar {ivar_idx})"

                # Determine loop structure based on time and ivar capability
                # This logic is complex and aims to
                # balance load/decrement/check operations
                # Simplified: if time can be achieved with
                # one load and a few dec/checks vs many.
                # The `timebalancer` method calculates
                # optimal `time_per_loop_line` and `load_line_time`.
                if (
                    actual_time_ns / self.maxtimestep / ivar_val / 2 <= 1
                ):  # Simpler loop structure
                    num_loop_lines_for_timing = 2  # dec, check
                    time_per_loop_line, load_line_time = self.timebalancer(
                        actual_time_ns, ivar_val, num_loop_lines_for_timing
                    )

                    # 1. Load ivar
                    self.new_dpatt_str += self.writew_line(
                        channels=dig_chan_settings,
                        time=load_line_time,
                        address={
                            "address": None,
                            "special": special_load_ivar,
                            "cond": None,
                        },
                        comment=f"Load ivar{verbose_comment}. {step_comment}",
                    )

                    loop_dec_target_row = self.pattern_row
                    # 2. Decrement ivar
                    self.new_dpatt_str += self.writew_line(
                        channels=dig_chan_settings,
                        time=time_per_loop_line,
                        address={
                            "address": None,
                            "special": special_decrement_ivar,
                            "cond": None,
                        },
                        comment=f"Decrement ivar{verbose_comment}. {step_comment}",
                    )

                    # 3. Check ivar (non-zero implies loop back to decrement)
                    self.new_dpatt_str += self.writew_line(
                        channels=dig_chan_settings,
                        time=time_per_loop_line,
                        address={
                            "address": loop_dec_target_row,
                            "special": special_check_ivar_nonzero,
                            "cond": None,
                        },
                        comment=f"Check ivar{verbose_comment}, loop to "
                        + f"{loop_dec_target_row}. {step_comment}",
                    )
                else:  # More complex loop for very long times
                    num_loop_lines_for_timing = ceil(
                        actual_time_ns / self.maxtimestep / ivar_val
                    )
                    time_per_loop_line, load_line_time = self.timebalancer(
                        actual_time_ns, ivar_val, num_loop_lines_for_timing
                    )

                    self.new_dpatt_str += self.writew_line(
                        channels=dig_chan_settings,
                        time=load_line_time,
                        address={
                            "address": None,
                            "special": special_load_ivar,
                            "cond": None,
                        },
                        comment=f"Load ivar{verbose_comment} (long). {step_comment}",
                    )

                    loop_dec_target_row = self.pattern_row
                    self.new_dpatt_str += self.writew_line(
                        channels=dig_chan_settings,
                        time=time_per_loop_line,
                        address={
                            "address": None,
                            "special": special_decrement_ivar,
                            "cond": None,
                        },
                        comment=f"Decrement ivar{verbose_comment} (long). "
                        + f"{step_comment}",
                    )

                    for _ in range(
                        num_loop_lines_for_timing - 2
                    ):  # Additional lines for timing
                        self.new_dpatt_str += self.writew_line(
                            channels=dig_chan_settings,
                            time=time_per_loop_line,
                            address={
                                "address": None,
                                "special": None,
                                "cond": None,
                            },
                            comment=f"Timing line for ivar{verbose_comment}. "
                            + f"{step_comment}",
                        )

                    self.new_dpatt_str += self.writew_line(
                        channels=dig_chan_settings,
                        time=time_per_loop_line,
                        address={
                            "address": loop_dec_target_row,
                            "special": special_check_ivar_nonzero,
                            "cond": None,
                        },
                        comment=f"Check ivar{verbose_comment} (long), "
                        + f"loop to {loop_dec_target_row}. {step_comment}",
                    )

                # If this ivar-based step is the last in the sequence, add explicit jump
                if seq_block.last_step_is_loop and is_last_step:
                    target_address = (
                        next_block_after_seq.first_row
                        if next_block_after_seq
                        else self.pattern_row + 1
                    )
                    self.new_dpatt_str += self.writew_line(
                        channels=dig_chan_settings,
                        time=self.timestep,  # Minimal time for jump
                        address={
                            "address": target_address,
                            "special": None,
                            "cond": None,
                        },
                        comment=f"End of ivar step, to {target_address}. "
                        + f"{step_comment}",
                    )

            else:  # Step does not use an ivar, simple time delay
                if ceil(time_ns / self.maxtimestep) < 1:  # Fits in one pattern line
                    target_address = (
                        next_block_after_seq.first_row
                        if is_last_step and next_block_after_seq
                        else None
                    )
                    self.new_dpatt_str += self.writew_line(
                        channels=dig_chan_settings,
                        time=time_ns,
                        address={
                            "address": target_address,
                            "special": None,
                            "cond": None,
                        },
                        comment=step_comment,
                    )

                else:  # Requires multiple pattern lines
                    remaining_time_ns = time_ns
                    while remaining_time_ns > 0:
                        current_line_time = min(remaining_time_ns, self.maxtimestep)
                        remaining_time_ns -= current_line_time
                        is_final_part_of_step = remaining_time_ns == 0
                        target_address = (
                            next_block_after_seq.first_row
                            if is_last_step
                            and is_final_part_of_step
                            and next_block_after_seq
                            else None
                        )

                        self.new_dpatt_str += self.writew_line(
                            channels=dig_chan_settings,
                            time=int(current_line_time),
                            address={
                                "address": target_address,
                                "special": None,
                                "cond": None,
                            },
                            comment=step_comment,
                        )
                        # count +=1
        seq_block.written = True

    def timebalancer(self, time, ivar_value, looplines=2):
        """
        Balances time distribution between the initial 'load ivar' line
        and subsequent looping lines for timed sequences using ivars.

        The goal is to make `(time - load_timestep) / ivar_value / timestep` evenly
        divisible by `looplines` (number of pattern lines per ivar decrement cycle).

        Args:
            time (int): Total desired time in ns for the ivar-controlled segment.
            ivar_value (int): The value of the ivar (number of loops).
            looplines (int): Number of pattern lines used per single
                             decrement of the ivar
                             (e.g., 2 for a decrement line and a check line).

        Returns:
            tuple: (time_per_loop_iteration_ns, load_instruction_time_ns)
                   - `time_per_loop_iteration_ns`: Time allocated to each of
                                                   the `looplines` within one ivar
                                                   decrement cycle.
                   - `load_instruction_time_ns`: Time allocated to the initial
                                                 'load ivar' instruction.
        """
        base_timestep = self.timestep  # Minimum hardware timestep
        load_instr_time = base_timestep  # Start with minimum time for load instruction

        # Increment time for the load instruction until the remaining time is perfectly
        # divisible by (ivar_value * base_timestep * looplines)
        # This ensures that (time - load_instr_time) / ivar_value can be split evenly
        # across 'looplines', each taking 'time_per_loop_iteration_ns'.
        while (time - load_instr_time) / ivar_value / base_timestep % looplines != 0:
            load_instr_time += base_timestep
            if (
                load_instr_time > time
            ):  # Safety break, should not happen with valid inputs
                raise ValueError(
                    "Time balancing failed: load_instr_time exceeded total time."
                )

        # Time remaining after the load instruction, per single ivar count
        time_per_ivar_count_after_load = (time - load_instr_time) / ivar_value
        # Time for each line within the actual looping part (e.g. for dec, for check)
        time_per_loop_line = int(time_per_ivar_count_after_load // looplines)

        return time_per_loop_line, load_instr_time

    def process_trigger_logic(self, trigger_block, end_block_unused, condition_str):
        """
        Generates 'writew' lines for a TriggerBlock.

        Args:
            trigger_block (TriggerBlock): The trigger block to process.
            end_block_unused: Not directly used, only a check, as trigger defines
                              its own success/failure targets.
            condition_str (str): The condition string from the main logic
                                 (e.g. "|success|") that exits the trigger block. It
                                 determines which path (success/failure) and checks with
                                 The trigger block itself which has its own .success
                                 and .failure attributes.
        """
        ivar_needed_for_timespan = False
        ivar_chan_for_timespan = None

        assert (
            trigger_block.count == self.evars[trigger_block.external_input - 1]
        ), "Count in trigger block doesn't match evars in control block"

        # Determine actual success and failure target blocks based on the incoming
        # condition_str,
        if condition_str[1:-1] == "success":
            success_target_id = end_block_unused.block_id
            failure_target_id = trigger_block.failure
        elif condition_str[1:-1] == "failure":
            failure_target_id = end_block_unused.block_id
            success_target_id = trigger_block.success

        trigger_block.check_consistent(
            success=success_target_id, failure=failure_target_id
        )

        # Handle 'loop_check' as a special target for success/failure,
        # meaning jump to loop's check mechanism
        if success_target_id == "loop_check":
            # The 'end_block' passed might be the loop that contains this trigger.
            # For now, if end_block_unused is the loop and has loop_check_row:
            if hasattr(
                end_block_unused, "loop_check_row"
            ):  # end_block_unused might be the loop object.
                success_target_row = end_block_unused.loop_check_row
            else:  # Fallback or error: loop_check target needs a defined row
                raise ValueError(
                    f"Trigger '{trigger_block.block_id}' success target "
                    + "'loop_check' but no loop_check_row found."
                )
        else:
            success_target_row = self.blocks[success_target_id].first_row

        if failure_target_id == "loop_check":
            if hasattr(end_block_unused, "loop_check_row"):
                failure_target_row = end_block_unused.loop_check_row
            else:
                raise ValueError(
                    f"Trigger '{trigger_block.block_id}' failure target "
                    + "'loop_check' but no loop_check_row found."
                )
        else:
            failure_target_row = self.blocks[failure_target_id].first_row

        # Determine if an ivar is needed for the trigger's time_span (if count-based)
        if (
            trigger_block.count_defined
            and trigger_block.time_span / self.maxtimestep > 1
        ):
            ivar_needed_for_timespan = True
            # find_good_ivar tries to find an ivar for the time_span with minimal rows.
            ivar_chan_for_timespan, _ = self.find_good_ivar(
                trigger_block.time_span, max_lines_for_loop=2
            )  # Max_lines for dec+check

        self.new_dpatt_str += (
            f"\n# Trigger Block: {trigger_block.block_id} "
            + f"({trigger_block.trigger_name})\n"
        )

        self.trigger_write(
            time_span=trigger_block.time_span
            if trigger_block.count_defined
            else self.timestep,  # Default to min time if rate-based
            ivar_needed=ivar_needed_for_timespan,
            ivar_chan=ivar_chan_for_timespan,
            evar_chan=trigger_block.external_input
            - 1,  # Convert 1-4 to 0-3 for hardware
            dig_chan={
                "chan": trigger_block.chan,
                "dac": trigger_block.dac,
            },  # trigger_block.dac is a list of dicts
            failure_row=failure_target_row,
            success_row=success_target_row,
            num_rows=trigger_block.num_rows,  # For debug/consistency,
            # actual lines written by trigger_write
        )
        trigger_block.written = True

    def trigger_write(
        self,
        time_span,
        ivar_needed,
        ivar_chan,
        evar_chan,
        dig_chan,
        failure_row,
        success_row,
        num_rows,
    ):
        """
        Writes the sequence of 'writew' lines for a trigger's operation.
        This is a low-level helper that constructs the hardware commands.

        Args:
            time_span (int): Duration for count-based trigger, or base timestep.
            ivar_needed (bool): If an ivar is used for the time_span.
            ivar_chan (int): Index of ivar used for time_span (0-3), if any.
            evar_chan (int): Index of external variable to check (0-3).
            dig_chan (dict): Digital channels and DAC settings.
            failure_row (int): Pattern row to jump to if evar is non-zero (trigger fail)
            success_row (int): Pattern row to jump to if evar is zero (trigger success).
            num_rows (int): Expected number of rows (mostly for consistency check).
        """

        # --- Command setup ---
        # evar load: (1<<12) | (1 << evar_idx)
        # ivar load: (1<<12) | ((1 << ivar_idx) << 4)
        # ivar dec : (1<<12) | ((1 << ivar_idx) << 8)
        # ivar check nonzero: ((12 + ivar_idx) << 12) + target_addr
        # evar check nonzero: ((8 + evar_idx) << 12) + target_addr (failure)

        special_load_evar_only = (1 << 12) | (1 << evar_chan)
        time_span_loop_line = 0  # Time for each line within ivar loop for timespan

        if ivar_needed:
            # Load both evar and ivar for timespan
            special_load_cmd = special_load_evar_only | ((1 << ivar_chan) << 4)
            special_dec_ivar_cmd = (1 << 12) | ((1 << ivar_chan) << 8)
            special_check_ivar_cmd = (12 + ivar_chan) << 12
            # Distribute time_span over ivar loops
            # (assuming 2 lines: dec, check per loop)
            time_span_loop_line = time_span // (
                self.ivars[ivar_chan] * 2
            )  # Approximate
            if time_span_loop_line == 0:
                time_span_loop_line = self.timestep  # Ensure minimum
        else:
            special_load_cmd = special_load_evar_only
            # No ivar specific commands needed beyond load if not ivar_needed

        special_check_evar_nonzero_cmd = (8 + evar_chan) << 12

        # --- Generate writew lines ---
        # 1. Load evar (and ivar for time_span if needed)
        self.new_dpatt_str += self.writew_line(
            channels=dig_chan,
            time=self.timestep,
            address={
                "address": None,
                "special": special_load_cmd,
                "cond": None,
            },
            comment="#Load evar (and ivar if used for time)",
        )

        # 2. Time elapsing part (using ivar loop or fixed lines)
        if ivar_needed:
            ivar_loop_decrement_target_row = self.pattern_row
            # 2a. Decrement ivar for time_span
            self.new_dpatt_str += self.writew_line(
                channels=dig_chan,
                time=time_span_loop_line,
                address={
                    "address": None,
                    "special": special_dec_ivar_cmd,
                    "cond": None,
                },
                comment="#Decrement ivar for time_span",
            )
            # 2b. Check ivar for time_span, loop back to decrement
            self.new_dpatt_str += self.writew_line(
                channels=dig_chan,
                time=time_span_loop_line,
                address={
                    "address": ivar_loop_decrement_target_row,
                    "special": special_check_ivar_cmd,
                    "cond": None,
                },
                comment="#Check ivar for time_span, loop if non-zero",
            )

        else:  # Fixed time delay
            # (num_rows = 5, 1 for load, 2 for this delay, 2 for evar check)
            # This needs to ensure the total time_span is met.
            # If num_rows is fixed at 5, 2 lines are for this delay.
            remaining_time_for_delay = (
                time_span - self.timestep
            )  # Subtract time for load line
            delay_line1_time = remaining_time_for_delay // 2
            delay_line2_time = remaining_time_for_delay - delay_line1_time
            if delay_line1_time < self.timestep:
                delay_line1_time = self.timestep  # ensure min
            if delay_line2_time < self.timestep:
                delay_line2_time = self.timestep  # ensure min

            self.new_dpatt_str += self.writew_line(
                channels=dig_chan,
                time=delay_line1_time,
                address={
                    "address": None,
                    "special": None,
                    "cond": None,
                },
                comment="#Time delay part 1",
            )
            self.new_dpatt_str += self.writew_line(
                channels=dig_chan,
                time=delay_line2_time,
                address={
                    "address": None,
                    "special": None,
                    "cond": None,
                },
                comment="#Time delay part 2",
            )

        # 3. Check evar: if non-zero (failure condition for trigger), go to failure_row
        self.new_dpatt_str += self.writew_line(
            channels=dig_chan,
            time=self.timestep,
            address={
                "address": failure_row,
                "special": special_check_evar_nonzero_cmd,
                "cond": None,
            },
            comment=f"#Check evar {evar_chan}. If non-zero (fail), goto {failure_row}",
        )

        # 4. If evar is zero (success condition for trigger),
        #    fall through to go to success_row
        self.new_dpatt_str += self.writew_line(
            channels=dig_chan,
            time=self.timestep,
            address={
                "address": success_row,
                "special": None,
                "cond": None,
            },  # Simple goto
            comment=f"#Evar {evar_chan} is zero (success). Goto {success_row}",
        )

    def time_write(self, time_ns):
        """
        Converts a time in nanoseconds to the hardware value (number of timesteps - 1).

        Args:
            time_ns (int): Time in nanoseconds.

        Returns:
            str: Formatted string for the time word in a 'writew' line.
        """
        # Hardware time word is (number of clock cycles - 1)
        # Number of clock cycles = time_ns / self.timestep (duration of one clock cycle)
        num_timesteps = time_ns // self.timestep
        hardware_time_value = num_timesteps - 1
        if hardware_time_value < 0:
            hardware_time_value = 0  # Cannot be negative
        return self.w16(num=hardware_time_value, hex=False)  # Time is usually decimal

    def address_write(self, address=None, special=None, cond=None):
        """
        Formats the address/special command word for a 'writew' line.

        Args:
            address (int, optional): Target row address for jumps.
                                     If None, implies next row.
            special (int, optional): Special command code (e.g., for ivar/evar ops).
            cond (any, optional): Conditional jump parameter (currently not implemented)

        Returns:
            str: Formatted string for the address word.

        Raises:
            NotImplementedError: If `cond` is used.
        """
        if cond is not None:
            raise NotImplementedError(
                "Conditional jumps ('cond' parameter) not implemented yet."
            )

        if special is None:  # Simple jump or fall-through
            if address is None:  # Fall-through to next pattern row
                return self.w16(self.pattern_row + 1, last=True)
            else:  # Simple jump to specified address
                return self.w16(address, last=True)
        # Special command (bit 12 is often an indicator for special ops)
        elif (special >> 12) == 1:  # Purely special command (e.g. load, dec)
            # Address field might be implicitly next row or not used by hardware.
            # This path is for special ops that DON'T branch (load, dec).
            return self.w16(
                special, last=True
            )  # The address part of this w16 might be effectively 0 or next_row.
        else:  # Special command combined with an address (e.g., check and branch)
            # This assumes 'special' contains the command bits
            # and 'address' is the target. Hardware expects these combined.
            # Example: ((8 + evar_idx) << 12) + target_addr
            return self.w16(
                special | address, last=True
            )  # Combine special op bits with address bits.

    def row_num_write(self, comment=None):
        """
        Generates a comment string indicating the current pattern row
        number and increments it.

        Args:
            comment (str, optional): Additional comment to append.

        Returns:
            str: Formatted comment string (e.g., "\t# row 5 # My comment").
        """
        if self.pattern_row == 512:
            warnings.warn("Warning, current_row_count exceed 512")
        row_str = f"\t# row {self.pattern_row}"
        if comment:  # Append provided comment if any
            # Ensure comment doesn't already start with #
            clean_comment = comment.lstrip("#").strip()
            if clean_comment:
                row_str += f" # {clean_comment}"
        self.pattern_row += 1
        return row_str

    def find_good_ivar(self, span_ns, max_lines_for_loop):
        """
        Finds an available internal variable (ivar) that can cover the given time
        `span_ns` using at most `max_lines_for_loop` for its decrement/check cycle.

        Args:
            span_ns (int): The total time duration in nanoseconds to cover.
            max_lines_for_loop (int): Maximum number of pattern lines acceptable
                                      for the ivar's decrement and check operations
                                      per full count.

        Returns:
            tuple: (ivar_index, achieved_min_rows)
                   - `ivar_index` (int): Index of the best ivar found (0-3).
                   - `achieved_min_rows` (float): Number of maxtimestep-based rows
                                                  this ivar would take.
        """
        min_achieved_rows = 512
        best_ivar_idx = 0  # Default to ivar 0

        # self.ivars contains pre-set initial values for ivars from control block
        for i, ivar_initial_value in enumerate(self.ivars):
            if ivar_initial_value == 0:
                continue  # Ivar with 0 count is useless

            effective_rows_per_ivar_decrement = (
                span_ns / self.maxtimestep / (ivar_initial_value + 1)
            )

            if effective_rows_per_ivar_decrement < min_achieved_rows:
                min_achieved_rows = effective_rows_per_ivar_decrement
                best_ivar_idx = i
            if (
                effective_rows_per_ivar_decrement < max_lines_for_loop
            ):  # Found one good enough
                break  # Stop searching

        if min_achieved_rows >= max_lines_for_loop:
            warnings.warn(
                f"No ivar found to cover span {span_ns}ns in < {max_lines_for_loop} "
                + "maxtimestep-based rows per ivar cycle. "
                + f"Using ivar {best_ivar_idx} which takes approx "
                + f"{min_achieved_rows:.2f} such rows."
            )
        return best_ivar_idx, min_achieved_rows

    def dig_chan_write(self, chan_list):
        """
        Converts a list of active digital channel numbers into hardware words.

        Args:
            chan_list (list): List of integer channel numbers to be active.

        Returns:
            str: Formatted string of 16-bit words for digital channels.
                 (2 words for 64-bit, 4 words for 128-bit pattern generator).
        """
        # Helper to sum bits for a range of channels
        def sum_chan_bits(channels, first_idx, last_idx):
            val = 0
            for ch_num in channels:
                if first_idx <= ch_num <= last_idx:
                    val |= 1 << (
                        ch_num - first_idx
                    )  # Bit position relative to start of word
            return val

        # Word 0: Channels 0-15
        out0 = sum_chan_bits(chan_list, 0, 15)
        # Word 1: Channels 16-31
        out1 = sum_chan_bits(chan_list, 16, 31)

        if self.patgen_128bit:
            # Word 2: Channels 32-47
            out2 = sum_chan_bits(chan_list, 32, 47)
            # Word 3: Channels 48-63
            out3 = sum_chan_bits(chan_list, 48, 63)
            return self.w16(out0) + self.w16(out1) + self.w16(out2) + self.w16(out3)
        else:  # 64-bit version
            return self.w16(out0) + self.w16(out1)

    def split_chan_dig_dac(self, channels_dict):
        """
        Splits a channels dictionary into digital channel list and
        DAC settings dictionary.

        Args:
            channels_dict (dict): A dictionary like {'chan': [0,1], 'dac': {0:100}}.

        Returns:
            tuple: (digital_channels_list, dac_settings_dict)
        """
        return channels_dict.get("chan", []), channels_dict.get("dac", {})

    def dac_config_allow(self, dac_chan_updates):
        """
        Checks if the requested DAC channel updates are allowed by the current
        global DAC configuration (`self.dacconfig`).

        Args:
            dac_chan_updates (dict): DAC channel-value pairs to be written.

        Returns:
            bool: True if allowed, False otherwise
                  (raises AssertionError if not allowed).

        Raises:
            AssertionError: If a DAC write is attempted that violates `self.dacconfig`.
        """
        if not dac_chan_updates:  # No DAC updates requested, always allowed.
            return True

        # dacconfig: 0=static, 1=single (DAC0), 2=half (DAC0-3), 3=full (DAC0-7)
        config_mode = self.dacconfig

        allowed = True
        for dac_idx in dac_chan_updates.keys():
            if config_mode == 0:  # Static: no dynamic updates allowed
                allowed = False
                assert allowed, "DAC write attempted but dacconfig is 'static'."
                break
            elif config_mode == 1:  # Single: only DAC 0 allowed
                if dac_idx != 0:
                    allowed = False
                    assert allowed, (
                        f"DAC write to {dac_idx} attempted but dacconfig is 'single'"
                        + " (only DAC 0 allowed)."
                    )
                    break
            elif config_mode == 2:  # Half: DAC 0-3 allowed
                if not (0 <= dac_idx <= 3):
                    allowed = False
                    assert allowed, (
                        f"DAC write to {dac_idx} attempted but dacconfig is 'half' "
                        + "(only DAC 0-3 allowed)."
                    )
                    break
            elif config_mode == 3:  # Full: DAC 0-7 allowed
                if not (0 <= dac_idx <= 7):
                    allowed = False
                    # This case should ideally not happen if DAC indices are always 0-7.
                    assert allowed, (
                        f"DAC write to {dac_idx} attempted; dacconfig is 'full' "
                        + "but index is out of 0-7 range."
                    )
                    break
            # If config_mode is unknown, it's an issue.
        return allowed

    def dac_chan_write(self, dac_chan_updates):
        """
        Converts DAC channel updates into hardware words (value and mask).
        Only applicable for 128-bit pattern generator version.

        Args:
            dac_chan_updates (dict): DAC channel (int) to value (int) pairs.
                                     All channels updated in one step must have
                                     the same value.

        Returns:
            str: Formatted string of two 16-bit words (DAC value, DAC mask).

        Raises:
            AssertionError: If not 128-bit version, if updates violate
                            `dac_config_allow`, or if multiple DACs are set to
                            different values in one step.
        """
        assert (
            self.patgen_128bit
        ), "DAC operations only available in 128-bit pattern generator version."
        if not dac_chan_updates:  # No DAC updates
            return self.w16(0) + self.w16(0)  # DAC Value = 0, DAC Mask = 0

        assert self.dac_config_allow(
            dac_chan_updates
        ), "DAC update conflicts with global DAC configuration."

        # All DACs updated in a single pattern line must share the same value.
        first_dac_value = next(iter(dac_chan_updates.values()))
        assert all(value == first_dac_value for value in dac_chan_updates.values()), (
            "In a single pattern step, all updated DAC channels "
            + "must be set to the same value."
        )

        dac_value_word = first_dac_value
        dac_mask_word = 0
        for dac_idx in dac_chan_updates.keys():
            assert (
                0 <= dac_idx <= 7
            ), f"Invalid DAC channel index: {dac_idx}. Must be 0-7."
            dac_mask_word |= 1 << dac_idx

        return self.w16(dac_value_word) + self.w16(dac_mask_word)

    def writew_line(self, channels, time, address, comment=None):
        """
        Constructs a complete 'writew' line string for the pattern file.

        Args:
            channels (dict): Dictionary with 'chan' (list of digital channels)
                             and 'dac' (dict of DAC updates).
            time (int): Time duration for this line in nanoseconds.
            address (dict or int): Address/special command.
                                   If dict:
                                   {'address': val, 'special': val, 'cond': val}.
                                   If int: direct address value.
            comment (str, optional): Comment for this line.

        Returns:
            str: The fully formatted 'writew' line string, including row number comment.
        """
        dig_chans, dac_updates = self.split_chan_dig_dac(channels)

        dig_chan_str = self.dig_chan_write(dig_chans)
        time_str = self.time_write(time)  # Converts ns to hardware time value

        if isinstance(address, dict):
            address_str = self.address_write(**address)
        else:  # Assuming it's a direct address integer or None
            address_str = self.address_write(address=address)

        row_num_comment_str = self.row_num_write(comment=comment)

        dac_chan_str = ""
        if self.patgen_128bit:
            dac_chan_str = self.dac_chan_write(dac_updates)

        return (
            f"writew {dig_chan_str}{dac_chan_str}"
            + f"{time_str}{address_str}{row_num_comment_str}\n"
        )

    def process_config(self):
        """
        Processes the 'control' block to set up global translator parameters
        like timestep, variable values, and hardware configuration bits.
        """
        control_block = self.blocks.get("control")
        if not control_block:
            raise ValueError("A 'control' block is required but not found.")

        self.timestep = control_block.timestep  # Base hardware timestep in ns
        self.maxtimestep = (
            self.timestep * 65536
        )  # Max duration of a single pattern line
        self.ivars = control_block.ivars  # Initial values for internal variables
        self.evars = control_block.evars  # Initial values for external variables

        self.config_bits = 0  # Reset global config bits

        if control_block.patgen_128bit:
            self.patgen_128bit = True
            self.dacconfig = control_block.dacconfig  # DAC mode (0-3)
            self.config_bits |= self.dacconfig << 11  # Bits 12:11 for DAC config
            self.config_bits |= (
                control_block.auxline_pol << 10
            )  # Bit 10 for AuxOut polarity
            # Parameter register for 128-bit:
            # startAddr, intThreshold, evars[4], ivars[4], dacs[8]
            self.param_register = [
                control_block.start_address,
                control_block.inthreshold,
                *control_block.evars,
                *control_block.ivars,
                *control_block.dacs,
            ]
        else:
            self.patgen_128bit = False
            # Parameter register for 64-bit: startAddr, evars[4], ivars[4]
            # (inthreshold and dacs are not applicable or handled differently)
            self.param_register = [
                control_block.start_address,
                *control_block.evars,
                *control_block.ivars,
            ]

        self.config_bits |= control_block.clock_select << 6  # Bits 7:6 for Clock Select
        self.config_bits |= control_block.auxconfig << 4  # Bits 5:4 for AuxOut Config
        self.config_bits |= control_block.level << 1  # Bit 1 for Input Level (NIM/TTL)

    def write_config(self, other_hardware_config_flags=0):
        """
        Writes the 'config' line to the .dpatt string.

        Combines configuration derived from the 'control' block with other
        hardware-specific flags.

        Args:
            other_hardware_config_flags (int): Additional hardware config bits
                                               (e.g., for table hooks, RAM target).
        """
        # Bit definitions for other_hardware_config_flags (example values):
        # PARAMETERWRITE = 8 (Bit 3: target RAM for writew is Params, else Pattern)
        # ADDRESSRESET = 4   (Bit 2: reset address on jumps)
        # TABLERESET = 1     (Bit 0: reset table pointer)
        # Bits 9:8 for table hooks are not set here, assumed 0 or part of other_flags.

        final_config_bits = self.config_bits | other_hardware_config_flags
        self.dpatt_str += "config " + self.w16(final_config_bits, last=True) + "\n"

    def write_param(self):
        """
        Writes the initial parameter values to the .dpatt string using 'writew'.
        These are loaded into the hardware's parameter RAM.
        """
        self.dpatt_str += "writew "  # Start of the parameter write line
        num_params = len(self.param_register)
        for i, val in enumerate(self.param_register):
            is_last_param = i == num_params - 1
            # Parameters are typically written in decimal for easy reading,
            # regardless of global 'hex' mode.
            self.dpatt_str += self.w16(val, last=is_last_param, hex=False)
        self.dpatt_str += "\n"  # End the writew line for parameters

    def w16(self, num, last=False, hex=None):
        """
        Formats a number as a 16-bit word string, optionally in hexadecimal.

        Args:
            num (int): The number to format (must be 0 <= num < 65536).
            last (bool): If True, append ';' as terminator, else ','.
            hex (bool, optional): If True, format as hex. Defaults to `self.hex`.

        Returns:
            str: The formatted 16-bit word string.

        Raises:
            AssertionError: If `num` is out of 16-bit range.
        """
        if hex is None:
            hex = self.hex  # Use instance's default hex mode if not specified
        assert 0 <= num < 65536, f"Number {num} out of 16-bit range [0, 65535]."

        terminator = ";" if last else ","
        if hex:
            return f"{num:#06x}{terminator}"  # Format as 0x####
        else:
            return f"{num}{terminator}"


# Example usage
if __name__ == "__main__":
    parser = configargparse.ArgumentParser(
        description="Loading of new Pattern Generator"
    )
    parser.add_argument(
        "--infile",
        "-i",
        default="../../examples/DPG/example1.txt",
        help="Input file in correct syntax",
    )
    parser.add_argument(
        "--outfile",
        "-o",
        default="../../examples/DPG/example1.dpatt",
        help="Output file for DPG",
    )
    parser.add_argument(
        "--hex",
        "-H",
        action="count",
        default=0,
        help="Write 16 bit words in hexadecimal, except for time word",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Set verbosity of comments in output pattern file",
    )
    args = parser.parse_args()
    filename = args.infile
    fileout = args.outfile
    verbose = args.verbose
    hex_mode = True if args.hex > 0 else False
    p = MermaidParser(filename)
    p.parse()
    out = Translator(
        p.get_blocks(), p.get_logic(), filename, fileout, hex_mode, verbose
    )
