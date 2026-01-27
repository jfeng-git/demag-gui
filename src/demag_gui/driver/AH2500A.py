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

# from MCT_Callibration import MCT_calculator
# mct = MCT_calculator()


class AH2500A(VisaInstrument):
    def __init__(self, name, address, initiate_voltage=None, **kwargs):
        super().__init__(name, address, **kwargs)

        self.add_parameter('C',
                           label='Capacitance',
                           get_cmd=self.get_C,
                           unit='pF',
                          )

        # self.add_parameter('TmK',
        #                    label='calculated temperature',
        #                    get_cmd=self.get_TmK,
        #                    unit='mK',
        #                   )
        
        # output frequency and amplitude
        self.add_parameter('L',
                           label='Loss',
                           get_cmd=self.get_L,
                          )

        self.add_parameter('V',
                           label='Voltage',
                           get_cmd=self.get_V,
                           set_cmd=self.set_V
                          )
        
        self.add_parameter('C_L',
                           label='capacitance and Loss',
                           get_cmd=self.get_C_L,
                          )

        self.add_parameter('C_L_V',
                           label='capacitance and Loss',
                           get_cmd=self.get_C_L_V,
                          )

        self.add_parameter('Average',
                           label='averaging',
                           get_cmd=self.get_Average,
                           set_cmd=self.set_Average,
                          )
        
        # Interface
        self.add_function('reset', call_cmd='*RST')

        if initiate_voltage is not None:
            self.V(initiate_voltage)
            time.sleep(0.1)
            self._read_cv()
            print(f'voltage set to {self.V()}')
            self.Average(4)
            self._read_cv()
            print(f'averaging set to {self.Average()}')
        

    def _read_cv(self):
        # Read the current value
        max_retries = 5
        for _ in range(max_retries):
            try:
                s = self.ask('CO')
                break
            except:
                print('failed reading capacitance\n')
                pass
        else:  
            raise Exception(f"Failed after {max_retries} attempts while self.ask('CO') ")
        
        # convert to values
        self.C_cv = 0
        while self.C_cv == 0:
            s = self.ask('CO')
            self.C_cv, self.L_cv, self.V_cv = float(re.findall(r'\d+\.\d+', s)[0]), float(re.findall(r'\d+\.\d+', s)[1]), float(re.findall(r'\d+\.\d+', s)[2])
        return [self.C_cv, self.L_cv, self.V_cv]
        
    def get_C(self):
        return self._read_cv()[0]

    def get_L(self):
        return self.L_cv

    def get_V(self):
        return self.V_cv

    def get_C_L(self):
        return self._read_cv()[:1]

    def get_C_L_V(self):
        return self._read_cv()

    def set_V(self, v):
        self.write(f'V {v}')

    def set_Average(self, val):
        self.write(f'AV {val}')

    def get_Average(self):
        return int(self.ask('SH AV').split('=')[-1][:-1])

    SNAP_PARAMETERS = {'C': '1',
                       'L': '2',
                       'V': '3'
                       }

    # def snap(self, *parameters: str) -> Tuple[float, ...]:
    #     """
    #     :param parameters: *parameters
    #         from 1 to 6 strings of names of parameters for which the values are requested.
    #         inlcuding 'DATA1', 'DATA2', 'FREQ', 'SENSITIVITY', 'OVERLEVEL'.
    #     :return: A tuple of floating point values in the same order as requested.
    #     """
    #     for name in parameters:
    #         if name.upper() not in self.SNAP_PARAMETERS:
    #             raise KeyError(f'{name} is an unknown parameter. Refer'
    #                            f' to `SNAP_PARAMETERS` for a list of valid'
    #                            f' parameter names')

    #     p_ids = [self.SNAP_PARAMETERS[name.upper()] for name in parameters]
    #     output = self.ask(f'?ODT {",".join(p_ids)}')

    #     return tuple(float(val) for val in output.split(','))

