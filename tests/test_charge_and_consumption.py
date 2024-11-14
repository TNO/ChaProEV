import datetime
import typing as ty

import numpy as np
import pandas as pd


def test_charge_and_consumption() -> None:

    # The charge and consuption might differ due to
    # boundary effects (i.e. if the run starts/stops at moments
    # where the consumption has happened, but the charge might not
    # have had the chance to occur)
    case_name: str = 'Mopo'
    test_start_year: int = 2018
    test_start_day: int = 1
    test_start_month: int = 1
    test_start_hour: int = 5
    test_end_year: int = 2018
    test_end_month: int = 12
    test_end_day: int = 31
    test_end_hour: int = 4
    test_start_date: datetime.datetime = datetime.datetime(
        year=test_start_year,
        month=test_start_month,
        day=test_start_day,
        hour=test_start_hour,
    )
    test_end_date: datetime.datetime = datetime.datetime(
        year=test_end_year,
        month=test_end_month,
        day=test_end_day,
        hour=test_end_hour,
    )

    test_range: pd.DatetimeIndex = pd.date_range(
        start=test_start_date, end=test_end_date, freq='1h', inclusive='both'
    )
    test_scenarios: ty.List[str] = [
        'XX_bus',
        'XX_van',
        'XX_truck',
        'XX_car'
    ]
    for scenario in test_scenarios:
        charge_drawn_by_vehicles_dataframe: pd.DataFrame = pd.read_pickle(
            f'output/{case_name}/{scenario}_charge_drawn_by_vehicles_total.pkl'
        )

        charge_drawn_by_vehicles_dataframe_in_test = (
            charge_drawn_by_vehicles_dataframe.loc[test_range]
        )
        charge_drawn_in_test: float = (
            charge_drawn_by_vehicles_dataframe_in_test[
                'Total Charge Drawn (kW)'
            ].sum()
        )

        consumption_dataframe: pd.DataFrame = pd.read_pickle(
            f'output/{case_name}/{scenario}_consumption_table.pkl'
        )
        consumption_dataframe_in_test = consumption_dataframe.loc[test_range]
        consumption_in_test: float = consumption_dataframe_in_test[
            'electricity consumption kWh'
        ].sum()
        print(scenario, f'{charge_drawn_in_test=}', f'{consumption_in_test=}')
        np.testing.assert_almost_equal(
            charge_drawn_in_test, consumption_in_test
        )


if __name__ == '__main__':
    test_charge_and_consumption()
