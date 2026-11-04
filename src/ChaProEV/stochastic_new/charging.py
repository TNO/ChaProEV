

from ETS_CookBook import ETS_CookBook as cook

DO WE ACTUALLY NEED DOESS CHARGE?????
IF WE FILTER ON CAN CHARGE< MAybe NOT


for 
    time_stamp, can_charge, consumption, session_duration, 
available_charge_power_to_vehicle,
available_charge_power_from_network

@cook.function_timer
def compute_charging

step_index (though maybe first stime stamp or a bool that is done first)

Maybe have 


We initialised previous_loation_name to 'Not relevant before first step'
so the check previous_location_name == driving will fail

so no need for step_index

Have this below function for each step

current_battery_level_kWh -= consumption
if current_battery_level_kWh < 0:
    raise ValueError('Baatery level is negative!')

this_step_power_to_vehicle_kW: float = 0
this_step_power_drawn_from_network_kW: float = 0
...
Less tests 
if can_charge:
    wants_to_charge: bool = hdsjd
    if wants_to_charge:
        power_to_)veh=...
        power_from_net = ...
    
WE DO NEED battery_space_at_session_start_kWh  

Maybe with Session start bool parameters (also false if road) Initialised at (value from scenario)



If xxx --> compute wants and can (and does)

if does --> power dance (separate function)

....
current_battery_level_kWh += this_step_power_to_vehicle_kW * run_time_resolution_hours

(and discharge?)
 

 battery_charge_levels_kWh.append(current_battery_level_kWh)
power_to_vehicle_kW.append(this_step_power_to_vehicle_kW)
power_drawn_from_network_kW.append(this_step_power_drawn_from_network_kW)
previous_location_name = location_name


vectorisation __path__
start with DF   that also has can charge, wants to charge, does charge

if road --> power drawn and power to car are zero also can charge is False
identify road --> parking steps 
here can_charge can be computed/vectorized (with random draws)
Propafares down to departure <-- How to manage?

If we get a way to do can charge in advance.vectorally that would help 
DOCUMENT IT SAY THAT WE DO NOT NEED TO actually draw when it occurs (INCLUDING IF DRAW DEPENDS ON TIME STAMP <--COOL FEATURE TO placeholder)
If not doinf discharge, no need to propagate, as we only test at arrival
But we want discharge (evntually), so explore that

KEY= session ID (driven by transitions) Then can_charge(session_ID, location ) as a funcrion
Better name for session_ID

df = df.with_columns(
    (
        pl.col("Location") != pl.col("Location").shift(1)
    )
    .fill_null(True)
    .cum_sum()
    .alias("Location ID")
)


location_blocks = df.group_by("Location ID", maintain_order=True).agg(
    pl.col("Connectivity").first()
)

can_connect = (
    random_generator.random(location_blocks.height)
    < location_blocks["Connectivity"].to_numpy()
)

location_blocks = location_blocks.with_columns(
    pl.Series("Can connect", can_connect)
)

df = df.join(
    location_blocks.select("Location ID", "Can connect"),
    on="Location ID",
    how="left",
)

We also have hours at location from mobility (copy it to DF)

Use that for road --> park too?


Add nominal and availavle power to Charge DF (from net and to veh) (nominal --> available: through modulation)
also dischgarge