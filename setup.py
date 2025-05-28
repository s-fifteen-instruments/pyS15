import shlex
import shutil
import sysconfig

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
    return shlex.join(tokens)


def find_executable(command):
    tokens = shlex.split(command)
    idx = get_executable_index(tokens)
    return idx is not None


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
    if not find_executable(cc):  # replace build compiler with platform's
        return (
            replace_executable(platform_cc, cc),
            replace_executable(platform_cc, ldshared),
        )
    return cc, ldshared  # use default compiler


# setuptools project configuration
if __name__ == "__main__":
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
    )
