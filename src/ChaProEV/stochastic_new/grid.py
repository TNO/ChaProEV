import uuid
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import polars as pl
from box import Box

from ChaProEV.stochastic_new.monte_carlo import (
    RandomGenerators,
    draw_beta_value,
)

# 8. Connection-level checks do not necessarily require every connection profile

# You only need a connection-level profile where EV charging can occur and where the connection limit matters.

# For example:

# household connection with private charging: connection check required;
# street-charging connection: connection check required;
# household without EV charging: only contributes fixed load to the line;
# ordinary non-EV connection: individual connection state may not be needed during the charging algorithm.

# This suggests a hybrid approach:

# Plain Text
# All non-EV connections
# → generate profiles
# → aggregate fixed power to lines and transformers
#
# EV-capable connections only
# → retain connection-level baseline profiles
# → maintain connection-level EV state

# That may reduce memory considerably.

# So the mutable state could contain:

# Python
# EV_connection_non_EV_power_kW
# EV_connection_EV_power_kW

# only for connections that can host charging, together with full line and transformer arrays.

# Each EV-capable connection then has a simulation index into this subset.

# 9. Triple capacity check

# For a proposed charging profile:

# Python
# proposed_power_kW: npt.NDArray[np.float64]

# and:

# Python
# time_slice = slice(start_time_index, end_time_index)

# calculate:

# Python
# connection_available_power_kW = (
# topology.connection_capacities_kW[connection_index]
# - state.connection_non_EV_power_kW[
# connection_index,
# time_slice,
# ]
# - state.connection_EV_power_kW[
# connection_index,
# time_slice,
# ]
# )

# Then line:

# Python
# line_available_power_kW = (
# topology.line_capacities_kW[line_index]
# - state.line_non_EV_power_kW[line_index, time_slice]
# - state.line_EV_power_kW[line_index, time_slice]
# )

# And transformer:

# Python
# transformer_available_power_kW = (
# topology.transformer_capacities_kW[transformer_index]
# - state.transformer_non_EV_power_kW[
# transformer_index,
# time_slice,
# ]
# - state.transformer_EV_power_kW[
# transformer_index,
# time_slice,
# ]
# )

# The request fits if:

# Python
# fits = (
# np.all(proposed_power_kW <= connection_available_power_kW)
# and np.all(proposed_power_kW <= line_available_power_kW)
# and np.all(proposed_power_kW <= transformer_available_power_kW)
# )

# If accepted, add the same profile at all three levels:

# Python
# state.connection_EV_power_kW[
# connection_index,
# time_slice,
# ] += proposed_power_kW
#
# state.line_EV_power_kW[
# line_index,
# time_slice,
# ] += proposed_power_kW
#
# state.transformer_EV_power_kW[
# transformer_index,
# time_slice,
# ] += proposed_power_kW

# This keeps the checks fast because you process only the active session horizon.

# 10. Supporting vehicles that should bypass the grid

# I would not fill the code with checks such as:

# Python
# if vehicle_type == 'car':

# Instead, represent whether a charging location is grid-constrained.

# A simple first option is:

# Python
# @dataclass
# class ChargingInfrastructure:
# grid_connection_id: uuid.UUID | None

# Then:

# Python
# if charging_infrastructure.grid_connection_id is None:
# # No modeled grid-capacity restriction

# That can represent dedicated infrastructure for trucks, ships, aircraft, or other modelled modes.

# A cleaner long-term design is to give the charging infrastructure a capacity-management strategy:

# Python
# class ChargingCapacityManager(Protocol):
# def profile_fits(...) -> bool:
# ...
#
# def apply_profile(...) -> None:
# ...

# Implementations:

# Plain Text
# GridCapacityManager
# connection + line + transformer checks
#
# UnconstrainedCapacityManager
# always accepts the profile
#
# DedicatedCapacityManager
# checks only the dedicated site capacity

# I would not introduce this protocol immediately. For the first version, an optional grid connection is sufficient:

# Python
# grid_connection_id: uuid.UUID | None
# Recommended sequence from here

