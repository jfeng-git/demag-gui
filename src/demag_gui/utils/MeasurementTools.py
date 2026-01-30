from datetime import datetime
from time import sleep

def timming(target, trigger=1., actions=[]):
    # check input target
    if isinstance(target, str):
        try:
            target_time = datetime.strptime(target, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                target_time = datetime.strptime(target, '%Y/%m/%d %H:%M:%S')
            except ValueError:
                print("时间格式错误，请使用 'YYYY-MM-DD HH:MM:SS' 格式")
                return False
    elif isinstance(target, datetime):
        target_time = target
    else:
        print("target参数类型错误")
        return False
        
    print(f'current time is {datetime.now()}')
    print(f'timming target {target}')

    while True:
        current_time = datetime.now()
        
        # 显示剩余时间
        time_left = target_time - current_time
        if time_left.total_seconds() > 0:
            print(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')} | "
                  f"剩余时间: {str(time_left).split('.')[0]}", end='\r')
        else:
            print(f"\n\n目标时间已到达: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return True

        # take measurement
        for action in actions:
            action()
        sleep(trigger)

def magnet_heater_on(mips, actions=[]):
    # if already on, skip
    if mips.GRPZ.heater_switch() == 'ON':
        print(f'heater is already {mips.GRPZ.heater_switch()}, skip.')
        return 'already set'

    # check current status
    B_output = mips.GRPZ.field()
    B_persistance = mips.GRPZ.field_persistent()
    B_target = mips.GRPZ.field_target()
    
    print(f'output field = {B_output}, persistance field = {B_persistance}')
    print(f'current target = {B_target}, heater is {mips.GRPZ.heater_switch()}')

    # if output field is not persistance field, ramp output field first
    if abs(B_persistance - B_output)>0.001:
        print(f'set field target to {B_persistance} then ramp to set')
        mips.GRPZ.field_target(B_persistance)
        mips.ramp(mode="simul")
        print(f'rampping field to {mips.GRPZ.field_target()}')
        print(f'persistance field = {B_persistance}')
        while not mips.GRPZ.ramp_status()=='HOLD':
            print(f'output field = {mips.GRPZ.field()}', end='\r')
            for action in actions:
                action()
    print(f'output field = {mips.GRPZ.field()}\n')
    
    # check output field again
    B_output = mips.GRPZ.field()
    B_persistance = mips.GRPZ.field_persistent()
    
    if abs(B_persistance - B_output)<0.001:
        print('\nset heater on')
        mips.GRPZ.heater_switch('ON')
    else:
        print(f'output field = {B_output}, persistance field = {B_persistance}')
        print('failed to ramp field, check')
        