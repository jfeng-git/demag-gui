from functools import partial
import numpy as np
import time
from time import sleep
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

        self.gain_mapping = {
            80: 0,
            110: 1,
            160: 2,
            230: 3,
            330: 4,
            490: 5,
            710: 6,
            1000: 7,
            1500: 8,
            2200: 9,
            3100: 10,
            4600: 11,
            6500: 12,
            9300: 13,
            14000: 14,
            20000: 15
        }
        self.B_interval_mapping = {
            '1s': 0, 
            '2s': 1, 
            '5s': 2, 
            '10s': 3, 
            '15s': 4, 
            '30s': 5, 
            '60s': 6, 
            '2min': 7, 
            '5min': 8, 
            '10min': 9, 
        }
        self.measure_before_read = False
        
        self.operationstate_valmap = {
            'Idel': 0,
            'Single': 1,
            'Auto': 2
        }
        self.add_parameter('M0',
                           label='M0',
                           get_cmd=self.get_M0,
                          )

        self.add_parameter('C',
                           label='Curie constant',
                           get_cmd='NMRCURIEC?',
                           set_cmd='NMRCURIEC {}',
                           get_parser=float
        )

        self.add_parameter('TmK',
                           label='measured TCurie',
                           get_cmd=self.get_TmK,
                           unit='mK',
                          )
        
        self.add_parameter('TmKCal',
                           label='calculated TCurie',
                           get_cmd=self.get_TmKCal,
                           unit='mK',
                          )

        self.add_parameter('Burst',
                           label='Burst number',
                           get_cmd=self.get_Burst,
                           set_cmd='NMRTXMIT {}',
                           get_parser=int
        )

        self.add_parameter('Gain',
                           label='NMR gain',
                           # get_cmd=self.get_gain,
                           get_cmd=self.get_Gain,
                           # set_cmd=self.set_gain,
                           set_cmd='NMRGAIN {}', 
                           val_mapping=self.gain_mapping
        )

        self.add_parameter('BurstAmp',
                           label='Burst amplitude',
                           get_cmd = self.get_BurstAmp,
                           set_cmd = self.set_BurstAmp
                          )
        
        self.add_parameter('event',
                           label='nmr event',
                           get_cmd=self.get_event,
                          )
        
        self.add_parameter('OperationState',
                           label='nmr operation state',
                           set_cmd=self.set_operationstate,
                           get_cmd=self.get_operationstate,
        )

        self.add_parameter('KnownT_A',
                           label='Known T for calibration A',
                           set_cmd=self.set_KnownT_A,
                           get_cmd=self.get_KnownT_A
        )

        self.add_parameter('KnownM0_A',
                           label='Known M0 for calibration A',
                           set_cmd=self.set_KnownM0_A,
                           get_cmd=self.get_KnownM0_A
        )

        self.add_parameter('CalBKnownT',
                           label='Known T for calibration B',
                           set_cmd='NMRCBKT{}',
                           get_cmd='NMRCBKT?',
                           get_parser=float
        )

        self.add_parameter('CalBRepeat',
                           label='Number of repeat for calibration B',
                           set_cmd='NMRCBREPT{}',
                           get_cmd='NMRCBREPT?',
                           get_parser=int
        )

        self.add_parameter('CalBInterval',
                           label='Interval for calibration B',
                           set_cmd='NMRCBITVL{}',
                           get_cmd='NMRCBITVL?',
                           val_mapping=self.B_interval_mapping
        )

        self.add_parameter('XRefRepeat',
                           label='Repeat for the transfer between setups',
                           set_cmd='NMRXFREPT {}',
                           get_cmd='NMRXFREPT?',
                           get_parser=int,
                          )

        self.add_parameter('XRefInterval',
                           label='Interval between measurements for the transfer',
                           get_cmd='NMRXFITVL?',
                           set_cmd='NMRXFITVL{}',
                           val_mapping=self.B_interval_mapping
                          )

        self.add_parameter('CS10Current',
                           label='current of CS-10, field current',
                           get_cmd="CSCURRENT?",
                           get_parser=float,
        )

        self.add_parameter('Background',
                           label='calculated background',
                           get_cmd=self.get_Background,
                           get_parser=float,
        )

    def CalibrationB(self, KnownT):
        interval = self.CalBInterval()
        if 's' in interval:
            interval = float(interval[:-1])
        else:
            interval = float(interval[:-3])*60
        repeat = self.CalBRepeat()
        wait_time = interval*repeat
        self.CalBKnownT(KnownT)
        self.ask('*OPC?')
        self.OperationState('Idel')
        print('calibration B started')
        self.write('NMRCBACTION1')
        sleep(wait_time+10)
        self.ask('*OPC?')
        print('calibration B ended')
        self.OperationState('Auto')

    def Transfer(self):
        interval = self.XRefInterval()
        if 's' in interval:
            interval = float(interval[:-1])
        else:
            interval = float(interval[:-3])*60
        repeat = self.XRefRepeat()
        wait_time = interval*repeat
        self.ask('*OPC?')
        self.OperationState('Idel')
        print('transfer started')
        self.write('NMRXFACTION1')
        sleep(wait_time+10)
        self.ask('*OPC?')
        print('transfer ended')
        # print('copy setup 2 to 1')
        # self.write('NMRCOPYSETUP2')
        print('use setup 2')
        self.write('NMRSETUP1')
        print('set back to Auto mode')
        self.OperationState('Auto')

    def CalibrationA(self, KnownT, KnownM0):
        self.KnownT_A(KnownT)
        self.KnownM0_A(KnownM0)
        self.write('NMRCACALC1')
    
    def get_M0(self):
        self.ask('*OPC?')
        s = self.ask('NMRMAGNA?')
        return float(s.split(';')[0])
        
    def get_TmK(self):
        self.ask('*OPC?')
        s = self.ask('NMRTCURIE?')
        return float(s.split(';')[0])
    
    def get_TmKCal(self):
        C = float(self.ask('NMRCURIEC?'))
        Bg = self.Background()
        M0 = self.M0()
        return C/(M0-Bg)
    
    def get_Burst(self):
        self.ask('*OPC?')
        s = self.ask('NMRTXMIT?')
        return float(s.split(';')[0])

    def get_Gain(self):
        self.ask('*OPC?')
        s = self.ask('NMRGAIN?')
        return float(s.split(';')[0])
    
    def get_Background(self):
        self.ask('*OPC?')
        s = self.ask('NMRBKG?')
        return float(s.split(';')[0])

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


    
    def set_operationstate(self, val):
        if not val in ['Idel', 'Single', 'Auto']:
            print('input should be Idel, Single or Auto')
        
        self.write(f'NMROPSTATE{self.operationstate_valmap[val]}')
    
    def get_operationstate(self):
        return  self.ask('NMROPSTATE?')

    def set_KnownM0_A(self, val):
        self.write(f'NMRCAKM {val}')
        
    def set_KnownT_A(self, val):
        self.write(f'NMRCAKT {val}')

    def get_KnownM0_A(self):
        s = self.ask('NMRCAKM?')
        if ',' in s:
            s = s.split(' ')[-1]
        return float(s)

    def get_KnownT_A(self):
        s = self.ask('NMRCAKT?')
        if ',' in s:
            s = s.split(' ')[-1]
        return float(s)

    def set_Burst(self, val):
        self.write(f'NMRTXMIT {int(val)}')

    def get_Burst(self):
        return int(self.ask(f'NMRTXMIT?').split(';')[0])

    def get_BurstAmp(self):
        return 40*float(self.ask('NMRTXAMPL?'))/256

    def set_BurstAmp(self, val):
        self.write(f'NMRTXAMPL {int(val)}')
