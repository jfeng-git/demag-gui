from qcodes import VisaInstrument
from qcodes.utils.validators import Numbers, Ints, Enum


class MercuryITC(VisaInstrument):
    """
    Oxford MercuryITC (Heliox)
    """


    def __init__(self, name, address, reset=True, device_clear=True,  **kwargs):
        super().__init__(name, address,  terminator='\n', **kwargs)

        self.add_parameter(name='temperature',
                           label='temperature',
                           unit='K',
                           get_cmd=self._get_temperature,
                           set_cmd= self._set_temperature,
                           #get_parser=lambda s : float(s[1:].split(':')[-1][:-1]),
                           vals=Numbers(min_value=0,
                                        max_value=300))
                                        
	### manually added
        self.add_parameter(name='setpoint',
                           label='temperature loop setpoint',
                           unit='K',
                           get_cmd='READ:DEV:DB7.T1:TEMP:LOOP:TSET',
                           set_cmd= self._set_temperature,
                           get_parser=lambda s : float(s[1:].split(':')[-1][:-1]),
                           vals=Numbers(min_value=0,
                                        max_value=300))
	### manually added

        self.add_function('reset', call_cmd='*RST')

 
    def _set_temperature(self, temperature):
        """ Set the temperature """
        if temperature < 0:
            temperature = 0
        self.ask_raw('SET:DEV:DB7.T1:TEMP:LOOP:TSET:{}'.format(temperature))
        
    def _get_temperature(self):
        T7 = float(self.ask("READ:DEV:DB7.T1:TEMP:SIG:TEMP?").split(":")[-1][:-1])
        T8 = float(self.ask("READ:DEV:DB8.T1:TEMP:SIG:TEMP?").split(":")[-1][:-1])
        if T7 > 1.2:
            return T7
        return T8