

```python
    scenarios: list[Box] = scenarios_module.load_scenarios(case_name)

    set_amount_of_processes: bool = (
        general_parameters.parallel_processing.set_amount_of_processes
    )
    if set_amount_of_processes:
        amount_of_parallel_processes: int | None = None
    else:
        amount_of_parallel_processes = (
            general_parameters.parallel_processing.amount_for_scenarios
        )

    pool_inputs: ty.Iterator[tuple[Box, str, Box]] | ty.Any = zip(
        scenarios, repeat(case_name), repeat(general_parameters)
    )
    # the ty.Any alternative is there because transforming it with the
    # progress bar makes mypy think it change is type
    progress_bars_parameters: Box = general_parameters.progress_bars
    display_scenario_run: bool = progress_bars_parameters.display_scenario_run
    scenario_run_description: str = (
        progress_bars_parameters.scenario_run_description
    )
    if display_scenario_run:
        pool_inputs = tqdm.tqdm(
            pool_inputs,
            desc=scenario_run_description,
            total=len(scenarios),
        )

    with Pool(amount_of_parallel_processes) as scenarios_pool:
        scenarios_pool.starmap(scenarios_module.run_scenario, pool_inputs)
```