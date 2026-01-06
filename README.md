# S-Fifteen Python library

S15lib is a [Python](https://www.python.org) package for controlling [S-Fifteen Instruments](https://s-fifteen.com/) devices.

## Installation

Python 3.7+ is required.
Install the package directly with:

```
pip install S15lib
```

<details>
<summary>Alternative installation methods</summary>

To install directly from the source:

```
# For Linux/MacOS
pip install git+https://github.com/s-fifteen-instruments/pyS15.git

# For Windows and/or systems with compile-related installation difficulties
pip install git+https://github.com/s-fifteen-instruments/pyS15.git@no_compile
```

or alternatively, clone or [download](https://github.com/s-fifteen-instruments/pyS15/archive/refs/heads/master.zip)
the repository and install as an editable local library with `pip install -e .` from within the project directory.

</details>

<details>
<summary>Last supported versions for older Python versions</summary>

| Python | S15lib version | EOL |
|--------|----------------|-----|
| 3.6    | [v0.2.0](https://github.com/s-fifteen-instruments/pyS15/releases/tag/v0.2.0) | June 2023 |

For example, to install version `v0.2.0` of the library from source:

```
pip install git+https://github.com/s-fifteen-instruments/pyS15.git@v0.2.0
```

:warning: Upgrading your version of Python is highly recommended to benefit from bug fixes.
Consider using a Python manager to install current versions of Python on the same system (to avoid mangling system Python).
Recommended Python version management tools include [uv](https://docs.astral.sh/uv/) and [pyenv](https://github.com/pyenv/pyenv), e.g.

```powershell
uv venv --python 3.13
.venv\Scripts\activate.ps1
uv pip install S15lib
```

</details>

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
