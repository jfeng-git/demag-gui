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
from time import sleep

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
        # Read the current value
        max_retries = 100
        
        for _ in range(max_retries):
            try:
                s = float(self.ask('CURR?'))
                break
            except:
                # wait 0.3s if failed
                print('failed in reading UDP5303 current \n')
                sleep(0.3)
        else:  
            raise Exception(f"Failed after {max_retries} attempts while self.ask('CO') ")
        return s

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
        
    def set_HS(self, status, ts=1, step=0.002, actions=[]):
        status = status.lower()
        ts = max([ts, 0.1])
        if not status in ['on', 'off']:
            print('input should be on or off')
            return 0
        I_vals = np.arange(0, 0.501, step)
        
        if status == 'off':
            I_vals = I_vals[::-1]

        I_cv = self.I()
        I_ind = abs(I_vals - I_cv).argmin()

        for I in I_vals[I_ind:]:

            self.I(I)
            sleep(ts)
            print(f'Heater current {self.I()}', end='\r')
            if len(action) == 0:
                sleep(0.1)
            for action in actions:
                action()
        print(f'Heater current {self.I()}')