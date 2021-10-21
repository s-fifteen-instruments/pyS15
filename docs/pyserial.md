# Working with pySerial

## Documentation

The documentation for the latest `pySerial` is hosted on [ReadTheDocs](https://pyserial.readthedocs.io/en/latest/index.html) (v:latest),
not [PythonHosted](https://pythonhosted.org/pyserial/index.html) (v3.0).
When in doubt, refer back to the main [GitHub](https://github.com/pyserial/pyserial) project repository for the backend code.

This tidbit is current as at 2021-10-21, with v:latest corresponding to v:3.5.

## Project usage

The backbone of the project relies on the `pySerial` library for cross-platform programmatic access to serial connections in order to communicate with S-Fifteen devices.
This library is primarily used in the [`SerialConnection`](/S15lib/instruments/serial_connection.py) class.

### Summary of serial.Serial

The `Serial` class of pySerial has many different methods that potentially overlap in functionality (e.g. `read_all` vs `reset_input_buffer`), or are already deprecated (e.g. `reset_input_buffer` vs `flushInput`).
To clear the noise, we list a quick summary of `serial.Serial`:

#### Read methods

```
read(size=1) -> bytes
    length specified by size

read_until(expected='\n', size=None) -> bytes
    terminated read once 'expected' character is encountered, or size read

readline(size=-1) -> bytes
    - returns up to and including termination '\r\n'
    - maintained for compatibility with io library

readlines(hint=-1)
    returns array of bytes like readline(), reads up until timeout

reset_input_buffer()
    - clears input buffer
    - supersedes the deprecated `flushInput()`

*read_all() -> bytes
    - undocumented functionality, but exposed as public method
    - recommended to use `Serial.read(Serial.in_waiting)` instead, which is also
      verified to be the implementation within the codebase
```

#### Read attributes

```
in_waiting (int)
    - number of bytes in input buffer
    - supersedes the deprecated `inWaiting()`

timeout (float)
    sets read timeout in seconds
```

#### Writing

```
write(data: bytes)
    interesting behaviour
    - hard limit of 255 bytes, then somehow buffer seems to be completely flushed
      instead of a circular array
    - almost always blocking, likely due to speed of writing than actually blocking
    - commands are processed in bursts upon writes,
      e.g. write("PTEMP?;HTEMP?;") results in a single line with both outputs
           concatenated. Undocumented behaviour when calling with "*IDN?" though...

writelines(lines: List[bytes])
    similar to 'write'; calls 'write' for every byte string in list

flush()
    blocks until all data written - does nothing in practice, see 'out_waiting'

reset_output_buffer()
    - clears output buffer, and abords current output - does nothing in practice
    - supersedes the deprecated `flushOutput()``
```

#### Write attributes

```
out_waiting: int
    - number of bytes in output buffer
    - in practice have never seen it spit out 0 after writing, likely
      due to high baudrates
    - supersedes the deprecated `outWaiting()`

write_timeout: float = None
    - sets write timeout in seconds
    - supersedes the deprecated `writeTimeout`
```

### Working with serial

#### Baudrate specification

S-Fifteen instruments typically can be operated over a number of different baudrates,
the default being 9600.

#### Reading immediately after writing

Upon attempting to read the input buffer immediately after a write, this
induces a race condition between (1) how fast the query is executed, and
(2) how fast the device processes the input and writes to its output buffer.

A quick test to demonstrate:

```python
d = serial.Serial("COM7") # specify the port
d.write("*IDN?;".encode())
num_fail_to_read = 0
while not d.read_all():
    num_fail_to_read += 1
print(num_fail_to_read)  # roughly 20 to 45
```

In practice, a timeout is performed to await incoming bytes. This is
already done natively in `Serial.readline()` (uses a software-based read timeout,
i.e. `Serial.timeout`), but this is not protected from non-blocking reads, i.e.
`Serial.reset_input_buffer()`, `Serial.in_waiting`, `Serial.read()`, `Serial.read_all()`.

To circumvent this, we force a wait and repeatedly check the input stream for
contents using `in_waiting`, with a timeout override if there isn't an output in
the first place.

```python
end_time = time.time() + timeout
while not self.in_waiting:
    if time.time() > end_time:
        break
```

This is effectively performed in `SerialConnection._cleanup()`,
`SerialConnection.getresponses()`, and `SerialConnection.getresponse()`.

#### Buffering input stream

The input stream flushes faster than the baudrate (or perhaps due to OS scheduling
instead?). Instead of waiting for the whole input stream to finish buffering,
we repeatedly flush the replies into a `bytearray`. In practice, a sleep time of
10ms is sufficient to allow the input stream to repopulate and avoid premature
termination of the flushing.

A snippet of usage found in `getresponses()`:

```python
replies = bytearray()
while True:
    if not self.in_waiting:
        break
    replies.extend(self.read(self.in_waiting))
    if time.time() > end_time:
        break
    time.sleep(SerialConnection.BUFFER_WAITTIME)
```
