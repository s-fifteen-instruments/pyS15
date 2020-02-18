# private_mathias
S15lib is a python package to control [s-fifteen instruments](https://s-fifteen.com/).

### 1 Requirements
- [Python](https://www.python.org) installed.  We support Python >3.6.
- [pip](https://pypi.org/project/pip/) installed (Already installed if you are using Python 2 >=2.7.9 or Python 3 >=3.4)

### 2 Install S15lib
Clone or download https://github.com/sfifteen/private_mathias.git.

Open a command-line terminal, go into the repository folder and type
  
    pip install -e .
    
### 3 Use a device in your python script
Here an example to use the s-fivteen power meter:

    from S15lib.devices import PowerMeter
    pm_dev = PowerMeter('/dev/seriabl/by-id/....')
    wave_length = 780 # impending light on the power meter has a wavelength of 780 nm
    optical_power = pm_dev.get_power(wave_length)
    print(optical_power)
    op, op_std = pm_dev.get_avg_power(10, wave_length) # samples the optical power 10 times and returns mean and standard deviation
    print(op, op_std)
    
 ### 4 Use a device app
 The apps folder contains graphical user interfaces for s-fifteen devices.
 Those with plotting features require PyQt5 and pyqtgraph (install them with:  pip install PyQt5, pyqtgraph).
