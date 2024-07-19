from setuptools import Extension, setup

import numpy as np
from Cython.Build import cythonize

package = Extension(
    name="delta",
    sources=["delta.pyx"],
    include_dirs=[np.get_include()],
    define_macros=[
        ("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")
    ],  # https://stackoverflow.com/a/64915608
)
setup(ext_modules=cythonize([package], language_level="3"))
