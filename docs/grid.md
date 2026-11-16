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
### Power line capacities

The model distributes the transformer capacity over its connected power lines. For each power line, a relative capacity weight is drawn from a [bounded beta distribution](monte-carlo.md#drawing-bounded-parameter-values). These weights are subsequently normalised and multiplied by the transformer capacity. This introduces variation between the capacities assigned to individual power lines while ensuring that the sum of all line capacities remains equal to the transformer capacity:

$$
P_{\mathrm{line},i}
=
P_{\mathrm{transformer}}
\frac{w_i}{\sum_j w_j}
$$

and therefore:

$$
\sum_i P_{\mathrm{line},i}
=
P_{\mathrm{transformer}}
$$

This represents a deliberately conservative modelling assumption. The available transformer capacity is effectively divided between the individual power lines, and the model subsequently tests the power demand on each line against its assigned capacity. Because the line capacities sum to the transformer capacity, satisfying the capacity restriction of every individual line also guarantees that the total transformer-capacity restriction is satisfied.

In an actual distribution grid, the physical capacities of the outgoing power lines do not necessarily sum to the transformer capacity and may collectively exceed it. If one line is lightly loaded, another line may therefore carry a larger share of the transformer load, provided that its own physical capacity and the total transformer capacity are not exceeded. The model does not currently represent such dynamic sharing of transformer capacity between lines. Instead, each line receives a fixed share of the transformer capacity. This results in a conservative representation of the line-level capacity restrictions.

### Assigning EV users to lines

To determine whether the individual power lines can support the EV charging demand connected to them, the model needs to know which EV users are connected to each line. This is done in two steps. First, the EV chargers are assigned to power lines. The users associated with each charger are then assigned to the same line.

Chargers are assigned while respecting the capacity of each power line. A charger can only be assigned to a line if the remaining line capacity is at least equal to the rated power of the charger. The sum of the rated powers of all chargers assigned to a line can therefore never exceed that line's capacity.

The chargers are processed from highest to lowest rated power. Assigning the largest chargers first reduces the risk of filling the lines with smaller chargers in such a way that insufficient capacity remains for a larger charger, even though a feasible allocation could otherwise have existed.

For each charger, the model determines which lines have sufficient remaining capacity. The charger is then randomly assigned to one of these eligible lines, with the probability of selecting a line proportional to its remaining capacity:

$$
p_i =
\frac{P_{\mathrm{remaining},i}}
{\sum_{j \in E} P_{\mathrm{remaining},j}}
$$

where $E$ is the set of lines with sufficient remaining capacity for the charger. After assigning a charger, its rated power is subtracted from the remaining capacity of the selected line. Consequently, lines with more available capacity are more likely to receive chargers, while lines that are becoming more heavily occupied become progressively less likely to receive additional chargers.

This procedure allows both situations in which some lines have no EV chargers and situations in which multiple chargers are connected to the same line. If no line has sufficient remaining capacity for a charger, the assignment fails. The method is a greedy stochastic allocation: processing the largest chargers first reduces the chance of an unsuccessful allocation, but does not mathematically guarantee finding a feasible allocation whenever one exists.

Finally, the model looks up the EV users associated with each charger and assigns these users to the same power line as their charger. This provides the mapping between EV users and power lines that is subsequently used to aggregate their charging profiles and test the line-level capacity restrictions.

> **Note:** The sum of the nominal powers of all chargers cannot exceed the
> transformer capacity. This is a conservative modelling assumption that ensures
> that all chargers connected to the transformer could operate simultaneously at
> their nominal power without exceeding the transformer capacity.
>
> If the total charger power exceeds the transformer capacity, the model cannot
> assign all chargers within the available capacity. The following model inputs
> can be adjusted:
>
> - **Increase the transformer capacity.**
> - **Reduce the nominal power of the chargers.**
> - **Increase the proportion of street chargers.** Street chargers are shared
>   between users, reducing the number of chargers required.
> - **Reduce the street charger connectivity.** More users then share each
>   street charger, also reducing the number of chargers required.








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

### Non-EV demand



#### Household node demand profiles

To determine the electricity demand on each power line, the model first creates
an individual non-EV electricity profile for every household node. This profile
represents the net electricity exchange between the household node and the grid
at each time step, excluding EV charging.

Each household node can contain four components that contribute to its net
non-EV profile:

- Basic household electricity demand
- Heat-pump electricity demand
- Solar-panel production
- Home-battery charging and discharging

Demand from the household and heat pump is represented as positive power,
whereas electricity production from the solar panels is represented as negative
power. Similarly, charging of the home battery represents positive power and
discharging represents negative power. The net non-EV profile of a household
node is therefore calculated as:

$$
P_{\mathrm{non\text{-}EV},n}(t)
=
P_{\mathrm{household},n}(t)
+
P_{\mathrm{heat\ pump},n}(t)
+
P_{\mathrm{solar},n}(t)
+
P_{\mathrm{battery},n}(t)
$$

A positive value indicates that the household node has a net electricity demand
from the grid at that time step, while a negative value indicates that the
household node is supplying electricity to the grid.

The model creates each household node by independently creating its basic
household demand, heat pump, solar panels, and home battery. The stochastic
properties of these components are therefore determined at the individual
household level. Once the four component profiles have been created, they are
added together to obtain the net non-EV profile of that household node.

These node-level profiles are subsequently assigned to the power lines based on
the number of household nodes allocated to each line. The profiles of the nodes
connected to a line are summed to obtain the line-level non-EV demand profile.

#### Basic household electricity demand

TODO: Describe how the yearly basic household electricity demand is drawn and
how this yearly demand is converted into a time-dependent demand profile.

#### Heat-pump demand

TODO: Describe how the presence and characteristics of heat pumps are
determined, how household heat demand is calculated, and how the coefficient
of performance (COP) is used to convert heat demand into an electricity demand
profile.

#### Solar-panel production

TODO: Describe how the presence and characteristics of solar panels are
determined and how their electricity-production profile is calculated. Solar
production is represented by negative power because it supplies electricity
rather than consuming it.

#### Home-battery demand

TODO: Describe how the presence, capacity, charging power, and discharging
power of home batteries are determined, and how their state of charge and
resulting power profile are calculated. Battery charging is represented as
positive power demand, while battery discharging is represented as negative
power demand.

#### Assigning household nodes to lines

The household nodes are distributed over the power lines proportionally to their capacities. For each line, the ideal number of household nodes is first calculated from its share of the total line capacity:

$$
n_i^*
=
N_{\mathrm{households}}
\frac{P_{\mathrm{line},i}}
{\sum_j P_{\mathrm{line},j}}
$$

Since the number of household nodes assigned to a line must be an integer, these ideal values cannot generally be used directly. The model therefore applies the **largest remainder method**. First, the ideal number of nodes for each line is rounded down to the nearest integer. This generally leaves a small number of household nodes unassigned. These remaining nodes are assigned, one by one, to the lines with the largest fractional remainders in their ideal allocations. This ensures that the total number of assigned nodes is exactly equal to the number of households, while keeping the distribution as close as possible to proportional to the line capacities. A line may receive no household nodes if the number of households is small relative to the number of lines or its proportional allocation is sufficiently small.


#### Assigning non-EV demand to lines

After determining the number of household nodes connected to each power line, the corresponding non-EV demand profiles are assigned to these lines. The household profiles have already been generated using random draws, so no additional randomisation is applied during this assignment. Instead, the profiles are assigned sequentially according to the previously determined number of nodes per line.

For each power line, the non-EV demand profiles of all household nodes assigned to that line are summed to obtain a single line-level non-EV demand profile:

$$
P_{\mathrm{non\text{-}EV},i}(t)
=
\sum_{n \in N_i} P_{\mathrm{non\text{-}EV},n}(t)
$$

where $N_i$ is the set of household nodes assigned to line $i$. The resulting profile therefore represents the total non-EV household demand connected to that power line at each time step. These line-level profiles can subsequently be combined with the EV charging demand assigned to the same lines to determine the total line load and assess whether the line capacity is exceeded.

#### Own driveway chargers
Users x Own driveway proportion

also power?



Trafo --> Lines 
Non EV profiles

EV cpacities