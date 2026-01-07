# ----------------------------------------------------------------------------------------------------------------------------------------------
# LNHR DAC II Telnet driver (Python)
# v0.1.0
# Copyright (c) Basel Precision Instruments GmbH (2024)
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the 
# Free Software Foundation, either version 3 of the License, or any later version. This program is distributed in the hope that it will be 
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
# General Public License for more details. You should have received a copy of the GNU General Public License along with this program.  
# If not, see <https://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------------------------------------------------------------------------

# imports --------------------------------------------------------------

import numpy as np
from qcodes.instrument.parameter import Parameter
from qcodes.utils.validators import Numbers
from typing import Optional, List

# class ----------------------------------------------------------------

class GateParameter(Parameter):
    """
    This class helps to set an d sweep DC voltages
    """
    def __init__(self, param, name, value_range, unit: Optional[str]='V', 
                 scaling: Optional[float]=1, offset: Optional[float]=0):
        
        super().__init__(name=name, instrument=param.instrument, unit=unit,
                         vals=Numbers(value_range[0], value_range[1]))
    
        self.param = param
        self.scaling = scaling
        self.offset = offset
        self.vals = Numbers(value_range[0], value_range[1])
        
    def get_raw(self):
        return self.param.get()
    
    def set_raw(self,val):
        dacval = self.scaling*val+self.offset
        self.vals.validate(dacval)
        self.param.set(dacval)
        
    def range(self, value_range):
        self.vals = Numbers(value_range[0], value_range[1])
        
# class ----------------------------------------------------------------

class VirtualGateParameter(Parameter):
    """
    This class is used to combine multiple GateParameter objects
    """
    def __init__(self, name, params, set_scaling, 
                 offsets: Optional[List[float]]=None, 
                 get_scaling: Optional[float]=1 ):
        
        super().__init__(name=name, instrument=params[0].instrument, 
                         unit=params[0].unit)
        
        self.params = params
        self.set_scaling = set_scaling
        self.get_scaling = get_scaling
        
        if offsets is None:
            self.offsets = np.zeros(len(params))
        else:
            self.offsets = offsets
            
    def get_raw(self):
        return self.get_scaling*self.params[0].get()
        
    def set_raw(self, val):
        for i in range(len(self.params)):
            dacval = self.set_scaling[i]*val+self.offsets[i]
            self.params[i].set(dacval)
            
    def get_all(self):
        values = []
        keys = []
        for param in self.params:
            values.append(param.get())
            keys.append(param.name)
        return dict(zip(keys, values))   

        
