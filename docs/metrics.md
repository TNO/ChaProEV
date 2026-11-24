### Matching EV demand to the residential grid

After EV charging has been simulated, the resulting charging demand is matched
to the residential power lines to which the EV users are connected.

For each power line, the model considers all EV users assigned to that line.
Only charging taking place at **home** is included in the residential-grid
demand. Charging at other locations is not assigned to the residential power
line.

The home-charging demand of all EV users connected to a line is summed for
each timestep:

$$
P_{\mathrm{EV},t} = \sum_i P_{\mathrm{EV},i,t}
$$

where $P_{\mathrm{EV},i,t}$ is the power drawn from the grid by EV user $i$ at
home during timestep $t$.

This EV demand is combined with the existing non-EV demand of the power line:

$$
P_{\mathrm{total},t}
=
P_{\mathrm{non-EV},t}
+
P_{\mathrm{EV},t}
$$

The total demand is compared with the capacity of the power line. The line is
considered overloaded when:

$$
P_{\mathrm{total},t} > P_{\mathrm{capacity}}
$$

For an overloaded timestep, the additional capacity required is calculated as:

$$
P_{\mathrm{additional},t}
=
P_{\mathrm{total},t}
-
P_{\mathrm{capacity}}
$$

If the capacity is not exceeded, the additional capacity required is zero.

For example, consider a power line with a capacity of 100 kW. If non-EV demand
is 70 kW and home EV charging contributes another 45 kW, total demand is
115 kW:

$$
70 + 45 = 115\ \mathrm{kW}
$$

The power line is therefore overloaded. The additional capacity required is:

$$
115 - 100 = 15\ \mathrm{kW}
$$

The resulting EV demand, overload status, and additional capacity requirement
are stored for every timestep in the power line's EV-demand-matching DataFrame.
These results can subsequently be aggregated across power lines to calculate
the residential grid-congestion statistics.







### Residential grid congestion statistics

Residential grid congestion is evaluated for each power line and timestep.
A power line is considered overloaded when its total electricity demand exceeds
its available capacity.

Two related but distinct measures of congestion are calculated:

1. **Number of overloaded lines**

   For every timestep, the number of power lines exceeding their capacity is
   counted. Because multiple lines can be overloaded simultaneously, this value
   can be larger than one.

   The average number of overloaded lines per timestep is calculated over the
   simulation.

2. **Timesteps with an overload**

   A timestep is considered congested when at least one power line exceeds its
   capacity. The proportion of congested timesteps therefore represents how
   often residential grid congestion occurs, irrespective of how many lines
   are overloaded simultaneously.

For example, consider four timesteps with the following numbers of overloaded
lines:

| Timestep | Overloaded lines | At least one overloaded |
|----------|------------------|-------------------------|
| 1        | 0                | No                      |
| 2        | 1                | Yes                     |
| 3        | 2                | Yes                     |
| 4        | 0                | No                      |

There are three line-overload occurrences in total. The average number of
overloaded lines per timestep is therefore `3 / 4 = 0.75`.

However, an overload occurs during only two of the four timesteps. The
proportion of timesteps with at least one overloaded line is therefore
`2 / 4 = 0.50`.

Both measures are also calculated separately for each hour of the day
(0–23). This makes it possible to identify both when congestion occurs most
frequently and when multiple power lines tend to be overloaded simultaneously.