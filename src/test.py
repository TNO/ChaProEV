

import pandas as pd
soorce = pd.read_pickle('reference_run/XX_car_holiday_battery_spaces.pkl')
soorce.to_csv('Ref holiday batt.csv')

soorce = pd.read_pickle('output/Mopo//XX_car_holiday_battery_spaces.pkl')
soorce.to_csv('Fast holiday batt.csv')


# moo = pd.read_pickle('output/Mopo/XX_car_holiday_battery_spaces.pkl')
# print(moo.iloc[96])

# WHere does car come from????