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