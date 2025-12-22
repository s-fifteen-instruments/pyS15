import os
import shlex
import shutil
import sys
import sysconfig

import numpy as np
import setuptools

# Use C compiler as specified in env, or system's default, for compiling delta.so
# Necessary on portable Python built with other compilers, e.g. gcc/clang
#
# Precedence:
#   1. User environment variable, e.g. CC=gcc
#   2. OS executable in PATH, e.g. /usr/bin/cc
#   3. Python build-time compiler
#
# TODO: Check if compatible with Windows installations


def get_executable_index(tokens, check_exists=True):
    for i, token in enumerate(tokens):
        if "=" not in token:  # ignore environment variables
            if check_exists and not shutil.which(token):
                continue
            return i
    return None


def replace_executable(target, command):
    tokens = shlex.split(command)
    idx = get_executable_index(tokens, check_exists=False)
    tokens = list(tokens)  # replace with mutable container
    tokens[idx] = target
    if sys.version_info >= (3, 8):
        return shlex.join(tokens)
    else:
        return " ".join(shlex.quote(token) for token in tokens)


def find_executable(command):
    if command is None:
        return False
    tokens = shlex.split(command)
    idx = get_executable_index(tokens)
    if idx is not None:
        return True


def get_compiler(config=sysconfig.get_config_vars(), env={}):
    """Returns preferred cc and ldshared programs.

    Args:
        config: config dictionary from Python's sysconfig.
        env: environment variables.

    Examples:
        $ export PROG="python -c 'import setup, os; \
            print(setup.get_compiler(setup.config, os.environ))'"

        # Assuming gcc build compiler, not present on host
        $ eval $PROG
        ('cc -pthread', 'cc -pthread -shared -Wl,--exclude-libs,ALL -LModules/_hacl')

        # Creating a symlink named 'gcc'
        $ ln -s /usr/bin/cc /usr/bin/gcc
        $ eval $PROG
        ('gcc -pthread', 'gcc -pthread -shared -Wl,--exclude-libs,ALL -LModules/_hacl')

        # Use env-defined compilers
        $ CC='clang -Wall' eval $PROG
        ('clang -Wall', 'clang -Wall -shared')
        $ CC=clang LDSHARED='clang -shared -O2' eval $PROG
        ('clang', 'clang -shared -O2')
    """

    # Prefer user-supplied compiler (flags)
    if "CC" in env:
        cc = env.get("CC")
        return cc, env.get("LDSHARED", f"{cc} -shared")

    platform_cc = shutil.which("cc")
    cc = config.get("CC", platform_cc)
    ldshared = config.get("LDSHARED", f"{platform_cc} -shared")
    if find_executable(cc):  # replace build compiler with platform's
        return (
            replace_executable(platform_cc, cc),
            replace_executable(platform_cc, ldshared),
        )
    return cc, ldshared  # use default compiler


# setuptools project configuration
if __name__ == "__main__":

    config = sysconfig.get_config_vars()
    config["CC"], config["LDSHARED"] = get_compiler(config, os.environ)

    setuptools.setup(
        license="MIT",  # legacy field for Python 3.7
        ext_modules=[
            setuptools.Extension(
                name="S15lib.g2lib.delta",
                sources=["S15lib/g2lib/delta.c"],
                include_dirs=[np.get_include()],
                define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
            )
        ],
    )
