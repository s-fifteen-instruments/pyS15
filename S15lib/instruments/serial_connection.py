"""
General serial device class.

Encloses some of the common read write actions into convenient methods.

"""
import serial
import time
import sys
import glob

# from serial import SerialException


def search_for_serial_devices(device: str):
    '''Searches for serial devices defined in the input paremater device.
    If the device identification string containes the string given in the input paramter 'device', the device path is 
    appended to a list. This list is then returned as search result.
    '''
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port, timeout=1)
            s.write(b'*idn?\r\n')
            id_str = s.readline()
            s.close()
            if device in id_str:
                result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


class SerialConnection(serial.Serial):
    """
    The USB device is seen as an object through this class,
    inherited from the generic serial one.
    """

    def __init__(self, device_path: str = None):
        """
        Initializes the USB device.
        It requires the full path to the serial device as arguments
        """
        try:
            super(SerialConnection, self).__init__(device_path, timeout=1)
            self.write(b'\r\n')
            self.readlines()
        except serial.SerialException:
            print('Connection failed')
        self._reset_buffers()
        self._cleanup()

    def _reset_buffers(self):
        """ Resets input and output buffers"""
        self.reset_input_buffer()
        self.reset_output_buffer()

    def _cleanup(self, timeout: float = 1):
        """ cleanup of read buffer of the device.

        :param timeout: optional timeout, defaults to 1
        :type timeout: float, optional
        """
        t_start = time.time()
        while True:
            if self.in_waiting + self.out_waiting == 0:
                break
            if time.time() > t_start + timeout:
                break
            self.read_all()

    def getresponses(self, cmd: str):
        """
        Send commands and read the response of the device.

        The timeout is the general device timeout.

        :param cmd: command to send. No newline is necessary.
        :type cmd: string
        :param timeout: timeout in seconds, defaults to 2
        :type timeout: float, optional
        :return: the reply of the device
            only the first line and stripped of decorations
        :rtype: {string}
        """
        self._cleanup()
        self._reset_buffers()
        self.write((cmd + '\r\n').encode())
        time.sleep(0.01)
        return [k.decode().strip() for k in self.readlines()]

    def getresponse(self, cmd: str, timeout: float = 1):
        """
        Send commands and reads a single line as response from the device.

        Timeout is defined independently from the general timeout device.
        This is useful for measurement with integration time longer than
        communication timeout

        :param cmd: command to send. No newline is necessary.
        :type cmd: string
        :param timeout: timeout in seconds, defaults to .5
        :type timeout: float, optional
        :return: the reply of the device
            only the first line and stripped of decorations
        :rtype: {string}
        """
        self._cleanup()
        self.timeout = timeout
        self.write((cmd + '\r\n').encode())
        t_start = time.time()
        while True:
            if self.inWaiting() > 0:
                break
            if time.time() > (t_start + timeout):
                print(time.time() - t_start)
                raise serial.SerialTimeoutException('Command timeout')
        return self.readline()

    def writeline(self, cmd: str):
        """
        Sends command to device.

        Provided as a wrapper to 'Serial.write', which accepts
        a string command 'cmd' without newline termination.

        :param cmd: command to send
        :type cmd: string
        """
        self.write("{};".format(cmd).encode())

    def readline(self) -> str:
        """
        Reads a single line as response from device.

        Provided as a wrapper to 'Serial.readline' to automatically
        decode binary response as a simple string. Stripping is performed since
        devices are designed to terminate with '\r\n'.
        """
        return super().readline().decode().strip()

    def help(self):
        """
        Prints device help text
        """
        [print(k) for k in self.getresponses('help')]


if __name__ == '__main__':
    print(search_for_serial_devices('optical power meter'))
