%load_ext autoreload
%autoreload 2 

import numpy as np
import qcodes as qc
from qcodes.dataset import (
    Measurement,
    dond,
    do1d,
    experiments,
    initialise_or_create_database_at,
    load_by_run_spec,
    load_or_create_experiment,
    plot_dataset,
    ArraySweep
)
from qcodes.parameters import ElapsedTimeParameter, Parameter

from time import sleep
import re
import matplotlib.pyplot as plt
from qcodes.instrument_drivers.oxford import OxfordMercuryiPS

from time import time
from datetime import datetime

import sys
import os
from pathlib import Path

current_dir = Path(os.getcwd())  
parent_dir = current_dir.parent.parent/ 'UserFunctions'
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))


from Tools.DemagCalculator import MCT_calculator
from MeasurementFunctions.TimeControls import timming
mct =  MCT_calculator()


initialise_or_create_database_at("D:/Data/Experiments/0.Data/Demag.db")
Demag = load_or_create_experiment(
    experiment_name="Demag-2026-01-02", sample_name="nosample"
)

station = qc.Station()
instrs = [t, ah2500, mips.GRPZ.field_persistent, nmr]
for instr in instrs:
    station.add_component(instr)
context_meas = Measurement(exp=Demag, station=station, name="starting")


t = ElapsedTimeParameter("t")
mips = OxfordMercuryiPS("mips", "TCPIP0::10.18.18.9::7020::SOCKET")
ah2500 = AH2500A('AH2500A', 'GPIB0::28::INSTR')
# model715 = Model715('model715', 'ASRL1::INSTR')
HS = UDP5303('HeatSwitch', 'ASRL3::INSTR')
# kelvinox = Triton('kelvinox', address="10.18.18.11", port=33576)
nmr = NMR("nmr", 'GPIB1::22::INSTR')

context_meas.name = 'go to minimum'

indeps = (t, )
deps = [ah2500.C, mips.GRPZ.field_persistent, nmr.TmK, nmr.M0]
# deps = [ah2500.C, mips.GRPZ.field_persistent]
sn = station.snapshot()

for indep in indeps:
    context_meas.register_parameter(indep)
for dep in deps:
    context_meas.register_parameter(dep, setpoints=indeps)
    
with context_meas.run() as datasaver:
    t.reset_clock()
    def get_data(trigger=0.3):
        results = [(dev, dev()) for dev in list(indeps) + list(deps)]
        datasaver.add_result(
            *results
        )
        sleep(trigger)
    print('keep reading data')
    while True:
        get_data()