# I would pause GridState and build this in order:

# Rename/create the domain-level Grid.
# Add GridConnection.
# Add connections to PowerLine.
# Generate household and street-charging connections during grid creation.
# Define how users or households are assigned to existing connections.
# Extend GridTopology with flattened connection arrays and mappings.
# Decide which connection-level profiles must remain in memory.
# Define GridState.
# Implement the connection → line → transformer capacity check.
# Add alternative charging profiles only after the basic accept/reject flow works.

# The most important design correction is: draw or select a connection for the user, not a transformer and line independently. The chosen connection already uniquely determines the upstream line and transformer, preventing inconsistent assignments.

# Define the Grid, GridConnection, and updated PowerLine classesShow how to create household and street-charging connectionsDesign user assignment for private and public charging

# I would initially make Grid a domain object only. The optimized arrays remain separate:

# grid = Grid.create(...)
# grid_topology = GridTopology.create(grid=grid)
# grid_state = GridState.create(...)


# NetworkTopology → GridTopology
# NetworkState    → GridState
# transformer_index, line_index, connection_index = (
#     grid_topology.get_grid_indices(
#         connection_id=charging_connection_id,
#     )
# )

# What power profiles should be stored?

# I would distinguish between:

# fixed non-EV net power;
# mutable accepted EV power.

# At connection level:

# Python
# connection_non_EV_power_kW
# connection_EV_power_kW

# Line and transformer values can be aggregated from the connections.

# However, I would not automatically store all six full arrays without considering memory:

# Plain Text
# connection non-EV
# connection EV
# line non-EV
# line EV
# transformer non-EV
# transformer EV

# The connection level could be much larger than the line level.

# A practical first design is:

# Python
# @dataclass
# class GridState:
# connection_non_EV_power_kW: npt.NDArray[np.float64]
# connection_EV_power_kW: npt.NDArray[np.float64]
#
# line_non_EV_power_kW: npt.NDArray[np.float64]
# line_EV_power_kW: npt.NDArray[np.float64]
#
# transformer_non_EV_power_kW: npt.NDArray[np.float64]
# transformer_EV_power_kW: npt.NDArray[np.float64]

# This is straightforward and fast, but potentially memory-heavy.

# Before committing to that structure, estimate:

# Python
# bytes_per_array = (
# number_of_entities
# * amount_of_time_steps
# * np.dtype(np.float64).itemsize
# )

# For example, 10,000 connections and 525,600 minute steps would require approximately 42 GB for one float64 array. In that case, full-year connection-level arrays would be infeasible.

# Possible remedies are:

# float32, halving memory;
# shorter simulation horizons;
# rolling windows;
# storing fixed profiles externally and loading the relevant horizon;
# storing only connections that can host EV charging;
# aggregating non-EV load at line level where connection-level checking is unnecessary.

# def get_grid_indices(
#     self,
#     *,
#     connection_id: uuid.UUID,
# ) -> tuple[int, int, int]:
#     connection_index: int = self.connection_id_to_index[connection_id]

#     line_index: int = int(
#         self.connection_to_line[connection_index]
#     )

#     transformer_index: int = int(
#         self.line_to_transformer[line_index]
#     )

#     return (
#         transformer_index,
#         line_index,
#         connection_index,
#     )

# @dataclass
# class GridTopology:
#     transformer_id_to_index: dict[uuid.UUID, int]
#     connection_id_to_index: dict[uuid.UUID, int]

#     transformer_capacities_kW: npt.NDArray[np.float64]
#     line_capacities_kW: npt.NDArray[np.float64]
#     connection_capacities_kW: npt.NDArray[np.float64]

#     transformer_line_offsets: npt.NDArray[np.int64]
#     line_to_transformer: npt.NDArray[np.int64]


#     line_connection_offsets: npt.NDArray[np.int64]
#     connection_to_line: npt.NDArray[np.int64]
#     connection_to_transformer: npt.NDArray[np.int64]
@dataclass
class GridConnection:
    ID: uuid.UUID
    index: int
    capacity_kW: float
    connection_type: GridConnectionType


