import setuptools

setuptools.setup(
    name='S15lib',
    version='0.1',
    description='S-Fifteen python library',
    url='https://s-fifteen.com/',
    author='https://s-fifteen.com/',
    author_email='',
    license='MIT',
    packages=["S15lib", "S15apps", "S15lib.devices"],
    install_requires=['pyserial', 'numpy'],
)
