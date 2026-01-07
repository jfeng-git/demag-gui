from functools import partial
import numpy as np
import time
import matplotlib.pyplot as plt
from IPython.display import clear_output

from qcodes import VisaInstrument
from qcodes.instrument.parameter import ArrayParameter
from qcodes.utils.validators import Numbers, Ints, Enum, Strings

from typing import Tuple


class AH2500A(VisaInstrument):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        self.add_parameter('C',
                           label='Capacitance',
                           get_cmd=self.read_C,
                           unit='pF',
                          )

        # output frequency and amplitude
        self.add_parameter('L',
                           label='Loss',
                           get_cmd=self.read_L,
                          )
        
        # Interface
        self.add_function('reset', call_cmd='*RST')

    def read_C(self):
        result = self.ask('SI?')
        return float

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