@dataclass
class PowerLine:
    index: int
    capacity_kW: float
    connections: list[GridConnection]


# @dataclass
# class Transformer:
#     ID: uuid.UUID
#     capacity_kW: float
#     power_lines: list[PowerLine]


# @dataclass
# class Grid:
#     transformers: list[Transformer]

# # While writing get_non_EV_power_demand_per_line_kW, I thought of the following (not the change from network --> grid):      # Go through lines and draw powers by:
# # setting an amount of connections per line
# # (ransdom draw between zero and line_power/power per connection)
# # Then for each connection, draw a yearly consumption adn profile
# # shape. The sum of these connections per line will then provide
# # line_non_EV_power_kW: npt.NDArray[np.float64] = np.zeros(
# # Note that we probably should introduce connections to the grid
# # (In addition to transformers and power lines)
# # maybe move all this to a grid.py module
# # Then we draw a connection within all connection when creating the users
# # (rather than drawing the characteristics as we do now)
# # It might be useful to have uuids for lines and connections too,
# # with conversions to indices.
# # This also means that we probably have to add the connection level
# # into the Grid object.
# # Does that mean that we can only update/work with connection level
# # power profiles sums and then do the go/no-go with
# # a triple check: connection ok, line ok, grid ok
# # where we need to do these checks only for the horizon at hand
# # and where all the non-EV parts are fixed anyway?
# # Also, this grid would be for the homes of the users.
# # We assume that other locations are fine (dedicated charging infrastrure)                                                       This means, I will take a step back. I first want to create a grid that has transfromers to which lines are attached, to which connections are attached.  Some of the connections will be street chargers. Some will be household chargers (in own driveways). Then, when we create users, they will get a transformer and line drawn to them. If they have own driveways, then they will get a hosuehold connection drawn for them. The amount of street chargers per line is given by the connectivity of street parking (need to think that all through). I also need spme kind of way to avoid this whole grid thing if looking at things other than cars (as they will have their own infrastructure).


# # User gets a line (street) and if charge at home--> connection
# # Otherwise connection is street
# # ALs skip this whole thing for bus, truck, van


from enum import StrEnum

# create grid
# → create household and street-charging connections
# → create users
# → assign users to suitable existing connections

# if user has own driveway
# user → household → household grid connection

# connection → line → transformer


# Private charging:
# User → household connection → line → transformer

# Street charging:
# User/activity → street charger → connection → line → transformer
# @dataclass
# class GridConnection:
#     ID: uuid.UUID
#     index: int
#     capacity_kW: float
#     connection_type: GridConnectionType


class GridConnectionType(StrEnum):
    HOUSEHOLD = 'household'
    STREET_CHARGING = 'street_charging'


# @dataclass
# class PowerLine:
#     index: int
#     capacity_kW: float
#     connections: list[GridConnection]


# @dataclass
# class Transformer:
#     ID: uuid.UUID
#     capacity_kW: float
#     power_lines: list[PowerLine]

# @dataclass
# class Connection:
#     ID: uuid.UUID
#     index: int


# @dataclass
# class PowerLine:
#     ID: uuid.UUID
#     index: int
#     capacity_kW: float


# @dataclass
# class Transformer:
#     ID: uuid.UUID
#     capacity_kW: float
#     power_lines: list[PowerLine]

#     @classmethod
#     def create(
#         cls,
#         *,
#         transformers_settings: Box,
#         random_generators: RandomGenerators,
#         beta_shape: float,
#     ) -> Transformer:
#         ID: uuid.UUID = uuid.uuid4()

#         transformer_capacities_kW: float = draw_beta_value(
#             minimum=transformers_settings.capacity_kW_min,
#             typical=transformers_settings.capacity_kW_typical,
#             maximum=transformers_settings.capacity_kW_max,
#             random_generator=random_generators.transformers,
#             shape=beta_shape,
#         )

