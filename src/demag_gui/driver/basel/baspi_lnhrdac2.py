# ----------------------------------------------------------------------------------------------------------------------------------------------
# LNHR DAC II Telnet driver (Python)
# v0.1.1
# Copyright (c) Basel Precision Instruments GmbH (2024)
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the 
# Free Software Foundation, either version 3 of the License, or any later version. This program is distributed in the hope that it will be 
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
# General Public License for more details. You should have received a copy of the GNU General Public License along with this program.  
# If not, see <https://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------------------------------------------------------------------------

# imports --------------------------------------------------------------

from typing import Optional, Sequence, Any
from time import sleep
from warnings import warn
import pyvisa as visa
import logging
from functools import partial
from qcodes import VisaInstrument, InstrumentChannel, ChannelList
from qcodes.instrument.channel import MultiChannelInstrumentParameter
from qcodes.utils import validators
import sys
sys.path.append("C:/Users/Demo/Downloads/addons")
log = logging.getLogger(__name__)

# class ----------------------------------------------------------------

class SP1060Exception(Exception):
    """
    Empty class for Errors raised by the LNHR DAC II
    """
    pass

# class ----------------------------------------------------------------

class SP1060Reader(object):
    """
    This class contains methods to convert a voltage value of the 
    LNHR DAC II to a hexadecimal value and vice versa. Hexadecimal values
    are used in the devices memory.
    """

    #-------------------------------------------------

    def _vval_to_dacval(self, vval: float) -> int:
        """
        Convert a LNHR DAC II voltage into an internal hexadecimal value

        Parameters:
        vval: voltage value in V

        Returns:
        int: hexadecimal value, used internally by the DAC
        """

        dacval = round((float(vval) + 10.000000) * 838860.74)

        return dacval

    #-------------------------------------------------

    def _dacval_to_vval(self, dacval: int) -> float:
        """
        Convert a LNHR DAC II internal hexadecimal value into a voltage

        Parameters:
        dacval: hexadecimal value, used internally by the DAC
        
        Returns:
        float: voltage value in V
        """

        vval = round((int(dacval.strip(), 16) / 838860.74) - 10.000000, 6)
    
        return vval

# class ----------------------------------------------------------------

class SP1060MultiChannel(MultiChannelInstrumentParameter, SP1060Reader):
    """
    Class to enable manipulation of parameters on multiple channels of
    the LNHR DAC II
    """

    #-------------------------------------------------

    def __init__(self, channels:Sequence[InstrumentChannel], param_name: str, *args: Any, **kwargs: Any):
        super().__init__(channels, param_name, *args, **kwargs)
        self._channels = channels
        self._param_name = param_name

        #-------------------------------------------------
        
        def get_raw(self):
            # TODO: docstring
            output = tuple(chan.parameters[self._param_name].get() for chan in self._channels)
            return output
        
        #-------------------------------------------------
        
        def set_raw(self, value):
            # TODO: docstring
            for chan in self._channels:
                chan.volt.set(value)
            
# class ----------------------------------------------------------------
    
class SP1060Channel(InstrumentChannel, SP1060Reader):
    """
    Class to hold the 12 or 24 channels of the LNHR DAC II
    """

    #-------------------------------------------------
   
    def __init__(self, parent, name, channel, min_val=-10, max_val=10):
        super().__init__(parent, name)
        
        # validate channel number
        self._CHANNEL_VAL = validators.Ints(1,24)
        self._CHANNEL_VAL.validate(channel)
        self._channel = channel

        # limit voltage range
        self._volt_val = validators.Numbers(min(min_val, max_val), max(min_val, max_val))
        
        self.add_parameter('volt',
                           label = 'C {}'.format(channel),
                           unit = 'V',
                           set_cmd = partial(self._parent._set_voltage, channel),
                           set_parser = self._vval_to_dacval,
                           get_cmd = partial(self._parent._read_voltage, channel),
                           vals = self._volt_val 
                           )
        
# class ----------------------------------------------------------------

