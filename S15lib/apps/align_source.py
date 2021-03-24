from datetime import datetime
import os
import time
import matplotlib.pyplot as plt
import numpy as np
from S15lib.g2lib import g2lib
from S15lib.instruments import TimeStampTDC1
import sys
print(sys.version)


class Result(object):
    def __init__(self, info) -> None:
        super().__init__()
        self.pairs = info['histogram']
        self.dt = info['time_bins']
        self.acq_time = int(info['total_time']) * 1e-9
        self.pair_mask = (self.dt > 0) & (self.dt <= 20)
        self.acc_mask = (self.dt > 100) & (self.dt < 150)
        self.acc_rate_per_bin = np.sum(
            self.pairs[self.acc_mask]) / (len(self.pairs[self.acc_mask]) * self.acq_time)

        self.pair_rate = (np.sum(self.pairs[self.pair_mask]) / self.acq_time) - \
            (len(self.pairs[self.pair_mask]) * self.acc_rate_per_bin)

        self.rate_ch1 = int(info['channel1']) / self.acq_time
        self.rate_ch2 = int(info['channel2']) / self.acq_time
        self.efficiency = self.pair_rate / \
            (np.sqrt(self.rate_ch1 * self.rate_ch2))
        self.efficiency_ch1 = self.pair_rate / self.rate_ch1
        self.efficiency_ch2 = self.pair_rate / self.rate_ch2


def show_source_properties(dev_path: str = None, logging: bool = False,
                           ch_stop_delay: float = 5, t_acq: float = 1, input_pulse='NIM'):
    print(dev_path)
    if dev_path is None:
        dev = TimeStampTDC1()
    else:
        dev = TimeStampTDC1(dev_path)
    dev.level = input_pulse
    file_time_str = datetime.now().isoformat()
    plt.figure()
    hl, = plt.plot([], [], '.-')
    error_counter = 0
    while True:
        try:
            info = dev.count_g2(t_acq=t_acq, ch_stop_delay=ch_stop_delay)
            result = Result(info)
            os.system('clear')
            print('Acquisition time {:.3f} s'.format(result.acq_time))
            print(
                'Accidentals per bin (1/s): {:.0f}'.format(result.acc_rate_per_bin))
            print(
                'Pair rate corrected for accidentals (1/s): {:.0f}'.format(result.pair_rate))
            print('Avg. efficiency: {:.2f}%'.format(result.efficiency * 100))
            print(
                'Singles channel1 (1/s): {:.0f}\tSingles channel2 (1/s): {:.0f}'.format(result.rate_ch1, result.rate_ch2))
            print(
                'pairs / acc: {:.2f}'.format((result.pair_rate / (2 * result.acc_rate_per_bin))))
            print('ch1 heralding eff.: {:.2f}%\tch2 heralding eff.: {:.2f}%'.format(
                result.efficiency_ch1 * 100, result.efficiency_ch2 * 100))

            if logging is True:
                with open(file_time_str + 'source_performance_log.txt', 'a+') as f:
                    now = datetime.now().isoformat()
                    log_txt = '{},{:.0f},{:.3f},{:.0f},{:.0f},{:.0f}'.format(
                        now, result.pair_rate, result.efficiency, result.rate_ch1, result.rate_ch2, result.acc_rate_per_bin)
                    f.write(log_txt)

            hl.set_xdata(result.dt)
            hl.set_ydata(result.pairs)
            plt.xlim(-10, 100)
            plt.ylim(0, np.max(result.pairs) + 10)
            plt.draw()
            plt.pause(0.01)
        except Exception as a:
            print(type(a))
            error_counter += 1
            if error_counter == 10:
                print('too many errors in a row')
                break
        finally:
            error_counter = 0


if __name__ == '__main__':
    acq_time = input("Enter gate time in s: ")
    if acq_time == '':
        print('no user input. default to 0.1 seconds gate time')
        acq_time = 0.1
    else:
        acq_time = float(acq_time)
    pulse_type = input("Choose input pulse type (1: TTL, 2: NIM): ")
    if pulse_type == '':
        print('no user input. default to TTL')
        pulse_type = 'TTL'  
    if pulse_type == '1':
        pulse_type = 'TTL'
    elif pulse_type =='2':
        pulse_type = 'NIM'
    else:
        print('Pulse type input was not correct. Input 1 for TTL and 2 for NIM')

    show_source_properties(logging=False, t_acq = acq_time, input_pulse=pulse_type)
