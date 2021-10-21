"""General serial device class for S-Fifteen instruments.

Extends the Serial class to allow string-based IO methods, as well as add
other methods for common S-Fifteen instruments device responses.
"""

import glob
import sys
import time
from typing import List, Optional

import serial


def search_for_serial_devices(device: str) -> List[str]:
    """Returns a list of device paths with corresponding device name.

    If the device identification string contains the string given in the input
    paramter 'device', the device path is appended to the return list.
    Used as a backup method for device lookup in the event user does not
    know exact device path - list of device paths allows it to be used as part
    of a dropdown selection.

    Args:
        device: Name of target device.
    Returns:
        List of device paths for which 'device' partially matches the returned
        identifier from a device identification request.
    Raises:
        EnvironmentError: Unsupported OS.
    """
    if sys.platform.startswith("win"):
        ports = [f"COM{i}" for i in range(1, 257)]
    elif sys.platform.startswith("linux") or sys.platform.startswith("cygwin"):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob("/dev/tty[A-Za-z]*")
    elif sys.platform.startswith("darwin"):
        ports = glob.glob("/dev/tty.*")
    else:
        raise EnvironmentError("Unsupported platform")

    result = []
    for port in ports:
        try:
            s = SerialConnection(port)
            try:
                id_str = s.getresponse("*IDN?")
            finally:
                s.close()  # guarantee port is closed
            if device in id_str:
                result.append(port)
        except serial.SerialException:
            pass
    return result


class SerialConnection(serial.Serial):
    """
    The USB device is seen as an object through this class,
    inherited from the generic serial one.

    Note:
        Inheritance used because SerialConnection extends Serial with custom
        functionality, while avoiding manually exposing methods.
    """

    BUFFER_WAITTIME: float = 0.01  # duration to allow buffer to populate, in seconds

    def __init__(self, device_path: str, timeout: float = 0.1):
        """Initializes the connection to the USB device.

        Args:
            device_path: The full path to the serial_device.
            timeout: Device timeout.
        Raises:
            serial.SerialException:
                Port does not exist, no access permissions or attempted
                read/write on unopened port.
        """
        super().__init__(device_path, timeout=timeout)
        self.cleanup()

    def cleanup(self):
        """Cleans up the device to prepare for IO.

        Resets the input and output buffers if data is present, and repeatedly
        checks until buffers are empty or read timeout of device is reached
        (0.1 seconds if not specified).

        Raises:
            serial.SerialException: Attempted to access a closed port.
        """
        timeout = 0.1 if self.timeout is None else self.timeout
        end_time = time.time() + timeout
        while True:
            time.sleep(SerialConnection.BUFFER_WAITTIME)
            if not (self.in_waiting or self.out_waiting):
                break
            self.reset_input_buffer()
            self.reset_output_buffer()
            if time.time() > end_time:
                break

    @classmethod
    def connect_by_name(cls, device: str):
        """Searches for and returns a connection to the specified device.

        Args:
            device: Name of target device.
        Returns:
            SerialConnection with port opened.
        Raises:
            serial.SerialException: Number of matching ports not exactly one.
        """
        ports: List = search_for_serial_devices(device)
        if not ports:
            raise serial.SerialException(f"No available '{device}' devices connected.")
        if len(ports) > 1:
            raise serial.SerialException(
                f"More than one '{device}' device available. "
                + "Please specify the full device path."
            )
        return SerialConnection(ports[0])

    def getresponses(self, cmd: str, timeout: Optional[float] = None) -> List[str]:
        """Sends command and reads the device response.

        Commands do not need to be terminated by a newline, unless commands
        are chained together.

        Timeout can be defined independently from the general timeout device.
        This is useful for measurements with integration time longer than
        communication timeout. The timeout for the response uses the following
        values in order of precedence:
            1. timeout, if specified
            2. SerialConnection.timeout, if not None
            3. 0.1 seconds

        Args:
            cmd: Command to send. No newline is necessary.
            timeout: Optional timeout override in seconds. Defaults to None.
        Returns:
            Multi-line reply of the device, stripped of leading/trailing whitespace.
        Raises:
            serial.SerialException: Attempted to access a closed port.
        Note:
            This behaviour seems to identical to a combination of `cleanup()`,
            `writeline(cmd)` and `readlines()`, with the exception of the
            additional read timeout override. To consider refactoring to
            `readlines()` + read timeout adjustment instead.
        """
        self.cleanup()
        self.writeline(cmd)

        # Wait until characters are available, or until timeout reached
        if timeout is None:
            timeout = 0.1 if self.timeout is None else self.timeout
        end_time = time.time() + timeout
        while not self.in_waiting:
            if time.time() > end_time:
                break

        # Used instead of Serial.readlines() to allow consecutive blank lines as well
        # Flush all the incoming buffer repeatedly
        replies = bytearray()
        while True:
            if not self.in_waiting:
                break
            replies.extend(self.read(self.in_waiting))
            if time.time() > end_time:
                break
            time.sleep(SerialConnection.BUFFER_WAITTIME)

        return [line.strip("\r\n") for line in replies.decode().split("\n")]

    def getresponse(self, cmd: str, timeout: Optional[float] = None) -> str:
        """Sends command and reads a single-line device response.

        Commands do not need to be terminated by a newline, unless commands
        are chained together.

        Timeout can be defined independently from the general timeout device.
        This is useful for measurements with integration time longer than
        communication timeout. The timeout for the response uses the following
        values in order of precedence:
            1. timeout, if specified
            2. SerialConnection.timeout, if not None
            3. 0.1 seconds

        Args:
            cmd: Command to send. No newline is necessary.
            timeout: Optional timeout override in seconds. Defaults to None.
        Returns:
            Single line reply of the device, stripped of leading/trailing whitespace.
        Raises:
            serial.SerialException: Attempted to access a closed port.
        """
        self.cleanup()
        self.writeline(cmd)

        # Wait until characters are available, or until timeout reached
        if timeout is None:
            timeout = 0.1 if self.timeout is None else self.timeout
        end_time = time.time() + timeout
        while not self.in_waiting:
            if time.time() > end_time:
                break

        # Flush all the incoming buffer repeatedly
        reply = bytearray()
        while True:
            reply.extend(self.read_until(b"\n", self.in_waiting))
            if reply and reply[-1] == 10:  # b'\n' === int(10)
                break
            if time.time() > end_time:
                break
            time.sleep(SerialConnection.BUFFER_WAITTIME)

        return reply.decode().strip("\r\n")

    def writeline(self, cmd: str) -> None:
        """Sends command to device.

        Commands do not need to be terminated by a newline, unless commands
        are chained together.

        Args:
            cmd: Command to send. No newline is necessary.
        Raises:
            serial.SerialException: Attempted to access a closed port.
        """
        self.write("{};".format(cmd).encode())

    def print_help(self) -> None:
        """Prints out help information stored on device.

        Raises:
            serial.SerialException: Attempted to access a closed port.
        """
        for line in self.getresponses("HELP"):
            print(line)

    def get_identity(self) -> str:
        """Returns identity of device.

        Raises:
            serial.SerialException: Attempted to access a closed port.
        """
        return self.getresponse("*IDN?")
