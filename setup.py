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
