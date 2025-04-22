# Developer guide

Instructions below use `uv` as the frontend.


## Environment setup

Clone the repository and create a virtual environment for dependencies as usual,

```bash
# Clone repository
git clone git@github.com:s-fifteen-instruments/pyS15.git
cd pyS15

# Create virtual environment
uv venv
source .venv/bin/activate  # for Linux

# Install dependencies
uv pip install -e .[dev]
```

> :warning: If working on the apps within the `apps/` directory, additionally
specify the `apps` flag to install the corresponding dependencies,
> i.e. `uv pip install -e .[dev,apps]`

Finally, set up the necessary pre-commit hooks for the project, which provide
auto-formatting and linting services, facilitated by the
[`pre-commit`](https://pre-commit.com/) library.

```
pre-commit install
```

> The pre-commit configuration is specified in `.pre-commit-config.yaml`.
The same checks are used on the repository to validate changes to commits pushed
or submitted as part of a pull request, for continuous integration.
For more information on the formatting/linting tools used, see the corresponding
documentation:
[isort](https://pycqa.github.io/isort/),
[black](https://black.readthedocs.io/en/stable/),
[flake8](https://github.com/pycqa/flake8),
[mypy](https://mypy.readthedocs.io/en/latest/).

Prior to pushing, sign the commits using a registered GPG/SSH key, e.g.
`git config core.sshCommand "ssh -i ~/.ssh/id_rsa"`

## Pushing changes in delta.pyx

Previous versions of the library required a separate build step for the C-based $g^{(2)}$ code
in `S15lib/g2lib/delta.pyx`, involving (a) Cython compile from `.pyx` to `.c`, and (b) CC compile into shared library `.so`.
Step (b) is now automatically performed during package installation.

Step (a) is relatively expensive, and requires the `Cython` package. This should now be performed out-of-band to speed up
package installation, i.e. changes to the `delta.pyx` source should accompany a recompilation to `delta.c` in the same commit,

```bash
cython -3 S15lib/g2lib/delta.pyx
```

## Documentation

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
