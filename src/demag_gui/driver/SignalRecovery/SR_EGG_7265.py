import numpy as np
from qcodes import VisaInstrument
from qcodes.utils.validators import Numbers, Ints, Enum


class SR_EGG_7265(VisaInstrument):
    """
    SignalRecovery / EG&G 7265 Lockin Amplifier
    """
    _VOLT_TO_N = {2e-9:1,5e-9:2,10e-9:3,20e-9:4,50e-9:5,100e-9:6,200e-9:7,500e-9:8,
                     1e-6:9,2e-6:10,5e-6:11,10e-6:12,20e-6:13,50e-6:14,100e-6:15,200e-6:16,500e-6:17,
                     1e-3:18,2e-3:19,5e-3:20,10e-3:21,20e-3:22,50e-3:23,100e-3:24,200e-3:25,500e-3:26,
                     1:27}
    
    _N_TO_VOLT = {v: k for k, v in _VOLT_TO_N.items()}

    def __init__(self, name, address, reset=True, device_clear=True,  **kwargs):
        super().__init__(name, address,  terminator='\n', **kwargs)
        self.add_parameter(name='sensitivity',
                           label='Sensitivity',
                           get_cmd='SEN.?',
                           set_cmd='SEN {}',
                           get_parser=float,
                           set_parser=self._set_sensitivity)
        self.add_parameter(name='input_mode',
                           label='voltage_input_mode',
                           get_cmd='VMODE?',
                           set_cmd='VMODE {}',
                           val_mapping={'GND': 0,'A' : 1,'-B':2,'A-B':3 })
        self.add_parameter(name='amplitude',
                           label='Internal Oscillator Amplitude',
                           get_cmd='OA.',
                           set_cmd='OA. {}',
                           get_parser=float)
        self.add_function('auto_sensitivity', call_cmd='AS')
        self.add_parameter(name='time_constant',
                           label='Time constant',
                           unit='s',
                           get_cmd='TC',
                           set_cmd='TC {}',
                           val_mapping={10e-6: 0, 20e-6: 1,
                                        40e-6: 2, 80e-6: 3,
                                        160e-6: 4, 320e-6: 5,
                                        640e-6: 6, 5e-3: 7,
                                        10e-3: 8, 20e-3: 9,
                                        50e-3: 10, 100e-3: 11,
                                        200e-3: 12, 500e-3: 13,
                                        1: 14, 2: 15,
                                        5: 16, 10: 17,
                                        20: 18, 50: 19,
                                        100: 20, 200: 21,500:22,1e3:23,2e3:24,5e3:25,10e3:26,20e3:27,50e3:28,100e3:29})
        self.add_parameter('X',
                           label='In-phase Magnitude',
                           get_cmd='X.',
                           get_parser=float,
                           unit='V')
        self.add_parameter('Y',
                           label='Out-Of-phase Magnitude',
                           get_cmd='Y.',
                           get_parser=float,
                           unit='V')
        self.add_parameter('R',
                           label='Magnitude',
                           get_cmd='MAG.',
                           get_parser=float,
                           unit='V')
        self.add_parameter('THETA',
                           label='Phase Angle',
                           get_cmd='PHA.',
                           get_parser=float,
                           unit='V')
        self.add_parameter('XY',
                           label='X and Y',
                           get_cmd='XY.',
                           get_parser=lambda x: list(map(float,x.split(","))),
                           unit='V')

        self.add_function('reset', call_cmd='*RST')


    def _get_sensitivity(self, s):
        return self._N_TO_VOLT[int(s)]

    def _set_sensitivity(self, s):
        return(self._VOLT_TO_N.get(s) or self._VOLT_TO_N[min(self._VOLT_TO_N.keys(), key = lambda key: abs(key-s))]+1)

