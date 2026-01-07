# measurements.py
from datetime import datetime
import numpy as np
import time
import qcodes as qc
from qcodes.dataset import (
    Measurement,
    initialise_or_create_database_at,
    load_or_create_experiment,
)
from qcodes.parameters import ElapsedTimeParameter, Parameter
import importlib

# ============ Measurement function whitelist ============
MEASUREMENT_WHITELIST = [
    'RampField',
    'MonitorConnectedInstruments',
    'TemperatureSweep',
    'HeatLeak'
]

def reload_measurements_module():
    """Reload measurements module"""
    try:
        import measurements
        importlib.reload(measurements)
        return measurements, True
    except Exception:
        import measurements
        return measurements, False

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


def MonitorConnectedInstruments(mct_panel, nmr_panel, mips_panel, hs_panel, signals=None, **kwargs):
    """
    Monitor readings from connected instruments using displayed values from UI panels
    
    Args:
        mct_panel: MCT control panel object with display widgets
        nmr_panel: NMR control panel object with display widgets
        mips_panel: MIPS control panel object with display widgets
        hs_panel: HS control panel object with display widgets
        signals: MeasurementSignals object for UI updates
        **kwargs: Additional parameters
    """
    if signals:
        signals.status_updated.emit("Starting monitoring of connected instruments...")
    
    # Get parameters
    duration = kwargs.get('duration', 3600)  # seconds
    interval = kwargs.get('interval', 5)  # seconds
    database_path = kwargs.get('database_path', "D:/Data/Experiments/0.Data/Monitor.db")
    experiment_name = kwargs.get('experiment_name', f"Monitor-{datetime.now().strftime('%Y-%m-%d_%H%M%S')}")
    
    try:
        # QCoDeS database initialization
        initialise_or_create_database_at(database_path)
        experiment = load_or_create_experiment(
            experiment_name=experiment_name,
            sample_name="monitoring"
        )

        # Create measurement station and time parameter (like RealMeasurement)
        station = qc.Station()
        t = ElapsedTimeParameter("t")
        station.add_component(t)

        # Helper to create a Parameter that reads from a panel widget's text()
        def _display_parameter(name, label, unit, widget, index=0):
            p = Parameter(name=name, label=label, unit=unit)
            def _get():
                try:
                    text = widget.text()
                    if text and text not in ("Unknown", "Error"):
                        parts = text.split()
                        return float(parts[index]) if parts else np.nan
                except Exception:
                    pass
                return np.nan
            p.get = _get
            return p

        monitor_params = {}

        # Build parameters from panel displays (prefer UI textboxes — stable even without drivers)
        if mct_panel:
            try:
                cap = _display_parameter("MCT_Capacitance", "Capacitance", "F", mct_panel.cap_display)
                loss = _display_parameter("MCT_Loss", "Loss", "", mct_panel.loss_display)
                temp = _display_parameter("MCT_Temperature", "Temperature", "mK", mct_panel.temp_display)
                for p in (cap, loss, temp):
                    station.add_component(p)
                monitor_params.update({"MCT_C": cap, "MCT_L": loss, "MCT_T": temp})
            except Exception:
                pass

        if nmr_panel:
            try:
                m0 = _display_parameter("NMR_M0", "M0", "", nmr_panel.m0_display)
                nt = _display_parameter("NMR_Temperature", "Temperature", "mK", nmr_panel.temp_display)
                for p in (m0, nt):
                    station.add_component(p)
                monitor_params.update({"NMR_M0": m0, "NMR_T": nt})
            except Exception:
                pass

        if mips_panel:
            try:
                field = _display_parameter("MIPS_Field", "Field", "T", mips_panel.field_display)
                station.add_component(field)
                monitor_params.update({"MIPS_Field": field})
            except Exception:
                pass

        if hs_panel:
            try:
                cur = _display_parameter("HS_Current", "Current", "A", hs_panel.current_display)
                station.add_component(cur)
                monitor_params.update({"HS_I": cur})
            except Exception:
                pass

        # Create measurement context and register parameters (time as independent)
        context_meas = Measurement(exp=experiment, station=station, name="monitoring")
        indeps = (t,)
        deps = list(monitor_params.values())

        for indep in indeps:
            context_meas.register_parameter(indep)
        for dep in deps:
            context_meas.register_parameter(dep, setpoints=indeps)

        # Start monitoring loop (similar to RealMeasurement's continuous read)
        if signals:
            signals.status_updated.emit(f"Starting {duration}-second monitoring with {interval}-second interval")

        with context_meas.run() as datasaver:
            t.reset_clock()
            start_time = time.time()
            sample_count = 0

            while time.time() - start_time < duration:
                results = []
                # collect independent(s)
                for dev in indeps:
                    try:
                        results.append((dev, dev()))
                    except Exception:
                        results.append((dev, np.nan))
                # collect dependent(s)
                for dev in deps:
                    try:
                        results.append((dev, dev()))
                    except Exception:
                        results.append((dev, np.nan))

                datasaver.add_result(*results)
                sample_count += 1

                if signals:
                    elapsed = time.time() - start_time
                    progress = min(100.0, (elapsed / duration) * 100 if duration > 0 else 0)
                    signals.progress_updated.emit(progress, f"Monitoring: {sample_count} samples, {elapsed:.1f}/{duration}s")

                time.sleep(interval)

        result = f"Monitoring completed. {sample_count} samples saved to {database_path}"
        if signals:
            signals.status_updated.emit(result)
            signals.measurement_finished.emit(result)
        return result

    except Exception as e:
        error_msg = f"Error in instrument monitoring: {str(e)}"
        if signals:
            signals.status_updated.emit(error_msg)
            signals.measurement_finished.emit(f"ERROR: {error_msg}")
        return error_msg

# Placeholder functions (add your implementations here)


def run_measurement(func_name, mct_panel=None, nmr_panel=None, mips_panel=None, hs_panel=None,
                   mct=None, nmr=None, mips=None, hs=None, signals=None, **kwargs):
    """
    Run selected measurement function
    
    Args:
        func_name: Name of measurement function
        mct_panel, nmr_panel, mips_panel, hs_panel: Instrument panel objects
        mct, nmr, mips, hs: Instrument objects
        signals: MeasurementSignals object for UI updates
        **kwargs: Additional parameters
    """
    # Reload module to get latest functions
    measurements_module, reloaded = reload_measurements_module()
    
    if hasattr(measurements_module, func_name):
        func = getattr(measurements_module, func_name)
        try:
            # Pass appropriate objects
            if func_name == "MonitorConnectedInstruments":
                result = func(mct_panel, nmr_panel, mips_panel, hs_panel, signals, **kwargs)
            else:
                result = func(mct, nmr, mips, hs, signals, **kwargs)
            return result
        except Exception as e:
            return f"Error in {func_name}: {str(e)}"
    else:
        return f"Function {func_name} not found"