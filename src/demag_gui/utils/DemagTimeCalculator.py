import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd



def DemagTimeCalculator():
    # TODO: make this a class that can be imported and used elsewhere
    # start_time is a datetime for the beginning of the demagnetization schedule
    start_time = '2026-01-29T00:00:00'
    start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')


    field_targets = [8, 7, 6, 5, 4, 3, 2, 1, 0.6, 0.03]
    field_windows = [[8.5, field_targets[0]]]
    field_windows += [[field_targets[i], field_targets[i+1]] for i in range(len(field_targets)-1)]

    # decay constant (1/hour) used to compute window end times, B=B0*exp(-k*t)
    time_to_1T_hours = 10
    k = np.log(8.5/0.6)/time_to_1T_hours

    # window_times_hours: for each field window produce [start_hour, stop_hour]
    window_times_hours = [np.log(8.5/np.asarray(f))/k for f in field_windows]
    # avg_rates_T_per_hr: average rate across each window in Tesla/hour
    avg_rates_T_per_hr = [(target[0]-target[1])/(t[1]-t[0]) for target, t in zip(field_windows, window_times_hours)]

    # field_rate_map_mT_per_min: mapping used/presented to the user (units: mT/min)
    field_rate_mapping = {
            f'{field[0]} to {field[1]}': round(rate * 1000 / 60, 0) for field, rate in zip(field_windows, avg_rates_T_per_hr)
            }
    
    for field, rate in field_rate_mapping.items():
        print(field, f"{rate} mT/min")
    
    print('\n')
    for window, rate in zip(field_windows, field_rate_mapping.values()):
        print(f"{window[1]}: {rate}, ")
    print('\n')

    # build arrays of sample times (hours from start) and field values (T)
    time_points_hours = []
    field_values_T = []

    # parse numeric targets from the field window key strings
    field_targets = [float(s.split(' ')[-1]) for s in list(field_rate_mapping.keys())]

    total_time_hours = 0
    summary_table_rows = []
    target_rates = {}
    for window, t_hours, rate_T_per_hr in zip(field_windows, window_times_hours, avg_rates_T_per_hr):
        # present rate in mT/min for human-readable table
        rate_mT_per_min = round(rate_T_per_hr * 1000 / 60, 0)
        # sample 100 points across this window (t_hours is [start_hour, stop_hour])
        time_points_hours += list(np.linspace(t_hours[0], t_hours[1], 100))

        start_T, stop_T = window[0], window[1]
        wait_time_min = 0 if stop_T>2 else 10

        field_values_T += list(np.linspace(start_T, stop_T, num=100))


        summary_table_rows += [
            [
                f"from {start_T} to {stop_T}",  
                f"{rate_mT_per_min} mT/min", 
                f"{(t_hours[1]-t_hours[0]):.2f} hrs", 
                f"wait for {wait_time_min} min" if wait_time_min>0 else "no wait"]
        ]
        total_time_hours += t_hours[1]-t_hours[0]
        target_rates[stop_T] = {'rate':rate_mT_per_min, 'wait_time_min': wait_time_min}

    # convert sampled hour offsets into actual datetimes
    time_datetimes = [datetime.fromtimestamp(start_time.timestamp() + th * 3600) for th in time_points_hours]
    field_values_T = np.asarray(field_values_T)
    time_datetimes = np.asarray(time_datetimes)

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

    print(f'start time is {start_time}, end time is {time_datetimes[-1]}')

    estimated_indices = [
        abs(field_values_T - b).argmin() for b in estimated_points.values()
    ]

    df['time'] = time_datetimes[estimated_indices]
    df['time'] = df.time.dt.strftime('%m-%d %H:%M')

    fig, ax = plt.subplots(dpi=150)
    ax.plot(time_datetimes, field_values_T)

    for idx, field in zip(estimated_indices, estimated_points.values()):
        if not idx == 0 or not idx == len(time_datetimes)-1:
            plt.plot([time_datetimes[idx]]*2, [0, field], color='red', zorder=0, ls='--')
            plt.plot([time_datetimes[0], time_datetimes[idx]], [field]*2, color='red', zorder=0, ls='--')

    ax_table1 = fig.add_axes((0.95, 0.5, 0.6, 0.5))
    ax_table1.axis('off')
    table = ax_table1.table(
        cellText=summary_table_rows,
        cellLoc = 'center',
        loc = 'center',
    )

    ax_table = fig.add_axes((0.95, 0.2, 0.4, 0.5))
    ax_table.axis('off')
    print(df)
    table = ax_table.table(cellText=df.values,
                           colLabels=df.columns,
                           cellLoc='center',
                           loc='center',
                           colColours=['#f2f2f2']*len(df.columns))
    ax.set(ylim=0, xlim=[time_datetimes[0], time_datetimes[-1]], xlabel='time', ylabel='field (T)', title=f'Total Time = {total_time_hours:.2f} hrs')
    ax.tick_params('x', rotation=30)
    plt.show()
    return target_rates

if __name__ == "__main__":
    DemagTimeCalculator()