class SP1060(VisaInstrument, SP1060Reader):
    """
    Main class for integrating the Basel Precision Instruments 
    LNHR DAC II into QCoDeS as an instrument.
    """

    ##################################################

    # CLASS CONSTRUCTOR

    ##################################################

    #-------------------------------------------------
    
    def __init__(self, 
                 name: str, 
                 address: str, 
                 min_val: float = -10, 
                 max_val: float = 10, 
                 baud_rate: int = 115200,
                 channel_number: int = 24,
                 **kwargs: Any
                 ) -> None:
        """
        Constructor. Creates an instance of the Basel Precision Instruments 
        LNHR DAC II SP1060 instrument.

        Parameters:
        name: Local name of this DAC
        address: The VISA address of this DAC. For a serial port this is usually ASRLn::INSTR
            n is replaced with the address set in the VISA control panel.
        channel_number: Number of channels of this DAC
        min_val: The minimum voltage that can be output by the DAC
        max_val: The maximum voltage that can be output by the DAC
        baud_rate: Set accordingly to the VISA control panel
        """
        # TODO: check "create channels" and "safety limits", check addition of channel_number

        super().__init__(name, address, **kwargs)

        # VISA resource properties
        self.visa_handle.baud_rate = baud_rate
        self.visa_handle.parity = visa.constants.Parity.none
        self.visa_handle.stop_bits = visa.constants.StopBits.one
        self.visa_handle.data_bits = 8
        self.visa_handle.flow_control = visa.constants.VI_ASRL_FLOW_XON_XOFF
        self.visa_handle.write_termination = "\r\n"
        self.visa_handle.read_termination = "\r\n"

        # protected properties for communication with device
        self._ctrl_cmd_delay = 0.2
        self._mem_write_delay = 0.3

        # create channels of this device
        channels = ChannelList(self, 
                               "Channels", 
                               SP1060Channel, 
                               snapshotable = False,
                               multichan_paramclass = SP1060MultiChannel
                               )
        
        self.channel_number = channel_number
        
        for i in range(1, self.channel_number + 1):
            channel = SP1060Channel(self, f"chan{i:1}", i)
            channels.append(channel)
            self.add_submodule(f"ch{i:1}", channel)
        channels.lock()
        self.add_submodule("channels", channels)

        # Safety limits for sweeping DAC voltages
        # inter_delay: Minimum time (in seconds) between successive sets.
        #              If the previous set was less than this, it will wait until the
        #              condition is met. Can be set to 0 to go maximum speed with
        #              no errors.    
         
        # step: max increment of parameter value.
        #       Larger changes are broken into multiple steps this size.
        #       When combined with delays, this acts as a ramp.
        for chan in self.channels:
            chan.volt.inter_delay = 0.02
            chan.volt.step = 0.01
        
        # display some information after instanciation/ initial connection
        self.connect_message()
        voltages = self.channels[:].volt.get()
        print("Current DAC output (Channel 1 ... Channel 24): ")
        print(voltages)

    #-------------------------------------------------

    ##################################################

    # COMMUNICATION/ QCODES METHODS

    ##################################################

    #-------------------------------------------------

    def write(self, command: str) -> Optional[str]:
        """
        Sends a command or a query to the device. This method overrides 
        the standard QCoDeS write() method

        Parameters:
        command: command as per programmers manual of the device

        Returns:
        string: answer of the device in case of a query

        Raises:
        KeyError: command couldn't be processed by the device
        """
        # TODO: empty_buffer() necessary?, return sequence (multi command)

        answer = self.ask(command)

        # handshaking: check for succesful acknowledge/ valid answer
        if not "?" in command:
            if answer != "0":
                raise KeyError(f"Command ({command}) could not be processed by the device")
        else:
            if "?" in answer:
                raise KeyError(f"Command ({command}) could not be processed by the device")

        # in case of a control command wait to allow for internal 
        # synchronisation of all the devices variables
        if command[0].lower() == "c":
            sleep(self._ctrl_cmd_delay)
            if "write" in command:
                sleep(self._mem_write_delay)

        return answer
    
    #-------------------------------------------------

    def _set_voltage(self, channel: int, dacvalue: int) -> str:
        """
        Set a specific DAC channel to a specific value

        Parameters:
        channel: DAC channel
        dacvalue: hexadecimal value (0x0 - 0xFFFFFF)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"{channel:0} {dacvalue:X}")
    
    #-------------------------------------------------
            
    def _read_voltage(self, channel: int) -> float:
        """
        Read the voltage of a specific DAC channel

        Parameters:
        channel: DAC channel

        Returns:
        float: voltage value (+/- 10.000000 V)
        """

        dac_code=self.write(f"{channel:0} V?")
        return self._dacval_to_vval(dac_code)
    
    # alias for reverse compatibility
    query_chan_voltage = _read_voltage
    
    #-------------------------------------------------

    def empty_buffer(self) -> None:
        """
        Empty the buffer of the VISA communication interface
        """

        self.visa_handle.clear() 
           
    #-------------------------------------------------
    
    def get_idn(self) -> dict:
        """
        Read the IDN of the device

        Returns:
        dictionary: consisting of manufacturer, model, 
            serial number and firmware version
        """

        serial = self.get_serial()
        firmware = self.get_firmware()

        idn = { "vendor": "Basel Precision Instruments",
                "model": "LNHR DAC II (SP1060)", 
                "serial": serial, 
                "firmware": firmware
                }
        
        return idn

    #-------------------------------------------------

    def set_all(self, voltage: float) -> None:
        """
        Set all channels to a voltage using the Parameter "volt"

        Parameters:
        voltage: voltage value (+/-10.000000 V)
        """
        for chan in self.channels:
            chan.volt.set(voltage)

    #-------------------------------------------------
    
    def query_all(self) -> list:
        """
        Read the on/off status of all DAC channels

        Returns:
        list: list of the on/off status of all channels
        """
        reply = self.write('All S?')
        print(reply)
        return reply.replace("\r\n","").split(';')

    #-------------------------------------------------

    ##################################################

    # SET DAC COMMANDS

    ##################################################

    #-------------------------------------------------

    def set_channel_dacvalue(self, channel: int, dacvalue: int) -> str:
        """
        Set a specific DAC channel to a specific value

        Parameters:
        channel: DAC channel
        dacvalue: hexadecimal value (0x0 - 0xFFFFFF)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"{channel:0} {dacvalue:x}")

    # alias for reverse compatibility
    set_chan_voltage = set_channel_dacvalue
    
    #-------------------------------------------------

    def set_all_dacvalue(self, dacvalue: int) -> str:
        """
        Set all DAC channels to a specific value

        Parameters:
        dacvalue: hexadecimal value (0x0 - 0xFFFFFF)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"all {dacvalue:x}")
    
    # alias for reverse compatibility
    set_all_voltage = set_all_dacvalue
    
    #-------------------------------------------------

    def set_channel_on(self, channel: int) -> str:
        """
        Turn on a specific DAC channel

        Parameters:
        channel: DAC channel (1 - 24)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"{channel} on")
    
    # alias for reverse compatibility
    set_chan_on = set_channel_on

    #-------------------------------------------------

    def set_channel_off(self, channel: int) -> str:
        """
        Turn off a specific DAC channel

        Parameters:
        channel: DAC channel ("1" - "24")

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"{channel} off")
    
    # alias for reverse compatibility
    set_chan_off = set_channel_off

    #-------------------------------------------------

    def set_all_on(self) -> str:
        """
        Turn on all DAC channels

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """
        
        return self.write("all on")
    
    # alias for reverse compatibility
    all_on = set_all_on

    #-------------------------------------------------
    
    def set_all_off(self) -> str:
        """
        Turn off all DAC channels

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """
        
        return self.write("all off")
    
    # alias for reverse compatibility
    all_off = set_all_off

    #-------------------------------------------------

    def set_channel_bandwidth(self, channel: int, bandwidth: str) -> str:
        """
        Set the bandwidth of a specific channel to high- or low-bandwith 
        (100 Hz or 100 kHz)

        Parameters:
        channel: DAC channel
        bandwith: bandwith mode ("LBW" or "HBW")

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """
        
        return self.write(f"{channel} {bandwidth}")
    
    # alias for reverse compatibility
    set_chan_bandwidth = set_bandwidth = set_channel_bandwidth

    #-------------------------------------------------

    def set_all_bandwidth(self, bandwidth: str) -> str:
        """
        Set the bandwidth of all channels to high- or low-bandwith 
        (100 Hz or 100 kHz)

        Parameters:
        bandwith: bandwith mode ("LBW" or "HBW")

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """
        
        return self.write(f"all {bandwidth}")
    
    #-------------------------------------------------
    
    ##################################################

    # SET AWG COMMANDS

    ##################################################
    
    #-------------------------------------------------

    def set_awg_memory_value(self, memory: str, address: int, dacvalue: int) -> str:
        """
        Set an AWG memory address to a specific value

        Parameters:
        memory: AWG memory to write into ("A", "B", "C" or "D")
        address: hexadecimal memory address (0x0 - 0x84CF)
        dacvalue: hexadecimal value (0x0 - 0xFFFFFF)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"awg-{memory} {address:x} {dacvalue:x}")
    
    # alias for reverse compatibility
    set_adr_AWGmem = set_awg_memory_value

    #-------------------------------------------------

    def set_awg_memory_all(self, memory: str, dacvalue: int) -> str:
        """
        Set the full AWG memory to a specific value

        Parameters:
        memory: AWG memory to write into ("A", "B", "C" or "D")
        dacvalue: hexadecimal value (0x0 - 0xFFFFFF)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"awg-{memory} ALL {dacvalue:x}")
    
    # alias for reverse compatibility
    set_all_AWGMem = set_awg_memory_all

    #-------------------------------------------------
    
    ##################################################

    # SET WAVE COMMANDS

    ##################################################

    #-------------------------------------------------

    def set_wav_memory_value(self, memory: str, address: int, dacvalue: int) -> str:
        """
        Set a wave memory address to a specific value

        Parameters:
        memory: AWG memory to write into ("A", "B", "C" or "D")
        address: hexadecimal memory address (0x0 - 0x84CF)
        dacvalue: hexadecimal value (0x0 - 0xFFFFFF)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"wav-{memory} {address:x} {dacvalue:x}")

    # alias for reverse compatibility
    set_adr_WAVMem = set_wav_memory_value

    #-------------------------------------------------

    def set_wav_memory_all(self, memory: str, dacvalue: int) -> str:
        """
        Set the full wave memory to a specific value

        Parameters:
        memory: AWG memory to write into ("A", "B", "C" or "D")
        dacvalue: hexadecimal value (0x0 - 0xFFFFFF)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"wav-{memory} all {dacvalue:x}")
    
    # alias for reverse compatibility
    set_all_WAVMem = set_wav_memory_all
    
    #-------------------------------------------------
    
    ##################################################

    # SET POLYNOMIAL COMMANDS

    ##################################################

    #-------------------------------------------------

    def set_polynomial(self, memory: str, coefficients: list[float]) -> str:
        """
        Set polynomial coefficients. The polynomial can be applied to 
        the values of the AWG memory when the wave memory is copied into 
        the AWG memory

        Parameters:
        memory: associated AWG memory ("A", "B", "C" or "D")
        coefficients: list of floating-point coefficients in ascending 
            order of their order of power

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        coefficient_string = ""

        for element in coefficients:
            coefficient_string = coefficient_string + f" {str(element)}"

        return self.write(f"poly-{memory}{coefficient_string}")
    
    #-------------------------------------------------

    ##################################################

    # QUERY DATA COMMANDS

    ##################################################

    #-------------------------------------------------

    def get_channel_dacval(self, channel: int) -> str:
        """
        Read the present value of a specified DAC channel

        Parameters:
        channel: DAC channel

        Returns:
        string: hexadecimal DAC value (0x0 - 0xFFFFFF)
        """

        return self.write(f"{channel} v?")

    #-------------------------------------------------

    def get_all_dacval(self) -> str:
        """
        Read the present value of all DAC channels

        Returns:
        string: hexadecimal DAC value (0x0 - 0xFFFFFF) of all channels, 
            comma separated
        """

        return self.write("all v?")
    
    # alias for reverse compatibility
    query_all_voltage = get_all_dacval

    #-------------------------------------------------

    def get_channel_dacvalue_registered(self, channel: int) -> str:
        """
        Read the registered value of a specified channel. This is the 
        next value that will be outputted

        Parameters:
        channel: DAC channel

        Returns:
        string: hexadecimal DAC value (0x0 - 0xFFFFFF)
        """
        
        warn("This method has been slightly changed in this version of the driver. "
             + "If you want the original version of this method, uncomment the section in the method definition.")
        
        res = self.write(f"{channel} vr?")
        # uncomment for original version
        # res = self._dacval_to_vval(res)
        return res
    
    # alias for reverse compatibility
    query_chan_voltageReg = get_channel_dacvalue_registered

    #-------------------------------------------------

    def get_all_dacvalue_registered(self) -> str:
        """
        Read the registered value of all channels. This is the next 
        value that will be outputted

        Returns:
        string: hexadecimal registered DAC value (0x0 - 0xFFFFFF) of all channels, 
            comma separated
        """
        
        return self.write("all vr?")

    # alias for reverse compatibility
    query_all_voltageReg = get_all_dacvalue_registered
    
    #-------------------------------------------------

    def get_channel_status(self, channel: int) -> str:
        """
        Read the on or off status of a specified DAC channel

        Parameters:
        channel: DAC channel

        Returns:
        string: status ("ON" or "OFF")
        """
        
        return self.write(f"{channel} s?")
    
    # alias for reverse compatibility
    query_chan_status = get_channel_status

    #-------------------------------------------------

    def get_all_status(self) -> list:
        """
        Read the on or off status of all DAC channels

        Returns:
        list: statuses ("ON" or "OFF") of all channels
        """
        
        return self.write("all s?").replace("\r\n","").split(';')

    # alias for reverse compatibility
    query_all_status = get_all_status
    
    #-------------------------------------------------

    def get_channel_bandwidth(self, channel: int) -> str:
        """
        Read the bandwith of a specified DAC channel (100 Hz or 100 kHz)

        Parameters:
        channel: DAC channel

        Returns:
        string: bandwith mode ("LBW" or "HBW")
        """
        
        return self.write(f"{channel} bw?")
    
    # alias for reverse compatibility
    query_chan_bandwidth = get_bandwidth = get_channel_bandwidth

    #-------------------------------------------------

    def get_all_bandwidth(self) -> str:
        """
        Read the bandwith of all DAC channels (100 Hz or 100 kHz)

        Returns:
        list: bandwidth modes ("LBW" or "HBW") of all channels
        """

        return self.write("all bw?").replace("\r\n","").split(';')
    
    # alias for reverse compatibility
    query_all_bandwidth = get_all_bandwidth

    #-------------------------------------------------

    def get_channel_mode(self, channel: int) -> str:
        """
        Read the current DAC mode of a specific DAC channel

        Parameters:
        channel: DAC channel

        Returns:
        string: current DAC mode ("ERR", "DAC", "SYN", "RMP", "AWG", "---")
        """
        
        return self.write(f"{channel} m?")
    
    # alias for reverse compatibility
    query_chan_DACMode = read_mode = get_channel_mode

    #-------------------------------------------------

    def get_all_mode(self) -> list:
        """
        Read the current DAC mode of all DAC channels

        Returns:
        list: current DAC mode ("ERR", "DAC", "SYN", "RMP", "AWG", "---") of all channels
        """

        return self.write("all m?").replace("\r\n","").split(';')
    
    # alias for reverse compatibility
    query_all_DACMode = get_all_mode

    #-------------------------------------------------

    def get_awg_memory_value(self, memory: str, address: int) -> str:
        """
        Read the value of a specific AWG memory adress. The AWG must not run

        Parameters:
        memory: AWG memory to read out of ("A", "B", "C" or "D")
        address: hexadecimal memory address (0x0 - 0x84CF)

        Returns:
        string: hexadecimal value (0x0 - 0xFFFFFF)
        """
        
        return self.write(f"awg-{memory} {address:x}?")
    
    # alias for reverse compatibility
    query_adr_AWGmem = get_awg_memory_value

    #-------------------------------------------------

    def get_awg_memory_block(self, memory: str, block_start_address: int) -> str:
        """
        Read the values of a AWG memory block (1000 values). The AWG must not run

        Parameters:
        memory: AWG memory to read out of ("A", "B", "C" or "D")
        address: hexadecimal memory address (0x0 - 0x84CF)

        Returns:
        string: hexadecimal values (0x0 - 0xFFFFFF) of the memory block, 
            semicolon separated
        """
        
        return self.write(f"awg-{memory} {block_start_address:x} blk?").replace("\r\n","").split(';')
    
    # alias for reverse compatibility
    query_block_AWGmem = get_awg_memory_block

    #-------------------------------------------------

    def get_wav_memory_value(self, memory: str, address: int) -> str:
        """
        Read the value of a specific wave memory adress

        Parameters:
        memory: wave memory to read out of ("A", "B", "C" or "D")
        address: hexadecimal memory address (0x0 - 0x84CF)

        Returns:
        string: voltage ("+/- 10.000000" or "NaN")
        """
        
        return self.write(f"wav-{memory} {address:x}?")
    
    # alias for reverse compatibility
    query_adr_WAVmem = get_wav_memory_value

    #-------------------------------------------------

    def get_wav_memory_block(self, memory: str, block_start_address: int) -> str:
        """
        Read the values of a wave memory block (1000 values)

        Parameters:
        memory: AWG memory to read out of ("A", "B", "C" or "D")
        address: hexadecimal memory address (0x0 - 0x84CF)

        Returns:
        string: hexadecimal values (0x0 - 0xFFFFFF) of the memory block, 
            semicolon separated
        """
        
        return self.write(f"wav-{memory} {block_start_address:x} blk?").replace("\r\n","").split(';')
    
    # alias for reverse compatibility
    query_block_WAVmem = get_wav_memory_block

    #-------------------------------------------------

    def get_polynomial(self, memory: str) -> str:
        """
        Read polynomial coefficients. The polynomial can be applied to 
        the values of the AWG memory when the wave memory is copied 
        into the AWG memory

        Parameters:
        memory: associated AWG memory ("A", "B", "C" or "D")

        Returns:
        string: listing of floating-point coefficients in ascending 
            order of their order of power, semicolon separated
        """
        
        return self.write(f"poly-{memory}?").replace("\r\n","").split(';')
    
    # alias for reverse compatibility
    query_coefs_Polymem = get_polynomial
    
    #-------------------------------------------------

    ##################################################

    # QUERY INFORMATION COMMANDS

    ##################################################

    #-------------------------------------------------

    def get_help_commands(self) -> str:
        """
        Get an overview of the ASCII commands and queries of the device
        
        Returns:
        string: overview of the ASCII commands and queries of the device
        """
        # TODO: check multiline output
        
        return self.write("?")
    
    # alias for reverse compatibility
    get_overview = get_help_commands
    #-------------------------------------------------

    def get_help_control(self) -> str:
        """
        Get a help text of the device

        Returns:
        string: help text of the device
        """
        # TODO: check multiline output

        return self.write("help?")
    
    # alias for reverse compatibility
    get_help = get_help_control
    
    #-------------------------------------------------
    
    def get_firmware(self) -> str:
        """
        Get the firmware of the device

        Returns:
        string: firmware of the device
        """
        # TODO: check multiline output, fix get_idn()

        answer = self.write("soft?")
        self.empty_buffer()
       
        return answer[17:33]

    #-------------------------------------------------

    def get_serial(self) -> str:
        """
        Returns the serial number of the device

        Returns:
        string: serial number of the device
        """
        # TODO: check multiline output, fix get_idn()

        answer = self.write("hard?")
        self.empty_buffer()

        return answer[36:51]
    
    #-------------------------------------------------
    
    def get_health(self) -> str:
        """
        Get health parameters (temperature, cpu-load, power-supplies) 
        from the device 
        
        Returns:
        string: temperature, cpu-load, power-supplies of the device
        """
        # TODO: check multiline output, 

        return self.write("health?")

    #-------------------------------------------------

    def get_ip(self) -> str:
        """
        Get the IP address of the device

        Returns:
        string: IP-adress and subnet mask of the device
        """
        # TODO: check multiline output, 
        
        return self.write("ip?")
    
    #-------------------------------------------------

    def get_baudrate(self) -> str:
        """
        Get the baudrate of the RS-232 port of the device

        Returns:
        string: baudrate of the RS-232 port of the device
        """
        # TODO: check multiline output, 

        return self.write("serial?")

    #-------------------------------------------------

    def get_contact(self) -> str:
        """
        Get the contact information in case of a problem

        Returns:
        string: contact information
        """
        # TODO: check multiline output, 

        return self.write("contact?")

    #-------------------------------------------------

    ##################################################

    # UPDATE/ SYNCHRONIZATION CONTROL COMMANDS

    ##################################################

    #-------------------------------------------------
    
    def get_board_update_mode(self, board: str) -> str:
        """
        Read the output channel update mode of a DAC board. A channel 
        can get updated instantly after setting its value or synchronous 
        with all other channels, triggered externally or by software

        Parameters:
        board: higher DAC board ("H") or lower DAC board ("L")

        Returns:
        string: DAC board updates instantly ("0") or synchronous ("1")
        """
        return self.write(f"C UM-{board}?")
    
    # alias for reverse compatibility
    read_updateMode = get_board_update_mode

    #-------------------------------------------------

    def set_board_update_mode(self, board: str, mode: int) -> str:
        """
        Set the output channel update mode of a DAC board. A channel can 
        get updated instantly after setting its value or synchronous with 
        all other channels, triggered externally or by software

        Parameters:
        board: higher DAC board ("H") or lower DAC board ("L")
        string: DAC board updates instantly ("0") or synchronous ("1")

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C UM-{board} {mode}")
    
    # alias for reverse compatibility
    write_updateMode = set_board_update_mode

    #-------------------------------------------------

    def update_board_channels(self, board: str) -> str:
        """
        Update all channels of a DAC board synchronously

        Parameters:
        board: higher DAC board ("H"), lower DAC board ("L"), 
            or both ("LH")

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C SYNC-{board}")
    
    # alias for reverse compatibility
    update_board_sync = update_board_channels

    #-------------------------------------------------
    
    ##################################################

    # RAMP/ STEP GENERATOR CONTROL COMMANDS

    ##################################################

    #-------------------------------------------------

    def set_ramp_mode(self, ramp: str, mode: str) -> str:
        """
        Set the mode of a ramp/step generator

        Parameters:
        ramp: ramp/step generator ("A", "B", "C", "D" or "all")
        mode: ramp/step generator mode ("start", "stop" or "hold")

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C RMP-{ramp} {mode}")
    
    # alias for reverse compatibility
    write_rampMode = set_ramp_mode

    #-------------------------------------------------

    def get_ramp_state(self, ramp: str) -> str:
        """
        Read the state of a ramp/step generator

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: ramp is idle ("0"), ramping up ("1"), ramping down ("2") 
            or on hold ("3")
        """
        
        return self.write(f"C RMP-{ramp} S?")
    
    # alias for reverse compatibility
    read_rampState = get_ramp_state

    #-------------------------------------------------

    def get_ramp_cycles_done(self, ramp: str) -> str:
        """
        Read the number of cycles that have been completed by a 
        ramp/step generator. This value is internally reset on each 
        ramp/step generator start

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: completed ramp/step cycles (0 - 4000000000)
        """

        return self.write(f"C RMP-{ramp} CD?")
    
    # alias for reverse compatibility
    read_rampCyclesDone = get_ramp_cycles_done

    #-------------------------------------------------

    def get_ramp_steps_done(self, ramp: str) -> str:
        """
        Read the number of single steps that have been completed by a 
        ramp/step generator. This value is internally reset on each 
        ramp/step generator start

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: completed ramp/step steps (0 - 4000000000)
        """

        return self.write(f"C RMP-{ramp} SD?")
    
    # alias for reverse compatibility
    read_rampStepsDone = get_ramp_steps_done

    #-------------------------------------------------

    def get_ramp_step_size(self, ramp: str) -> str:
        """
        Read the internally calculated step size in Volts

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: step size in V/step (+/- 10.000000 V)
        """

        return self.write(f"C RMP-{ramp} SSV?")
    
    # alias for reverse compatibility
    read_rampStepSizeVoltage = get_ramp_step_size

    #-------------------------------------------------

    def get_ramp_cycle_steps(self, ramp: str) -> str:
        """
        Read the internally calculated steps per ramp cycle

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: number of steps per cycle (0 - 200000000)
        """

        return self.write(f"C RMP-{ramp} ST?")
    
    # alias for reverse compatibility
    read_rampStepsPerCycle = get_ramp_cycle_steps

    #-------------------------------------------------

    def get_ramp_channel_availability(self, ramp: str) -> str:
        """
        Read if the associated DAC channel of a ramp/step generator is 
        available

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: associated DAC channel is available ("1") 
            or not available ("0")
        """

        return self.write(f"C RMP-{ramp} AVA?")
    
    # alias for reverse compatibility
    read_rampChannelAvailable = get_ramp_channel_availability

    #-------------------------------------------------

    def get_ramp_channel(self, ramp: str) -> str:
        """
        Read which DAC channel is associated with a ramp/step generator

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: associated DAC channel ("1" - "24")
        """
        return self.write(f"C RMP-{ramp} CH?")
    
    # alias for reverse compatibility
    read_rampSelectedChannel = get_ramp_channel

    #-------------------------------------------------

    def set_ramp_channel(self, ramp: str, channel: int) -> str:
        """
        Set which DAC channel will be associated with a 
        ramp/step generator

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")
        channel: selected DAC channel (1 - 24)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """
        
        return self.write(f"C RMP-{ramp} CH {channel}")
    
    # alias for reverse compatibility
    write_rampSelectedChannel = set_ramp_channel
    
    #-------------------------------------------------

    def get_ramp_starting_voltage(self, ramp: str) -> str:
        """
        Read the starting voltage of a ramp/step generator

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: starting voltage (+/- 10.0000000 V)
        """

        return self.write(f"C RMP-{ramp} STAV?")
    
    # alias for reverse compatibility
    read_rampStartVoltage = get_ramp_starting_voltage

    #-------------------------------------------------

    def set_ramp_starting_voltage(self, ramp: str, voltage: float) -> str:
        """
        Set the starting voltage of a ramp/step generator

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")
        voltage: starting voltage (+/- 10.0000000 V)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C RMP-{ramp} STAV {voltage:.6f}")
    
    # alias for reverse compatibility
    write_rampStartVoltage = set_ramp_starting_voltage

    #-------------------------------------------------

    def get_ramp_peak_voltage(self, ramp: str) -> str:
        """
        Read the peak voltage of a ramp/step generator.
        If the ramp shape is UP- or DOWN-ONLY, this is the stop voltage

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: stop/peak voltage (+/- 10.0000000 V)
        """

        return self.write(f"C RMP-{ramp} STOV?")
    
    # alias for reverse compatibility
    read_rampStopPeakVoltage = get_ramp_peak_voltage

    #-------------------------------------------------

    def set_ramp_peak_voltage(self, ramp: str, voltage: float) -> str:
        """
        Set the peak voltage of a ramp/step generator.
        If the ramp shape is UP- or DOWN-ONLY, this is the stop voltage

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")
        voltage: stop/peak voltage (+/- 10.0000000 V)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C RMP-{ramp} STOV {voltage:.6f}")
    
    # alias for reverse compatibility
    write_rampStopPeakVoltage = set_ramp_peak_voltage
    
    #-------------------------------------------------

    def get_ramp_duration(self, ramp: str) -> str:
        """
        Read the ramp time of a ramp/step generator. 
        The resolution is given by the default update rate of 5 ms

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: ramp time (0.05 s - 1000000 s)
        """

        return self.write(f"C RMP-{ramp} RT?")
    
    # alias for reverse compatibility
    read_rampTime = get_ramp_duration

    #-------------------------------------------------

    def set_ramp_duration(self, ramp: str, time: int) -> str:
        """
        Set the ramp time of a ramp/step generator. 
        The resolution is given by the default update rate of 5 ms

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")
        time: ramp time (0.05 s - 1000000 s)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C RMP-{ramp} RT {time:.3f}")
    
    # alias for reverse compatibility
    write_rampTime = set_ramp_duration
    
    #-------------------------------------------------

    def get_ramp_shape(self, ramp: str) -> str:
        """
        Read the set ramp shape of a ramp/step generator. Ramping up generates 
        a sawtooth, ramping up and down generates a triangular waveform

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: ramp up only ("0"), ramp up and down ("1")
        """

        return self.write(f"C RMP-{ramp} RS?")
    
    # alias for reverse compatibility
    read_rampShape = get_ramp_shape

    #-------------------------------------------------

    def set_ramp_shape(self, ramp: str, shape: int) -> str:
        """
        Set the ramp shape of a ramp/step generator. Ramping up generates 
        a sawtooth, ramping up and down generates a triangular waveform

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")
        shape: ramp up only (0), ramp up and down (1)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C RMP-{ramp} RS {shape}")
    
    # alias for reverse compatibility    
    write_rampShape = set_ramp_shape

    #-------------------------------------------------

    def get_ramp_cycles(self, ramp: str) -> str:
        """
        Read the set number of ramping cycles of a ramp/step generator. 
        Upon completing the set cycles, the ramp/step generator is stopped

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: set number of ramp cycles (1 - 4000000000) or infinite cycles (0)
        """

        return self.write(f"C RMP-{ramp} CS?")
    
    # alias for reverse compatibility
    read_rampCyclesSet = get_ramp_cycles
    
    #-------------------------------------------------

    def set_ramp_cycles(self, ramp: str, cycles: int) -> str:
        """
        Set the number of ramping cycles of a ramp/step generator. 
        Upon completing the set cycles, the ramp/step generator is stopped

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")
        cycles: number of ramp cycles (1 - 4000000000) or infinite cycles (0)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C RMP-{ramp} CS {cycles}")
    
    # alias for reverse compatibility
    write_rampCyclesSet = set_ramp_cycles
    
    #-------------------------------------------------

    def get_ramp_mode(self, ramp: str) -> str:
        """
        Read the set mode of a ramp/step generator. In ramp mode the 
        output is updated every 5 ms. In step mode the output is updated 
        internally, after the associated AWG has finished a cycle

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")

        Returns:
        string: RAMP mode ("0") or STEP ("1")
        """

        return self.write(f"C RMP-{ramp} STEP?")
    
    # alias for reverse compatibility
    read_rampStepSelection = get_ramp_mode

    #-------------------------------------------------

    def select_ramp_step(self, ramp: str, mode: int) -> str:
        """
        Read the set mode of a ramp/step generator. In ramp mode the 
        output is updated every 5 ms. In step mode the output is updated 
        internally, after the associated AWG has finished a cycle

        Parameters:
        ramp: ramp/step generator ("A", "B", "C" or "D")
        mode: RAMP mode (0) or STEP mode (1)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C RMP-{ramp} STEP {mode}")
    
    # alias for reverse compatibility
    write_rampStepSelection = select_ramp_step

    #-------------------------------------------------

    ##################################################

    # 2D-SCAN CONTROL COMMANDS

    ##################################################

    #-------------------------------------------------

    def get_awg_start_mode(self, awg: str) -> str:
        """
        Read the set AWG starting mode of an AWG generator. In auto-start 
        the AWG is internally started after the associated step generator 
        was updated. In normal-start the AWG is started by an external 
        trigger or by software

        Parameters:
        awg: AWG ("A", "B", "C" or "D")

        Returns:
        string: normal-start ("0") or auto-start ("1")
        """

        return self.write(f"C AWG-{awg} AS?")

    # alias for reverse compatibility
    read_AWGStartMode = get_awg_start_mode

    #-------------------------------------------------

    def set_awg_start_mode(self, awg: str, mode: int) -> str:
        """
        Set the AWG starting mode of an AWG generator. In auto-start the 
        AWG is internally started after the associated step generator 
        was updated. In normal-start the AWG is started by an external 
        trigger or by software

        Parameters:
        awg: AWG ("A", "B", "C" or "D")
        mode: normal-start (0) or auto-start (1)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-{awg} AS {mode}")
    
    # alias for reverse compatibility
    write_AWGStartMode = set_awg_start_mode

    #-------------------------------------------------

    def get_awg_reload_mode(self, awg: str) -> str:
        """
        Read the set AWG memory reload mode. In reload-mode, the 
        contents of the associated wave memory are loaded into 
        the AWG memory before each restart. In keep-mode, the AWG 
        memory is not updated. A polynomial can only be applied to 
        the waveform in reload-mode (used for adaptive 2D-scans)

        Parameters:
        awg: AWG ("A", "B", "C" or "D")

        Returns:
        string: keep-mode ("0") or reload-mode ("1")
        """

        return self.write(f"C AWG-{awg} RLD?")
    
    # alias for reverse compatibility
    read_AWGReloadMode = get_awg_reload_mode

    #-------------------------------------------------

    def set_awg_reload_mode(self, awg: str, mode: int) -> str:
        """
        Set the AWG memory reload mode. In reload-mode, the contents of 
        the associated wave memory are loaded into the AWG memory before 
        each restart. In keep-mode, the AWG memory is not updated. 
        A polynomial can only be applied to the waveform in reload-mode 
        (used for adaptive 2D-scans). Must not be changed if a 2D-scan 
        is running

        Parameters:
        awg: AWG ("A", "B", "C" or "D")
        mode: keep-mode (0) or reload-mode (1)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-{awg} RLD {mode}")
    
    # alias for reverse compatibility
    write_AWGReloadMode = set_awg_reload_mode

    #-------------------------------------------------

    def get_apply_polynomial (self, polynomial: str) -> str:
        """
        Read if the associated polynomial of an AWG is applied or not. 
        The polynomial is applied each time the AWG memory is reloaded 
        from its associated wave memory

        Parameters:
        polynomial: polynomial ("A", "B", "C" or "D")

        Returns:
        string: skip polynomial ("0") or apply polynomial ("1")
        """

        return self.write(f"C AWG-{polynomial} AP?")
    
    # alias for reverse compatibility
    read_AWGApplyPolyMode = get_apply_polynomial

    #-------------------------------------------------
    
    def set_apply_polynomial(self, polynomial: str, mode: int) -> str:
        """
        Set if the associated polynomial of an AWG is applied or not. 
        The polynomial is applied each time the AWG memory is reloaded 
        from its associated wave memory

        Parameters:
        polynomial: polynomial ("A", "B", "C" or "D")
        mode: skip polynomial (0) or apply polynomial (1)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-{polynomial} AP {mode}")
    
    # alias for reverse compatibility
    write_AWGApplyPolyMode = set_apply_polynomial
    
    #-------------------------------------------------
    
    def get_adaptive_shift_voltage(self, awg: str) -> str:
        """
        Set the voltage shift which is applied to an AWG after each step 
        of it's associated step generator. This modifies the constant 
        coefficient of the associated polynomial

        Parameters:
        awg: AWG ("A", "B", "C" or "D")
        voltage: shift voltage per step (+/- 10.000000 V)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-{awg} SHIV?")
    
    # alias for reverse compatibility
    read_AWGShiftVoltage = get_adaptive_shift_voltage

    #-------------------------------------------------

    def set_adaptive_shift_voltage(self, awg: str, voltage: float) -> str:
        """
        Set the voltage shift which is applied to an AWG after each step 
        of it's associated step generator. This modifies the constant 
        coefficient of the associated polynomial

        Parameters:
        awg: AWG ("A", "B", "C" or "D")
        voltage: shift voltage per step (+/- 10.000000 V)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-{awg} SHIV {voltage:.6f}")
    
    # alias for reverse compatibility
    write_AWGShiftVoltage = set_adaptive_shift_voltage

    #-------------------------------------------------

    ##################################################

    # AWG CONTROL COMMANDS 

    ##################################################

    #-------------------------------------------------

    def get_awg_board_mode(self, board: str) -> str:
        """
        Read the set AWG mode of a DAC board (AWG-A/B or AWG-C/D). In 
        normal mode, all outputs can be used for noraml operation. In 
        AWG-only mode all outputs which have no AWG assigned get blocked.

        Parameters:
        board: lower DAC board ("AB") or higher DAC board ("CD")

        Returns:
        string: normal mode ("0") or AWG-only mode ("1")
        """

        return self.write(f"C AWG-{board} ONLY?")
    
    # alias for reverse compatibility
    read_AWGNormalMode = get_awg_board_mode

    #-------------------------------------------------

    def set_awg_board_mode(self, board: str, mode: int) -> str: 
        """
        Set the AWG mode of a DAC board (AWG-A/B or AWG-C/D). In normal 
        mode, all outputs can be used for noraml operation. In AWG-only 
        mode all outputs which have no AWG assigned get blocked.

        Parameters:
        board: lower DAC board ("AB") or higher DAC board ("CD")
        mode: normal mode (0) or AWG-only mode (1)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-{board} ONLY {mode}")
    
    # alias for reverse compatibility
    write_AWGNormalMode = set_awg_board_mode

    #-------------------------------------------------

    def set_awg_start_stop(self, awg: str, command: str) -> str: 
        """
        Start or stop one or multiple AWGs

        Parameters:
        awg: AWG ("A", "B", "C", "D", "AB", "CD" or "all")
        command: start or stop command ("start" or "stop")

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-{awg} {command}")
    
    # alias for reverse compatibility
    write_AWGControlMode = set_awg_start_stop
    
    #-------------------------------------------------

    def get_awg_state(self, awg: str) -> str:
        """
        Read the current state of operation of an AWG

        Parameters:
        awg: AWG ("A", "B", "C" or "D")

        Returns:
        string: AWG is idle/not running ("0") or AWG is running ("1")
        """

        return self.write(f"C AWG-{awg} S?")
    
    # alias for reverse compatibility
    read_AWGState = get_awg_state

    #-------------------------------------------------

    def get_awg_cycles_done(self, awg: str) -> str: 
        """
        Read the number of cycles that have been completed by an AWG.
        This value is internally reset on each AWG start

        Parameters:
        awg: AWG ("A", "B", "C" or "D")

        Returns:
        string: completed AWG cycles (0 - 4000000000)
        """

        return self.write(f"C AWG-{awg} CD?")
    
    # alias for reverse compatibility
    read_AWGCyclesDone = get_awg_cycles_done
    
    #-------------------------------------------------

    def get_awg_duration(self, awg: str) -> str:
        """
        Read the internally calculated duration of one complete AWG cycle

        Parameters:
        awg: AWG ("A", "B", "C" or "D")

        Returns:
        string: AWG cycle duration (0.00002 s - 136000000 s)
        """

        return self.write(f"C AWG-{awg} DP?")
    
    # alias for reverse compatibility
    read_AWGDuration = get_awg_duration
    
    #-------------------------------------------------

    def get_awg_channel_availability(self, awg: str) -> str: 
        """
        Read the current availability for the selected output channel of an 
        AWG. A channel is only available if there is no AWG running on it

        Parameters:
        awg: AWG ("A", "B", "C" or "D")

        Returns:
        string: DAC channel is not available ("0") or is available ("1")
        """

        return self.write(f"C AWG-{awg} AVA?")
    
    # alias for reverse compatibility
    read_AWGChannelAvailable = get_awg_channel_availability
    
    #-------------------------------------------------

    def get_awg_channel(self, awg: str) -> str:
        """
        Read the selected output channel of an AWG

        Parameters:
        awg: AWG ("A", "B", "C" or "D")

        Returns:
        string: selected DAC channel ("1" - "24"), depending on AWG
        """

        return self.write(f"C AWG-{awg} CH?")
    
    # alias for reverse compatibility
    read_AWGSelectedChannel = get_awg_channel
    
    #-------------------------------------------------

    def set_awg_channel(self, awg: str, channel: int) -> str: 
        """
        Select an output channel for an AWG

        Parameters:
        awg: AWG ("A", "B", "C" or "D")
        channel: selected DAC channel (1 - 24), depending on AWG

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-{awg} CH {channel}")
    
    # alias for reverse compatibility
    write_AWGSelectedChannel = set_awg_channel
    
    #-------------------------------------------------

    def get_awg_memory_size(self, awg: str) -> str:
        """
        Read the size of an AWG memory

        Parameters:
        awg: AWG ("A", "B", "C" or "D")

        Returns:
        string: AWG memory size ("2" - "34000")
        """

        return self.write(f"C AWG-{awg} MS?")
    
    # alias for reverse compatibility
    read_AWGMemorySize = get_awg_memory_size

    #-------------------------------------------------

    def set_awg_memory_size(self, awg: str, size: int) -> str:
        """
        Set the size of an AWG memory

        Parameters:
        awg: AWG ("A", "B", "C" or "D")
        string: AWG memory size (2 - 34000)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-{awg} MS {size}")
    
    # alias for reverse compatibility
    write_AWGMemorySize = set_awg_memory_size
    
    #-------------------------------------------------

    def get_awg_cycles(self, awg: str) -> str:
        """
        Read the set number of AWG cycles. Upon completing the set 
        cycles, the AWG is stopped

        Parameters:
        awg: AWG ("A", "B", "C" or "D")

        Returns:
        string: AWG cycles (0 - 4000000000)
        """

        return self.write(f"C AWG-{awg} CS?")
    
    # alias for reverse compatibility
    read_AWGCyclesSet = get_awg_cycles

    #-------------------------------------------------

    def set_awg_cycles(self, awg: str, cycles: int) -> str:
        """
        Set the number of AWG cycles. Upon completing the set cycles, 
        the AWG is stopped

        Parameters:
        awg: AWG ("A", "B", "C" or "D")
        cycles: AWG cycles (0 - 4000000000)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-{awg} CS {cycles}")
    
    # alias for reverse compatibility
    write_AWGCyclesSet = set_awg_cycles
    
    #-------------------------------------------------

    def get_awg_trigger_mode(self, awg: str) -> str:
        """
        Read the external trigger mode of an AWG. The external trigger 
        can be disabled, only trigger the start, trigger the start and 
        stop or trigger each single step of an AWG

        Parameters:
        awg: AWG ("A", "B", "C" or "D")

        Returns:
        string: external trigger is disabled ("0"), only triggers the start
            of an AWG ("1"), triggers start and stop of an AWG ("2"), or
            triggers every single step of an AWG ("3")
        """

        return self.write(f"C AWG-{awg} TM?")
    
    # alias for reverse compatibility
    read_AWGExtTriggerMode = get_awg_trigger_mode

    #-------------------------------------------------

    def set_awg_trigger_mode(self, awg: str, mode: int) -> str: 
        """
        Set the external trigger mode of an AWG. The external trigger 
        can be disabled, only trigger the start, trigger the start and 
        stop or trigger each single step of an AWG

        Parameters:
        awg: AWG ("A", "B", "C" or "D")
        mode: external trigger is disabled ("0"), only triggers the start
            of an AWG ("1"), triggers start and stop of an AWG ("2"), or
            triggers every single step of an AWG ("3")

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-{awg} TM {mode}")
    
    # alias for reverse compatibility
    write_AWGExtTriggerMode = set_awg_trigger_mode

    #-------------------------------------------------

    def get_awg_clock_period(self, board: str) -> str:
        """
        Read the AWG clock period of a DAC board (AWG-A/B or AWG-C/D) 
        in us (micro-seconds)

        Parameters:
        board: DAC board ("AB" or "CD")

        Returns:
        string: clock period (10 us - 4000000000 us (micro-seconds))
        """

        return self.write(f"C AWG-{board} CP?")
    
    # alias for reverse compatibility
    read_AWGClkPeriod = get_awg_clock_period

    #-------------------------------------------------

    def set_awg_clock_period(self, board: str, period: int) -> str:
        """
        Set the AWG clock period of a DAC board (AWG-A/B or AWG-C/D) 
        in us (micro-seconds). It might influence or be influenced 
        by another AWG or the SWG

        Parameters:
        board: DAC board ("AB" or "CD")
        period: clock period (10 us - 4000000000 us (micro-seconds))

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-{board} CP {period}")
    
    # alias for reverse compatibility
    write_AWGClkPeriod = set_awg_clock_period
    
    #-------------------------------------------------

    def get_awg_refclock_state(self) -> str:
        """
        Read if the 1 MHz reference clock is on or off

        Returns:
        string: reference clock on or off ("on" or "off")
        """

        return self.write("C AWG-1MHz?")
    
    # alias for reverse compatibility
    read_AWGClkRefState = get_awg_refclock_state

    #-------------------------------------------------

    def set_awg_refclock_state(self, state: int) -> str: 
        """
        Turn the 1 MHz reference clock on or off

        Parameters:
        state: reference clock on ("1") or off ("0")

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C AWG-1MHz {state}")
    
    # alias for reverse compatibility
    write_AWGClkRefState = set_awg_refclock_state

    #-------------------------------------------------

    ##################################################

    # STANDARD WAVEFORM GENERATION CONTROL COMMANDS

    ##################################################

    #-------------------------------------------------

    def get_swg_mode(self) -> str:
        """
        Read the mode for the SWG (generate new waveform or use saved 
        waveform)

        Returns:
        string: generate new waveform (1) or use saved waveform (0)
        """

        return self.write("C SWG MODE?")
    
    # alias for reverse compatibility
    read_SWGMode = get_swg_mode

    #-------------------------------------------------

    def set_swg_mode(self, mode: int) -> str:
        """
        Set the mode for the SWG (generate new waveform or use saved 
        waveform)

        Parameters:
        mode: generate new waveform (1) or use saved waveform (0)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C SWG MODE {mode}")
    
    # alias for reverse compatibility
    write_SWGMode = set_swg_mode
    
    #-------------------------------------------------

    def get_swg_shape(self) -> str:
        """
        Read the shape of the SWG (sine, triangle, sawtooth, ramp, 
        pulse, noise or DC voltage)

        Returns:
        string: sine ("0"), triangle ("1"), sawtooth ("2"), ramp ("3"), 
            pulse ("4"), fixed noise ("5"), random noise ("6") 
            or DC voltage ("7")
        """

        return self.write("C SWG WF?")
    
    # alias for reverse compatibility
    read_SWGFunction = get_swg_shape

    #-------------------------------------------------

    def set_swg_shape(self, shape: int) -> str:
        """
        Set the shape of the SWG (sine, triangle, sawtooth, ramp, pulse, 
        noise or DC voltage)

        Parameters:
        shape: sine (0), triangle (1), sawtooth (2), ramp (3), pulse (4), 
            fixed noise (5), random noise (6) or DC voltage (7)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C SWG WF {shape}")
    
    # alias for reverse compatibility
    write_SWGFunction = set_swg_shape
   
    #-------------------------------------------------

    def get_swg_desired_frequency(self) -> str:
        """
        Read the set desired SWG frequency (0.001 Hz - 10 kHz). Not all 
        frequencies can be reached, dependent on the clock period

        Returns:
        string: desired frequency (0.001 Hz - 10 kHz)
        """

        return self.write("C SWG DF?")
    
    # alias for reverse compatibility
    read_SWGDesFrequency = get_swg_desired_frequency

    #-------------------------------------------------

    def set_swg_desired_frequency(self, frequency: int) -> str:
        """
        Set the desired SWG frequency (0.001 Hz - 10 kHz). Not all 
        frequencies can be reached, dependent on the clock period

        Parameters:
        frequency: desired frequency (0.001 Hz - 10 kHz)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """
         
        return self.write(f"C SWG DF {frequency}")
    
    # alias for reverse compatibility
    write_SWGDesFrequency = set_swg_desired_frequency
    
    #-------------------------------------------------

    def get_swg_adaptclock_state(self) -> str:
        """
        Read the state of the adaptive clock (keep AWG clock period or 
        adapt clock period). If set to adapt, the clock period gets 
        automatically adjusted to reach the desired frequency as close 
        as possible. This might affect the other AWG on the DAC board

        Returns:
        string: keep AWG clock period ("0") or adapt clock period ("1")
        """

        return self.write("C SWG ACLK?")
    
    # alias for reverse compatibility
    read_SWGApdativeClk = get_swg_adaptclock_state

    #-------------------------------------------------

    def set_swg_adaptclock_state(self, state: int) -> str:
        """
        Set the state of the adaptive clock (keep AWG clock period or 
        adapt clock period). If set to adapt, the clock period gets 
        automatically adjusted to reach the desired frequency as close 
        as possible. This might affect the other AWG on the DAC board

        Parameters:
        state: keep AWG clock period ("0") or adapt clock period ("1")

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C SWG ACLK {state}")
    
    # alias for reverse compatibility
    write_SWGAdaptiveClk = set_swg_adaptclock_state
    
    #-------------------------------------------------

    def get_swg_amplitude(self) -> str:
        """
        Read the set SWG amplitude (peak voltage). For noise this is 
        the RMS value

        Returns:
        string: amplitude (+/- 50.000000 V)
        """

        return self.write("C SWG AMP?")
    
    # alias for reverse compatibility
    read_SWGAmplitude = get_swg_amplitude

    #-------------------------------------------------

    def set_swg_amplitude(self, amplitude: float) -> str:
        """
        Set the SWG amplitude (peak voltage). For noise this is 
        the RMS value

        Parameters:
        amplitude: amplitude (+/- 50.000000 V)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C SWG AMP {amplitude:.6f}")
    
    # alias for reverse compatibility
    write_SWGAmplitude = set_swg_amplitude
    
    #-------------------------------------------------

    def get_swg_offset(self) -> str:
        """
        Set the SWG DC offset voltage

        Parameters:
        offset: DC offset voltage (+/- 10.000000 V)
        """

        return self.write("C SWG DCV?")
    
    # alias for reverse compatibility
    read_SWGDCOffset = get_swg_offset

    #-------------------------------------------------

    def set_swg_offset(self, offset: float) -> str:
        """
        Set the SWG DC offset voltage

        Parameters:
        offset: DC offset voltage (+/- 10.000000 V)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C SWG DCV {offset:.6f}")
    
    # alias for reverse compatibility
    write_SWGDCOffset = set_swg_offset
    
    #-------------------------------------------------

    def get_swg_phase(self) -> str:
        """
        Read the SWG phase shift. Not applacable to noise, ramp 
        and DC offset

        Returns:
        string: phase shift (+/- 360.0000°)
        """

        return self.write("C SWG PHA?")
    
    # alias for reverse compatibility
    read_SWGPhase = get_swg_phase

    #-------------------------------------------------

    def set_swg_phase(self, phase: float) -> str:
        """
        Set the SWG phase shift. Not applacable to noise, ramp 
        and DC offset

        Parameters:
        phase: phase shift (+/- 360.0000°)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C SWG PHA {phase:.4f}")
    
    # alias for reverse compatibility
    write_SWGPhase = set_swg_phase
    
    #-------------------------------------------------

    def get_swg_dutycycle(self) -> str:
        """
        Read the SWG duty cylce for the pulse waveform function. A high 
        level is applied for the set percentage of the waveforms period

        Returns:
        string: duty cycle (0.000 % - 100.000 %)
        """

        return self.write("C SWG DUC?")
    
    # alias for reverse compatibility
    read_SWGDutyCycle = get_swg_dutycycle

    #-------------------------------------------------

    def set_swg_dutycycle(self, dutycycle: float) -> str:
        """
        Set the SWG duty cylce for the pulse waveform function. A high 
        level is applied for the set percentage of the waveforms period

        Parameters:
        dutycycle: duty cycle (0.000 % - 100.000 %)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C SWG DUC {dutycycle:.3f}")
    
    # alias for reverse compatibility
    write_SWGDutyCycle = set_swg_dutycycle

    #-------------------------------------------------

    def get_swg_memory_size(self) -> str:
        """
        Read the size of the wave memory
        
        Returns:
        string: wave memory size (10 - 34000)
        """

        return self.write("C SWG MS?")
    
    # alias for reverse compatibility
    read_SWGMemSize = get_swg_memory_size

    #-------------------------------------------------

    def get_swg_nearest_frequency(self) -> str:
        """
        Read the actual SWG frequency (0.001 Hz - 10 kHz). 
        Since not all frequencies can be reached, the closest frequency 
        to the set desired frequency is internally calculated and used

        Returns:
        string: SWG frequency (0.001 Hz - 10 kHz)
        """
        return self.write("C SWG NF?")
    
    # alias for reverse compatibility
    read_SWGNearestFreq = get_swg_nearest_frequency

    #-------------------------------------------------

    def get_swg_clipping_status(self) -> str:
        """
        Read the waveform clipping status. If the waveform exceeds the 
        devices limits (+/- 10.0 V) anywhere, the waveform is clipping 
        
        Returns:
        string: waveform is clipping ("1") or not clipping ("0")
        """

        return self.write("C SWG CLP?")
    
    # alias for reverse compatibility
    read_SWGClippingStatus = get_swg_clipping_status
    
    #-------------------------------------------------

    def get_swg_clock_period(self) -> str:
        """
        Read the SWG clock period in us (micro seconds). This reads 
        the value that will be used during the waveform generation. 
        It is dependent on other settings of the device and might 
        influence or be influenced by another AWG

        Returns:
        string: clock period in us (micro seconds) (10 - 4000000000)
        """

        return self.write("C SWG CP?")
    
    # alias for reverse compatibility
    read_SWGClkPeriod = get_swg_clock_period
    
    #-------------------------------------------------

    def get_swg_wav_memory(self) -> str:
        """
        Read the selected wave memory into which the SWG saves the 
        generated waveform. Each AWG memory has an associated wave 
        memory ("A", "B", "C" or "D")

        Returns:
        string: selected wave memory A ("0"), B ("1"), C ("2") 
            or D ("3") 
        """

        return self.write("C SWG WMEM?")
    
    # alias for reverse compatibility
    read_SWGMemSelected = get_swg_wav_memory

    #-------------------------------------------------

    def set_swg_wav_memory(self, wav: int) -> str:
        """
        Select the wave memory into which the SWG saves the generated 
        waveform. Each AWG memory has an associated 
        wave memory ("A", "B", "C" or "D")

        Parameters:
        wav: select wave memory A (0), B (1), C (2) or D (3)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """
        
        return self.write(f"C SWG WMEM {wav}")
    
    # alias for reverse compatibility
    write_SWGMemSelected = set_swg_wav_memory
    
    #-------------------------------------------------

    def get_swg_selected_operation(self) -> str:
        """
        Read the selected wave memory operation that will be applied 
        with the command "Apply to wave memory now" 
        (apply_swg_operation()), represented by a number

        Returns:
        string: select operation "overwrite wave memory" ("0"), "append 
            to start of memory" ("1"), "append to end of memory" ("2"), 
            "sum to start of memory" ("3"), "sum to end of memory" ("4"), 
            "multiply to start of memory" ("5"), "multiply to end of 
            memory" ("6"), "divide to start of memory" ("7") 
            or "divide to end of memory" ("8")
        """

        return self.write("C SWG WFUN?")
    
    # alias for reverse compatibility
    read_SWGSelectedFunc = get_swg_selected_operation

    #-------------------------------------------------

    def set_swg_selected_operation(self, operation: int) -> str:
        """
        Select the wave memory operation that will be applied with the command 
        "Apply to wave memory now" (apply_swg_operation())

        Parameters:
        operation: select operation "overwrite wave memory" (0), "append 
            to start of memory" (1), "append to end of memory" (2), 
            "sum to start of memory" (3), "sum to end of memory" (4),
            "multiply to start of memory" (5), "multiply to end of 
            memory" (6), "divide to start of memory" (7) 
            or "divide to end of memory" (8)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """
        return self.write(f"C SWG WFUN {operation}")
    
    # alias for reverse compatibility
    write_SWGSelectedFunc = set_swg_selected_operation
    
    #-------------------------------------------------

    def get_swg_linearization_state(self) -> str:
        """
        Read if the output linearization will be applied, when writing 
        a wave memory's contents to its associated AWG memory

        Returns:
        string: apply linearization ("1") or do not apply 
            linearization ("0")
        """

        return self.write("C SWG LIN?")
    
    # alias for reverse compatibility
    read_SWGLinearization = get_swg_linearization_state

    #-------------------------------------------------

    def set_swg_linearization_state(self, state: int) -> str:
        """
        Set if the output linearization will be applied, when writing a 
        wave memory's contents to its associated AWG memory. A channel 
        must be assigned to the associated AWG

        Parameters:
        state: apply linearization (1) or do not apply linearization (0)

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C SWG LIN {state}")
    
    # alias for reverse compatibility
    write_SWGLinearization = set_swg_linearization_state
    
    #-------------------------------------------------

    def apply_swg_operation(self) -> str:
        """
        The selected SWG operation is applied to the selected wave memory

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write("C SWG APPLY")
    
    # alias for reverse compatibility
    apply_SWGFunction = apply_swg_operation
    
    #-------------------------------------------------

    ##################################################

    # WAVE CONTROL COMMANDS

    ##################################################

    #-------------------------------------------------

    def get_wav_memory_size(self, wav: str) -> str:
        """
        Read the size of a wave memory ("A", "B", "C", "D" or "S")

        Parameters:
        wav: wave memory ("A", "B", "C", "D" or "S")
        """

        return self.write(f"C WAV-{wav} MS?")
    
    # alias for reverse compatibility
    read_WAVMemSize = get_wav_memory_size
    
    #-------------------------------------------------

    def clear_wav_memory(self, wav: str) -> str:
        """
        Clear all contents of a wave memory. The memory size is 
        internally reset to 0

        Parameters:
        wav: wave memory ("A", "B", "C", "D" or "S")

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C WAV-{wav} CLR")
    
    # alias for reverse compatibility
    clear_WAVMem = clear_wav_memory
    
    #-------------------------------------------------

    def save_wav_memory(self, wav: str) -> str:
        """
        Save all contents of a wave memory ("A", "B", "C" or "D") 
        to the internal volatile "WAV-S" memory

        Parameters:
        wav: wave memory ("A", "B", "C" or "D") to copy

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C WAV-{wav} SAVE")
    
    # alias for reverse compatibility
    save_WAVMem = save_wav_memory
    
    #-------------------------------------------------

    def get_wav_linearization_channel(self, wav: str) -> str:
        """
        Read which DAC channel is associated to a wave memory. The 
        output linearization will be applied to this channel when 
        the wave memory is written to the associated AWG memory

        Parameters:
        wav: wave memory ("A", "B", "C" or "D")

        Returns:
        string: associated channel for linearization ("1" - "24"), 
            "0" if no linearization will be applied
        """

        return self.write(f"C WAV-{wav} LINCH?")
    
    # alias for reverse compatibility
    read_WAVMemLinChannel = get_wav_linearization_channel
    
    #-------------------------------------------------
    
    def write_wav_to_awg(self, wav_awg: str) -> str:
        """
        Write all contents of a wave memory to its associated AWG memory.
        The "WAV-S" memory can not be written directly to an AWG memory

        Parameters:
        wav_awg: wave/ AWG memory ("A", "B", "C" or "D")

        Returns:
        string: DAC-Error Code ("0" - "5"). "0" is always "no error"
        """

        return self.write(f"C WAV-{wav_awg} WRITE")
    
    # alias for reverse compatibility
    write_WAVMemToAWGMem = write_wav_to_awg

    #-------------------------------------------------

    def get_wav_memory_busy(self, wav: str) -> str:
        """
        Read the state of the wave memory busy flag. If set, 
        the wave memory is written to its associated AWG memory

        Parameters: 
        wav: wave/ AWG memory ("A", "B", "C" or "D")

        Returns:
        string: wave memonry busy ("1") or not busy ("0")
        """

        return self.write(f"C WAV-{wav} BUSY?")
    
    # alias for reverse compatibility
    read_WAVBusyWriting = get_wav_memory_busy

    #-------------------------------------------------

    ##################################################

    # SPECIAL AND COMPOUND FUNCTIONS

    ##################################################

    #-------------------------------------------------

    def set_newWaveform(self, channel = '12', waveform = '0', frequency = '100.0', 
                        amplitude = '5.0', wavemem = '0'):
        """
        Write the Standard Waveform Function to be generated
        - Channel: [1 ... 24]
        Note: AWG-A and AWG-B only DAC-Channel[1...12], AWG-C and AWG-D only DAC-Channel[13...24]
        - Waveforms: 
            0 = Sine function, for a Cosine function select a Phase [°] of 90°
            1 = Triangle function
            2 = Sawtooth function
            3 = Ramp function
            4 = Pulse function, the parameter Duty-Cycle is applied
            5 = Gaussian Noise (Fixed), always the same seed for the random/noise-generator
            6 = Gaussian Noise (Random), random seed for the random/noise-generator
            7 = DC-Voltage only, a fixed voltage is generated
        - Frequency: AWG-Frequency [0.001 ... 10.000]
        - Amplitude: [-50.000000 ... 50.000000]
        - Wave-Memory (WAV-A/B/C/D) are represented by 0/1/2/3 respectively
        """
        memsave = ''
        if (wavemem == '0'):
            memsave = 'A'
        elif (wavemem == '1'):
            memsave = 'B'
        elif (wavemem == '2'):
            memsave = 'C'
        elif (wavemem == '3'):
            memsave = 'D'

        self.write('C WAV-B CLR') # Wave-Memory Clear.
        self.write('C SWG MODE 0') # generate new Waveform.
        self.write('C SWG WF ' + waveform) # set the waveform.
        self.write('C SWG DF ' + frequency) # set frequency.
        self.write('C SWG AMP ' + amplitude) # set the amplitude.
        self.write('C SWG WMEM ' + wavemem) # set the Wave-Memory.
        self.write('C SWG WFUN 0') # COPY to Wave-MEM -> Overwrite.
        self.write('C SWG LIN ' + channel) # COPY to Wave-MEM -> Overwrite.
        self.write('C AWG-' + memsave + ' CH ' + channel) # Write the Selected DAC-Channel for the AWG.
        self.write('C SWG APPLY') # Apply Wave-Function to Wave-Memory Now.
        self.write('C WAV-' + memsave + ' SAVE') # Save the selected Wave-Memory (WAV-A/B/C/D) to the internal volatile memory.
        self.write('C WAV-' + memsave + ' WRITE') # Write the Wave-Memory (WAV-A/B/C/D) to the corresponding AWG-Memory (AWG-A/B/C/D).
        self.write('C AWG-' + memsave + ' START') # Apply Wave-Function to Wave-Memory Now.

    #-------------------------------------------------

    def scan1D(self, param, start, stop, num_points, delay, measured_param):
        """
        Creates a linear scan of the given parameter (for example a DAC channel), from a START value
        to a STOP value, with num_points pauses/measurements. A time delay is made before a measured 
        dependent parameter is read and stored into a list.  The list is returned after the scan.
        @param - the independent parameter.  Must have a set() method
        @start - the starting value for the scan
        @stop - the stopping value for the scan
        @num_points - the number of points within the scan.
        @delay - the time to pause at each point before reading any dependent parameters.
        @measured_param - the dependent parameter to measure.  Must have a get() method.
        """
        data = [] 
        increment = (stop - start) / (num_points-1)
        current = start
        
        values = []
        for i in range(num_points - 1):
            values.append(current)
            current += increment
        values.append(stop)
        for val in values:
            param.set(val)
            sleep(delay)
            m = measured_param.get()
            print(m)
            data.append(m)
        return data

    #-------------------------------------------------

    def scan2D(self, param1, start1, stop1, num_points1, delay1, param2, start2, stop2, num_points2, delay2, measured_params_list):
        """
        Creates a 2D linear scan of two independent parameters.  The "outer-loop" parameter is param1, and runs through it's
        scan only once. The "inner-loop" parameter, param2, runs through a scan each time param1 steps. At each step, 
        the dependent parameters, stored in a list, are read and recorded.
        @param1 - the independent outer-loop parameter.  Must have a set() method
        @start1 - the starting value for the outer scan
        @stop1 - the stopping value for the outer scan
        @num_points1 - the number of points within the outer scan.
        @delay1 - the time to pause at each point of the outer scan before reading any dependent parameters.
        @param2 - the independent inner-loop parameter.  Must have a set() method
        @start2 - the starting value for the inner scan
        @stop2 - the stopping value for the inner scan
        @num_points2 - the number of points within the inner scan.
        @delay2 - the time to pause at each point of the inner scan before reading any dependent parameters.
        @measured_params_list - a list of dependent parameters. Each must have a get() method
        """
        data = [] # return variable
        increment1 = (stop1 - start1) / (num_points1 - 1)
        increment2 = (stop2 - start2) / (num_points2 - 1)

        current1 = start1
        current2 = start2
        values1 = []
        values2 = []
        for i in range(num_points1 - 1):
            values1.append(current1)
            current1 += increment1
        values1.append(stop1)
        for i in range(num_points2 - 1):
            values2.append(current2)
            current2 += increment2
        values2.append(stop2)
        
        for val1 in values1:
            param1.set(val1)
            sleep(delay1)
            line_data = []
            for val2 in values2:
                param2.set(val2)
                sleep(delay2)
                data_point = []
                for p in measured_params_list:
                    data_point.append(p.get())
                line_data.append(tuple(data_point))
            # append data list for scan line into return variable
            data.append(line_data)
        return data

    #-------------------------------------------------

    def handleDACSetErrors(self, code):
        num = int(code)
        if num == 0:
            return num
        elif num == 1:
            print("Invalid DAC-Channel")
        elif num == 2:
            print("Missing DAC-Value, Status or BW")
        elif num == 3:
            print("DAC-Value out of range")
        elif num == 4:
            print("Mistyped")
        elif num == 5:
            print("Writing not allowed (Ramp/Step-Generator or AWG are running on this DAC-Channel)")
        return num

    #-------------------------------------------------

    def handleAWGSetErrors(self, code):
        num = int(code)
        if num == 0:
            return num
        if num == 1:
            print("Invalid AWG-Memory")
        elif num == 2:
            print("Missing AWG-Address and/or AWG-Value")
        elif num == 3:
            print("AWG-Address and/or AWG-Value out of range")
        elif num == 4:
            print("Mistyped")
        return num

    #-------------------------------------------------

    def handleWAVSetErrors(self, code):
        num = int(code)
        if num == 0:
            return num
        if num == 1:
            print("Invalid WAV-Memory")
        elif num == 2:
            print("Missing WAV-Address and/or WAV-Voltage")
        elif num == 3:
            print("WAV-Address and/or WAV-Voltage out of range")
        elif num == 4:
            print("Mistyped")
        return num

    #-------------------------------------------------

    def handlePOLYSetErors(self, code):
        num = int(code)
        if num == 0:
            return num
        if num == 1:
            print("Invalid Polynomial Name")
        elif num == 2:
            print("Missing Polynomial Coefficient(s)")
        elif num == 4:
            print("Mistyped")
        return num

    #-------------------------------------------------

    def handleCONTROLWriteErrors(self, code):
        num = int(code)
        if num == 0:
            return num
        if num == 1:
            print("Invalid DAC-Channel")
        elif num == 2:
            print("Invalid Parameter")
        elif num == 4:
            print("Mistyped")
        elif num == 5:
            print("Writing not allowed")

    #-------------------------------------------------


# main -----------------------------------------------------------------

if __name__ == "__main__":

    # connect to DAC using the VISA resources as per NI MAX
    dac = SP1060('LNHRDAC', 'TCPIP0::192.168.0.5::23::SOCKET')

    # small testing script to check if the general 
    # behaviour of the driver stays the same
    print()
    res = dac.all_off()
    print(res)
    sleep(1)
    res = dac.all_on()
    print(res)
    sleep(1)
    res = dac.all_off()
    print(res)
    sleep(1)
    res = dac.set_chan_voltage(25, 5000)

    dac.handleDACSetErrors(res)

    res = dac.all_on()
    print(res)
    sleep(1)
    res = dac.all_off()
    print(res)
    dac.handleDACSetErrors(res)
    sleep(1)
    print(type(res))

    res = dac.get_all_status()
    print(res)
    print(type(res))



    
