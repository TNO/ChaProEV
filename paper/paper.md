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




\begin{align}
e_{t} & =e_{t-1}+\eta^{\mathrm{G2V}}p_{t}^{\mathrm{G2V}}\Delta-\frac{p_{t}^{\mathrm{V2G}}}{\eta^{\mathrm{V2G}}}\Delta-E_{t}^{\mathrm{drive}}\Delta N\alpha\quad\forall t\label{eq:EV-soc}\\
\underline{E}N_{t}^{\mathrm{plugged}}N\alpha & \leq e_{t}\leq\bar{E}N_{t}^{\mathrm{plugged}}N\alpha\qquad\forall t\label{eq:soc-limits}\\
0 & \leq p_{t}^{\mathrm{G2V}}\leq\bar{P}_{t}^{\mathrm{G2V}}N_{t}^{\mathrm{plugged}}N\alpha\qquad\forall t\\
0 & \leq p_{t}^{\mathrm{V2G}}\leq\bar{P}_{t}^{\mathrm{V2G}}N_{t}^{\mathrm{plugged}}N\alpha\qquad\forall t\label{eq:v2G-limits}
\end{align}
where $t$ is the time index and parameter $\Delta$ (h) is the duration
of the time step. Variable $e_{t}$ (kWh) tracks the total state of
charge of the plugged EVs to the grid. Variables $p_{t}^{\mathrm{G2V}}$/$p_{t}^{V2G}$
(kW) are the power consumed/provided by the EVs from/to the grid. Parameters $\eta^{\mathrm{G2V}}$/$\eta^{\mathrm{V2G}}$
(p.u.) are the charging/discharging efficiencies; $\underline{E}$/$\bar{E}$
(kWh) are the minimum/maximum storage capacity per vehicle; $N$ is
the total number of EVs; and $\alpha$ (p.u.) is the share of controllable
EVs providing demand response to the system. 


Section \ref{boundary_output}
defines the remaining parameters (profiles).


\autoref{eq:EV-soc}-\autoref{eq:v2G-limits} model the demand
response provided by controllable EVs through $p_{t}^{\mathrm{G2V}}$
and $p_{t}^{\mathrm{V2G}}$. The total EV demand $d_{t}^{\mathrm{Tot}}$
(kW), including the non-controllable load, is defined as
\begin{align}
d_{t}^{\mathrm{Tot}} & =D_{t}^{0}N\left(1-\alpha\right)+p_{t}^{\mathrm{G2V}}-p_{t}^{\mathrm{V2G}}\qquad\forall t\label{eq:Total-EV-demand}
\end{align}
where $D_{t}^{0}$ is the reference (non-demand response) profile given by ChaProEV (see Section \ref{reference_profile_data}),
and $\alpha$ is the proportion of vehicles that are optimally providing demand response.




## Further modelling


The formulation \autoref{eq:EV-soc}-\autoref{eq:v2G-limits} has several
shortcomings because there is no clear distinction between plugged
and unplugged EVs. For example, suppose that plugged EVs were fully charged and
the unplugged EVs were near to being empty, equation \autoref{eq:EV-soc}
allows that unplugged EVs could be charging while they should be unavailable
to the system. [@momber_2014_pevstorage_1_22] shows this and more
detailed cases where the traditional EV aggregated formulation fails.

To overcome the above shortcomings, [@momber_2014_pevstorage_1_22]
proposed a more rigorous formulation, in which inventories for plugged/unplugged
EVs are clearly distinguished from each other. This formulation ensures
that only EVs plugged to the grid are charged/discharged from the
electric system. It also guarantees that unplugged EVs cannot further
charge while driving.

The state of charge of EVs in \autoref{eq:EV-soc} is now replaced by
the separated plugged \autoref{eq:soc-plugged} and unplugged \autoref{eq:soc-unplugged}
state of charges. Additionally, \autoref{eq:soc-limits} is replaced
by \autoref{eq:soc-plugged-limits} and \autoref{eq:soc-unplugged-limits}.
\begin{align}
e_{t}^{\mathrm{plugged}}= & e_{t-1}^{\mathrm{plugged}}+\eta^{\mathrm{G2V}}p_{t}^{\mathrm{G2V}}\Delta-\frac{p_{t}^{\mathrm{V2G}}}{\eta^{\mathrm{V2G}}}\Delta\nonumber \\
 & +N_{t-1}^{\mathrm{plugging}}N\alpha e_{t-1}^{\mathrm{unplugged}}-N_{t-1}^{\mathrm{unplugging}}N\alpha e_{t-1}^{\mathrm{plugged}}\quad\forall t\label{eq:soc-plugged}\\
