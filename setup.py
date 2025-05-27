import os
import shlex
import shutil
import sysconfig

import numpy as np
import setuptools

requirements = [
    "psutil",
    "pyserial",
    "numpy",
]
requirements_dev = [
    "pre-commit",
    "Cython",
]
requirements_apps = [
    "PyQt5",
    "Pyqtgraph",
    "configargparse",
]


# Use C compiler as specified in env, or system's default, for compiling delta.so
# Necessary on portable Python built with other compilers, e.g. gcc/clang
#
# Precedence:
#   1. User environment variable, e.g. CC=gcc
#   2. Python build-time compiler
#   3. OS executable in PATH, e.g. /usr/bin/cc
#
# TODO: Check if compatible with Windows installations
config = sysconfig.get_config_vars()

# Check if Python was cross-compiled (i.e. build-time compiler does not exist)
def tokenize(command):  # noqa
    return shlex.split(command)


def get_executable_index(tokens, check_exists=True):
    for i, token in enumerate(tokens):
        # Ignore environment variables, and check executable exists
        if "=" not in token:
            if check_exists and not shutil.which(token):
                continue
            return i
    else:
        return None


def replace_executable(target, command):
    tokens = tokenize(command)
    idx = get_executable_index(tokens, check_exists=False)
    tokens = list(tokens)  # replace with mutable container
    tokens[idx] = target
    return shlex.join(tokens)


def find_executable(command):
    tokens = tokenize(command)
    idx = get_executable_index(tokens)
    return idx is not None


u_cc = os.environ.get("CC", None)  # user-specified compiler
if u_cc is not None:
    config["CC"] = u_cc
    config["LDSHARED"] = f"{u_cc} -shared"  # for shared libraries
    u_ldshared = os.environ.get("LDSHARED", None)
    if u_ldshared is not None:
        config["LDSHARED"] = u_ldshared  # if manual library linking required

else:
    b_cc = config.get("CC", None)  # build compiler
    b_ldshared = config.get("LDSHARED", None)
    p_cc = shutil.which("cc")  # platform default compiler (w/o options)
    if b_cc is None:
        config["CC"] = p_cc
        config["LDSHARED"] = f"{p_cc} -shared"
    elif not find_executable(b_cc):
        config["CC"] = replace_executable(p_cc, b_cc)
        config["LDSHARED"] = replace_executable(p_cc, b_ldshared)


# setuptools project configuration
setuptools.setup(
    name="S15lib",
    version="0.2.0",
    description="S-Fifteen Python Library",
    url="https://s-fifteen.com/",
    author="Mathias Seidler;",
    author_email="",
    license="MIT",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    extras_require={
        "dev": requirements_dev,
        "apps": requirements_apps,
    },
    python_requires=">=3.6",
    ext_modules=[
        setuptools.Extension(
            name="S15lib.g2lib.delta",
            sources=["S15lib/g2lib/delta.c"],
            include_dirs=[np.get_include()],
            define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
        )
    ],
)
