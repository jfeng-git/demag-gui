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


class Model715(VisaInstrument):
    

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        self.add_parameter('P',
                           label='pressure',
                           get_cmd=self.read_P,
                           unit='MPa',
                          )

    def read_P(self):
        return float(self.ask('*0100P3')[5:-2])/1000

    SNAP_PARAMETERS = {'P': '1',}

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

