import streamlit as st
from ETS_CookBook import ETS_CookBook as cook
import ChaProEV_plus
from pathlib import Path
from box import Box


if __name__ == '__main__':
    scenario_path: Path = Path('scenarios/plus/test.toml')
    scenario: Box = cook.parameters_from_TOML(scenario_path)
    scenario_A: Box = scenario.copy()
    scenario_B: Box = scenario.copy()
    charging_dataframe_A, hourly_values_A = ChaProEV_plus.run_ChaProEV(
        scenario=scenario_A)
    charging_dataframe_B, hourly_values_B = ChaProEV_plus.run_ChaProEV(
        scenario=scenario_B)

    print(hourly_values_A)
    print(hourly_values_B)    



    # sliders for SD!
    # spin off streamlit
    # high SD/low SD button
    # maybe one for base case (low SD, no adaptove, no thrsh) and opposite


    run_parameters: Box = scenario.run
    if run_parameters.use_seed:
        run_seed: int | None = run_parameters.seed
    else:
        run_seed = None
    
    random_generator: np.random.Generator = np.random.default_rng(run_seed)