import sys
print(sys.version)

from S15lib.instruments import TimeStampTDC1
from S15lib.g2lib import g2lib

import numpy as np
import matplotlib.pyplot as plt
import time
import os
import pylab
from datetime import datetime





def show_source_properties(dev_path: str = None, logging: bool = True):
    print(dev_path)
    plt.figure()
    plt.ion()
    if dev_path is None:
        dev = TimeStampTDC1()
    else:
        dev = TimeStampTDC1(dev_path)
    t_acq = 1
    dev.mode = 'singles'
    dev.time= 1
    print('Singles counts', dev.get_counts())
    file_time_str = datetime.now().isoformat()
    # time.sleep(1)
    while True:
        try:
            info, dt, pairs = dev.count_g2(t_acq)
            acq_time = int(info['total_time']) * 1e-9
            os.system('clear')
            print('Acquisition time {:.3f} s'.format(acq_time))
            pair_mask = (dt >= 5) & (dt <= 20)
            acc_mask = (dt > 100) & (dt < 150)
            acc_rate_per_bin = np.sum(
                pairs[acc_mask]) / (len(pairs[acc_mask]) * acq_time)

            pair_rate = (np.sum(pairs[pair_mask]) / acq_time) - \
                (len(pairs[pair_mask]) * acc_rate_per_bin)

            rate_ch1 = int(info['channel1']) / acq_time
            rate_ch2 = int(info['channel2']) / acq_time
            efficiency = pair_rate / (np.sqrt(rate_ch1 * rate_ch2))
            efficiency_ch1 = pair_rate / rate_ch1
            efficiency_ch2 = pair_rate / rate_ch2

            print('Accidentals per bin (1/s): {:.0f}'.format(acc_rate_per_bin))
            print('Pair rate corrected for accidentals (1/s): {:.0f}'.format(pair_rate))
            print('Avg. efficiency: {:.2f}%'.format(efficiency * 100))
            print('Singles channel1 (1/s): {:.0f}\tSingles channel2 (1/s): {:.0f}'.format(rate_ch1, rate_ch2))
            print('pairs / acc: {:.2f}'.format((pair_rate / (2 * acc_rate_per_bin))))
            print('ch1 heralding eff.: {:.2f}%\tch2 heralding eff.: {:.2f}%'.format(
                efficiency_ch1 * 100, efficiency_ch2 * 100))

            if logging is True:
                with open(file_time_str + 'source_performance_log.txt', 'a+') as f:
                    now = datetime.now().isoformat()
                    log_txt = f'{now},{pair_rate:.0f},{efficiency:.3f},{rate_ch1:.0f},{rate_ch2:.0f},{acc_rate_per_bin:.0f}\n'
                    f.write(log_txt)

            plt.plot(dt, pairs, 'o-')
            plt.xlim(-10, 100)
            plt.draw()
            plt.pause(0.0001)
            # time.sleep(59)
        except Error:
            print('error')


if __name__ == '__main__':
    show_source_properties('/dev/tty.usbmodemTDC1_00141')

