import sys
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QGridLayout, QWidget, QAction, qApp, QMenuBar
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5 import QtGui
import pyqtgraph as pg
import PyQt5

from datetime import datetime
import time
from S15lib.instruments import powermeter
from S15lib.instruments import serialconnection

PLT_SAMPLES = 500


def convert_to_pwr_string(pwr):
    if pwr < 1e-3:
        return "{:06.2f} \u03BCW".format(pwr * 1e6)
    else:
        return "{:07.3f} mW".format(pwr * 1e3)


class DataLoggingThread(QThread):
    signal = pyqtSignal('PyQt_PyObject')
    signal_thread_finished = pyqtSignal('PyQt_PyObject')

    def __init__(self, tot_time, sampling_rate, file_name, device_path, wave_length, avg_samples, stop_flag):
        QThread.__init__(self)
        self.device_path = device_path
        self.file_name = file_name
        self.tot_time = tot_time
        self.sampling_rate = sampling_rate
        self.wave_length = wave_length
        self.stop_flag = stop_flag
        self._avg_samples = avg_samples

    def run(self):
        start = time.time()
        now = start
        pm_dev = powermeter.PowerMeter(self.device_path)

        while (now - start) < self.tot_time and self.stop_flag() is False:
            pwr, pwr_std = pm_dev.get_avg_power(self.wave_length, 15)
            time.sleep(1 / self.sampling_rate)
            now = time.time()
            self.signal.emit(pwr)
            try:
                f = open(self.file_name)
            except IOError:
                f = open(self.file_name, 'w')
                f.write('#time_stamp,power(Watt),power_standard_deviation(Watt)\n')
            finally:
                with open(self.file_name, 'a+') as f:
                    write_str = '{},{},{}\n'.format(
                        datetime.now().isoformat(), pwr, pwr_std)
                    f.write(write_str)
        self.signal_thread_finished.emit('Finished logging')


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self._pm_dev = None
        self._prev_pwr = 0
        self.acq_flag = False
        self._wave_length = 780
        self._logfile_name = ''
        self.thread_stop_flag = False
        self._avg_samples = 10
        self._thread_running_flag = False

        # start Gui design
        self.setWindowTitle("Powermeter S-Fivteen")

        menubar = QMenuBar()
        fileMenu = menubar.addMenu('File')
        fileMenu.addAction('tst')
        # power label

        self.curr_power_label = QLabel('000.00 \u03BCW')
        self.curr_power_label.setFont(
            QtGui.QFont("Arial", 60, QtGui.QFont.Bold))

        # Plot
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setBackground('w')
        self.draw_plot()

        # Device selection drop down
        dev_list = serialconnection.search_for_serial_devices(
            powermeter.PowerMeter.DEVICE_IDENTIFIER)
        self.comboBox = QtGui.QComboBox()
        self.comboBox.addItems(dev_list)
        # self.comboBox.setStyleSheet("font-size: 20px;height:30px");

        # Start plot
        self.button = QtGui.QPushButton('Live start')
        # self.button.setStyleSheet("font-size: 15px;height:25px;width: 60self.comboBox.setEnabled(False)px;")
        self.button.clicked.connect(self.on_button_clicked)

        # wavelength selection
        self.wavelength_label = QtGui.QLabel(self.tr("wave length (nm):"))
        self.wavelength_spinBox = QtGui.QSpinBox()
        self.wavelength_spinBox.setRange(400, 900)
        self.wavelength_spinBox.setValue(780)
        self.wavelength_spinBox.valueChanged.connect(self.update_wavelength)

        # logging
        self.label_logfile = QtGui.QLabel('')
        label_tot_time = QtGui.QLabel('Acquisition time (s):')
        label_sample_rate = QtGui.QLabel('Sampling rate (1/s):')
        label_sample_rate.setAlignment(PyQt5.QtCore.Qt.AlignRight)
        label_tot_time.setAlignment(PyQt5.QtCore.Qt.AlignRight)
        self.logfile_button = QtGui.QPushButton('Select log file')
        self.startLoggin_button = QtGui.QPushButton('Start logging')
        self.stopLoggin_buton = QtGui.QPushButton('Stop logging')
        self.startLoggin_button.clicked.connect(self.on_clicked_start_log)
        self.startLoggin_button.setEnabled(False)
        self.logfile_button.clicked.connect(self.file_save)
        self.log_tot_time = QtGui.QSpinBox()
        self.log_sample_rate = QtGui.QSpinBox()
        # self.log_tot_time.setRange(1, 1000)
        self.log_tot_time.setValue(10)
        self.log_sample_rate.setRange(0, 200)
        self.log_sample_rate.setValue(10)

        # Grid
        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self.grid.addWidget(self.comboBox, 0, 1, 1, 1)
        self.grid.addWidget(self.button, 0, 0, 1, 1)
        self.grid.addWidget(self.wavelength_label, 1, 0, 1, 1)
        self.grid.addWidget(self.wavelength_spinBox, 1, 1, 1, 1)
        self.grid.addWidget(self.curr_power_label, 3, 0, 1, 2)
        self.grid.addWidget(self.graphWidget, 4, 0, 1, 5)
        self.grid.addWidget(self.logfile_button, 0, 2, 1, 1)
        self.grid.addWidget(self.label_logfile, 0, 3, 1, 2)
        self.grid.addWidget(label_tot_time, 1, 2, 1, 1)
        self.grid.addWidget(self.log_tot_time, 1, 3, 1, 1)
        self.grid.addWidget(label_sample_rate, 2, 2, 1, 1)
        self.grid.addWidget(self.log_sample_rate, 2, 3, 1, 1)
        self.grid.addWidget(self.startLoggin_button, 3, 2, 1, 1)

        # Create widget
        self.widget = QWidget()
        self.widget.setLayout(self.grid)
        self.setCentralWidget(self.widget)

        # Set timer to update plot
        self.timer = QTimer()
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.update_plot_data)

        # Set timer for logging
        self.log_thread = None

    def on_button_clicked(self):
        if self.acq_flag is True:
            self.button.setText('Live start')
            self.acq_flag = False
            self.timer.stop()
            self._pm_dev = None
            self._prev_pwr = 0
            self.comboBox.setEnabled(True)
            if self._logfile_name != '':
                self.startLoggin_button.setEnabled(True)
        else:
            self.start_pwr_plot()
            self.button.setText('Live stop')
            self.acq_flag = True
            self.comboBox.setEnabled(False)
            self.startLoggin_button.setEnabled(False)

    def update_wavelength(self):
        self._wave_length = self.wavelength_spinBox.value()

    def file_save(self):
        default_filetype = 'csv'
        start = datetime.now().strftime('%Y%m%d') + 'powermeter.' + default_filetype
        self._logfile_name = QtGui.QFileDialog.getSaveFileName(
            self, 'Save to log file', start)[0]
        self.label_logfile.setText(self._logfile_name)
        if self.timer.isActive() == False:
            self.startLoggin_button.setEnabled(True)

    def on_clicked_start_log(self):
        if self._logfile_name != '' and self._thread_running_flag is False:
            self.log_thread = DataLoggingThread(self.log_tot_time.value(),
                                                self.log_sample_rate.value(),
                                                self._logfile_name,
                                                self.comboBox.currentText(),
                                                self._wave_length,
                                                self._avg_samples,
                                                lambda: self.thread_stop_flag)
            self.button.setEnabled(False)
            self.x = []
            self.y = []
            self.thread_stop_flag = False
            self._thread_running_flag = True
            self.log_thread.signal.connect(self.update_from_thread)
            self.log_thread.signal_thread_finished.connect(
                self.logging_finished)
            self.log_thread.start()
            self.startLoggin_button.setText('Stop logging')
            self.logfile_button.setEnabled(False)
        elif self._thread_running_flag is True:
            self.thread_stop_flag = True
            self._thread_running_flag = False
            self.startLoggin_button.setText('Start logging')
            self.logfile_button.setEnabled(True)
            self.button.setEnabled(True)

    def logging_finished(self, signal_str):
        self.button.setEnabled(True)
        self.logfile_button.setEnabled(True)
        self.log_thread = None
        self._thread_running_flag = False

    def update_from_thread(self, data):
        self.x.append(len(self.x) + 1)
        self.y.append(data)
        self.data_line.setData(self.x, self.y)
        self.curr_power_label.setText(convert_to_pwr_string(data))
        self.graphWidget.setYRange(0, max(self.y) * 1.2)

    def draw_plot(self):
        font = QtGui.QFont("Arial", 18)
        self.graphWidget.getAxis("bottom").textFont = font

        labelStyle = '<span style=\"color:black;font-size:25px\">'
        self.graphWidget.setLabel('left', labelStyle + 'Optical power', 'W')
        self.graphWidget.setLabel('bottom', labelStyle + 'Sample number', '')
        self.graphWidget.getAxis("left").tickFont = font
        self.graphWidget.getAxis("bottom").tickFont = font
        self.graphWidget.getAxis("bottom").setPen(color='k')
        self.graphWidget.getAxis("left").setPen(color='k')
        self.graphWidget.showGrid(y=True)

        self.x = []
        self.y = []  # 100 data points

        pen = pg.mkPen(width=2, color=(255, 0, 0))
        self.data_line = self.graphWidget.plot(self.x, self.y, pen=pen)

    def update_plot_data(self):
        pwr, _ = self._pm_dev.get_avg_power(self._wave_length, 10)
        if len(self.x) == PLT_SAMPLES:
            self.x = self.x[1:]
            self.x.append(self.x[-1] + 1)
            self.y = self.y[1:]
        else:
            self.x.append(len(self.x) + 1)
        self.y.append(pwr)
        self.data_line.setData(self.x, self.y)
        self.curr_power_label.setText(convert_to_pwr_string(pwr))
        self.graphWidget.setYRange(0, max(self.y) * 1.2)

    def start_pwr_plot(self):
        self.x = []
        self.y = []
        self._prev_pwr = 0
        self._pm_dev = powermeter.PowerMeter(self.comboBox.currentText())
        self.timer.start()
        return


def main():
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
