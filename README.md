# S-Fifteen Python library

S15lib is a Python package for controlling [S-Fifteen instruments](https://s-fifteen.com/).

## Installation

[Python](https://www.python.org) 3.7+ is required.
Install the package directly with

```
# For Linux/MacOS
pip install git+https://github.com/s-fifteen-instruments/pyS15.git

# For Windows and/or systems with compile-related installation difficulties
pip install git+https://github.com/s-fifteen-instruments/pyS15.git@no_compile
```

Alternatively, clone or [download](https://github.com/s-fifteen-instruments/pyS15/archive/refs/heads/master.zip)
the repository and execute the following
command from within the project directory.

```
pip install -e .
```

The library can be uninstalled with,

```
pip uninstall S15lib
```

For older versions of Python, see the relevant last supported version:

* Python 3.6 @ [v0.2.0](https://github.com/s-fifteen-instruments/pyS15/releases/tag/v0.2.0): `pip install git+https://github.com/s-fifteen-instruments/pyS15.git@v0.2.0`

## Usage

### Via Python interpreter

Here is a minimal script to interface with the S-Fifteen power meter:

```
>>> from S15lib.instruments import PowerMeter
>>> pm = PowerMeter('/dev/serial/by-id/...')
>>> pm.get_power(780)  # optical power in mW, with 780nm incident wavelength
0.003378571428571428
```

More examples are available in the [`examples/`](examples) directory.

### Via device application

The [`apps/`](S15lib/apps) directory contains apps and graphical user interfaces (GUIs) for
selected S-Fifteen devices, some of which require additional (graphing) dependencies that
can installed with

```
pip install -e .[apps]
```

The apps can then be started either in the interpreter,

```
>>> from S15lib.apps import powermeter_app
>>> powermeter_app.main()
```

or by downloading the apps from the [`apps/`](S15lib/apps) and starting them with,

```
python powermeter_app.py
```

## Development

See the [developer guide](docs/developer.md).
