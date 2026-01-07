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



class NMR(VisaInstrument):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)
        self.event_mapping = {
            7: '0',
            6: 'MR measurement was completed',
            5: '0',
            4: '0',
            3: 'Noise floor warning was issued',
            2: 'ADC overload was detected',
            1: 'Transfer of calibration procedure was completed',
            0: 'Calibration procedure was completed',
        }
        self.add_parameter('M0',
                           label='M0',
                           get_cmd=self.get_M0,
                          )

        self.add_parameter('TmK',
                           label='TCurie',
                           get_cmd=self.get_TmK,
                           unit='K',
                          )

        self.add_parameter('event',
                           label='nmr event',
                           get_cmd=self.get_event,
                          )
    def get_M0(self):
        return float(self.ask('NMRMAGNA?'))
        
    def get_TmK(self):
        return float(self.ask('NMRTCURIE?'))

    def get_event(self):
        """
        This register is cleared when it is read. Also *CLS clears the NMREVENT register.
        event mapping:
        7: 0
        6: MR measurement was completed
        5: 0
        4: 0
        3: Noise floor warning was issued
        2: ADC overload was detected
        1: Transfer of calibration procedure was completed
        0: Calibration procedure was completed
        """
        return int(self.ask('NMREVENT?'))


    
    SNAP_PARAMETERS = {'M0': '1',
                       'T': '2',
                       }
