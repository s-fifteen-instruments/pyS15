#!/usr/bin/env python3
#
# Example script to operate EPPS
#   Initial script - Justin 29.09.2021

import time

from S15lib.instruments import SPDCDriver

DEVICE_FILE = "COM7"  # CHANGEME, for Windows (e.g. "/dev/ttyACM0" for Linux)
spdc = SPDCDriver(DEVICE_FILE)  # connect to EPPS board

# Setpoint constants
LCURRENT = 70
HSETTEMP = 50
PSETTEMP = 29


#####################
##  SUPPLEMENTARY  ##
#####################


def _write(msg):
    """Writes command to device."""
    spdc._com.write((str(msg) + ";").encode())


def _rwrite(msg):
    """Writes command to device and reads back.

    Temporary supplementary function. To deprecate once program updated.
    """
    _write(msg)
    return spdc._com.readline()


#####################
##  SUPPLEMENTARY  ##
#####################


def status():
    """Displays all current board settings."""

    def _print(description, value, unit="", **kw):
        print("{:22s} {: >8s} {}".format(description, str(value), unit), **kw)

    print(spdc.identity, end="\n\n")

    # Laser status
    _print("Power:", _rwrite("POWER?"))
    _print("Laser current:", spdc.laser_current, "mA")
    _print("Laser current limit:", spdc.laser_current_limit, "mA", end="\n\n")

    # Heater status
    _print("Heater loop status:", spdc.heater_loop)
    _print("Heater temp:", spdc.heater_temp, "°C")
    _print("Heater set temp:", spdc.heater_temp_setpoint, "°C")
    _print("Heater ramp rate:", _rwrite("HRATE?"), "K/s")
    _print("Heater ramp target:", _rwrite("HTARGET?"), "°C")
    _print("Heater voltage:", spdc.heater_voltage, "V")
    _print("Heater voltage limit:", _rwrite("HLIMIT?"), "V")
    _print("Heater [P]ID:", spdc.hconstp, "V/K")
    _print("Heater P[I]D:", spdc.hconsti, "V/(Ks)")
    _print("Heater PI[D]:", _rwrite("HCONSTD?"), "Vs/K", end="\n\n")

    # Peltier status
    _print("Peltier loop status:", spdc.peltier_loop)
    _print("Peltier temp:", spdc.peltier_temp, "°C")
    _print("Peltier set temp:", spdc.peltier_temp_setpoint, "°C")
    _print("Peltier voltage:", spdc.peltier_voltage, "V")
    _print("Peltier voltage limit:", _rwrite("PLIMIT?"), "V")
    _print("Peltier [P]ID:", spdc.pconstp, "V/K")
    _print("Peltier P[I]D:", spdc.pconsti, "V/(Ks)")
    _print("Peltier PI[D]:", _rwrite("PCONSTD?"), "Vs/K")


def monitor():
    """Monitor heater and peltier temperatures."""
    try:
        print("Monitoring heater & peltier temperature...")
        print("(Ctrl-C to stop monitoring)")
        while True:
            print("{: >8.3f} {: >8.3f}".format(spdc.heater_temp, spdc.peltier_temp))
            time.sleep(1)
    except KeyboardInterrupt:
        pass


######################
##  POWER ROUTINES  ##
######################


def initialize():
    """Resets board constants and saves."""
    # Laser settings
    _rwrite("POWER 0")
    spdc.laser_current = 0  # for ramp sequence
    spdc.laser_current_limit = 85

    # Peltier settings
    spdc.peltier_loop_off()
    _write("PSETTEMP {}".format(PSETTEMP))
    _write("PLIMIT 2.5")
    spdc.pconstp = 0.4
    spdc.pconsti = 0.035
    _write("PCONSTD 0")

    # Heater settings
    spdc.heater_loop_off()
    _write("HSETTEMP 20")  # near room temperature for ramp
    _write("HRATE 0.05")
    _write("HLIMIT 4.5")
    spdc.hconstp = 0.3
    spdc.hconsti = 0.003
    _write("HCONSTD 0")
    spdc.save_settings()

    # (optional) Accelerates HTARGET to setpoint
    htarget = float(_rwrite("HTARGET?"))
    if htarget != 20.0:
        try:
            print("Resetting HTARGET...")
            _write("HRATE 1")
            while htarget != 20.0:
                time.sleep(1)
                htarget = float(_rwrite("HTARGET?"))
            print("HTARGET reset.")
        except KeyboardInterrupt:
            print("HTARGET acceleration cancelled.")
        finally:
            _write("HRATE 0.05")  # failsafe


def setup():
    """Initial power up routine.

    Additionally ramps up and monitors the heater temperature.
    """
    _write("POWER 3")
    spdc.peltier_loop_on()
    spdc.heater_loop_on()
    spdc.save_settings()

    _write("HSETTEMP {}".format(HSETTEMP))  # heater ramp
    spdc.laser_on(LCURRENT)  # laser current ramp
    print("Laser switched on with current:", spdc.laser_current, "mA")

    # Monitor temperature
    try:
        print("Monitoring current heater temperature...")
        print("Terminates at {}°C (Ctrl-C to stop monitoring)".format(HSETTEMP))
        while True:
            heater_temp = spdc.heater_temp
            print(heater_temp, "°C")
            if heater_temp > HSETTEMP:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    print(
        "Device started up with:"
        + "\n  - Laser current: {} mA".format(spdc.laser_current)
        + "\n  - Heater temp: {} °C".format(spdc.heater_temp)
        + "\n  - Peltier temp: {} °C".format(spdc.peltier_temp)
    )


def laser_off():
    """Switch off laser.

    Heater and peltier PID loops are kept running.
    """
    spdc.laser_off()
    _write("POWER 1")


def laser_on():
    """Switch on laser."""
    _write("POWER 3")
    spdc.laser_on(LCURRENT)


def teardown():
    """Shutdown routine prior to transportation.

    Additionally ramps down and monitors the heater temperature.
    """
    spdc.laser_off()

    # Verify heater has cooled sufficiently before switching off HLOOP
    _write("HSETTEMP 20")
    try:
        print("Monitoring current heater temperature...")
        print("Terminates at 25°C (Ctrl-C to stop monitoring)")
        while True:
            heater_temp = spdc.heater_temp
            print(heater_temp, "°C")
            if heater_temp < 25:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    spdc.heater_loop_off()  # HLOOP 0; HVOLT 0;
    spdc.peltier_loop_off()  # PLOOP 0; PVOLT 0;
    _write("POWER 0")
    spdc.save_settings()

    print(
        "Device powered down with:"
        + "\n  - Laser current: {} mA".format(spdc.laser_current)
        + "\n  - Heater temp: {} °C".format(spdc.heater_temp)
        + "\n  - Peltier temp: {} °C".format(spdc.peltier_temp)
    )
