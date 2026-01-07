import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.optimize import root_scalar
from collections.abc import Iterable



class MCT_calculator:
    def __init__(self):

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
        self.PT_T = np.logspace(-3, 0.1, 200)
        self.PT_P = np.asarray([
            coe*self.PT_T**p for coe, p in zip(coe_PT, poly)
        ]).sum(axis=0)

        # read the callibrated C-P data
        exp_data = pd.read_csv("data.txt", sep='\t')
        self.C = np.asarray(exp_data['C'].values)
        self.C_inv = 1/self.C
        self.P_mea = np.asarray(exp_data['P'].values)

        self.popts_1, pcovs_1 = curve_fit(self.poly_1, self.C_inv, self.P_mea)
        self.popts_4, pcovs_4 = curve_fit(self.poly_4, self.C_inv, self.P_mea)
        self.perr1 = np.sqrt(np.diag(pcovs_1))
        self.perr4 = np.sqrt(np.diag(pcovs_4))

        self.deltaP = 0.0013720
        self.deltaP = 0.0014177987800887415
        self.fit_func = self.poly_4
    
    def plot_P_Cinv(self):
        fig, axes = plt.subplots(2, 1, figsize=[6, 4], dpi=200, sharex=True)
        axes[0].plot(self.C_inv, self.P_mea, marker='d', ls='', color='black')

        xs = np.linspace(0.01, 0.019, 200)
        xs = self.C_inv
        axes[0].plot(xs, self.poly_1(xs, *self.popts_1), zorder=0, label='P-linear', color='tab:blue')
        axes[0].plot(xs, self.poly_4(xs, *self.popts_4), zorder=0, label='P-Poly4', color='tab:red')

        axes[1].plot(xs, self.P_mea - self.poly_1(xs, *self.popts_1), zorder=0, label=r'$\Delta$P-linear', color='tab:blue')
        axes[1].plot(xs, self.P_mea - self.poly_4(xs, *self. popts_4), zorder=0, label=r'$\Delta$P-Poly4', color='tab:red')

        axes[1].axhline(0, color='black', ls='--', zorder=0)
        for ax in axes:
            ax.legend(frameon=False, loc='upper right')
            ax.set(xlim=[self.C_inv.min(), self.C_inv.max()])

        axes[1].set(xlabel='1/C', ylabel=r'$\Delta$P')
        axes[0].set(ylabel='P (MPa)')
    
    def C2P(self, C_cv):
        C_cv = np.asarray(C_cv)
        C_cv_inv = 1/C_cv
        p_cv = self.fit_func(C_cv_inv, *self.popts_4) - self.deltaP
        return p_cv
    
    def C2T_low(self, C_cv):
        return self.P2T_low(self.C2P(C_cv))
    
    def C2T_high(self, C_cv):
        return self.P2T_high(self.C2P(C_cv))
    
    def P2T_low(self, P_cv):
        if not isinstance(P_cv, Iterable):
            P_cv = [P_cv]
        P_cv = np.asarray(P_cv)        
        return [self.P2T_single(p)[0] for p in P_cv]
    
    def P2T_high(self, P_cv):
        if not isinstance(P_cv, Iterable):
            P_cv = [P_cv]
        P_cv = np.asarray(P_cv)
        return [self.P2T_single(p)[-1] for p in P_cv]
    
    def P2T_single(self, P_cv):
        xp, yp = self.PT_T, self.PT_P
        cs = PchipInterpolator(xp, yp) 

        roots = cs.derivative().roots() 
        valid_roots = roots[(roots >= xp[0]) & (roots <= xp[-1])]
        
        if len(valid_roots) > 0:

            min_idx = np.argmin(cs(valid_roots))
            x_min = valid_roots[min_idx]
            y_min = cs(x_min)
        else:
            min_idx = np.argmin(yp)
            x_min = xp[min_idx]
            y_min = yp[min_idx]

        if P_cv < y_min:
            return []
        

        def f(x):
            return cs(x) - P_cv
        
        solutions = []
        intervals = [] 
        intervals.append((xp[0], x_min))

        sorted_roots = np.sort(valid_roots)
        for i in range(len(sorted_roots) - 1):
            intervals.append((sorted_roots[i], sorted_roots[i+1]))
        
        intervals.append((x_min, xp[-1]))

        for a, b in intervals:
            try:
                sol = root_scalar(f, bracket=[a, b], method='brentq')
                if sol.converged:
                    if not any(np.isclose(sol.root, s, atol=1e-6) for s in solutions):
                        solutions.append(sol.root)
            except (ValueError, RuntimeError):
                continue
        solutions = [s*1000 for s in solutions]
        return sorted(solutions)
    
    def C2T(self):
        pass
    
    def poly_1(self, x, a, b):
        return a*x+b

    def poly_4(self, x, A, B, C, D, E):
        return A + B*x + C*x**2 + D*x**3 + E*x**4
    
    def MCT_plot_C2T(self, C_cv, T_cv):
        C_inv = 1/C_cv
        P_mea = self.C2P(C_cv)
        T_cal = self.P2T_single(P_mea)

        fig, axes = plt.subplots(1, 2,figsize=[8, 3], dpi=150, gridspec_kw=dict(width_ratios=[1, 2]))

        axes[0].plot(self.C_inv, self.P_mea, marker='d', ls='', color='black', label=r'P${_mea}$')
        axes[0].plot(self.C_inv, self.poly_1(self.C_inv, *self.popts_1), color='orange', label='linear fit')
        axes[0].set(xlabel='1/C', ylabel='P (MPa)')

        axes[0].plot(C_inv, P_mea, marker='o', color='r', label=r'C$_{\sim' + f'{T_cv}' +'mK}$')
        axes[0].legend(frameon=False)

        axes[1].plot(self.PT_T*1000, self.PT_P, color='black')
        axes[1].axhline(P_mea, color='tab:red', label=r'P$_{cal}$', ls='--')
        axes[1].axvline(T_cv, color='tab:blue', label=r'T$_{MC}$' + f'={T_cv}mK')
        label = r'T$_{L}$=' + f'{T_cal[0]:.2f}mK' + '\n'+r'T$_{H}$=' + f'{T_cal[1]:.2f}mK'
        axes[1].plot(T_cal, [P_mea]*2, color='tab:red', marker='d', ls='', label=label)
        axes[1].legend(frameon=False, handlelength=1)
        axes[1].set(xlabel='T (mK)', ylabel='P (MPa)', xscale='log')