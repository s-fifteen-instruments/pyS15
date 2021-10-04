# Developer guide

Mainly for ab-initio introduction to the conventions used within the project,
so that the codebase looks consistent across developer transitions.

## Environment setup

### Initial repository cloning

Clone the repository as usual:

```
git clone git@github.com:s-fifteen-instruments/pyS15.git
cd pyS15
```

If using SSH-based authentication, register the SSH key associated with the
corresponding GitHub account:

```
git config core.sshCommand "ssh -i ~/.ssh/id_rsa"
```

### Create virtual environment

Create a virtual environment to isolate all required dependencies
from your own global pacakage environment. For Windows,

```
# For Windows
python -m venv .venv
.\env\Scripts\activate  # activate virtual environment

# For Mac/Linux
python3 -m venv .venv
source env/bin/activate
```

### Install dependencies

Install the required dependencies using the following,

```
python -e .[dev]
```

If working on the apps within the `apps/` directory, additionally
specify the following flag to install the corresponding dependencies,

```
python -e .[dev,apps]
```

Finally, set up the necessary pre-commit hooks for the project, which provide
auto-formatting and linting services, facilitated by the
[`pre-commit`](https://pre-commit.com/) library.
The pre-commit configuration is specified in `.pre-commit-config.yaml`.

```
pre-commit install
```

For more information on the formatting/linting tools, see the corresponding
documentation:
[isort](https://pycqa.github.io/isort/),
[black](https://black.readthedocs.io/en/stable/),
[flake8](https://github.com/pycqa/flake8),
[mypy](https://mypy.readthedocs.io/en/latest/).

TODO: Add GitHub CI workflow to validate commits.

# Documentation

Currently mixed with various styles...
To standardize with [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) moving forward,
for three main reasons:

- Widely supported across many documentation generation tools, including
  Sphinx
- Of the three most popular docstring styles (i.e.
  [Sphinx](https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html),
  [Google](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html),
  [Numpy](http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_numpy.html#example-numpy)),
  Google-style docstrings are sufficiently readable (Sphinx uses multiple directives for the same variable),
  while remaining compact (Numpy-style generally takes up much more vertical space)
- Google-style docstrings already exist within the repository
