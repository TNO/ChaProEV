

**Multirpocessing**
```python
    scenarios: ty.List[ty.Dict] = load_scenarios(case_name)

    number_of_parallel_processes: int = general_parameters[
        'parallel_processing'
    ]['number_of_parallel_processes']['for_scenarios']
    with Pool(number_of_parallel_processes) as scenarios_pool:
        scenarios_pool.starmap(
            run_scenario,
            zip(scenarios, repeat(case_name), repeat(general_parameters)),
        )
```

speeds up considerably 