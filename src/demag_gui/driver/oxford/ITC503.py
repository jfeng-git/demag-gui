from qcodes import VisaInstrument
from qcodes.utils.validators import Numbers, Ints, Enum


class ITC503(VisaInstrument):
    """
    Oxford ITC503 Temperature Controller (VTIs and Heliox)
    """


    def __init__(self, name, address, reset=True, device_clear=True,  **kwargs):
        super().__init__(name, address,  terminator='\r', **kwargs)

        self.add_parameter(name='temperature',
                           label='temperature',
                           unit='K',
                           get_cmd='R1',
                           set_cmd= self._set_temperature,
                           get_parser=lambda s : float(s[1:]),
                           vals=Numbers(min_value=0,
                                        max_value=300))
	### manually added
        self.add_parameter(name='temperature_He3',
                           label='temperature_He3',
                           unit='K',
                           get_cmd='R3',
                           set_cmd= self._set_temperature,
                           get_parser=lambda s : float(s[1:]),
                           vals=Numbers(min_value=0,
                                        max_value=300))

        self.add_parameter(name='setpoint',
                           label='setpoint',
                           unit='K',
                           get_cmd='R0',
                           set_cmd= self._set_temperature,
                           get_parser=lambda s : float(s[1:]),
                           vals=Numbers(min_value=0,
                                        max_value=300))   

        self.add_parameter(name='heater_mode',
                           label='heater_mode',
                           get_cmd='X',
                           val_mapping={
                               'auto': 1,
                               'manual': 0,
                           },
                           set_cmd= self._set_heater_mode,
                           get_parser=lambda s : float(s[3]))

        self.add_parameter(name='heater_output',
                           label='heater_output',
                           get_cmd='R5',
                           get_parser=lambda s : float(s[1:]),
                           set_cmd= self._set_heater_output)
                           
        self.add_parameter(name='P',
                           label='Proportional gain',
                           get_cmd='R8',
                           set_cmd= self._set_P,
                           get_parser=lambda s : float(s[1:]))

        self.add_parameter(name='I',
                           label='Integration time',
                           get_cmd='R9',
                           set_cmd= self._set_I,
                           get_parser=lambda s : float(s[1:]))

        self.add_parameter(name='D',
                           label='Derivative time',
                           get_cmd='R10',
                           set_cmd= self._set_D,
                           get_parser=lambda s : float(s[1:]))


        self.add_parameter(name='heater_sensor',
                           label='heater_sensor',
                           get_cmd='X',
                           vals=Numbers(min_value=0,
                                        max_value=3),
                           set_cmd= self._set_heater_sensor,
                           get_parser=lambda s : int(s[10]))

        self.add_function('reset', call_cmd='*RST')
        self.ask_raw('C3')

 
    def _set_temperature(self, temperature):
        """ Set the temperature """
        if temperature < 0:
            temperature = 0
        self.ask_raw('T {}'.format(temperature))
        
    def _set_heater_mode(self, mode):
        """ Set the heater mode """
        self.ask_raw('A{}'.format(mode))

    def _set_P(self, mode):
        self.ask_raw('P{}'.format(mode))

    def _set_heater_output(self, output):
        self.ask_raw('O{}'.format(output))
    
    def _set_I(self, mode):
        self.ask_raw('I{}'.format(mode))
        
    def _set_D(self, mode):
        self.ask_raw('D{}'.format(mode))
        
    def _set_heater_sensor(self, sensor):
        """ Set the heater mode """
        self.ask_raw('H{}'.format(sensor))
