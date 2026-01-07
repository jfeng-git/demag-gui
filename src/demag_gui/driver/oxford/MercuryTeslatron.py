from qcodes import VisaInstrument
from qcodes.utils.validators import Numbers, Ints, Enum
import time


class MercuryITC_Teslatron(VisaInstrument):
    """
    Combined driver for controlling a Teslatron, i.e. a MercuryIPS and two MercurzITCs for the VTI and the Heliox.
    Aug 2023, 1st version: This is for reading the VTI Mercury as of now, not the one for Heliox.
    230823: changed to a two-in-one driver for both VTI and Heliox operation
    """


    def __init__(self, name, address, mode='heliox', Temperature_Switch_High_Low=8, reset=True, device_clear=True,  **kwargs):
        super().__init__(name, address,  terminator='\n', **kwargs)
        """Initialize a connection to MercuryITC for Teslatron operation.

        Args:
            name (str)    : name of the instrument
            address (str) : instrument address, eg 'TCPIP0::192.168.0.5::7020::SOCKET'
            mode (str) : 'heliox' for operating a HelioxVL insert via a dedicated MercuryITC. 'vti' for operating with a VTI dedicated ITC. Note that the expansion slot numbers are different.
        """
        
        
        self._mode = mode
        self._Temperature_Switch_High_Low = Temperature_Switch_High_Low
        
        self.add_parameter(name='TempVTI',
                           label='Temperature VTI',
                           unit='K',
                           get_cmd=self._get_temperatureVTI,
                           set_cmd= self._set_temperatureVTI,
                           #get_parser=lambda s : float(s[1:].split(':')[-1][:-1]),
                           vals=Numbers(min_value=0,
                                        max_value=300))
                                        
        self.add_parameter(name='TempProbe',
                           label='Temperature Probe',
                           unit='K',
                           get_cmd=self._get_temperature,
                           set_cmd= self._set_temperatureProbe,
                           #get_parser=lambda s : float(s[1:].split(':')[-1][:-1]),
                           vals=Numbers(min_value=0,
                                        max_value=300))
                                        
        self.add_parameter(name='TempSorb',
                           label='Temperature Sorb Heliox',
                           unit='K',
                           get_cmd=self._get_temperatureSorb,
                           #set_cmd= self._set_temperatureSorb,
                           #get_parser=lambda s : float(s[1:].split(':')[-1][:-1]),
                           vals=Numbers(min_value=0,
                                        max_value=300))

        self.add_parameter(name='Temp1K',
                           label='Temperature 1K Pot Heliox',
                           unit='K',
                           get_cmd="READ:DEV:DB5.T1:TEMP:SIG:TEMP?",
                           #set_cmd= self._set_temperatureSorb,
                           get_parser=lambda s : float(s[1:].split(':')[-1][:-1]),
                           vals=Numbers(min_value=0,
                                        max_value=300))

        self.add_parameter(name='Temperature_DB7',
                           label='Temperature DB7',
                           unit='K',
                           get_cmd=self._get_temperature_DB7,
                           set_cmd= self._set_temperature,
                           #get_parser=lambda s : float(s[1:].split(':')[-1][:-1]),
                           vals=Numbers(min_value=0,
                                        max_value=300))
                                        
        self.add_parameter(name='Temperature_DB8',
                           label='Temperature DB8',
                           unit='K',
                           get_cmd=self._get_temperature_DB8,
                           set_cmd= self._set_temperature,
                           #get_parser=lambda s : float(s[1:].split(':')[-1][:-1]),
                           vals=Numbers(min_value=0,
                                        max_value=300))
                                        
        self.add_parameter(name='Temperature',
                           label='Sample Temperature',
                           unit='K',
                           get_cmd=self._get_temperature,
                           set_cmd= self._set_temperature,
                           #get_parser=lambda s : float(s[1:].split(':')[-1][:-1]),
                           vals=Numbers(min_value=0,
                                        max_value=300))
                                        
        self.add_parameter(name='pressure',
                           label='VTI pumping line pressure',
                           unit='mbar',
                           get_cmd=self._get_pressure,
                           set_cmd=self._set_pressure_setpoint,
                           #get_parser=lambda s : float(s[1:].split(':')[-1][:-2]),
                           vals=Numbers(min_value=0,
                                        max_value=100))
	
        self.add_parameter(name='pressure_setpoint',
                           label='pressure setpoint for needlevalve control',
                           unit='mbar',
                           get_cmd=self._get_pressure_setpoint,
                           set_cmd= self._set_pressure_setpoint,
                           #get_parser=lambda s : float(s[1:].split(':')[-1][:-2]),
                           vals=Numbers(min_value=0,
                                        max_value=100))

        self.add_parameter(name='needlevalve',
                           label='needle valve position',
                           unit='%',
                           get_cmd='READ:DEV:DB4.G1:AUX:SIG:PERC',
                           set_cmd= self._set_needlevalve,
                           get_parser=lambda s : float(s[1:].split(':')[-1][:-1]),
                           vals=Numbers(min_value=0,
                                        max_value=100))
	### manually added

        self.add_function('reset', call_cmd='*RST')
        self.add_function('recondense_start', call_cmd=self._recondense_start)
        self.add_function('debug_output', call_cmd=self._debug_output)
        self.add_function('recondense_stop', call_cmd=self._recondense_stop)
        #self.ask_raw("*IDN?\n")
        self.connect_message()

 
    def _recondense_start(self):
        if self._mode=='heliox':
            #open the needle valve manually a lot
            self._set_needlevalve(25)
            time.sleep(3)
            self._set_pressure_setpoint(20)
            #MB1 is sorb, DB7 is high temp, DB8 is low temp, DB6 is VTI
            #first set a low temperature to switch to low temp mode
            self._set_temperature(0.25)
            #then switch of all heating and turn on sorb heater to fixed percent
            self.ask_raw('SET:DEV:DB6.T1:TEMP:LOOP:ENAB:0')
            self.ask_raw('SET:DEV:DB6.T1:TEMP:LOOP:HSET:0')
            self.ask_raw('SET:DEV:DB7.T1:TEMP:LOOP:ENAB:0')
            self.ask_raw('SET:DEV:DB7.T1:TEMP:LOOP:HSET:0')
            self.ask_raw('SET:DEV:DB8.T1:TEMP:LOOP:ENAB:0')
            self.ask_raw('SET:DEV:DB8.T1:TEMP:LOOP:HSET:0')
            time.sleep(1)
            self.ask_raw('SET:DEV:MB1.T1:TEMP:LOOP:HSET:{}'.format(30))
            self.ask_raw('SET:DEV:MB1.T1:TEMP:LOOP:ENAB:1')
            
            
    def _recondense_stop(self):
        if self._mode=='heliox':
            self._set_pressure_setpoint(10)
            #MB1 is sorb, DB7 is high temp, DB8 is low temp, DB6 is VTI
            #set the low T heater to 0.25K carefully
            self.ask_raw('SET:DEV:DB7.T1:TEMP:LOOP:ENAB:0')
            self.ask_raw('SET:DEV:DB7.T1:TEMP:LOOP:HSET:0')
            self.ask_raw('SET:DEV:DB7.T1:TEMP:LOOP:TSET:0.25')
            self.ask_raw('SET:DEV:DB7.T1:TEMP:LOOP:ENAB:1')
            self.ask_raw('SET:DEV:DB8.T1:TEMP:LOOP:ENAB:0')
            self.ask_raw('SET:DEV:DB8.T1:TEMP:LOOP:HSET:0')
            time.sleep(1)
            self.ask_raw('SET:DEV:MB1.T1:TEMP:LOOP:ENAB:0')
            self.ask_raw('SET:DEV:MB1.T1:TEMP:LOOP:HSET:0')

    def _get_pressure(self):
        if self._mode=='vti':
            return float(self.ask("READ:DEV:DB4.G1:PRES:SIG:PRES").split(":")[-1][:-2]) # for VTI mode
        elif self._mode=='heliox':
            return float(self.ask("READ:DEV:DB4.G1:PRES:SIG:PRES").split(":")[-1][:-2]) # for Heliox mode

    def _set_pressure_setpoint(self, pressure):
        """ Set the NV pressure setpoint and switch to PID mode """
        if pressure < 0:
            pressure = 0
        if self._mode=='vti':
            #self.ask_raw('SET:DEV:DB5.P1:PRES:LOOP:ENAB:1') # for VTI
            self.ask_raw('SET:DEV:DB5.P1:PRES:LOOP:PRST:{}'.format(pressure)) # for VTI
            self.ask_raw('SET:DEV:DB5.P1:PRES:LOOP:FAUT:1')
        elif self._mode=='heliox':
             #self.ask_raw('SET:DEV:DB3.P1:PRES:LOOP:ENAB:1')
             self.ask_raw('SET:DEV:DB3.P1:PRES:LOOP:PRST:{}'.format(pressure)) # for heliox
             self.ask_raw('SET:DEV:DB3.P1:PRES:LOOP:FAUT:1')
          
    def _set_needlevalve(self, nv):
        """ Set the NVposition manually. switch to manual control """
        if nv < 0:
            nv = 0
        if self._mode=='vti':
            self.ask_raw('SET:DEV:DB5.P1:PRES:LOOP:FAUT:0')
            self.ask_raw('SET:DEV:DB5.P1:PRES:LOOP:FSET:{}'.format(nv)) # for VTI
        elif self._mode=='heliox':
            self.ask_raw('SET:DEV:DB3.P1:PRES:LOOP:FAUT:0')
            self.ask_raw('SET:DEV:DB3.P1:PRES:LOOP:FSET:{}'.format(nv)) # for heliox
          
    def _get_pressure_setpoint(self):
        """ Get the NV pressure setpoint """
        if self._mode=='vti':
             return float(self.ask("READ:DEV:DB5.P1:PRES:LOOP:PRST").split(":")[-1][:-2]) # for VTI mode
        elif self._mode=='heliox':
             return float(self.ask("READ:DEV:DB3.P1:PRES:LOOP:PRST").split(":")[-1][:-2]) # for heliox mode

    def _set_temperatureVTI(self, temperature):
        """ Set the temperature """
        if temperature < 0:
            temperature = 0
        if self._mode=='vti':
             self.ask_raw('SET:DEV:MB1.T1:TEMP:LOOP:TSET:{}'.format(temperature)) # for VTI mode
        elif self._mode=='heliox':
            self.ask_raw('SET:DEV:DB6.T1:TEMP:LOOP:TSET:{}'.format(temperature)) # for heliox mode
            self.ask_raw('SET:DEV:DB6.T1:TEMP:LOOP:ENAB:1') # for heliox mode

    def _set_temperature(self, temperature):
        """ Set the temperature of both Probe and VTI """
        if temperature < 0:
            temperature = 1
        if self._mode=='vti': # in VTI mode set both VTI and probe close to each other with the VTI a little lower
            self._set_temperatureProbe(temperature)
            self._set_temperatureVTI(temperature-min(0.2,temperature*0.02))
        elif self._mode=='heliox': #in heliox mode keep 1K pot (ie VTI) running at base until 30K, then heat VTI as well
            if temperature < 30:
                self._set_temperatureVTI(1.5)
                self.ask_raw('SET:DEV:HelioxX:HEL:TSET:{}'.format(temperature)) 
            else:
                self.ask_raw('SET:DEV:HelioxX:HEL:TSET:{}'.format(temperature)) 
                time.sleep(4)
                self._set_temperatureVTI(temperature-min(2,temperature*0.04))
        
    def _set_temperatureProbe(self, temperature):
        """ Set the temperature """
        if temperature < 0:
            temperature = 0
        if self._mode=='vti':
             self.ask_raw('SET:DEV:DB8.T1:TEMP:LOOP:TSET:{}'.format(temperature)) # for VTI mode
        elif self._mode=='heliox':
             self.ask_raw('SET:DEV:HelioxX:HEL:TSET:{}'.format(temperature)) # for heliox mode
        

    def _get_temperatureVTI(self):
        if self._mode=='vti':
             return float(self.ask("READ:DEV:MB1.T1:TEMP:SIG:TEMP?").split(":")[-1][:-1]) # for VTI mode
        elif self._mode=='heliox':
             return float(self.ask("READ:DEV:DB6.T1:TEMP:SIG:TEMP?").split(":")[-1][:-1]) # for heliox mode

    def _get_temperatureSorb(self):
        if self._mode=='vti':
             return(0) # not valid for VTI mode
        elif self._mode=='heliox':
             return float(self.ask("READ:DEV:MB1.T1:TEMP:SIG:TEMP?").split(":")[-1][:-1]) # for heliox mode

    def _get_temperature(self):
        if self._mode=='vti':
             return float(self.ask("READ:DEV:DB8.T1:TEMP:SIG:TEMP?").split(":")[-1][:-1]) # for VTI mode
        elif self._mode=='heliox':
             low=self._get_temperature_DB7()
             high=self._get_temperature_DB8()
             if high < self._Temperature_Switch_High_Low:
                return(low)
             else:
                return(high)
        
    def _get_temperature_DB7(self):
            return float(self.ask("READ:DEV:DB7.T1:TEMP:SIG:TEMP?").split(":")[-1][:-1]) 

    def _get_temperature_DB8(self):
            return float(self.ask("READ:DEV:DB8.T1:TEMP:SIG:TEMP?").split(":")[-1][:-1])     

    def _debug_output(self):
        print("Heliox Status: {}".format(self.ask('READ:DEV:HelioxX:HEL:SIG:STAT?').split(":")[-1]))   
        print("DB5 (1K Plate): {}".format(self.Temp1K()))        
        print("DB6 (VTI): {}".format(self._get_temperatureVTI()))        
        print("DB7 (He3 Pot Low Temperature, RuO2): {}, Setpoint: {}, Heater%: {}, Automatic(ON)/Manual(OFF): {}".format(
            self._get_temperature_DB7(),
            self.ask('READ:DEV:DB7.T1:TEMP:LOOP:TSET?').split(":")[-1]  ,
            self.ask('READ:DEV:DB7.T1:TEMP:LOOP:HSET?').split(":")[-1]  ,
            self.ask('READ:DEV:DB7.T1:TEMP:LOOP:ENAB?').split(":")[-1]  
        ))  
        print("DB8 (He3 Pot High Temperature, Cernox): {}, Setpoint: {}, Heater%: {}, Automatic(ON)/Manual(OFF): {}".format(
            self._get_temperature_DB8(),
            self.ask('READ:DEV:DB7.T1:TEMP:LOOP:TSET?').split(":")[-1]  ,
            self.ask('READ:DEV:DB8.T1:TEMP:LOOP:HSET?').split(":")[-1]  ,
            self.ask('READ:DEV:DB8.T1:TEMP:LOOP:ENAB?').split(":")[-1]  
        ))  
        print("Sorb Temperature: {}".format(self._get_temperatureSorb()))  
        print("Heliox reported H3PT (He3 Pot Temperature shown on Display): {}".format(self.ask('READ:DEV:HelioxX:HEL:SIG:H3PT?').split(":")[-1])) 
        print("Heliox Temperature reported by this driver: {}".format(self.Temperature())) 
        print("Heliox Temperature Setpoint (Setpoint shown on Display): {}".format(self.ask('READ:DEV:HelioxX:HEL:SIG:TSET?').split(":")[-1])) 
        print("Needlevalve: NV%: {}, Pressure: {}, Pressure Setpoint: {}, Automatic(ON)/Manual(OFF): {}".format(
            self.needlevalve(),
            self.pressure(),
            self.pressure_setpoint(),
            self.ask('READ:DEV:DB3.P1:PRES:LOOP:FAUT?').split(":")[-1]  
        ))                