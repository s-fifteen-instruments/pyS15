import setuptools

requirements = [
    "psutils",
    "pyserial",
    "numpy",
]
requirements_dev = [
    "pre-commit",
]
requirements_apps = [
    "PyQt5",
    "Pyqtgraph",
    "configargparse",
    "Cython",
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
)
