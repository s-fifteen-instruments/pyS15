import setuptools

requirements = [
    "pyserial",
    "numpy",
]
requirements_apps = [
    "PyQt5",
    "Pyqtgraph",
]

setuptools.setup(
    name='S15lib',
    version='0.1.2',
    description='S-Fifteen Python Library',
    url='https://s-fifteen.com/',
    author='Mathias Seidler;',
    author_email='',
    license='MIT',
    packages=setuptools.find_packages(),
    install_requires=requirements,
    extras_require={
        "apps": requirements_apps,
    },
    python_requires=">=3.6",
)
