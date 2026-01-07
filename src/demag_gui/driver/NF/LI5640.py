from functools import partial
import numpy as np
import time
import matplotlib.pyplot as plt
from IPython.display import clear_output

from qcodes import VisaInstrument
from qcodes.instrument.parameter import ArrayParameter
from qcodes.utils.validators import Numbers, Ints, Enum, Strings

from typing import Tuple


class LI5640(VisaInstrument):
    """
    This is the qcodes driver for the Stanford Research Systems NF LI5640
    Lock-in Amplifier
    """

    _VOLT_TO_N = {0.05: 1, 0.5: 1, 5: 2}
    _N_TO_VOLT = {v: k for k, v in _VOLT_TO_N.items()}

    _CURR_TO_N = {2e-15:    0, 5e-15:    1, 10e-15:  2,
                  20e-15:   3, 50e-15:   4, 100e-15: 5,
                  200e-15:  6, 500e-15:  7, 1e-12:   8,
                  2e-12:    9, 5e-12:   10, 10e-12:  11,
                  20e-12:  12, 50e-12:  13, 100e-12: 14,
                  200e-12: 15, 500e-12: 16, 1e-9:    17,
                  2e-9:    18, 5e-9:    19, 10e-9:   20,
                  20e-9:   21, 50e-9:   22, 100e-9:  23,
                  200e-9:  24, 500e-9:  25, 1e-6:    26}
    _N_TO_CURR = {v: k for k, v in _CURR_TO_N.items()}

    _VOLT_ENUM = Enum(*_VOLT_TO_N.keys())
    _CURR_ENUM = Enum(*_CURR_TO_N.keys())

    _AMPL_TO_N = {50e-3: 0,
                  500e-3: 1,
                  5: 2}

    _DOUT1_TO_N = {'X': 0,
                   'R': 1,
                   'NOISE': 2,
                   'AUX IN1': 3}
    _N_TO_DOUT1 = {v: k for k, v in _DOUT1_TO_N.items()}

    _DOUT2_TO_N = {'Y': 0,
                   'THETA': 1,
                   'NOISE': 2,
                   'AUX IN1': 3}
    _N_TO_DOUT2 = {v: k for k, v in _DOUT2_TO_N.items()}

    _INPUT_CONFIG_TO_N = {
        'a': 0,
        'a-b': 1,
        'I 1M': 2,
        'I 100M': 3,
    }

    _N_TO_INPUT_CONFIG = {v: k for k, v in _INPUT_CONFIG_TO_N.items()}

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        # Reference and phase
        '''
        self.add_parameter('reference_source',
                           label='Reference source',
                           get_cmd='RSCR?',
                           set_cmd='RSCR {}',
                           val_mapping={
                               'REF_IN': 0,
                               'INT_OSC': 1,
                               'SIGNAL': 2,
                           },
                           vals=Enum('REF_IN', 'INT_OSC', 'SIGNAL'))
        '''

        self.add_parameter('phase',
                           label='Phase',
                           get_cmd='PHAS?',
                           get_parser=float,
                           set_cmd='PHAS {:.2f}',
                           unit='deg',
                           vals=Numbers(min_value=-360, max_value=729.99))

        # output frequency and amplitude
        self.add_parameter('frequency',
                           label='Frequency',
                           get_cmd='FREQ?',
                           get_parser=float,
                           set_cmd='FREQ {:.4f}',
                           unit='Hz',
                           vals=Numbers(min_value=1e-3, max_value=102e3))

        def change_AMPL(s):
            for ii, key in enumerate(self._AMPL_TO_N.keys()):
                if float(s) < key:
                    break
            self.write('AMPL {:.4f},{}'.format(s, ii))

        def get_AMPL(s):
            return float(s.split(',')[0])

        self.add_parameter('amplitude',
                           label='Amplitude',
                           get_cmd='AMPL?',
                           get_parser=get_AMPL,
                           set_cmd=change_AMPL,
                           unit='V',
                           vals=Numbers(min_value=1e-3, max_value=5.)
                           )

        # set display data
        def change_dout1_disp(s):
            if s not in self._DOUT1_TO_N.keys():
                print('undefined key, set to X')
                self.write('DDEF1, 0')
            else:
                self.write('DDEF1, {}'.format(self._DOUT1_TO_N[s.upper()]))

        def change_dout2_disp(s):
            if s not in self._DOUT2_TO_N.keys():
                print('undefined key, set to Y')
                self.write('DDEF2, 0')
            else:
                self.write('DDEF2, {}'.format(self._DOUT2_TO_N[s.upper()]))

        self.add_parameter('DOUT1_display',
                           label='DOUT1_DIS',
                           get_cmd='DDEF? 1',
                           set_cmd=change_dout1_disp,
                           unit='a.u.')

        self.add_parameter('DOUT2_display',
                           label='DOUT2_DIS',
                           get_cmd='DDEF? 2',
                           set_cmd=change_dout2_disp,
                           unit='a.u.')

        # Data transfer
        def parse_DOUT1_get(s):
            parts = s.split(',')
            return float(parts[0])
        
        def parse_DOUT2_get(s):
            parts = s.split(',')
            return float(parts[1])
        
        self.add_parameter('DOUT1',
                           get_cmd='DOUT?',
                           get_parser=parse_DOUT1_get,
                           unit='a. u. ')

        self.add_parameter('DOUT2',
                           get_cmd='DOUT?',
                           get_parser=parse_DOUT2_get,
                           unit='a. u. ')

        self.add_parameter('DOUTs',
                           get_cmd=self._get_DOUTs,
                           unit='a. u. ')

    def _get_DOUTs(self):
        s = self.ask('DOUT?')
        parts = s.split(',')
        return float(parts[0]), float(parts[1])

        # Interface
        self.add_function('reset', call_cmd='*RST')

    SNAP_PARAMETERS = {'DATA1': '1',
                       'DATA2': '2',
                       'FREQ': '3',
                       'SENSITIVITY': '4',
                       'OVERLEVEL': '5'}

    def snap(self, *parameters: str) -> Tuple[float, ...]:
        """
        :param parameters: *parameters
            from 1 to 6 strings of names of parameters for which the values are requested.
            inlcuding 'DATA1', 'DATA2', 'FREQ', 'SENSITIVITY', 'OVERLEVEL'.
        :return: A tuple of floating point values in the same order as requested.
        """
        for name in parameters:
            if name.upper() not in self.SNAP_PARAMETERS:
                raise KeyError(f'{name} is an unknown parameter. Refer'
                               f' to `SNAP_PARAMETERS` for a list of valid'
                               f' parameter names')

        p_ids = [self.SNAP_PARAMETERS[name.upper()] for name in parameters]
        output = self.ask(f'?ODT {",".join(p_ids)}')

        return tuple(float(val) for val in output.split(','))

    def optimize_frequency(self, freq_start=3, freq_stop=70, freq_step=0.02, N=10):
        digit = 1
        while freq_step%1 != 0:
            freq_step = freq_step*10
            digit = digit*10
        frequencies = np.arange(freq_start*digit, freq_stop*digit, freq_step)/digit
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
                time.sleep(3/freq)
                freqs_meas.append(self.frequency())
                temp1, temp2 = self.DOUTs()
                DOUT1.append(temp1)
                DOUT2.append(temp2)
            mean1 = np.array(DOUT1[jj*N:jj*N+N]).mean()
            rmse1.append(np.sqrt(sum((np.array(DOUT1[jj*N:jj*N+N]) - mean1)**2)/N))
            mean2 = np.array(DOUT2[jj*N:jj*N+N]).mean()
            rmse2.append(np.sqrt(sum((np.array(DOUT2[jj*N:jj*N+N]) - mean2)**2)/N))
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
                if round(int(num*dig))%10 != 0:
                    break
            num = int(num*dig)
            if all(num % i != 0 for i in range(2, int(np.sqrt(num) + 1))):
                prime_list.append(num/dig)
        print(prime_list)
        return np.array(prime_list)

