import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import math


def DemagTimeCalculator(field_rate_mapping=None):
    start_time = '2026-01-27T23:00:00'
    start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')

    if field_rate_mapping is None:
        total_time1T = 10 # 10 hours to 1T
        start_field = 8.5
        end_field = 1
        field_targets = [7, 6, 5, 4, 3, 2, 1, 0.03]
        field_windows = [[8.5, field_targets[0]]]
        field_windows += [[field_targets[i], field_targets[i+1]] for i in range(len(field_targets)-1)]
        target_rate_mapping = {}
        
        k = 0.212
        times = [np.log(8.5/np.asarray(f))/k for f in field_windows]
        avg_rates = [(target[0]-target[1])/(t[1]-t[0]) for target, t in zip(field_windows,times)]
        print(avg_rates)
        field_rate_mapping = {
                f'{field[0]} to {field[1]}': round(rate* 1000 / 60, 0) for field, rate in zip(field_windows, avg_rates)
                }
    for field, rate in field_rate_mapping.items():
        print(field, rate)

    ts = []
    Bs = []

    field_targets = [float(s.split(' ')[-1]) for s in list(field_rate_mapping.keys())]
    print(field_targets)
    # rates converted to T/s
    field_rates = np.asarray(list(field_rate_mapping.values()))/1e3/60
    elapsed_times = abs(np.diff(field_targets)/field_rates[:-1])
    total_time = sum(elapsed_times)
    elapsed_times = list(elapsed_times)
    time_steps = [0] + [np.sum(elapsed_times[:ii+1]) for ii in range(len(elapsed_times))]

    s_field_rate_mapping = []
    for ii in range(len(field_targets)-1):
        ts += list(np.linspace(time_steps[ii], time_steps[ii+1], 100))
        start, stop = field_targets[ii], field_targets[ii+1]
        Bs += list(np.linspace(start, stop, num=100))
        rate = list(field_rate_mapping.values())[ii]
        s_field_rate_mapping += [
            [f"from {start} to {stop}",  f"{rate} mT/min", f"{elapsed_times[ii]/3600:.2f} hrs"]
        ]

    ts = [datetime.fromtimestamp(start_time.timestamp()+t) for t in ts]
    Bs = np.asarray(Bs)
    ts = np.asarray(ts)

    estimated_points= {
        'start': 8.5,
        # 'reduce Burst': 3.1,
        'A': 2.5,
        'AB': 1.4,
        'reduce Gain': 1,
        'Neel': 0.7,
        'end': 0.03
    }

    df = pd.DataFrame(
        {
            'point': estimated_points.keys(),
            'field': estimated_points.values(),
        }
    )

    end_time = datetime.fromtimestamp(start_time.timestamp() + np.sum(elapsed_times))

    print(f'start time is {start_time}, end time is {end_time}')

    estimated_pointtimes = [
        abs(Bs - b).argmin() for b in estimated_points.values()
    ]

    df['time'] = ts[estimated_pointtimes]
    df['time'] = df.time.dt.strftime('%m-%d %H:%M')

    fig, ax = plt.subplots(dpi=150)
    ax.plot(ts, Bs)
    # ax.text(
    #     0.2,
    #     0.6,
    #     s_field_rate_mapping, transform=ax.transAxes,)

    for t, field in zip(estimated_pointtimes, estimated_points.values()):
        if not t == ts[0] or not t == ts[-1]:
            plt.plot([ts[t]]*2, [0, field], color='red', zorder=0, ls='--')
            plt.plot([ts[0], ts[t]], [field]*2, color='red', zorder=0, ls='--')

    ax_table1 = fig.add_axes((0.3, 0.5, 0.6, 0.5))
    ax_table1.axis('off')
    table = ax_table1.table(
        cellText=s_field_rate_mapping,
        cellLoc = 'center',
        loc = 'center',
    )

    ax_table = fig.add_axes((0.5, 0.2, 0.4, 0.5))
    ax_table.axis('off')
    print(df)
    table = ax_table.table(cellText=df.values,
                           colLabels=df.columns,
                           cellLoc='center',
                           loc='center',
                           colColours=['#f2f2f2']*len(df.columns))
    ax.set(ylim=0, xlim=[ts[0], ts[-1]], xlabel='time', ylabel='field', title=f'Total Time = {total_time/3600:.2f} hrs')
    ax.tick_params('x', rotation=30)
    # fig.tight_layout()
    plt.show()

if __name__ == "__main__":
    DemagTimeCalculator()
