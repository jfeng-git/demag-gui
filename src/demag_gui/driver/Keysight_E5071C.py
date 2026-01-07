from typing import Union
from functools import partial
import logging

import numpy as np

from qcodes.instrument.visa import VisaInstrument
from qcodes.instrument.parameter import ArrayParameter
import qcodes.utils.validators as vals

from qcodes.utils.helpers import create_on_off_val_mapping

log = logging.getLogger(__name__)

_unit_map = {
    'Log mag': 'dB',
    'Phase': 'degree',
    'Delay': None,
    'Smith chart': 'dim. less',
    'Polar': 'dim. less',
    'Lin mag': 'dim. less',
    'Real': None,
    'Imaginary': None,
    'SWR': 'dim. less'
}

#
# class TraceNotReady(Exception):
#   pass


class E5071C(VisaInstrument):
    """
Keysight E5071C driver
    """

    # all instrument constructors should accept **kwargs and pass them on to
    # super().__init__
    def __init__(self, name, address, **kwargs):

        super().__init__(name=name, address=address, terminator='\n', **kwargs)

        # Working
        self.add_parameter('start_frequency',
                           label='Sweep start frequency',
                           unit='Hz',
                           set_cmd=':SENS1:FREQ:STAR {}',
                           get_cmd=':SENS1:FREQ:STAR?',
                           get_parser=VISA_str_to_int,
                           vals=vals.Numbers(3e5, 20e9))

        self.add_parameter('trigger_source',
                           label='Trigger Source',
                           set_cmd=':TRIG:SOUR {}',
                           get_parser=VISA_str_to_int,
                           get_cmd=':TRIG:SOUR?')

        self.add_parameter('sweep_type',
                           label='Sweep Type',
                           get_parser=VISA_str_to_int,
                           set_cmd=':SENS1:SWE:TYPE {}',
                           get_cmd=':SENS1:SWE:TYPE?')

        # Working
        self.add_parameter('stop_frequency',
                           label='Sweep stop frequency',
                           unit='Hz',
                           set_cmd=':SENS1:FREQ:STOP {}',
                           get_cmd=':SENS1:FREQ:STOP?',
                           get_parser=VISA_str_to_int,
                           vals=vals.Numbers(3e5, 20e9))

        self.add_parameter('continuous_mode_all',
                           label='Continuous Mode',
                           get_parser=VISA_str_to_int,
                           set_cmd=':INIT1:CONT {}',
                           get_cmd=':INIT1:CONT?')

        self.add_parameter('min_sweep_time',
                           label='Min Sweep Time',
                           get_parser=VISA_str_to_int,
                           set_cmd=':SENS1:SWE:TIME:AUTO ON',
                           get_cmd=':SENS1:SWE:TIME:AUTO?')

        # Working
        self.add_parameter('center_frequency',
                           label='Center frequency',
                           unit='Hz',
                           get_parser=VISA_str_to_int,
                           set_cmd=':SENS1:FREQ:CENT {}',
                           get_cmd=':SENS1:FREQ:CENT?',
                           vals=vals.Numbers(3e5, 20e9))

        self.add_parameter('span_frequency',
                           label='Span frequency',
                           unit='Hz',
                           get_parser=VISA_str_to_int,
                           set_cmd=':SENS1:FREQ:SPAN {}',
                           get_cmd=':SENS1:FREQ:SPAN?',
                           vals=vals.Numbers(1, 5.9e9))

        self.add_parameter(name='averaging',
                           label='Averaging state',
                           set_cmd=':SENS1:AVER {};',
                           get_cmd=':SENS1:AVER?',
                           val_mapping={
                               'ON': 1,
                               'OFF': 0
                           })

        self.add_parameter(name='trigger_averaging',
                           label='trigger averaging state',
                           set_cmd=':TRIG:AVER {};',
                           get_cmd=':TRIG:AVER?',
                           val_mapping={
                               'ON': 1,
                               'OFF': 0
                           })

        self.add_parameter(name='n_avg',
                           unit='',
                           label='Number of averages',
                           get_parser=VISA_str_to_int,
                           set_cmd=':SENS1:AVER:COUN {}',
                           get_cmd=':SENS1:AVER:COUN?',
                           vals=vals.Numbers(1, 1000))

        self.add_parameter(name='bandwidth',
                           label='Bandwidth',
                           get_parser=VISA_str_to_int,
                           unit='Hz',
                           get_cmd='SENS1:BAND?',
                           set_cmd='SENS1:BAND {}',
                           vals=vals.Numbers(1, 1e6))

        # Working
        self.add_parameter('avg',
                           label='Number of averages',
                           set_cmd=':SENSe:AVERage:COUNt {}',
                           get_cmd=':SENSe:AVERage:COUNt?',
                           get_parser=VISA_str_to_int,
                           vals=vals.Ints(0, 999))

        self.add_parameter('npts',
                           label='Number of points in trace',
                           set_cmd=':SENS1:SWE:POIN {}',
                           get_cmd=':SENS1:SWE:POIN?',
                           get_parser=VISA_str_to_int,
                           vals=vals.Ints(1, 100001))

        self.add_parameter('sweep_time',
                           label='Sweep time',
                           set_cmd=':SENS1:SWE:TIME {}',
                           get_cmd=':SENS1:SWE:TIME?',
                           get_parser=VISA_str_to_float,
                           unit='s',
                           vals=vals.Numbers(0.01, 86400))

        self.add_parameter('power',
                           label='Output power',
                           unit='dBm',
                           set_cmd=':SOUR1:POW {}',
                           get_cmd=':SOUR1:POW?',
                           get_parser=VISA_str_to_float,
                           vals=vals.Numbers(-85, 20))

        self.add_parameter('status',
                           label='RF Output',
                           get_cmd=':OUTP:STAT?',
                           set_cmd=':OUTP:STAT {}',
                           val_mapping=create_on_off_val_mapping(on_val='1',
                                                                 off_val='0'))

        self.add_parameter(
            'calibration_state',
            label='calibration state',
            set_cmd=':SENS1:CORR:STAT {}',
            get_cmd=':SENS1:CORR:STAT?',
            val_mapping={'ON': 1, 'OFF': 0})

        self.add_parameter('S_parameter',
                           label='S_parameter',
                           set_cmd=':CALC1:PAR1:DEF {}',
                           get_cmd=':CALC1:PAR1:DEF?')

        self.add_function('reset', call_cmd='*RST')

        self.add_function('autoscale_trace',
                          call_cmd=':DISP:WIND1:TRAC1:Y:AUTO')

        # it's a good idea to call connect_message at the end of your constructor.
        # this calls the 'IDN' parameter that the base Instrument class creates for
        # every instrument (you can override the `get_idn` method if it doesn't work
        # in the standard VISA form for your instrument) which serves two purposes:
        # 1) verifies that you are connected to the instrument
        # 2) gets the ID info so it will be included with metadata snapshots later.
        self.connect_message()

    def invalidate_trace(self, cmd: str,
                         value: Union[float, int, str]) -> None:
        """
        Wrapper for set_cmds that make the trace not ready
        """
        self._traceready = False
        self.write(cmd.format(value))

    # def start_sweep_all(self):
    #     # self.write('ABORT')
    #     self.write('ABORT;:INITIATE:IMMEDIATE')
    #     self.write(':TRIG:SOUR BUS')
    #     self.write(':TRIG:SING')
    #     self.write('*WAI')
    #     print('measuring')
    #     print(self.ask('*OPC?'))
    #     print('measurement done')

    def start_sweep_all(self):
        # self.write('ABORT')
        self.write(':TRIG:SOUR BUS')
        self.write(':INIT1:CONT ON')
        self.write(':TRIG:SING')
        self.ask('*OPC?')
        # self.write('*WAI')
        # print('measuring')
        # print(self.ask('*OPC?'))
        # print('measurement done')

    # def wait_to_continue(self):
    #     return self.ask('*OPC?')

    def prepare_trace(self):
        """
        Update setpoints, units and labels
        """

        # we don't trust users to keep their fingers off the front panel,
        # so we query the instrument for all values

        fstart = self._instrument.start_freq()
        fstop = self._instrument.stop_freq()
        npts = self._instrument.trace_points()

        sps = np.linspace(fstart, fstop, npts)
        self.setpoints = (tuple(sps), )
        self.shape = (len(sps), )

        self.label = self._instrument.s_parameter()
        self.unit = _unit_map[self._instrument.display_format()]

        self._instrument._traceready = True

    def SetActiveTrace(self, mystr, ch=1):
        # self.write('CALC{}:PAR:SEL "{}"'.format(ch, mystr))
        self.write('CALC{}:PAR:SEL "{}"')

    def get_real_imaginary_data(self, ch=1):
        # data_str = self.ask(":CALC1:DATA:SDAT?".format(ch))
        data_str = self.ask(':CALC1:DATA:SDAT?')
        data_double = np.array(data_str.split(','), dtype=np.double)

        real_data = data_double[::2]
        imag_data = data_double[1::2]

        return real_data, imag_data

    def get_stimulus(self, ch=1):
        # freq = self.ask(':SENS1:FREQ:DATA?'.format(ch))
        freq = self.ask(':SENS1:FREQ:DATA?')
        freq = np.asarray([float(xx) for xx in freq.split(',')])
        return freq

    def on(self):
        self.status('on')

    def off(self):
        self.status('off')


def VISA_str_to_int(message):
    return int(float(message.strip('\\n')))


def VISA_str_to_float(message):
    return float(message.strip('\\n'))
