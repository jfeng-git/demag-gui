# virtual_instruments.py
import random
from qcodes import VisaInstrument
from qcodes import Instrument

class NMR(Instrument):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, **kwargs)
        self.add_parameter('M0', get_cmd=self._ramdn)
        self.add_parameter('TmK', get_cmd=self._ramdn)
        self.add_parameter('KnownM0_A', get_cmd=self._ramdn)
        self.add_parameter('KnownT_A', get_cmd=self._ramdn)

    def _ramdn(self):
        return random.uniform(73, 74.55)

class AH2500A(Instrument):
    def __init__(self, name, address, **kwargs):

        super().__init__(name, **kwargs)
        self.add_parameter(
            'C',
            get_cmd=self.get_C
        )
        self.add_parameter(
            'L',
            get_cmd=self.get_L
        )

    def get_C(self):
        return random.uniform(73, 74.55)
    
    def get_L(self):
        return random.uniform(0.001, 0.1)
    
    def close(self):
        pass

class MLP:
    def __init__(self, name, address):
        pass
    def close(self):
        pass

class OxfordMercuryiPS(Instrument):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, **kwargs)
        pass


    def close(self):
        pass

class UDP:
    def __init__(self, name, address):
        pass
    def close(self):
        pass