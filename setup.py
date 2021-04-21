import setuptools

setuptools.setup(
    name='S15lib',
    version='0.1',
    description='S-Fifteen Python Library',
    url='https://s-fifteen.com/',
    author='Mathias Seidler;',
    author_email='',
    license='MIT',
    packages=setuptools.find_packages(),
    install_requires=['pyserial', 'numpy'],
)
