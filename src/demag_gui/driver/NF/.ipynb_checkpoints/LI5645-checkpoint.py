from functools import partial
import numpy as np
import matplotlib.pyplot as plt
from numpy.distutils.misc_util import get_cmd
from qcodes import VisaInstrument
from qcodes.instrument.parameter import ArrayParameter
from qcodes.utils.validators import Numbers, Ints, Enum, Strings
from typing import Tuple
import time
from IPython.display import clear_output


class LI5645(VisaInstrument):
    """
    This is the qcodes driver for the Stanford Research Systems SR830
    Lock-in Amplifier
    """

    _VOLT_TO_N = {2e-9: 0, 5e-9: 1, 10e-9: 2,
                  20e-9: 3, 50e-9: 4, 100e-9: 5,
                  200e-9: 6, 500e-9: 7, 1e-6: 8,
                  2e-6: 9, 5e-6: 10, 10e-6: 11,
                  20e-6: 12, 50e-6: 13, 100e-6: 14,
                  200e-6: 15, 500e-6: 16, 1e-3: 17,
                  2e-3: 18, 5e-3: 19, 10e-3: 20,
                  20e-3: 21, 50e-3: 22, 100e-3: 23,
                  200e-3: 24, 500e-3: 25, 1: 26}
    _N_TO_VOLT = {v: k for k, v in _VOLT_TO_N.items()}

    _CURR_TO_N = {2e-15: 0, 5e-15: 1, 10e-15: 2,
                  20e-15: 3, 50e-15: 4, 100e-15: 5,
                  200e-15: 6, 500e-15: 7, 1e-12: 8,
                  2e-12: 9, 5e-12: 10, 10e-12: 11,
                  20e-12: 12, 50e-12: 13, 100e-12: 14,
                  200e-12: 15, 500e-12: 16, 1e-9: 17,
                  2e-9: 18, 5e-9: 19, 10e-9: 20,
                  20e-9: 21, 50e-9: 22, 100e-9: 23,
                  200e-9: 24, 500e-9: 25, 1e-6: 26}
    _N_TO_CURR = {v: k for k, v in _CURR_TO_N.items()}

    _VOLT_ENUM = Enum(*_VOLT_TO_N.keys())
    _CURR_ENUM = Enum(*_CURR_TO_N.keys())

    _INPUT_CONFIG_TO_N = {
        'a': 0,
        'a-b': 1,
        'I 1M': 2,
        'I 100M': 3,
    }

    _N_TO_INPUT_CONFIG = {v: k for k, v in _INPUT_CONFIG_TO_N.items()}

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        # Data transfer
        self.add_parameter('idn',
                           get_cmd=('*IDN?'))

        self.add_parameter('DOUT1',
                           get_cmd=':FETCh?',
                           get_parser=self.parse_DOUT1_get,
                           unit='a. u. ')

        self.add_parameter('DOUT2',
                           get_cmd=':FETCh?',
                           get_parser=self.parse_DOUT2_get,
                           unit='a. u. ')
        
        self.add_parameter('DOUTs',
                           get_cmd=self._get_DOUTs,
                           unit='a. u. ')
        
        self.add_parameter('amplitude',
                           get_cmd=':SOURce:VOLTage:LEVel:IMMediate:AMPLitude?',
                           get_parser=float, 
                           set_cmd=self._set_amplitude,
                           unit='V')

        self.add_parameter('frequency',
                           get_cmd=':SOURce:FREQuency1:CW?',
                           get_parser=float,
                           set_cmd=self._set_frequency,
                           unit='Hz')

        self.add_parameter('voltage_sense_range',
                           get_cmd=':SENSe:VOLTage:AC:RANGe?',
                           get_parser=float,
                           set_cmd=self._set_voltage_sense_range,
                           unit='V')

        self.add_parameter('voltage_sense_autorange',
                          get_cmd=':SENSe:VOLTage:AC:RANGe:AUTO?',
                          set_cmd=self._set_voltage_sense_autorange,
                          val_mapping={'0': 'ON', '1': 'OFF'})

        self.add_parameter('dynamic_reserve',
                           get_cmd=':DRES?',
                           set_cmd=self._set_dynamic_reserve)

        self.add_parameter('slop',
                           get_cmd=':FILT:SLOP?',
                           set_cmd=self._set_slop)

        # Interface
        self.add_function('reset', call_cmd='*RST')
        self.add_function('voltage_sense_autorange_once', call_cmd=':SENSe:VOLTage:AC:RANGe:AUTO:ONCE')
        self.add_function('initialize', call_cmd=self.initialize)

    def _set_amplitude(self, value):
        self.write(':SOUR:VOLT {}'.format(value))

    def _set_frequency(self, value):
        self.write(':SOUR:FREQ:CW {:.3f}'.format(value))

    def _set_voltage_sense_range(self, s):
        '''
        to make sure that the range is set correctly, using a string as input
        TO: use a value-string mapping
        '''
        self._set_voltage_sense_autorange(0)
        self.write(':SENSe:VOLTage:AC:RANGe:UPP ' + s)

    def _set_voltage_sense_autorange(self, value):
        self.write(':SENSe:VOLTage:AC:RANGe:AUTO {}'.format(value))

    def parse_DOUT1_get(self, s):
        parts = s.split(',')
        return float(parts[0])

    def parse_DOUT2_get(self, s):
        parts = s.split(',')
        return float(parts[1])

    def _get_DOUTs(self):
        s = self.ask(':FETCh?')
        parts = s.split(',')
        return float(parts[0]), float(parts[1])

    def _set_dynamic_reserve(self, s):
        dymamic_values = ['HIGH', 'LOW', 'MED']
        if s.upper() in dymamic_values:
            self.write(':DRES {}'.format(dymamic_values))
        else:
            print('allowed values are {}'.format(dymamic_values))

    def _set_slop(self, value):
        slops = ['6', '12', '18', '24']
        if str(int(value)) in slops:
            self.write(':FILT:SLOP {}'.format(int(value)))
        else:
            print('slop value should be {}'.format(slops))

    def initialize(self):
        """
        set the lock in to a state that works for most of the measurements
        :return:
        """
        dynamic = 'LOW'
        slop = '24'
        amplitude = 0.01
        sense_source = 'INIT'
        sense_range = '3'

        self.write(':DRES {}'.format(dynamic))
        self.write(':FILT:SLOP {}'.format(slop))
        self.write(':SOURce:VOLTage:LEVel:IMMediate:AMPLitude {}'.format(amplitude))
        self.write(':SENSe:ROSCillator:SOURce {}'.format(sense_source))
        self.write(':SENSe:VOLTage:AC:RANGe {}'.format(sense_range))

    def optimize_frequency(self, freq_start=3, freq_stop=70, freq_step=0.02, N=10):
        digit = 1
        while freq_step % 1 != 0:
            freq_step = freq_step * 10
            digit = digit * 10
        frequencies = np.arange(freq_start * digit, freq_stop * digit, freq_step) / digit
        prime_frequencies = self._prime_frequencies(frequencies)
        rmse1 = []
        rmse2 = []
        freqs_meas = []
        DOUT1 = []
        DOUT2 = []
        fig, [ax1, ax2, ax3, ax4] = plt.subplots(nrows=4, ncols=1, figsize=(3, 9))
        for jj, freq in enumerate(prime_frequencies):
            self.frequency(freq)
            for ii in range(N):
                time.sleep(3 / freq)
                freqs_meas.append(self.frequency())
                temp1, temp2 = self.DOUTs()
                DOUT1.append(temp1)
                DOUT2.append(temp2)
            mean1 = np.array(DOUT1[jj * N:jj * N + N]).mean()
            rmse1.append(np.sqrt(sum((np.array(DOUT1[jj * N:jj * N + N]) - mean1) ** 2) / N))
            mean2 = np.array(DOUT2[jj * N:jj * N + N]).mean()
            rmse2.append(np.sqrt(sum((np.array(DOUT2[jj * N:jj * N + N]) - mean2) ** 2) / N))
            clear_output()
            print('{:.3f}, {}/{} finished'.format(freq, jj, len(prime_frequencies)))
        ax1.plot(freqs_meas, DOUT1, '.-')
        ax1.set_title('Reading of channel 1')
        ax3.plot(freqs_meas, DOUT2, '.-')
        ax3.set_title('Reading of channel 2')
        ax2.plot(prime_frequencies, rmse1, '.-')
        ax2.set_title('Channel 1 rmse')
        ax4.plot(prime_frequencies, rmse2, '.-')
        ax4.set_title('Channel 2 rmse')
        fig.tight_layout()
        freq_optimized = prime_frequencies[rmse1.index(min(rmse1))]
        self.frequency(freq_optimized)
        print('frequency is set to {}'.format(freq_optimized))
        plt.figure()
        plt.plot(freqs_meas, 'd-')
        return {'frequency': prime_frequencies,
                'DOUT1': DOUT1,
                'DOUT2': DOUT2,
                'rmse1': rmse1,
                'rmse2': rmse2}

    def _prime_frequencies(self, frequencies):
        digs = [1000, 100, 10, 1]
        prime_list = []
        for num in frequencies:
            for dig in digs:
                if round(int(num * dig)) % 10 != 0:
                    break
            num = int(num * dig)
            if all(num % i != 0 for i in range(2, int(np.sqrt(num) + 1))):
                prime_list.append(num / dig)
        print(prime_list)
        return np.array(prime_list)

