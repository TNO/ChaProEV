import pandas as pd

if __name__ == '__main__':

    boo = pd.read_pickle('reference_run/XX_car_home_battery_space.pkl')
    baa = pd.read_pickle('reference_run/XX_car_location_split.pkl')
    pii = pd.read_pickle('output/Mopo/XX_van_van_customer_battery_space.pkl')
    # bii = boo[boo.columns[boo.sum()>0]]
    # print(boo.loc['bus_route_start', 'bus_depot'])
    # print(bii)
    # print(charge_drawn.iloc[89:100])
    print(boo.iloc[78:86].sum(axis=1))
    print(baa.iloc[78:86]['home'])

    print(boo.iloc[0:12].sum(axis=1))
    print(baa.iloc[0:12]['home'])
    print(pii)
    print(boo)
    exit()

    batt_space = pd.read_pickle('output/Mopo/XX_car_home_battery_space.pkl')
    run_range = batt_space.index.get_level_values('Time Tag')
    # print(run_range)
    day_end_batt_space = batt_space.loc[run_range.hour == 4]
    print(day_end_batt_space.columns)
    # exit()
    non_empty_day_end_batt_space = day_end_batt_space.drop(columns='0.0')
    print(day_end_batt_space)
    day_starts_with_leftover_battery_space = non_empty_day_end_batt_space.loc[
        non_empty_day_end_batt_space.sum(axis=1) != 0
    ].index.get_level_values('Time Tag')
    print(day_starts_with_leftover_battery_space)
