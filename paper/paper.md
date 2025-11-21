---
title: 'ChaProEV: Generating Charging Profiles for Electric Vehicles'
tags:
  - Python
  - Battery-Electric Vehicles
  - Charging Profiles
  - Boundary conditions for optimisation
  - Mobility
  - Grid Impact
authors:
  - name: Omar Usmani
    orcid: 0000-0001-5619-4201
    equal-contrib: true
    affiliation: 1
  - name: Germán Morales-España
    orcid: 0000-0002-6372-6197
    equal-contrib: true 
    affiliation: "1, 2"
affiliations:
 - name: TNO Energy and Materials Transition, Radarweg 60, Amsterdam, 1043 NT, The Netherlands
   index: 1
   ror: 01bnjb948
 - name: Faculty of Electrical Engineering, Mathematics and Computer Science, Delft University of Technology, Delft, The Netherlands
   index: 2
   ror: 02e2c7k09
date: 18 November 2025
bibliography: paper.bib

---

# Summary
ChaProEV is

# Statement of need

- Profiles are good and useful, but optimisation modes might also
need soem underlying parameters to do optimisation computations as well
- Provide optimisation models with the boundary conditions they need
- ChaProEV povides the necessary parameters (as explemplified in COMPETES,
Mopo/Ines, etc.) in a clear and accessible way, with the also allowing
a clear way to modify them without touching code
[@COMPETES_demand_response]

# Conceptual innovations: Supporting optimisation models

## Basic elements
A commonly used aggregated EV formulation is [@morales-espana_classifying_2022]:

$$
e_{t}  = e_{t-1}+\eta^{\mathrm{G2V}}p_{t}^{\mathrm{G2V}}\Delta -\frac{p_{t}^{\mathrm{V2G}}}{\eta^{\mathrm{V2G}}}\Delta-E_{t}^{\mathrm{drive}}\Delta N\alpha\quad\forall t \label{SOC} \\
\underline{E}N_{t}^{\mathrm{plugged}}N\alpha & \leq e_{t}\leq\bar{E}N_{t}^{\mathrm{plugged}}N\alpha\qquad\forall t
$$
Two equ



## Further modelling

# Software innovations

No code parameters and profiles modification (explain what kind of modifications 
are possible)
Scenarios

1. Demand for next leg (kWh) (from network): The charge that the vehicles 
  leaving in the next time step need to pull from the network 
  for the leg they are about to undertake, corrected by the charger efficiency. 
2.  Demand for next leg (kWh) (to vehicles): The part of the above that
vehicles get. ({$E_{t}^{\mathrm{drive}}$} in Equation )
3. Connected vehicles:The share of vehicles that
are connected to a charger ({$N_{t}^{\mathrm{plugged}}$} in Equation )
  \item \textit{Charging Power from Network (kW):} Maximum power that connected vehicles
  can potentially draw from the network. 
({$\bar{P}_{t}^{\mathrm{G2V}}$} in Equation)
4. Charging Power to Vehicles (kW): Maximum power that can potentially go to vehicles
  go to vehicles (i.e. the same as above with a charger efficiency correction).
  \item \textit{Vehicle Discharge Power (kW):} The amount of power connected
vehicles can discharge to the network.
5. Discharge Power to Network (kW): How much of that discharged power can go to the network. 
({$\bar{P}_{t}^{\mathrm{V2G}}$} in Equation)
6. Effective charging efficiency: Ratio between charging power going 
  to the vehicle and power coming from the network. This can vary in time,
  as the location of the charging vehicles (and thus the efficiency of the involved chargers)
  changes as they move around. 
($\eta^{\mathrm{G2V}}$ in Equation)
7. Effective discharging efficiency: Same as above, but for discharging
(it is the power going out of the vehicles divided by the power going into the network).
($\eta^{\mathrm{V2G}}$ in Equation)



# Acknowledgements

ChaProEV was partly developed under funding from the European Climate, 
Infrastructure and Environment Executive Agency under the European Union's
HORIZON Research and Innovation Actions under grant agreement no. 101095998.