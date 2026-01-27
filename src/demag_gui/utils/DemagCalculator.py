import numpy as np
import pandas as pd
import importlib.resources
from scipy.signal import savgol_filter
from scipy.signal import find_peaks

def load_time_measurements(run_ids):
    dses = [load_by_id(run_id=run_id).to_xarray_dataset() for run_id in run_ids]
    for ii, ds in enumerate(dses):
        if 'index' in ds.dims:
            ds = ds.swap_dims({'index': 't'}).drop_vars('index')
        # print(ds.dims)
        ds['ellapstime'] = (list(ds.dims), ds[list(ds.dims)[0]].data)
        base_time = pd.to_datetime(ds.attrs['run_timestamp'])
        timestamps = np.asarray([base_time + pd.Timedelta(seconds=s) for s in ds.t.data])
        # ds['tmin'] = (ds.dims, (timestamps - timestamps[0])/1e9/60)
        dses[ii] = ds.assign_coords(t=timestamps)
    # return xa.concat(dses, dim='t').rename_dims({'t': 'time'})
    ds = xa.concat(dses, dim='t')
    ts = [float(t - ds.t.data[0])/1e9/60 for t in ds.t.data]
    ds['time'] = (
        ds.dims, ts, dict(unit='min')
    )
    return ds

class MctCalculator:
    def __init__(self, C_Pdata=None):
        self.C_Pdata = C_Pdata
        # calculate the P-T curve
        coe_PT = [
            -1.3855442e-12,
            4.5557026e-9,
            -6.4430869e-6,
            3.4467434,
            -4.4176438,
            1.5417437e1,
            -3.5789853e1,
            7.1499125e1,
            -1.0414379e2,
            1.0518538e2,
            -6.9443767e1,
            2.6833087e1,
            -4.5875709
        ]
        poly = np.arange(-3, 10)    
        T_theory = np.logspace(-3.1, 0.1, 2000)
        P_theory = np.asarray([
            coe*T_theory**p for coe, p in zip(coe_PT, poly)
        ]).sum(axis=0)

        self.T_min = 315.24
        self.P_min = 2.93113

        self.T_A = 2.444
        self.P_Astd = 3.43407

        self.T_AB = 1.896
        self.P_ABstd = 3.43609

        self.T_Neel = 0.902
        self.P_Neel = 3.43934

        self.df = pd.DataFrame()
        self.df['P_theory'] = P_theory
        self.df['T_theory'] = T_theory
        self.Pmin_ind = P_theory.argmin()

        self.get_original_coes(4)

    def get_original_coes(self, deg=4):
        if self.C_Pdata is None:
            exp_data = pd.read_csv(importlib.resources.files("demag_gui.data").joinpath("data.txt"), sep='\t')
        else:
            exp_data = pd.read_csv(self.C_Pdata, sep='\t')
        # exp_data = pd.read_csv("../data/data.txt", sep='\t')
        self.C_mea = np.asarray(exp_data['C'].values[:])
        self.Cinv_mea = 1/self.C_mea
        self.P_mea = np.asarray(exp_data['P'].values[:])

        self.deg = deg
        self.coe_origin = np.polyfit(self.P_mea, self.Cinv_mea, deg=self.deg)
        self.df['Cinv_interp'] = np.polyval(self.coe_origin, self.df['P_theory'])
        self.df['C_interp'] = 1/self.df['Cinv_interp']

    def recalibrate(self, new_points):
        """
        Recalibrate polynomial coefficients for 1/C = g(P)
        using new calibration points.

        Parameters
        ----------
        new_points : list
            Either:
            [[C1, P1]]                         -> correct a0 only
            [[C1, P1], [C2, P2]]               -> correct a0 and a1

        Returns
        -------
        coeffs_desc_new : np.ndarray
            Updated coefficients in np.polyfit order (descending powers)
        """

        # Original coefficients for 1/C = g(P), descending powers
        coeffs_desc = np.asarray(self.coe_origin, dtype=float)

        # Convert to ascending powers: [a0, a1, ..., aN]
        coeffs_asc = coeffs_desc[::-1]

        # Higher-order contribution (i >= 2)
        def Cinv0(P):
            powers = np.arange(2, len(coeffs_asc))
            return np.sum(coeffs_asc[2:] * P**powers)

        # ----------------------
        # Single-point correction (offset only)
        # ----------------------
        if len(new_points) == 1:
            C1, P1 = new_points[0]
            Cinv1 = 1.0 / C1

            # Correct constant term only
            a0_new = Cinv1 - coeffs_asc[1] * P1 - Cinv0(P1)

            coeffs_asc_new = coeffs_asc.copy()
            coeffs_asc_new[0] = a0_new

        # ----------------------
        # Two-point correction (offset + slope)
        # ----------------------
        elif len(new_points) == 2:
            (C1, P1), (C2, P2) = new_points
            Cinv1 = 1.0 / C1
            Cinv2 = 1.0 / C2

            # Recompute linear term
            a1_new = (
                (Cinv1 - Cinv2) - (Cinv0(P1) - Cinv0(P2))
            ) / (P1 - P2)

            # Recompute constant term
            a0_new = Cinv1 - a1_new * P1 - Cinv0(P1)

            coeffs_asc_new = coeffs_asc.copy()
            coeffs_asc_new[0] = a0_new
            coeffs_asc_new[1] = a1_new

        else:
            raise ValueError("new_points must contain 1 or 2 points")

        # Convert back to descending powers for np.polyval
        self.coe_calibrated = coeffs_asc_new[::-1]
        self.df['Cinv_interp'] = np.polyval(self.coe_calibrated, self.df['P_theory'])
        self.df['C_interp'] = 1/self.df['Cinv_interp']
        return coeffs_asc_new[::-1]

    
    def C2T_low(self, C_cv):
        x, y = self.df['C_interp'][:self.Pmin_ind].values, self.df['T_theory'][:self.Pmin_ind].values
        if x[-1] < x[0]:
            x = x[::-1]
            y = y[::-1]
        T_low = np.interp(C_cv, x, y)
        return 1e3*T_low
    
    def C2T_high(self, C_cv):
        x, y = self.df['C_interp'][self.Pmin_ind:].values, self.df['T_theory'][self.Pmin_ind:].values
        if x[-1] < x[0]:
            x = x[::-1]
            y = y[::-1]
        T_low = np.interp(C_cv, x, y)
        return 1e3*T_low

    def C2P_low(self, C_cv):
        x, y = self.df['C_interp'].values[:self.Pmin_ind], self.df['P_theory'].values[:self.Pmin_ind]
        mask = x < 75
        x = x[mask]
        y = y[mask]
        if x[-1] < x[0]:
            x = x[::-1]
            y = y[::-1]
        P = np.interp(C_cv, x, y)
        return P
    
    def T2P(self, T_cv):
        T_cv = T_cv/1000
        P = np.interp(T_cv, self.df['T_theory'], self.df['P_theory'])
        return P

