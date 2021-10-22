#!/usr/bin/env python3
#
# Example script to operate EPPS
#   Initial script - Justin 29.09.2021

import time

from S15lib.instruments import SPDCDriver

spdc = SPDCDriver("COM7")  # CHANGEME, for Windows (e.g. "/dev/ttyACM0" for Linux)

# Setpoint constants
LCURRENT = 70
HSETTEMP = 50
PSETTEMP = 29


#####################
#   SUPPLEMENTARY   #
#####################


def status():
    """Displays all current board settings."""

    def _print(description, value, unit="", **kw):
        print("{:22s} {: >8s} {}".format(description, str(value), unit), **kw)

    print(spdc.identity, end="\n\n")

    # Laser status
    _print("Power:", spdc.power)
    _print("Laser current:", spdc.laser_current, "mA")
    _print("Laser current limit:", spdc.laser_current_limit, "mA", end="\n\n")

    # Heater status
    _print("Heater loop status:", spdc.heater_loop)
    _print("Heater temp:", spdc.heater_temp, "°C")
    _print("Heater set temp:", spdc.heater_temp_setpoint, "°C")
    _print("Heater ramp rate:", spdc.heater_temp_rate, "K/s")
    _print("Heater ramp target:", spdc.heater_temp_target, "°C")
    _print("Heater voltage:", spdc.heater_voltage, "V")
    _print("Heater voltage limit:", spdc.heater_voltage_limit, "V")
    _print("Heater [P]ID:", spdc.hconstp, "V/K")
    _print("Heater P[I]D:", spdc.hconsti, "V/(Ks)")
    _print("Heater PI[D]:", spdc.hconstd, "Vs/K", end="\n\n")

    # Peltier status
    _print("Peltier loop status:", spdc.peltier_loop)
    _print("Peltier temp:", spdc.peltier_temp, "°C")
    _print("Peltier set temp:", spdc.peltier_temp_setpoint, "°C")
    _print("Peltier voltage:", spdc.peltier_voltage, "V")
    _print("Peltier voltage limit:", spdc.peltier_voltage_limit, "V")
    _print("Peltier [P]ID:", spdc.pconstp, "V/K")
    _print("Peltier P[I]D:", spdc.pconsti, "V/(Ks)")
    _print("Peltier PI[D]:", spdc.pconstd, "Vs/K")


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
#   POWER ROUTINES   #
######################


def initialize():
    """Resets board constants and saves."""
    # Laser settings
    spdc.laser_off()
    spdc.laser_current = 0  # for ramp sequence
    spdc.laser_current_limit = 85

    # Peltier settings
    spdc.peltier_loop_off()
    spdc.peltier_temp_setpoint = PSETTEMP  # peltier target temperature
    spdc.peltier_voltage_limit = 2.5
    spdc.pconstp = 0.4
    spdc.pconsti = 0.035
    spdc.pconstd = 0

    # Heater settings
    spdc.heater_loop_off()
    spdc.heater_temp_setpoint = 20  # need near room temperature for ramp
    spdc.heater_temp_rate = 0.05
    spdc.heater_voltage_limit = 4.5
    spdc.hconstp = 0.3
    spdc.hconsti = 0.003
    spdc.hconstd = 0
    spdc.save_settings()

    # (optional) Accelerates HTARGET to setpoint
    # See `SPDCDriver.heater_temp_rate` for details.
    htarget = spdc.heater_temp_target
    if htarget != 20.0:
        try:
            print("Resetting HTARGET...")
            spdc.heater_temp_rate = 1
            while htarget != 20.0:
                time.sleep(1)
                htarget = spdc.heater_temp_target
            print("HTARGET reset.")
        except KeyboardInterrupt:
            print("HTARGET acceleration cancelled.")
        finally:
            spdc.heater_temp_rate = 0.05  # failsafe


def setup():
    """Initial power up routine.

    Additionally ramps up and monitors the heater temperature.
    """
    spdc.peltier_loop_on()
    spdc.heater_loop_on()
    spdc.save_settings()

    spdc.heater_temp_setpoint = HSETTEMP  # heater ramp
    spdc.laser_on(LCURRENT)  # laser current ramp

    # Monitor temperature
    print("Laser switched on with current:", spdc.laser_current, "mA")
    try:
        print("Monitoring current heater temperature...")
        print("Terminates at {}°C (Ctrl-C to stop monitoring)".format(HSETTEMP))
        while True:
            heater_temp = spdc.heater_temp
            print(heater_temp, "°C")
            if heater_temp > HSETTEMP:  # terminate monitoring once overshoot
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
    """Switch off laser."""
    spdc.laser_off()  # heater and peltier loops still running


def laser_on():
    """Switch on laser."""
    spdc.laser_on(LCURRENT)


def teardown():
    """Shutdown routine prior to transportation.

    Additionally ramps down and monitors the heater temperature.
    """
    spdc.laser_off()
    spdc.heater_temp_setpoint = 20

    # Verify heater has cooled sufficiently before switching off HLOOP
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

    spdc.heater_loop_off()  # HLOOP 0; HVOLT 0; POWER 1; (ploop still on)
    spdc.peltier_loop_off()  # PLOOP 0; PVOLT 0; POWER 0;
    spdc.save_settings()

    print(
        "Device powered down with:"
        + "\n  - Laser current: {} mA".format(spdc.laser_current)
        + "\n  - Heater temp: {} °C".format(spdc.heater_temp)
        + "\n  - Peltier temp: {} °C".format(spdc.peltier_temp)
    )