e_{t}^{\mathrm{unplugged}}= & e_{t-1}^{\mathrm{unplugged}}-E_{t-1}^{\mathrm{drive}}\Delta N\alpha\nonumber \\
 & -N_{t-1}^{\mathrm{plugging}}N\alpha e_{t-1}^{\mathrm{unplugged}}+N_{t-1}^{\mathrm{unplugging}}N\alpha e_{t-1}^{\mathrm{plugged}}\quad\forall t\label{eq:soc-unplugged}\\
\underline{E}N_{t}^{\mathrm{plugged}}N\alpha & \leq e_{t}^{\mathrm{plugged}}\leq\bar{E}N_{t}^{\mathrm{plugged}}N\alpha\qquad\forall t\label{eq:soc-plugged-limits}\\
\underline{E}N_{t}^{\mathrm{unplugged}}N\alpha & \leq e_{t}^{\mathrm{unplugged}}\leq\bar{E}N_{t}^{\mathrm{unplugged}}N\alpha\qquad\forall t\label{eq:soc-unplugged-limits}
\end{align}

# Software innovations

No code parameters and profiles modification (explain what kind of modifications 
are possible)
Scenarios

\begin{enumerate}
  \item \textit{Demand for next leg (kWh) (from network):} The charge that the vehicles 
  leaving in the next time step need to pull from the network 
  for the leg they are about to undertake, corrected by the charger efficiency. 
\item \textit{Demand for next leg (kWh) (to vehicles):} The part of the above that
vehicles get. ({$E_{t}^{\mathrm{drive}}$} in Equation \eqref{eq:EV-soc})
  \item \textit{Connected vehicles:} The share of vehicles that
are connected to a charger ({$N_{t}^{\mathrm{plugged}}$} in Equation \eqref{eq:soc-limits})
  \item \textit{Charging Power from Network (kW):} Maximum power that connected vehicles
  can potentially draw from the network. 
({$\bar{P}_{t}^{\mathrm{G2V}}$} in Equation \eqref{eq:EV-soc})
  \item \textit{Charging Power to Vehicles (kW):} Maximum power that can potentially go to vehicles
  go to vehicles (i.e. the same as above with a charger efficiency correction).
  \item \textit{Vehicle Discharge Power (kW):} The amount of power connected
vehicles can discharge to the network.
  \item \textit{Discharge Power to Network (kW):} How much of that discharged power can go to the network. 
({$\bar{P}_{t}^{\mathrm{V2G}}$} in Equation \eqref{eq:EV-soc})
  \item \textit{Effective charging efficiency:} Ratio between charging power going 
  to the vehicle and power coming from the network. This can vary in time,
  as the location of the charging vehicles (and thus the efficiency of the involved chargers)
  changes as they move around. 
($\eta^{\mathrm{G2V}}$ in Equation \eqref{eq:EV-soc})
\item \textit{Effective discharging efficiency:} Same as above, but for discharging
(it is the power going out of the vehicles divided by the power going into the network).
($\eta^{\mathrm{V2G}}$ in Equation \eqref{eq:EV-soc})

\end{enumerate}

ChaProEV also provides charging sessions (in case they are not obtained from energy system models). This provides another
description of the system that could be used for models and analyses that focus
on charging sessions rather than profiles (which are aggregates of such sessions).
Sessions include (in addition the elements that
a profile gets):
\begin{enumerate}
  \item \textit{Location:} Where the session takes place
  \item \textit{Start time:} At which moment the vehicles in the session can 
  start charging (i.e. when they arrive).
  \item \textit{End time:} At which moment the vehicles in the session must 
  stop charging (i.e. when they leave). 
  \item \textit{Demand for incoming leg (kWh) (to vehicle):} How much the incoming vehicles
  have spent on the leg arriving to the session.
  \item \textit{Maximal Possible Charge to Vehicles (kWh):} How much the vehicles
  could charge if they used the available power during their whole session.
  \item \textit{Charge to Vehicles (kWh):} How much of the vehicles actually charge
  during the session. This is based on the charging strategy of the vehicles
  and can be used to derive a charging profile.
  \item \textit{Charge from Network (kWh):} The same as above, but corrected
  for charging efficiency (i.e. how much the network  provides)
\end{enumerate}

![trips \label{fig:trips}](trips.png)

\autoref{trips}

# Acknowledgements

ChaProEV was partly developed under funding from the European Climate, 
Infrastructure and Environment Executive Agency under the European Union's
HORIZON Research and Innovation Actions under grant agreement no. 101095998.