def cal_Q(T_K, B=0., cal_dQdt=False, t=[]):
    # T_K in K, t in min
    T_K = np.asarray(T_K)
    t = np.asarray(t)
    n = 100 # in mol
    lambda_n_mu = 3.22e-6 # in

    gamma_e = 0.691e-3 # in J/mol/K^2
    N = 159.3 # in mol
    
    dQ = 0.5*N*gamma_e*T_K**2 - n*lambda_n_mu*B**2*(1/T_K) # in J
    
    if cal_dQdt:
        if len(T_K) == len(t):
            # convert t to s
            t = t * 60
            return dQ*1e6, 1e9*np.gradient(dQ)/np.gradient(t) # in uJ, nW
        else:
            print('len(T_K) != len(t)')
            return dQ*1e6 # in uJ
    else:
        return dQ*1e6 # in uJ


def process_demag_data(ds, Bi=8.2):
    try:
        ds = ds.swap_dims({'t': 'mips_GRPZ_field_persistent'})
    except:
        pass

    mct = MctCalculator()
    mct.recalibrate([[65.06, mct.P_min]])
    inds = [i for i, val in enumerate(list(ds.AH2500A_C.data < 73)) if val]
    for ind in inds:
        ds.AH2500A_C[ind] = ds.AH2500A_C[ind - 2]
    ds['T'] = ('mips_GRPZ_field_persistent', 1e-3 * mct.C2T_low(ds.AH2500A_C.data))
    ds['Tmct_mK'] = 1e3 * ds.T

    ts = ds.t.data
    ts = [float(t - ts[0]) / 1e9 for t in ts]  # in s
    ds['time_s'] = ('mips_GRPZ_field_persistent', ts)

    if 'nmr_TmK' in ds.data_vars:
        x, y = ds.mips_GRPZ_field_persistent.data, ds.nmr_TmK.data
        peaks, _ = find_peaks(abs(np.gradient(y)), distance=100)
        peaks = np.asarray(peaks) + 5
        Bnmr, Tnmr = x[peaks], y[peaks]

        ds['tnmr'] = (['Bnmr'], ds.t.data[peaks])
        ds['tnmr_s'] = (['Bnmr'], ds.time_s.data[peaks])
        ds.tnmr.attrs = dict(long_name='time')
        ds['Bnmr'] = Bnmr
        ds['M0'] = (['Bnmr'], ds.nmr_M0.data[peaks])
        ds['Tnmr'] = (['Bnmr'], Tnmr, dict(long_name=r'T$_{\mathrm{nmr}}$', unit='mK'))

    n = 100  # in mol
    lambda_n_mu = 3.22e-6  # in

    gamma_e = 0.691e-3  # in J/mol/K^2
    N = 159.3  # in mol

    def cal_Cn(T, B):
        return n * lambda_n_mu * (B / T) ** 2 + N*gamma_e*T

    def cal_Pdemag(T, B, Ti, Bi, dBdt):
        return cal_Cn(T, B) * Ti * dBdt / Bi

    def cal_Ptotal(T, B, dTdt):
        return cal_Cn(T, B) * dTdt

    # prepare data
    T = savgol_filter(ds.T.data, 71, 1)  # in K
    B = savgol_filter(ds.mips_GRPZ_field_persistent.data, 71, 1)  # in Tesla
    ind_init = abs(B - Bi).argmin()
    Ti, Bi = T[ind_init], B[ind_init]

    ds['Tideal'] = ('mips_GRPZ_field_persistent', Ti * ds.mips_GRPZ_field_persistent.data / Bi)
    ds['Tideal_mK'] = ('mips_GRPZ_field_persistent', 1e3 * Ti * ds.mips_GRPZ_field_persistent.data / Bi)

    ds['deltaT'] = ('mips_GRPZ_field_persistent', 1e3 * (ds.T.data - ds.Tideal.data))
    if 'nmr_TmK' in ds.data_vars:
        ds['Tnmr_ideal'] = (['Bnmr'], ds['Tideal_mK'][peaks].data)
    
    
    # Heat capacitance
    ds['Cn'] = ('mips_GRPZ_field_persistent', cal_Cn(T, B))

    # Cooling power in the ideal case
    ds['dBdt'] = ('mips_GRPZ_field_persistent', savgol_filter(np.gradient(B) / np.gradient(ts), 71, 1))
    ds['dBdt_abs'] = -1e3 * 60 * ds.dBdt
    ds['Pideal'] = ('mips_GRPZ_field_persistent', 1e6 * cal_Pdemag(T, B, Ti, Bi, ds.dBdt.data))  # uW

    # total cooling power
    ds['dTdt'] = ('mips_GRPZ_field_persistent', savgol_filter(np.gradient(T) / np.gradient(ts), 71, 1))
    ds['Ptotal'] = ('mips_GRPZ_field_persistent', 1e6 * cal_Ptotal(T, B, ds.dTdt.data))

    # Heating power
    ds['Pheat'] = ds.Ptotal - ds.Pideal  # uW

    return ds

