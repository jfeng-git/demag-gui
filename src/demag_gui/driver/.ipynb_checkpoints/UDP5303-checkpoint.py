from functools import partial
import numpy as np
import time
import matplotlib.pyplot as plt
from IPython.display import clear_output

from qcodes import VisaInstrument
from qcodes.instrument.parameter import ArrayParameter
from qcodes.utils.validators import Numbers, Ints, Enum, Strings
import re
from typing import Tuple


class UDP5303(VisaInstrument):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)
    
        self.add_parameter('I',
                           label='Current',
                           unit='A',
                           get_cmd=self.get_I,
                           set_cmd=self.set_I,
                           )

        self.add_parameter('Output',
                           label='output',
                           get_cmd=self.get_output,
                           set_cmd=self.set_output,
                           )

    def get_I(self):
        return float(self.ask('CURR?'))

    def set_I(self, val):
        self.write(f'CURR {val}')

    def get_output(self):
        val_map = {1:'on', 0:'off'}
        return val_map[int(self.ask('OUTP?'))]

    def set_output(self, val):
        val_map = {'on': 1, 'off': 0}
        if not val in ['on', 'off']:
            print('input should be on, off')
            return 0
        else:
            # print(f'OUTP {val_map[val]}')
            self.write(f'OUTP {val_map[val]}')
        
    # def get_L(self):
    #     s = self.ask('CO')
    #     return float(re.findall(r'\d+\.\d+', s)[1])

    # def get_V(self):
    #     s = self.ask('CO')
    #     return float(re.findall(r'\d+\.\d+', s)[2])

    # def get_C_L(self):
    #     s = self.ask('CO')
    #     return float(re.findall(r'\d+\.\d+', s)[0]), float(re.findall(r'\d+\.\d+', s)[1])

    # def get_C_L_V(self):
    #     s = self.ask('CO')
    #     return float(re.findall(r'\d+\.\d+', s)[0]), float(re.findall(r'\d+\.\d+', s)[1]), float(re.findall(r'\d+\.\d+', s)[2])

    # def set_V(self, v):
    #     self.write(f'V {v}')

    # def set_Average(self, val):
    #     self.write(f'AV {val}')

    # def get_Average(self):
    #     return int(self.ask('SH AV').split('=')[-1][:-1])

    SNAP_PARAMETERS = {'I': '1',
                       'V': '2',}