#         line_amount_to_transformer_capacity_ratio: float = draw_beta_value(
#             minimum=(
#                 transformers_settings.line_amount_to_transformer_capacity_ratio_min  # noqa:E501
#             ),
#             typical=(
#                 transformers_settings.line_amount_to_transformer_capacity_ratio_typical  # noqa:E501
#             ),
#             maximum=(
#                 transformers_settings.line_amount_to_transformer_capacity_ratio_max  # noqa:E501
#             ),
#             random_generator=random_generators.transformers,
#             shape=beta_shape,
#         )

#         amount_of_lines: int = int(
#             line_amount_to_transformer_capacity_ratio
#             * transformer_capacities_kW
#         )

#         if amount_of_lines < 1:
#             raise ValueError(
#                 'The calculated number of power lines is less than one: '
#                 f'{transformer_capacities_kW=}, '
#                 f'{line_amount_to_transformer_capacity_ratio=}, '
#                 f'{amount_of_lines=}.'
#             )

#         line_capacity_weights: list[float] = [
#             draw_beta_value(
#                 minimum=(
#                     transformers_settings.line_capacity_to_average_ratio_min
#                 ),
#                 typical=(
#                     transformers_settings.line_capacity_to_average_ratio_typical  # noqa:E501
#                 ),
#                 maximum=(
#                     transformers_settings.line_capacity_to_average_ratio_max
#                 ),
#                 random_generator=random_generators.transformers,
#                 shape=beta_shape,
#             )
#             for _ in range(amount_of_lines)
#         ]

#         total_line_capacity_weight: float = sum(line_capacity_weights)

#         power_lines: list[PowerLine] = [
#             PowerLine(
#                 ID=uuid.uuid4(),
#                 index=line_index,
#                 capacity_kW=(
#                     transformer_capacities_kW
#                     * line_capacity_weight
#                     / total_line_capacity_weight
#                 ),
#             )
#             for line_index, line_capacity_weight in enumerate(
#                 line_capacity_weights
#             )
#         ]

#         total_line_capacities_kW: float = sum(
#             power_line.capacity_kW for power_line in power_lines
#         )

#         if not np.isclose(
#             total_line_capacities_kW,
#             transformer_capacities_kW,
#         ):
#             raise RuntimeError(
#                 'The allocated power-line capacity does not equal the '
#                 'transformer capacity: '
#                 f'{total_line_capacities_kW=}, '
#                 f'{transformer_capacities_kW=}.'
#             )

#         return cls(
#             ID=ID,
#             capacity_kW=transformer_capacities_kW,
#             power_lines=power_lines,
#         )


# @dataclass
# class GridTopology:
#     '''
#     Numerical representation of the grid topology.

#     Maps transformers and their power lines to integer indices and stores
#     their capacities for efficient use in grid calculations.

#     '''

#     transformer_id_to_index: dict[uuid.UUID, int]
#     transformer_capacities_kW: npt.NDArray[np.float64]
#     line_capacities_kW: npt.NDArray[np.float64]

#     transformer_line_offsets: npt.NDArray[np.int64]
#     line_to_transformer: npt.NDArray[np.int64]

#     @classmethod
#     def create(
#         cls,
#         *,
#         transformers_pool: list[Transformer],
#     ) -> GridTopology:
#         transformer_id_to_index: dict[uuid.UUID, int] = {
#             transformer.ID: transformer_index
#             for transformer_index, transformer in enumerate(transformers_pool)
#         }

#         transformer_capacities_kW: npt.NDArray[np.float64] = np.array(
#             [transformer.capacity_kW for transformer in transformers_pool],
#             dtype=np.float64,
#         )

#         line_capacities_kW: npt.NDArray[np.float64] = np.array(
#             [
#                 power_line.capacity_kW
#                 for transformer in transformers_pool
#                 for power_line in transformer.power_lines
#             ],
#             dtype=np.float64,
#         )

#         line_amounts: npt.NDArray[np.int64] = np.array(
#             [
#                 len(transformer.power_lines)
#                 for transformer in transformers_pool
#             ],
#             dtype=np.int64,
#         )

