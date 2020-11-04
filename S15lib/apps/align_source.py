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





def show_source_properties(dev_path: str = None, logging: bool = True, ch_stop_delay: float = 5, t_acq: float = 1):
    print(dev_path)
    if dev_path is None:
        dev = TimeStampTDC1()
    else:
        dev = TimeStampTDC1(dev_path)
    # dev.mode = 'singles'
    # dev.time= 1
    # print('Singles counts', dev.get_counts())
    file_time_str = datetime.now().isoformat()
    plt.figure()
    hl, = plt.plot([], [], '.-')

    # time.sleep(1)
    error_counter = 0
    while True:
        try:
            info, dt, pairs = dev.count_g2(t_acq, ch_stop_delay = ch_stop_delay)
            acq_time = int(info['total_time']) * 1e-9
            os.system('clear')
            print('Acquisition time {:.3f} s'.format(acq_time))
            pair_mask = (dt > 0) & (dt <= 20)
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

            hl.set_xdata(dt)
            hl.set_ydata(pairs)
            # plt.plot(dt, pairs, 'o-')
            plt.xlim(-10, 100)
            plt.ylim(0, np.max(pairs) + 10)
            plt.draw()
            plt.pause(0.01)
            # time.sleep(59)
        except Exception as a:
            print(type(a))
            error_counter += 1
            if error_counter == 10:
            	print('too many errors in a row')
            	break
        finally:
        	error_counter = 0


if __name__ == '__main__':
    show_source_properties(dev_path = '/dev/tty.usbmodemTDC1_00141', logging=False)

