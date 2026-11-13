# Residential grid congestion

![Local_grid_figure](Local_grid.svg 'Residential grid')



## Goal
model impact of residnetial grid connection issues on charging profiles
charging demand can be high a the same time as other demand is high,
so chargign session demands might be delayed, reduced or outrighht denied
This will impact they way vehicles charge and change the charging profiles

Look at residnetial neighbourhood because it is likely that such conflicts will
occur (simultaeous demand, also the fact that in other locations the
grid might besolely dedicated to EV charging)

## WHen to use
The parameter include_residential_grid_congestion (set to either `true` or `false`)
in the `[grid]`  section of your scenario tells if you are using this modelling or not.

Set it to `true` if you want to add residetial grid congestion issues to our profile.

If you don't want to include such effects, or if you want to investigate them in another
model (fr example an optimisation one) using the profiles provided by ChaProEV,
or if it is not relevant (e.g. vehicles such as busses that charge in dedidcated locations)

This is mostly meant for cars



## Parameters
They are in the `[grid]` section of your scenario

```TOML

[grid]
include_residential_grid_congestion = true
transformer_capacity_kW = 200
amount_of_lines = 10
line_capacity_to_average_ratio_min = 0.8
line_capacity_to_average_ratio_typical = 1.0
line_capacity_to_average_ratio_max = 1.2
```

### Transformer capacity
The capacity of the transformer (in kW)
### Amount of lines
The amounts of lines connected to the transformer. 
### Line capacity to average ratio
These three parameters provide a range for 
[drawing](monte-carlo.md#drawing-bounded-parameter-values)
each line's capacity by fluctuating around dividing the transformer equally
within the lines.


## Approach

### Scope
One transformer for the neighbourhood with a given capacity and
a certain amount of lines, ach having its own capacity (sum of lines capacity is transformer capacity)
This provides two constraints. One at transformer level, and one at each level
so issues could come at the whole neighbourhood level, as well as at a more
local level (e.g. a street has many EVs and their users charge at the same time
as they have elecxtricity demand for other purposes)
### Line capacity determination
AVerage per line is capacity divided by amount of lines
Fluctuations around this determined by
[drawing](monte-carlo.md#drawing-bounded-parameter-values)
gives variations around that average
with total capaicty still equal to transformer capacity


### Non-EV demand

#Draw amounts of the below per line (based on line capacity/transfomer capacity)
One on one, or another draw level?
Each has a draw --> sum
Time conversion
#### Households
consumption beta draw
shape depends on connection type? MFFBAS
#### Heat pumps
Heat demand profile (wramteprofilengenrator)
+ size (beta draw)
#### Solar panels
production=consumption
shape entso-e
```python
clsss Grid:
    soo: int
```


### Assignment of home chargers and connectivity

Home chargers are created after the users have been generated. The procedure distinguishes between users with their own driveway and users who park on the street. A user with an own driveway receives an individual home charger and therefore has a home connectivity of 1. Whenever the vehicle is at home, the home charger is available to that user.

For street parking, chargers are shared between multiple users. The configured street-parking connectivity is used to determine the number of chargers that should be available. For \(N\) street-parking users with a configured connectivity \(c\), the expected number of chargers is
$$
N_{\mathrm{chargers, expected}} = N_{\mathrm{users}} \times c.
$$
Because the model must create a discrete number of physical chargers, this value is rounded to the nearest integer, with half values rounded upwards. If there are street-parking users, at least one charger is created. A connectivity of zero is therefore not allowed when street-parking users are present.

For example, with 12 street-parking users and a configured connectivity of 0.25:

$$
12 \times 0.25 = 3
$$

and three street chargers are created.

The street-parking users are first randomly shuffled and are subsequently assigned to the available chargers in round-robin order. This makes the assignment stochastic while distributing the users as evenly as possible over the chargers: the numbers of users assigned to any two chargers can differ by at most one.

After the users have been assigned, their actual home connectivity is recalculated from the number of users sharing their charger:

$$
c_{\mathrm{user}} = \frac{1}{N_{\mathrm{users\ on\ charger}}}.
$$

For example, a charger shared by four users gives each of those users a connectivity of 0.25, while a charger shared by three users gives each user a connectivity of approximately 0.333.

The recalculation is necessary because the configured connectivity represents the desired average availability, whereas the model contains a finite number of users and a discrete number of chargers. The exact configured connectivity can therefore not always be reproduced. For example, if 11 street-parking users have a configured connectivity of 0.25, the expected number of chargers is

$$
11 \times 0.25 = 2.75,
$$

which results in three physical chargers. The users are then distributed as 4, 4 and 3 users over these chargers, giving individual connectivities of 0.25, 0.25 and approximately 0.333, respectively. This preserves the physical interpretation of connectivity: it represents the probability that the shared charger assigned to a user is available when that user wants to charge.

The updated connectivity is stored on the user's home `Location`. The charging DataFrame is deliberately created only **after** the local grid and charger assignment have been constructed. This ensures that the stochastic charging-session availability draws use the final connectivity resulting from the actual charger allocation, rather than the original scenario-level connectivity.


#### Own driveway chargers
Users x Own driveway proportion

also power?



Trafo --> Lines 
Non EV profiles

EV cpacities