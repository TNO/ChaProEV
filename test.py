import pandas as pd

if __name__ == '__main__':

    charge_drawn = pd.read_pickle(
        'output/Mopo/XX_car_charge_drawn_by_vehicles.pkl'
    )

    print(charge_drawn.iloc[89:100])
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