#         transformer_line_offsets: npt.NDArray[np.int64] = np.concatenate(
#             (
#                 np.array([0], dtype=np.int64),
#                 np.cumsum(line_amounts),
#             )
#         )

#         line_to_transformer: npt.NDArray[np.int64] = np.repeat(
#             np.arange(len(transformers_pool), dtype=np.int64),
#             line_amounts,
#         )

#         return cls(
#             transformer_id_to_index=transformer_id_to_index,
#             transformer_capacities_kW=transformer_capacities_kW,
#             line_capacities_kW=line_capacities_kW,
#             transformer_line_offsets=transformer_line_offsets,
#             line_to_transformer=line_to_transformer,
#         )

#     def get_grid_indices(
#         self,
#         *,
#         transformer_id: uuid.UUID,
#         line_index: int,
#     ) -> tuple[int, int]:
#         transformer_index: int = self.transformer_id_to_index[transformer_id]

#         start: int = self.transformer_line_offsets[transformer_index]
#         end: int = self.transformer_line_offsets[transformer_index + 1]

#         amount_of_lines: int = end - start

#         if not 0 <= line_index < amount_of_lines:
#             raise IndexError(
#                 'Power-line index is outside the range for this transformer: '
#                 f'{transformer_id=}, '
#                 f'{line_index=}, '
#                 f'{amount_of_lines=}.'
#             )

#         global_line_index: int = start + line_index

#         return transformer_index, global_line_index


# @dataclass
# class GridState:
#     '''
#     Time-dependent power state of the electricity grid.
#     Stores non-EV and EV power for each transformer and power line.

#     '''

#     transformer_non_EV_power_kW: npt.NDArray[np.float64]
#     line_non_EV_power_kW: npt.NDArray[np.float64]

#     transformer_EV_power_kW: npt.NDArray[np.float64]
#     line_EV_power_kW: npt.NDArray[np.float64]

#     @classmethod
#     def create(
#         cls,
#         *,
#         topology: GridTopology,
#         line_non_EV_power_kW: npt.NDArray[np.float64],
#         amount_of_time_steps: int,
#     ) -> GridState:
#         transformer_non_EV_power_kW = np.zeros(
#             (
#                 len(topology.transformer_capacities_kW),
#                 amount_of_time_steps,
#             ),
#             dtype=np.float64,
#         )

#         for transformer_index in range(
#             len(topology.transformer_capacities_kW)
#         ):
#             start: int = topology.transformer_line_offsets[transformer_index]
#             end: int = topology.transformer_line_offsets[transformer_index + 1]

#             transformer_non_EV_power_kW[transformer_index] = (
#                 line_non_EV_power_kW[start:end].sum(axis=0)
#             )

#         transformer_EV_power_kW = np.zeros_like(transformer_non_EV_power_kW)

#         line_EV_power_kW = np.zeros_like(line_non_EV_power_kW)

#         return cls(
#             transformer_non_EV_power_kW=transformer_non_EV_power_kW,
#             line_non_EV_power_kW=line_non_EV_power_kW,
#             transformer_EV_power_kW=transformer_EV_power_kW,
#             line_EV_power_kW=line_EV_power_kW,
#         )


# @dataclass
# class Grid:
#     topology: GridTopology
#     state: GridState

#     @classmethod
#     def create(
#         cls,
#         *,
#         transformers_pool: list[Transformer],
#         line_non_EV_power_kW: npt.NDArray[np.float64],
#         amount_of_time_steps: int,
#     ) -> Grid:

#         topology: GridTopology = GridTopology.create(
#             transformers_pool=transformers_pool
#         )
#         state: GridState = GridState.create(
#             topology=topology,
#             line_non_EV_power_kW=line_non_EV_power_kW,
#             amount_of_time_steps=amount_of_time_steps,
#         )
#         return cls(topology=topology, state=state)


# def get_transformers_pool(
#     *, scenario: Box, random_generators: RandomGenerators
# ) -> list[Transformer]:

