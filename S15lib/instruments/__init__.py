from .digital_pattern_generator import PattGen
# from .lcr_driver import LCRDriver
from .powermeter import PowerMeter
from .serial_connection import SerialConnection
from .single_photon_detector import SinglePhotonDetector
from .spdc_driver import SPDCDriver
from .stepper_motor_driver import StepperMotorDriver
from .timestamp7 import TimestampTDC2
from .universal_discriminator import UniversalDiscriminator
from .usb_counter_fpga import TimestampTDC1, TimeStampTDC1

__all__ = [
    "LCRDriver",
    "PattGen",
    "PowerMeter",
    "SerialConnection",
    "SinglePhotonDetector",
    "SPDCDriver",
    "StepperMotorDriver",
    "TimestampTDC1",
    "TimeStampTDC1",
    "TimestampTDC2",
    "UniversalDiscriminator",
]

import importlib
import sys

class Proxy:
    """Performs lazy loading of module class.

    Main issue of using proxy method is introspection: attributes and methods
    inspected will be that of this Proxy class and not the underlying class.
    Can be circumvented by doing a manual replacement of the class, see example,
    or automating it by inspecting the global namespace and doing variable
    replacement (but this is probably extremely surprising behaviour for users).

    Examples:
        >>> LCRDriver = Proxy("S15lib.instruments.lcr_driver", "LCRDriver")
        >>> "DEVICE_IDENTIFIER" in LCRDriver
        False
        >>> LCRDriver = LCRDriver._get_class()
        >>> "DEVICE_IDENTIFIER" in LCRDriver
        True
    """

    def __init__(self, module: str, cls: str):
        self._module = module
        self._cls = cls

    def _get_class(self):
        """Loads module if needed, then retrieve class."""
        if self._module in sys.modules:
            module = sys.modules[self._module]
        else:
            module = importlib.import_module(self._module)
        return getattr(module, self._cls)

    def __call__(self, *args, **kwargs):
        """Pass constructor to referenced class."""
        cls = self._get_class()
        return cls(*args, **kwargs)

    def __getattr__(self, name: str):
        """Pass method lookup to referenced class."""
        cls = self._get_class()
        return getattr(cls, name)

LCRDriver = Proxy("S15lib.instruments.lcr_driver", "LCRDriver")
