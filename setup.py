import os
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
#   2. OS executable in PATH, e.g. /usr/bin/cc
#   3. Python build-time compiler
config = sysconfig.get_config_vars()
cc = os.environ.get("CC", shutil.which("cc"))
if cc is not None:
    config["CC"] = cc
    config["LDSHARED"] = f"{cc} -shared"  # for shared libraries
ldshared = os.environ.get("LDSHARED", None)  # allow user override
if ldshared is not None:
    config["LDSHARED"] = ldshared


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
