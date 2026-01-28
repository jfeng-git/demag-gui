# measurements.py
import importlib
import time
from datetime import datetime

import qcodes as qc
from qcodes.dataset import (
    Measurement,
    initialise_or_create_database_at,
    load_or_create_experiment,
)
from qcodes.parameters import ElapsedTimeParameter

# ============ Measurement function whitelist ============
MEASUREMENT_WHITELIST = [
    'RampField',
    'MonitorConnectedInstruments',
    'TemperatureSweep',
    'HeatLeak'
]

def reload_measurements_module():
    """Reload measurements module"""
    from demag_gui.utils import measurements
    importlib.reload(measurements)
    return measurements, True

def get_all_measurements():
    """Get all measurement functions from whitelist"""
    measurements_module, reloaded = reload_measurements_module()
    
    functions = []
    for name in MEASUREMENT_WHITELIST:
        if hasattr(measurements_module, name):
            func = getattr(measurements_module, name)
            doc = func.__doc__ or "No description"
            functions.append((name, doc))
    
    return functions, reloaded


def MonitorConnectedInstruments(mct_panel, nmr_panel, mips_panel, hs_panel, stop_callback=None, **kwargs):
    """
    Monitor readings from connected instruments using displayed values from UI panels
    
    Args:
        mct_panel: MCT control panel object with display widgets
        nmr_panel: NMR control panel object with display widgets
        mips_panel: MIPS control panel object with display widgets
        hs_panel: HS control panel object with display widgets
        **kwargs: Additional parameters
    """

    # Get parameters
    database_path = kwargs.get('database_path', "testdata/Monitor.db")
    experiment_name = kwargs.get('experiment_name', f"Monitor-{datetime.now().strftime('%Y-%m-%d_%H%M%S')}")
    interval = kwargs.get('interval', 0.35)
    
    # QCoDeS database initialization
    initialise_or_create_database_at(database_path)
    experiment = load_or_create_experiment(
        experiment_name=experiment_name,
        sample_name="no sample"
    )

    # Create measurement station and time parameter (like RealMeasurement)
    station = qc.Station()
    t = ElapsedTimeParameter("t")
    station.add_component(t)

    monitor_params = {}

    # Build parameters from panel displays (prefer UI textboxes — stable even without drivers)
    if mct_panel.mct_instrument:
        mct_dict = {
            'mct_C': {'instrument': mct_panel.mct_instrument.C, 'get':mct_panel.cap_display.displayText},
            'mct_L': {'instrument': mct_panel.mct_instrument.L, 'get': mct_panel.loss_display.displayText},
        }
        for p in mct_dict.values():
            station.add_component(p['instrument'])
        monitor_params.update(mct_dict)

    if nmr_panel.nmr:
        nmr_dict = {
            'M0': {
                'instrument': nmr_panel.nmr.M0,
                'get': nmr_panel.m0_label.text
            },
            'L': {
                'instrument': nmr_panel.nmr.TmK,
                'get': nmr_panel.t_label.text
            }
        }
        for p in nmr_dict.values():
            station.add_component(p['instrument'])
        monitor_params.update(nmr_dict)

    if mips_panel.mips_instrument:
        mips_dict = {
            'field_persistent': {
                'instrument': mips_panel.mips_instrument.GRPZ.field_persistent,
                'get': mips_panel.bpersistent_display
            },
            'field': {
                'instrument': mips_panel.mips_instrument.GRPZ.field,
                'get': mips_panel.bout_display
            },
        }
        for p in mips_dict.values():
            station.add_component(p['instrument'])
        monitor_params.update(mips_dict)
    #
    # if hs_panel:
    #     try:
    #         cur = _display_parameter("HS_Current", "Current", "A", hs_panel.current_display)
    #         station.add_component(cur)
    #         monitor_params.update({"HS_I": cur})
    #     except Exception:
    #         pass

    # Create measurement context and register parameters (time as independent)
    context_meas = Measurement(exp=experiment, station=station, name="monitor temperature")
    indeps = (t,)
    deps = list(monitor_params.values())

    for indep in indeps:
        context_meas.register_parameter(indep)
    for dep in deps:
        context_meas.register_parameter(dep['instrument'], setpoints=indeps)

    with context_meas.run() as datasaver:
        t.reset_clock()
        while True:
            if stop_callback and stop_callback():
                return 'Measurement stopped.'

            results = []
            for dev in indeps:
                results.append((dev, dev()))
            for dev in deps:
                results.append((dev['instrument'], float(dev['get']())))

            datasaver.add_result(*results)

            time.sleep(interval)

# Placeholder functions (add your implementations here)


def run_measurement(func_name, mct_panel=None, nmr_panel=None, mips_panel=None, hs_panel=None,
                   mct=None, nmr=None, mips=None, hs=None, **kwargs):
    """
    Run selected measurement function
    
    Args:
        func_name: Name of measurement function
        mct_panel, nmr_panel, mips_panel, hs_panel: Instrument panel objects
        mct, nmr, mips, hs: Instrument objects
        **kwargs: Additional parameters
    """
    # Reload module to get latest functions
    measurements_module, reloaded = reload_measurements_module()
    
    if hasattr(measurements_module, func_name):
        func = getattr(measurements_module, func_name)
        try:
            # Pass appropriate objects
            if func_name == "MonitorConnectedInstruments":
                result = func(mct_panel, nmr_panel, mips_panel, hs_panel, **kwargs)
            else:
                result = func(mct, nmr, mips, hs, **kwargs)
            return result
        except Exception as e:
            return f"Error in {func_name}: {str(e)}"
    else:
        return f"Function {func_name} not found"