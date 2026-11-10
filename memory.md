# ChaProEV charging: scaling and memory

## Problem

Scaling the charging simulation to larger fleets causes:

- increasing runtime;
- high memory consumption;
- a `MemoryError` at around 120 users.

A full year at minute resolution contains:

```text
365 * 24 * 60 = 525,600 time steps per user
```

The current implementation keeps several complete representations of these data for each user:

- the original charging DataFrame;
- `PreCharge` input lists;
- `TrackingVariables` output lists;
- the final charging DataFrame.

Python lists are particularly memory-intensive because their elements are Python objects/references.

Caching is therefore unlikely to help. `PreCharge` is effectively already a cache, and additional caching would probably increase memory consumption.

## Recommended changes

### 1. Remove timestamps from `PreCharge`

Every user currently stores:

```python
time_stamps: list[datetime]
```

However, all users use the same model time axis, which is already available through:

```python
run_time_stamps
```

Furthermore, `update_tracking()` only needs `run_index`.

Therefore, remove `time_stamps` from `PreCharge` and keep the timestamps only once at fleet/model level.

**Priority: high. Simple change and no change to model computations.**

---

### 2. Consider NumPy arrays for numerical `PreCharge` data

Switching from Polars Series to Python lists improved runtime because individual list access is cheap, but Python lists require considerably more memory.

Consider replacing numerical and Boolean lists with NumPy arrays.

Candidate fields:

```text
kilometers_driven_run
consumptions
can_charge_run
session_starts
session_durations_hours
available_charge_powers_to_vehicle
available_charge_powers_from_network
```

For example:

```python
consumptions: npt.NDArray[np.float64]
```

initialized with:

```python
consumptions=user.charge[consumption_header].to_numpy()
```

Approximate raw storage:

```text
float64: 525,600 * 8 bytes ~= 4.2 MB/user/column
bool:    525,600 * 1 byte  ~= 0.5 MB/user/column
```

This is considerably more compact than Python lists containing Python objects.

**Trade-off:** NumPy scalar indexing may be slower than Python-list indexing. Benchmark runtime and memory before converting everything.

---

### 3. Preallocate numerical `TrackingVariables`

Currently output is accumulated using Python lists:

```python
tracking.run_consumptions.append(consumption)
tracking.power_to_vehicle_kW.append(this_step_power_to_vehicle_kW)
```

Instead, numerical output arrays could be allocated once:

```python
np.empty(number_of_time_steps, dtype=np.float64)
```

and filled using the existing `run_index`:

```python
tracking.run_consumptions[run_index] = consumption

tracking.power_to_vehicle_kW[run_index] = (
    this_step_power_to_vehicle_kW
)

tracking.battery_charge_levels_kWh[run_index] = (
    tracking.current_battery_level_kWh
)
```

Candidate fields:

```text
run_kilometers_driven
run_consumptions
power_drawn_from_network_kW
power_to_vehicle_kW
battery_charge_levels_kWh
```

This avoids creating hundreds of thousands of Python float objects for every user.

**Priority: high if memory remains problematic after removing duplicated timestamps.**

---

### 4. Consider encoding locations

Locations are highly repetitive:

```text
home
home
home
...
driving
...
work
work
...
```

They could eventually be represented internally using integer codes:

```text
0 = home
1 = work
2 = driving
3 = fast
```

For example:

```python
run_locations = np.empty(
    number_of_time_steps,
    dtype=np.uint8,
)
```

The integer codes can be converted back to location names when constructing the final Polars DataFrame.

**Priority: lower. Only implement if the simpler changes are insufficient.**

---

## Larger scalability issue

At 120 users:

```text
120 * 525,600 ~= 63 million user-minutes
```

This is inherently a large result.

Even six `float64` values per user-minute require approximately:

```text
63 million * 6 * 8 bytes ~= 3 GB
```

This does not include:

- timestamps;
- locations;
- input columns;
- Polars DataFrames;
- Python objects;
- intermediate data;
- model state.

For hundreds or thousands of vehicles, retaining every vehicle's complete annual minute-resolution history in RAM may therefore not be practical.

A future architecture could instead:

1. keep only the current simulation state required for each user;
2. process the complete fleet one timestep at a time;
3. update line/transformer/fleet aggregates during the simulation;
4. retain only outputs actually required for model metrics;
5. optionally write detailed user-level results incrementally to Parquet instead of keeping everything in memory.

This would be a larger architectural change, so do not implement it unless the simpler memory improvements are insufficient.

## Recommended implementation order

Make one change at a time and benchmark runtime and memory after each step:

1. **Remove duplicated `time_stamps` from `PreCharge`.**
2. Benchmark.
3. **Replace numerical/Boolean `PreCharge` lists with NumPy arrays.**
4. Benchmark.
5. **Preallocate numerical `TrackingVariables` arrays.**
6. Benchmark.
7. If necessary, **encode locations as compact integer values.**
8. For much larger fleets, reconsider whether complete per-user minute-resolution histories need to remain in memory.

The immediate goal should be to reduce duplicate representations of the same data while preserving the current charging computations exactly.