#     transformers_settings: Box = scenario.transformers
#     beta_shape: float = scenario.monte_carlo.beta_shape
#     amount: int = transformers_settings.amount

#     return [
#         Transformer.create(
#             transformers_settings=transformers_settings,
#             random_generators=random_generators,
#             beta_shape=beta_shape,
#         )
#         for _ in range(amount)
#     ]


# @dataclass
# class Household:
#     yearly_consumption_kWh_excluding_EV_heat_pump_home_battery: float
#     profile_shape: pl.Series


# @dataclass
# class HeatPump:
#     yearly_consumption_kWh: float
#     profile_shape: pl.Series


# @dataclass
# class HomeBattery:
#     charge_profile: pl.Series
#     discharge_profile: pl.Series


# @dataclass
# class SolarPanels:
#     yearly_production_kWh: float
#     profile_shape: pl.Series

#     # @staticmethod
#     # def get_transformer_ID_and_line_index(
#     #     *,
#     #     transformers_pool: list[Transformer],
#     #     transformers_settings: Box,
#     #     random_generator: np.random.Generator,
#     # ) -> tuple[uuid.UUID, int]:
#     #     if not transformers_pool:
#     #         raise ValueError(
#     #             'Cannot assign a transformer because '
#     #             'transformers_pool is empty.'
#     #         )

#     #     proportions_of_users: list[float] = (
#     #         transformers_settings.proportions_of_users
#     #     )

#     #     if len(proportions_of_users) != len(transformers_pool):
#     #         raise ValueError(
#     #             'The number of user proportions must equal the number of '
#     #             'transformers: '
#     #             f'{len(proportions_of_users)=}, '
#     #             f'{len(transformers_pool)=}.'
#     #         )

#     #     if not np.isclose(sum(proportions_of_users), 1.0):
#     #         raise ValueError(
#     #             'Transformer user proportions must sum to 1.0: '
#     #             f'{sum(proportions_of_users)=}, '
#     #             f'{proportions_of_users=}.'
#     #         )

#     #     transformer_index: int = int(
#     #         random_generator.choice(
#     #             len(transformers_pool),
#     #             p=proportions_of_users,
#     #         )
#     #     )
#     #     user_transformer: Transformer = transformers_pool[transformer_index]

#     #     if not user_transformer.power_lines:
#     #         raise ValueError(
#     #             'The selected transformer has no power lines: '
#     #             f'{user_transformer.ID=}.'
#     #         )

#     #     line_capacities_kW: list[float] = [
#     #         power_line.capacity_kW
#     #         for power_line in user_transformer.power_lines
#     #     ]

#     #     total_line_capacities_kW: float = sum(line_capacities_kW)

#     #     line_probabilities: list[float] = [
#     #         capacity_kW / total_line_capacities_kW
#     #         for capacity_kW in line_capacities_kW
#     #     ]

#     #     selected_line_position: int = int(
#     #         random_generator.choice(
#     #             len(user_transformer.power_lines),
#     #             p=line_probabilities,
#     #         )
#     #     )

#     #     selected_power_line: PowerLine = user_transformer.power_lines[
#     #         selected_line_position
#     #     ]

#     #     return user_transformer.ID, selected_power_line.index

#     # @staticmethod
#     # def draw_non_EV(
#     #     *,
#     #     households_settings: Box,
#     #     random_generator: np.random.Generator,
#     #     beta_shape: float,
#     # ) -> tuple[Household, HeatPump, HomeBattery, SolarPanels]:

#     #     yearly_consumption_kWh_excluding_EV_heat_pump_home_battery: float = (
#     #         draw_beta_value(
#     #             minimum=households_settings.yearly_consumption_kWh_excluding_EV_heat_pump_home_battery_min,  # noqa: E501
#     #             typical=households_settings.yearly_consumption_kWh_excluding_EV_heat_pump_home_battery_typical,  # noqa: E501
#     #             maximum=households_settings.yearly_consumption_kWh_excluding_EV_heat_pump_home_battery_max,  # noqa: E501
#     #             random_generator=random_generator,
#     #             shape=beta_shape,
#     #         )
#     #     )