if __name__ == "__main__":
        
    app = dash.Dash(__name__)
    mct_calc = MctCalculator()
    
    # 创建P值选项列表 - 直接使用类属性中的值
    p_options = [
        {'label': f'P_Astd, {mct_calc.P_Astd:.6f}', 
         'value': mct_calc.P_Astd},
        {'label': f'P_ABstd, {mct_calc.P_ABstd:.6f}', 
         'value': mct_calc.P_ABstd},
        {'label': f'P_Neel, {mct_calc.P_Neel:.6f}', 
         'value': mct_calc.P_Neel}
    ]
    
    app.layout = html.Div([
        html.H3("MCT Demagnetization Calculator"),

        html.Div([
            html.Label("Heat Capacity C:"),
            dcc.Input(id='input-c', type='number', value=74.0, step=0.000001),
            html.Button('Calculate Temperature', id='btn-calc', n_clicks=0),
            html.Div(id='output-t', style={'margin-top': '10px', 'font-weight': 'bold'})
        ], style={'margin': '20px', 'padding': '10px', 'border': '1px solid #ccc'}),
        

        html.Div([
            html.H4("Recalibration"),

            html.Div([
                html.Label("Default calibration point (Pmin):"),
                html.Div([
                    html.Span("C₀ = "),
                    dcc.Input(id='c0', type='number', value=72, 
                                style={'width': '100px'}),
                    html.Span(" P₀ = "),
                    dcc.Input(id='p0', type='number', 
                                value=mct_calc.P_min, 
                                style={'width': '150px', 'background-color': '#f0f0f0'},
                                readOnly=True),
                ]),
                html.Button('Recalibrate from Pmin', id='btn-recal-pmin', n_clicks=0,
                            style={'margin-top': '5px'}),
            ], style={'margin-bottom': '15px', 'padding': '10px', 'background-color': '#f9f9f9'}),

            html.Div([
                html.Label("New calibration points:"),
                html.Div([
                    html.Span("Point 1: C1 = "),
                    dcc.Input(id='c1', type='number', placeholder='C1', style={'width': '80px'}),
                    html.Span(" \t P1 = "),
                    dcc.Dropdown(
                        id='p1-dropdown',
                        options=p_options,
                        placeholder='Select P1',
                        style={'width': '200px', 'display': 'inline-block', 'vertical-align': 'middle'}
                    ),
                ]),
                html.Div([
                    html.Span("Point 2: C2 = "),
                    dcc.Input(id='c2', type='number', placeholder='C2', style={'width': '80px'}),
                    html.Span(" P2 = "),
                    dcc.Dropdown(
                        id='p2-dropdown',
                        options=p_options,
                        placeholder='Select P2',
                        style={'width': '200px', 'display': 'inline-block', 'vertical-align': 'middle'}
                    ),
                ], style={'margin-top': '5px'}),
                html.Div([
                    html.Button('Recalibrate with new points', id='btn-recal', n_clicks=0, 
                                style={'margin-right': '10px'}),
                    html.Button('Restore Original', id='btn-restore', n_clicks=0)
                ], style={'margin-top': '10px'}),
            ]),
            
            html.Div(id='cal-status', style={'margin-top': '10px', 'font-weight': 'bold'})
        ], style={'margin': '20px', 'padding': '10px', 'border': '1px solid #ccc'})
    ])
    
    @callback(
        Output('output-t', 'children'),
        Input('btn-calc', 'n_clicks'),
        State('input-c', 'value'),
        prevent_initial_call=True
    )
    def calculate_temperature(n_clicks, c_value):
        if c_value is None:
            return "Please enter a C value"
        
        try:
            t_low = mct_calc.C2T_low(float(c_value))
            t_high = mct_calc.C2T_high(float(c_value))
            return html.Div([
                html.Div(f"C = {c_value}"),
                html.Div(f"P = {mct_calc.C2P_low(c_value)}"),
                html.Div([
                    html.Span("T", style={'vertical-align': 'baseline'}),
                    html.Sub("low", style={'vertical-align': 'baseline'}),
                    f" = {t_low:.2f} mK"
                ]),
                html.Div([
                    html.Span("T", style={'vertical-align': 'baseline'}),
                    html.Sub("high", style={'vertical-align': 'baseline'}),
                    f" = {t_high:.2f} mK"
                ])
            ])
        except Exception as e:
            return f"Error: {str(e)}"
    
    @callback(
        Output('cal-status', 'children'),
        Input('btn-recal-pmin', 'n_clicks'),
        Input('btn-recal', 'n_clicks'),
        Input('btn-restore', 'n_clicks'),
        State('c0', 'value'),
        State('p0', 'value'),
        State('c1', 'value'),
        State('p1-dropdown', 'value'),  # 改为使用dropdown的state
        State('c2', 'value'),
        State('p2-dropdown', 'value'),  # 改为使用dropdown的state
        prevent_initial_call=True
    )
    def update_calibration(recal_pmin_clicks, recal_clicks, restore_clicks, 
                            c0, p0, c1, p1_dropdown, c2, p2_dropdown):  # 参数名改为p1_dropdown和p2_dropdown
        ctx = dash.callback_context
        if not ctx.triggered:
            return ""
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == 'btn-restore':
            mct_calc.get_original_coes()
            return "✓ Restored to original coefficients"
        
        elif button_id == 'btn-recal-pmin':
            if c0 is not None:
                try:
                    new_points = [[float(c0), float(p0)]]
                    coeffs = mct_calc.recalibrate(new_points)
                    return f"✓ Recalibrated from Pmin point: C={c0}, P={p0:.6f}"
                except Exception as e:
                    return f"✗ Error: {str(e)}"
            else:
                return "Please enter C₀ value"
        
        elif button_id == 'btn-recal':
            new_points = []
            if c1 is not None and p1_dropdown is not None:  # 使用p1_dropdown
                new_points.append([float(c1), float(p1_dropdown)])  # 使用p1_dropdown
                if c2 is not None and p2_dropdown is not None:  # 使用p2_dropdown
                    new_points.append([float(c2), float(p2_dropdown)])  # 使用p2_dropdown
            
            if new_points:
                try:
                    coeffs = mct_calc.recalibrate(new_points)
                    return f"✓ Recalibrated with {len(new_points)} point(s)"
                except Exception as e:
                    return f"✗ Error: {str(e)}"
            else:
                return "Please enter at least one calibration point"
        
        return ""
    
    app.run(debug=False, host='192.168.1.17', port=8050)