#     #     demand_profile_shape_name: str = random_generator.choice(
#     #         np.array(households_settings.possible_profile_shape_references),
#     #         p=households_settings.possible_profile_shape_references_weights,
#     #     )

#     #     profiles_shapes_source: pl.DataFrame = pl.read_csv(
#     #         Path(households_settings.profiles_shapes_source)
#     #     )
#     #     profile_shape: pl.Series = profiles_shapes_source[
#     #         demand_profile_shape_name
#     #     ]
#     #     household: Household = Household(
#     #         yearly_consumption_kWh_excluding_EV_heat_pump_home_battery=yearly_consumption_kWh_excluding_EV_heat_pump_home_battery,  # noqa:E501
#     #         profile_shape=profile_shape,
#     #     )

#     #     adoption_rate_heat_pumps: float = (
#     #         households_settings.adoption_rate_heat_pumps
#     #     )
#     #     has_heat_pump: bool = bool(
#     #         random_generator.choice(
#     #             [True, False],
#     #             p=[adoption_rate_heat_pumps, 1 - adoption_rate_heat_pumps],
#     #         )
#     #     )
#     #     if has_heat_pump:
#     #         yearly_heat_pump_consumption_kWh: float = draw_beta_value(
#     #             minimum=households_settings.yearly_heat_pump_consumption_kWh_min,  # noqa: E501
#     #             typical=(
#     #                 households_settings.yearly_heat_pump_consumption_kWh_typical  # noqa:E501
#     #             ),
#     #             maximum=households_settings.yearly_heat_pump_consumption_kWh_max,  # noqa:E501
#     #             random_generator=random_generator,
#     #             shape=beta_shape,
#     #         )

#     #     else:
#     #         yearly_heat_pump_consumption_kWh = 0

#     #     heat_pump_shape: pl.Series = pl.Series()
#     #     heat_pump: HeatPump = HeatPump(
#     #         yearly_consumption_kWh=yearly_heat_pump_consumption_kWh,
#     #         profile_shape=heat_pump_shape,
#     #     )

#     #     adoption_rate_solar_panels: float = (
#     #         households_settings.adoption_rate_solar_panels
#     #     )
#     #     has_solar_panels: bool = bool(
#     #         random_generator.choice(
#     #             [True, False],
#     #             p=[adoption_rate_solar_panels, 1 - adoption_rate_solar_panels],
#     #         )
#     #     )
#     #     if has_solar_panels:
#     #         solar_production: float = (
#     #             yearly_consumption_kWh_excluding_EV_heat_pump_home_battery
#     #         )
#     #         adoption_rate_home_batteries: float = (
#     #             households_settings.adoption_rate_home_batteries_if_solar_panels  # noqa: E501
#     #         )
#     #     else:
#     #         solar_production = 0
#     #         adoption_rate_home_batteries = (
#     #             households_settings.adoption_rate_home_batteries_if_not_solar_panels  # noqa: E501
#     #         )

#     #     solar_shape: pl.Series = pl.Series()
#     #     solar_panels: SolarPanels = SolarPanels(
#     #         yearly_production_kWh=solar_production, profile_shape=solar_shape
#     #     )
#     #     has_home_battery: bool = bool(
#     #         random_generator.choice(
#     #             [True, False],
#     #             p=[
#     #                 adoption_rate_home_batteries,
#     #                 1 - adoption_rate_home_batteries,
#     #             ],
#     #         )
#     #     )
#     #     if has_home_battery:
#     #         home_battery_charge_profile: pl.Series = pl.Series()
#     #         home_battery_discharge_profile: pl.Series = pl.Series()
#     #     else:
#     #         home_battery_charge_profile = pl.Series()
#     #         home_battery_discharge_profile = pl.Series()

#     #     home_battery: HomeBattery = HomeBattery(
#     #         charge_profile=home_battery_charge_profile,
#     #         discharge_profile=home_battery_discharge_profile,
#     #     )

#     #     return household, heat_pump, home_battery, solar_panels
