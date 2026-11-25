import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
from box import Box

from ChaProEV.stochastic_new.define import User
from ChaProEV.stochastic_new.monte_carlo import draw_beta_value
from ChaProEV.stochastic_new.time import TimeConstants, TimeRange, reshape


@dataclass
class HouseholdBasicDemand:
    non_BEV_HP_run_demand_kWh: float
    demand_shape: pl.Series
    profile: pl.Series

    @classmethod
    def create(
        cls,
        *,
        household_parameters: Box,
        random_generator: np.random.Generator,
        beta_shape: float,
        time_ranges: TimeRange,
        time_constants: TimeConstants,
        profiles_shapes_source_households: pl.DataFrame,
    ) -> HouseholdBasicDemand:
        '''
        Create the basic electricity-demand profile of a household.

        This demand excludes heat pumps, stationary batteries, and EV charging.

        The total household electricity demand for the run is drawn in kWh from
        user-defined bounds. A demand shape is then randomly selected from the
        available profile shapes using user-defined selection weights.

        The selected shape is resized to match the model run range, if
        necessary, and normalised so that its values sum to one.
        The normalised shape is then scaled to the total electricity demand
        for the run.

        The resulting energy per time step in kWh is divided by the time-step
        duration in hours to obtain the average power demand in kW for each
        time step.
        '''

        MINUTES_PER_HOUR: int = time_constants.MINUTES_PER_HOUR

        if time_ranges.frequency_type != 'm':
            raise ValueError('You need to use minutes for the frequency!')
        run_frequency_size: int = time_ranges.frequency_size
        run_time_resolution_hours: float = (
            run_frequency_size / MINUTES_PER_HOUR
        )

        # Draw the total basic household electricity demand for the run.
        non_BEV_HP_run_demand_kWh: float = draw_beta_value(
            minimum=household_parameters.run_consumption_kWh_excluding_EV_heat_pump_home_battery_min,  # noqa: E501
            typical=household_parameters.run_consumption_kWh_excluding_EV_heat_pump_home_battery_typical,  # noqa: E501
            maximum=household_parameters.run_consumption_kWh_excluding_EV_heat_pump_home_battery_max,  # noqa: E501
            random_generator=random_generator,
            shape=beta_shape,
        )

        # Select a demand shape according to the user-defined probabilities.
        demand_profile_shape_name: str = random_generator.choice(
            np.array(household_parameters.possible_profile_shape_references),
            p=household_parameters.possible_profile_shape_references_weights,
        )

        demand_shape: pl.Series = profiles_shapes_source_households[
            demand_profile_shape_name
        ]
        run_stamps_amount: int = len(time_ranges.run_stamps)

        demand_shape = reshape(
            source_shape=demand_shape, run_stamps_amount=run_stamps_amount
        )

        # Scale the shape to the total run demand and convert the
        # resulting energy per time step to average power in kW.
        profile: pl.Series = (
            non_BEV_HP_run_demand_kWh
            * demand_shape
            / run_time_resolution_hours
        )

        return cls(
            non_BEV_HP_run_demand_kWh=non_BEV_HP_run_demand_kWh,
            demand_shape=demand_shape,
            profile=profile,
        )


@dataclass
class HeatPumpDemand:
    run_heat_demand_kWh: float
    heat_demand_shape: pl.Series
    COP: float
    profile: pl.Series

    @classmethod
    def create(
        cls,
        *,
        heat_pump_parameters: Box,
        random_generator: np.random.Generator,
        beta_shape: float,
        time_ranges: TimeRange,
        time_constants: TimeConstants,
        demand_shapes_source_heat: pl.DataFrame,
    ) -> HeatPumpDemand:
        '''
        Create the electricity-demand profile of a household heat pump.

        The total heat demand for the run is drawn in kWh from user-defined
        bounds. The coefficient of performance (COP) of the heat pump is
        drawn separately and is used to convert the heat demand into
        electricity demand.

        A heat-demand shape is randomly selected from the available profile
        shapes using user-defined selection weights. The selected shape is
        resized to match the model run range, if necessary, and normalised
        so that its values sum to one.

        The normalised shape is scaled to the total heat demand for the run.
        This thermal energy demand is divided by the COP to obtain electrical
        energy demand and by the time-step duration in hours to obtain the
        average electrical power demand in kW for each time step.
        '''
        MINUTES_PER_HOUR: int = time_constants.MINUTES_PER_HOUR

        if time_ranges.frequency_type != 'm':
            raise ValueError('You need to use minutes for the frequency!')

        run_frequency_size: int = time_ranges.frequency_size
        run_time_resolution_hours: float = (
            run_frequency_size / MINUTES_PER_HOUR
        )

        # Draw the total household heat demand for the run.
        run_heat_demand_kWh: float = draw_beta_value(
            minimum=heat_pump_parameters.run_heat_pump_consumption_heat_kWh_min,  # noqa: E501
            typical=heat_pump_parameters.run_heat_pump_consumption_heat_kWh_typical,  # noqa: E501
            maximum=heat_pump_parameters.run_heat_pump_consumption_heat_kWh_max,  # noqa: E501
            random_generator=random_generator,
            shape=beta_shape,
        )

        # Draw the heat pump's coefficient of performance.
        COP: float = draw_beta_value(
            minimum=heat_pump_parameters.COP_min,
            typical=heat_pump_parameters.COP_typical,
            maximum=heat_pump_parameters.COP_max,
            random_generator=random_generator,
            shape=beta_shape,
        )

        # Select a heat-demand shape according to the user-defined
        # probabilities.
        profile_variants: list[str] = heat_pump_parameters.profile_variants
        profile_proportions: list[float] = (
            heat_pump_parameters.profile_proportions
        )
        chosen_variant: str = random_generator.choice(
            profile_variants,
            p=profile_proportions,
        )

        heat_demand_shape: pl.Series = demand_shapes_source_heat[
            chosen_variant
        ]
        run_stamps_amount: int = len(time_ranges.run_stamps)

        # Match the heat-demand shape to the model run range and normalise it.
        heat_demand_shape = reshape(
            source_shape=heat_demand_shape,
            run_stamps_amount=run_stamps_amount,
        )

        # Convert the thermal energy demand to electrical energy using the
        # COP, distribute it over time, and convert it to average power in kW.
        profile: pl.Series = (
            (run_heat_demand_kWh / COP)
            * heat_demand_shape
            / run_time_resolution_hours
        )

        return cls(
            run_heat_demand_kWh=run_heat_demand_kWh,
            heat_demand_shape=heat_demand_shape,
            COP=COP,
            profile=profile,
        )


@dataclass
class SolarPanels:
    run_production_kWh: float
    production_shape: pl.Series
    profile: pl.Series

    @classmethod
    def create(
        cls,
        *,
        solar_panels_parameters: Box,
        random_generator: np.random.Generator,
        time_ranges: TimeRange,
        time_constants: TimeConstants,
        household_run_demand_kWh: float,
        has_stationary_battery: bool,
        profiles_shapes_source_solar: pl.DataFrame,
    ) -> SolarPanels:
        '''
        Create the solar-production profile of a household.

        The total solar production for the run is determined as a proportion
        of the household electricity demand (including heat pumps, if present).
        A different proportion can
        be specified depending on whether the household has a home battery.

        A solar-production shape is randomly selected from the available
        variants using user-defined selection probabilities. The selected
        shape is resized to match the model run range, if necessary, and
        normalised so that its values sum to one.

        The normalised shape is scaled to the total solar production for the
        run. The resulting energy per time step in kWh is divided by the
        time-step duration in hours to obtain average power in kW. Solar
        production is represented as negative power because it supplies
        electricity rather than consuming it.
        '''
        if time_ranges.frequency_type != 'm':
            raise ValueError('You need to use minutes for the frequency!')

        run_time_resolution_hours: float = (
            time_ranges.frequency_size / time_constants.MINUTES_PER_HOUR
        )

        # Select the solar-production-to-demand ratio based on whether
        # the household also has a home battery.
        if has_stationary_battery:
            production_demand_ratio: float = (
                solar_panels_parameters.run_production_as_proportion_of_demand_if_battery  # noqa:E501
            )
        else:
            production_demand_ratio = (
                solar_panels_parameters.run_production_as_proportion_of_demand_if_no_battery  # noqa:E501
            )

        # Determine the total solar production for the run from the
        # household's basic electricity demand.
        run_production_kWh: float = (
            household_run_demand_kWh * production_demand_ratio
        )

        # Select a solar-production shape according to the user-defined
        # probabilities.
        profile_variants: list[str] = solar_panels_parameters.profile_variants
        profile_proportions: list[float] = (
            solar_panels_parameters.profile_proportions
        )
        chosen_variant: str = random_generator.choice(
            profile_variants, p=profile_proportions
        )

        production_shape: pl.Series = profiles_shapes_source_solar[
            chosen_variant
        ]
        run_stamps_amount: int = len(time_ranges.run_stamps)

        # Match the production shape to the model run range and normalise it.
        production_shape = reshape(
            source_shape=production_shape,
            run_stamps_amount=run_stamps_amount,
        )

        # Scale the shape to the total production for the run, convert
        # the energy per time step to kW, and represent production
        # as negative grid demand.
        profile: pl.Series = (
            -run_production_kWh * production_shape / run_time_resolution_hours
        )

        return cls(
            run_production_kWh=run_production_kWh,
            production_shape=production_shape,
            profile=profile,
        )


@dataclass
class StationaryBattery:
    capacity_kWh: float
    charge_power_kW: float
    discharge_power_kW: float
    charge_level_kWh: pl.Series
    profile: pl.Series

    def __add__(self, other):
        if not isinstance(other, StationaryBattery):
            return NotImplemented

        if len(self.profile) != len(other.profile):
            raise ValueError(
                'Stationary-battery profiles must have equal lengths: '
                f'{len(self.profile)=}, {len(other.profile)=}.'
            )

        if len(self.charge_level_kWh) != len(other.charge_level_kWh):
            raise ValueError(
                'Stationary-battery charge-level series must have '
                'equal lengths: '
                f'{len(self.charge_level_kWh)=}, '
                f'{len(other.charge_level_kWh)=}.'
            )

        return StationaryBattery(
            capacity_kWh=self.capacity_kWh + other.capacity_kWh,
            charge_power_kW=self.charge_power_kW + other.charge_power_kW,
            discharge_power_kW=(
                self.discharge_power_kW + other.discharge_power_kW
            ),
            charge_level_kWh=(self.charge_level_kWh + other.charge_level_kWh),
            profile=self.profile + other.profile,
        )

    @classmethod
    def for_EV_charger(
        cls,
        *,
        charger_charge_power_kW: float,
        charger_reverse_power_kW: float,
        reserve_hours: float,
        time_ranges: TimeRange,
    ) -> StationaryBattery:
        '''
        Creates a stationary battery for an EV charger.
        Essentially, this battry can replace the charger at full
        power for reserve_hours (or longr at lower power) if using its
        full capcity.
        '''

        charge_level_kWh: pl.Series = pl.Series(
            np.zeros(len(time_ranges.run_stamps))
        )
        profile: pl.Series = pl.Series(np.zeros(len(time_ranges.run_stamps)))

        return cls(
            capacity_kWh=charger_charge_power_kW * reserve_hours,
            charge_power_kW=charger_reverse_power_kW,
            # The stationary battery discharges through the charger at the
            # charger's maximum EV-charging power.
            discharge_power_kW=charger_charge_power_kW,
            charge_level_kWh=charge_level_kWh,
            profile=profile,
        )

    @classmethod
    def for_non_EV(
        cls,
        *,
        grid_parameters: Box,
        household: HouseholdBasicDemand,
        heat_pump: HeatPumpDemand,
        solar_panels: SolarPanels,
        time_ranges: TimeRange,
        time_constants: TimeConstants,
    ) -> StationaryBattery:
        '''
        Create a stationary battery for non-EV household demand.

        The battery profile cannot be determined during grid initialisation
        because battery charging and discharging depend on the complete
        power profile, including EV charging. This method therefore only
        determines the battery capacity and its charging and discharging
        power limits.

        The battery capacity is based on the average daily basic household
        demand, heat-pump electricity demand, and solar production during
        the model run.
        A separate reserve-days factor is applied to each component.
        The component capacities are then added to obtain the
        total battery capacity.
        '''
        HOURS_IN_A_DAY: int = time_constants.HOURS_IN_A_DAY

        run_duration_hours: float = (
            len(time_ranges.run_stamps)
            * time_ranges.frequency_size
            / time_constants.MINUTES_PER_HOUR
        )

        run_duration_days: float = run_duration_hours / HOURS_IN_A_DAY

        reserve_days_basic: float = (
            grid_parameters.home_batteries.reserve_days_basic
        )
        reserve_days_heat_pump: float = (
            grid_parameters.home_batteries.reserve_days_heat_pump
        )
        reserve_days_solar_panels: float = (
            grid_parameters.home_batteries.reserve_days_solar_panels
        )

        capacity_for_basic_kWh: float = (
            household.non_BEV_HP_run_demand_kWh / run_duration_days
        ) * reserve_days_basic

        capacity_for_heat_pump_kWh: float = (
            heat_pump.run_heat_demand_kWh / heat_pump.COP / run_duration_days
        ) * reserve_days_heat_pump

        capacity_for_solar_panels_kWh: float = (
            solar_panels.run_production_kWh / run_duration_days
        ) * reserve_days_solar_panels

        capacity_kWh: float = (
            capacity_for_basic_kWh
            + capacity_for_heat_pump_kWh
            + capacity_for_solar_panels_kWh
        )
        charge_power_kW: float = (
            grid_parameters.home_batteries.charging_power_kW
        )
        discharge_power_kW: float = (
            grid_parameters.home_batteries.discharging_power_kW
        )
        charge_level_kWh: pl.Series = pl.Series(
            np.zeros(len(time_ranges.run_stamps))
        )
        profile: pl.Series = pl.Series(np.zeros(len(time_ranges.run_stamps)))

        return cls(
            capacity_kWh=capacity_kWh,
            charge_power_kW=charge_power_kW,
            discharge_power_kW=discharge_power_kW,
            charge_level_kWh=charge_level_kWh,
            profile=profile,
        )


@dataclass
class Node:
    household: HouseholdBasicDemand
    heat_pump: HeatPumpDemand
    solar_panels: SolarPanels
    stationary_battery: StationaryBattery

    def get_net_non_EV_profile(self) -> pl.Series:
        '''
        Return the net non-EV power profile of the household node.

        Positive values represent net electricity demand, while negative
        values represent net electricity supply to the grid.
        '''
        return (
            self.household.profile
            + self.heat_pump.profile
            + self.solar_panels.profile
        )

    @classmethod
    def create(
        cls,
        *,
        grid_parameters: Box,
        random_generator: np.random.Generator,
        beta_shape: float,
        time_ranges: TimeRange,
        time_constants: TimeConstants,
        profiles_shapes_source_households: pl.DataFrame,
        profiles_shapes_source_solar: pl.DataFrame,
        demand_shapes_source_heat: pl.DataFrame,
    ) -> Node:
        '''
        Create a household node and its non-EV demand components.
        '''

        household: HouseholdBasicDemand = HouseholdBasicDemand.create(
            household_parameters=grid_parameters.households,
            random_generator=random_generator,
            beta_shape=beta_shape,
            time_ranges=time_ranges,
            time_constants=time_constants,
            profiles_shapes_source_households=(
                profiles_shapes_source_households
            ),
        )
        zero_shape: pl.Series = pl.Series(
            np.zeros(len(time_ranges.run_stamps))
        )
        has_solar_panels: bool = (
            random_generator.random()
            < grid_parameters.solar_panels.adoption_rate_solar_panels
        )
        if has_solar_panels:
            has_stationary_battery: bool = (
                random_generator.random()
                < grid_parameters.home_batteries.adoption_rate_home_batteries_if_solar_panels  # noqa:E501
            )
        else:
            has_stationary_battery = (
                random_generator.random()
                < grid_parameters.home_batteries.adoption_rate_home_batteries_if_not_solar_panels  # noqa:E501
            )

        has_heat_pump: bool = (
            random_generator.random()
            < grid_parameters.heat_pumps.adoption_rate_heat_pumps
        )

        if has_heat_pump:
            heat_pump: HeatPumpDemand = HeatPumpDemand.create(
                heat_pump_parameters=grid_parameters.heat_pumps,
                random_generator=random_generator,
                beta_shape=beta_shape,
                time_ranges=time_ranges,
                time_constants=time_constants,
                demand_shapes_source_heat=demand_shapes_source_heat,
            )
        else:
            heat_pump = HeatPumpDemand(
                run_heat_demand_kWh=0.0,
                heat_demand_shape=zero_shape,
                COP=1.0,
                profile=zero_shape,
            )

        if has_solar_panels:
            run_demand_for_solar_panels_scale_kWh: float = (
                household.non_BEV_HP_run_demand_kWh
                + heat_pump.run_heat_demand_kWh / heat_pump.COP
            )
            solar_panels: SolarPanels = SolarPanels.create(
                solar_panels_parameters=grid_parameters.solar_panels,
                random_generator=random_generator,
                time_ranges=time_ranges,
                time_constants=time_constants,
                household_run_demand_kWh=run_demand_for_solar_panels_scale_kWh,
                has_stationary_battery=has_stationary_battery,
                profiles_shapes_source_solar=profiles_shapes_source_solar,
            )
        else:
            solar_panels = SolarPanels(
                run_production_kWh=0.0,
                production_shape=zero_shape,
                profile=zero_shape,
            )

        if has_stationary_battery:
            stationary_battery: StationaryBattery = (
                StationaryBattery.for_non_EV(
                    grid_parameters=grid_parameters,
                    household=household,
                    heat_pump=heat_pump,
                    solar_panels=solar_panels,
                    time_ranges=time_ranges,
                    time_constants=time_constants,
                )
            )
        else:
            stationary_battery = StationaryBattery(
                capacity_kWh=0.0,
                charge_power_kW=0.0,
                discharge_power_kW=0.0,
                charge_level_kWh=zero_shape,
                profile=zero_shape,
            )

        return cls(
            household=household,
            heat_pump=heat_pump,
            solar_panels=solar_panels,
            stationary_battery=stationary_battery,
        )


@dataclass
class Charger:
    ID: uuid.UUID
    type: str
    power_kW: float
    discharge_power_kW: float
    IDs_of_users: list[uuid.UUID]


@dataclass
class PowerLine:
    index: int
    capacity_kW: float
    non_EV_demand_profile: pl.Series
    EV_users: list[
        uuid.UUID
    ]  # Will give us charging demand profiles in the line
    stationary_battery_for_line: StationaryBattery
    # Can be made of seceral physically separated batetries, but they count
    # as one for the line
    EV_demand_matching: pl.DataFrame

    @staticmethod
    def create_EV_demand_matching_DF(
        non_EV_net_profile: pl.Series,
        run_range: pl.Series,
        matching_DF_settings: Box,
    ) -> pl.DataFrame:

        EV_demand_matching: pl.DataFrame = pl.DataFrame(
            {
                matching_DF_settings.time_header: run_range.cast(pl.Datetime),
                matching_DF_settings.non_EV_demand_header: (
                    non_EV_net_profile.cast(pl.Float64)
                ),
            }
        ).with_columns(
            pl.lit(None, dtype=pl.Float64).alias(
                matching_DF_settings.EV_demand_header
            ),
            pl.lit(None, dtype=pl.Boolean).alias(
                matching_DF_settings.capacity_exceeded_header
            ),
            pl.lit(None, dtype=pl.Float64).alias(
                matching_DF_settings.extra_capacity_needed_header
            ),
        )

        return EV_demand_matching


@dataclass
class LocalGrid:
    transformer_capacity_kW: float
    power_lines: list[PowerLine]

    # @staticmethod
    # def create_nodes() -> list[Node]:
    #     nodes: list[Node] = [Node.draw() for _ in nodes_amount]
    #     return []

    @staticmethod
    def create_chargers(
        users_pool: list[User],
        grid_parameters: Box,
        scenario: Box,
        random_generator: np.random.Generator,
    ) -> list[Charger]:
        '''
        Creates the home chargers in the local grid.

        Each own-driveway user receives an individual charger. Street-parking
        users share chargers and are distributed as evenly as possible across
        them. The home connectivity of each user is updated to the reciprocal
        of the number of users assigned to the same charger.
        '''
        chargers: list[Charger] = []
        charger_ID_user_IDs: dict[uuid.UUID, list[uuid.UUID]] = {}
        user_ID_charger_IDs: dict[uuid.UUID, uuid.UUID] = {}
        home_location_name: str = grid_parameters.home_location_name
        own_driveway_name: str = grid_parameters.own_driveway_name
        street_parking_name: str = grid_parameters.street_parking_name

        # Some checks to verify that names are consistent.
        supported_home_variants: set[str] = {
            own_driveway_name,
            street_parking_name,
        }

        unsupported_users: list[User] = [
            user
            for user in users_pool
            if user.locations[home_location_name].variant_name
            not in supported_home_variants
        ]

        if unsupported_users:
            unsupported_variants: set[str] = {
                user.locations[home_location_name].variant_name
                for user in unsupported_users
            }
            raise ValueError(
                'All users must have a supported home-parking variant. '
                f'{unsupported_variants=}'
            )

        # We divide users between own driveway users and
        # street parking users (who share chargers)
        own_driveway_users: list[User] = [
            user
            for user in users_pool
            if user.locations[home_location_name].variant_name
            == own_driveway_name
        ]

        street_parking_users: list[User] = [
            user
            for user in users_pool
            if user.locations[home_location_name].variant_name
            == street_parking_name
        ]

        # The case for own driveway chargers is straightforward:
        # There is one charger per user
        for own_driveway_user in own_driveway_users:
            # In that case, we have one charger per user.
            driveway_charger: Charger = Charger(
                ID=uuid.uuid4(),
                type=own_driveway_name,
                power_kW=own_driveway_user.locations[
                    home_location_name
                ].charging_power_kW,
                discharge_power_kW=own_driveway_user.locations[
                    home_location_name
                ].discharge_power_kW,
                IDs_of_users=[own_driveway_user.ID],
            )
            chargers.append(driveway_charger)
            charger_ID_user_IDs[driveway_charger.ID] = [own_driveway_user.ID]
            user_ID_charger_IDs[own_driveway_user.ID] = driveway_charger.ID

        # For street parking, it is more complex
        # We first need to figure out how many chargers there are.
        # This is given by the amount of users
        # times the connectivity, which we need to round
        # Note that we round this amount, which
        # will mean that we will need to update the connectivity
        # of some users. Either some will have less connectivity
        # (if the rounding goes down), corresponding the situation where
        # another users appears but not new charger is added), or they
        # will have more connectivity (if a charger is added in anticipation
        # of more users). By rounding, we have one of these two situations,
        # roughly reflecting a flow where the chanve of adding a charger
        # is higher the more chargers are occupied above the average
        # connectivity.
        street_parking_connectivity: float = scenario.locations[
            home_location_name
        ][street_parking_name].connectivity

        # Street parking connectivity is a probability
        if not 0.0 <= street_parking_connectivity <= 1.0:
            raise ValueError(
                f'{street_parking_connectivity=} must be between 0 and 1.'
            )
        if street_parking_connectivity == 0.0 and street_parking_users:
            raise ValueError(
                'You have street parking users but no street parking '
                'connectivity/no chargers for these users.'
            )

        street_charger_power_kW: float = scenario.locations[
            home_location_name
        ][street_parking_name].charging_power_kW

        street_charger__discharge_power_kW: float = scenario.locations[
            home_location_name
        ][street_parking_name].discharge_power_kW

        # We want 0.5 to round up instead of Python's banker's rounding
        expected_street_chargers: float = (
            len(street_parking_users) * street_parking_connectivity
        )

        amount_of_street_chargers: int = (
            # We ensure that there is at least one charger
            # if there is at least one street parking user.
            max(1, int(np.floor(expected_street_chargers + 0.5)))
            if street_parking_users
            else 0
        )

        # We now create the chargers. We put them in the main list, but also
        # in a separate list that will allow us to attribute user to them
        street_chargers: list[Charger] = []
        for _ in range(amount_of_street_chargers):
            street_charger: Charger = Charger(
                ID=uuid.uuid4(),
                type=street_parking_name,
                power_kW=street_charger_power_kW,
                discharge_power_kW=street_charger__discharge_power_kW,
                IDs_of_users=[],
            )
            chargers.append(street_charger)
            street_chargers.append(street_charger)
            # We initialise the list of users for that charger
            charger_ID_user_IDs[street_charger.ID] = []

        # We arrange the indices of the users randomly
        shuffled_indices: np.ndarray = random_generator.permutation(
            len(street_parking_users)
        )

        for position, user_index in enumerate(shuffled_indices):
            # Assign the randomly ordered users to the chargers in round-robin
            # order. This ensures that the numbers of users assigned to any two
            # chargers differ by at most one.
            street_charger: Charger = street_chargers[
                position % len(street_chargers)
            ]
            street_parking_user: User = street_parking_users[int(user_index)]
            # And add the user to its users
            charger_ID_user_IDs[street_charger.ID].append(
                street_parking_user.ID
            )
            street_charger.IDs_of_users.append(street_parking_user.ID)
            # And set the charger of that user
            user_ID_charger_IDs[street_parking_user.ID] = street_charger.ID

        # We now can update the home connectivities.
        for user in users_pool:
            ID_of_charger_used_by_user: uuid.UUID = user_ID_charger_IDs[
                user.ID
            ]
            users_on_that_charger: list[uuid.UUID] = charger_ID_user_IDs[
                ID_of_charger_used_by_user
            ]
            amount_of_users_for_that_charger: int = len(users_on_that_charger)
            updated_connectivity: float = 1 / amount_of_users_for_that_charger
            user.locations[home_location_name].connectivity = (
                updated_connectivity
            )

        return chargers

    @staticmethod
    def get_line_powers(
        grid_parameters: Box,
        random_generator: np.random.Generator,
        beta_shape: float,
    ) -> list[float]:
        '''
        Distribute the transformer capacity among its power lines.

        A capacity weight is drawn for each power line from a bounded beta
        distribution. These weights determine the relative capacities assigned
        to the individual power lines.

        The drawn weights are normalised so that the resulting line capacities
        sum to the transformer capacity.

        '''

        transformer_capacity_kW: float = (
            grid_parameters.transformer_capacity_kW
        )
        amount_of_lines: int = grid_parameters.amount_of_power_lines
        line_capacity_weight_min: float = (
            grid_parameters.line_capacity_weight_min
        )
        line_capacity_weight_typical: float = (
            grid_parameters.line_capacity_weight_typical
        )
        line_capacity_weight_max: float = (
            grid_parameters.line_capacity_weight_max
        )

        line_capacity_weights: list[float] = [
            draw_beta_value(
                minimum=line_capacity_weight_min,
                typical=line_capacity_weight_typical,
                maximum=line_capacity_weight_max,
                random_generator=random_generator,
                shape=beta_shape,
            )
            for _ in range(amount_of_lines)
        ]

        # Normalise the weights so that all line capacities together equal
        # the transformer capacity.
        total_capacity_weight: float = sum(line_capacity_weights)

        line_capacity_ratios: list[float] = [
            capacity_weight / total_capacity_weight
            for capacity_weight in line_capacity_weights
        ]

        line_powers_kW: list[float] = [
            capacity_ratio * transformer_capacity_kW
            for capacity_ratio in line_capacity_ratios
        ]

        return line_powers_kW

    @staticmethod
    def assign_chargers_to_lines(
        chargers: list[Charger],
        line_powers_kW: list[float],
        random_generator: np.random.Generator,
    ) -> list[int]:
        '''
        Assign chargers to power lines subject to their capacity limits.

        Chargers are processed from highest to lowest power. For each charger,
        the eligible power lines are those whose remaining capacity is at least
        equal to the charger power. One of these lines is selected randomly,
        weighted by its remaining capacity.

        This causes lines with more remaining capacity to be more likely to
        receive a charger, while ensuring that the total rated charger power
        assigned to a line does not exceed that line's capacity.

        Parameters
        ----------
        chargers
            EV chargers to assign to the power lines.
        line_powers_kW
            Capacities of the power lines.
        random_generator
            Random-number generator used for the weighted selection.

        Returns
        -------
        list[int]
            Power-line index assigned to each charger. The returned
            list follows
            the original order of ``chargers``.

        Raises
        ------
        ValueError
            If the charger powers or line capacities are invalid, or if
            a charger
            cannot be assigned without exceeding a line's capacity.
        '''
        charger_powers_kW: list[float] = [
            charger.power_kW for charger in chargers
        ]

        if not line_powers_kW and chargers:
            raise ValueError(
                'Chargers cannot be assigned because no power lines '
                'are available.'
            )

        if any(
            charger_power_kW <= 0 for charger_power_kW in charger_powers_kW
        ):
            raise ValueError('All charger powers must be greater than zero.')

        if any(line_power_kW <= 0 for line_power_kW in line_powers_kW):
            raise ValueError('All line capacities must be greater than zero.')

        remaining_line_powers_kW: np.ndarray = np.asarray(
            line_powers_kW,
            dtype=float,
        )

        # Initialise all indices as unassigned. Each value is replaced when
        # the corresponding charger is assigned to a power line.
        charger_line_indices: list[int] = [-1] * len(chargers)

        # Assign larger chargers first to reduce the risk of leaving fragmented
        # capacity that cannot accommodate them.
        charger_indices_by_descending_power: list[int] = sorted(
            range(len(chargers)),
            key=charger_powers_kW.__getitem__,
            reverse=True,
        )

        for charger_index in charger_indices_by_descending_power:
            charger_power_kW: float = charger_powers_kW[charger_index]

            eligible_line_indices: np.ndarray = np.flatnonzero(
                remaining_line_powers_kW >= charger_power_kW
            )

            if eligible_line_indices.size == 0:
                largest_remaining_capacity_kW: float = float(
                    remaining_line_powers_kW.max()
                )

                raise ValueError(
                    f'Charger {charger_index} with a power of '
                    f'{charger_power_kW:.2f} kW cannot be assigned to a power '
                    f'line. The largest remaining line capacity is '
                    f'{largest_remaining_capacity_kW:.2f} kW.'
                    f'Increasing the trnsformer capacity, reducing the '
                    f'amount of power lines or increasing '
                    f'line_capacity_weight_min might help'
                )

            eligible_remaining_powers_kW: np.ndarray = (
                remaining_line_powers_kW[eligible_line_indices]
            )

            # Select an eligible line randomly. Lines with more remaining
            # capacity have a proportionally higher selection probability.
            selection_probabilities: np.ndarray = (
                eligible_remaining_powers_kW
                / eligible_remaining_powers_kW.sum()
            )

            selected_line_index: int = int(
                random_generator.choice(
                    eligible_line_indices,
                    p=selection_probabilities,
                )
            )

            charger_line_indices[charger_index] = selected_line_index
            remaining_line_powers_kW[selected_line_index] -= charger_power_kW

        return charger_line_indices

    @staticmethod
    def get_nodes_per_line(
        line_powers_kW: list[float],
        amount_of_households: int,
    ) -> list[int]:
        '''
        Distribute household nodes over the power lines proportionally to
        their capacities.

        The ideal number of nodes per line is calculated from each line's
        share of the total line capacity. These values are rounded down first.
        Any remaining nodes are subsequently assigned to the lines with the
        largest fractional remainders.

        This ensures that the total number of assigned nodes equals the total
        number of households while keeping the distribution as close as
        possible to proportional to the line capacities.
        '''
        line_powers: np.ndarray = np.asarray(line_powers_kW, dtype=float)

        ideal_nodes_per_line: np.ndarray = (
            amount_of_households * line_powers / line_powers.sum()
        )

        nodes_per_line: np.ndarray = np.floor(ideal_nodes_per_line).astype(int)

        amount_of_remaining_nodes: int = (
            amount_of_households - nodes_per_line.sum()
        )

        remainders: np.ndarray = ideal_nodes_per_line - nodes_per_line

        lines_by_descending_remainder: np.ndarray = np.argsort(-remainders)

        nodes_per_line[
            lines_by_descending_remainder[:amount_of_remaining_nodes]
        ] += 1

        return nodes_per_line.tolist()

    @staticmethod
    def assign_non_EV_demand_to_lines(
        *,
        node_non_EV_profiles: list[pl.Series],
        line_powers_kW: list[float],
        grid_parameters: Box,
        time_ranges: TimeRange,
        lines_stationary_batteries: list[StationaryBattery],
        nodes_stationary_batteries: list[StationaryBattery],
    ) -> tuple[list[pl.Series], list[StationaryBattery]]:
        '''
        Assign the non-EV demand of household nodes to the power lines.

        The number of household nodes assigned to each line is proportional
        to its capacity. The corresponding non-EV demand profiles are then
        summed to obtain the total non-EV demand profile for each line.

        No additional randomisation is required because the household demand
        profiles were already created using random draws.
        We also add the node stationary batteries to their corresponding lines.
        '''
        amount_of_households: int = grid_parameters.amount_of_households

        if len(node_non_EV_profiles) != amount_of_households:
            raise ValueError(
                f'The number of non-EV profiles ({len(node_non_EV_profiles)}) '
                f'does not equal the number of households '
                f'({amount_of_households}).'
            )

        amounts_of_nodes_per_line: list[int] = LocalGrid.get_nodes_per_line(
            line_powers_kW=line_powers_kW,
            amount_of_households=amount_of_households,
        )

        zero_non_EV_demand: pl.Series = pl.Series(
            grid_parameters.non_EV_demand_header,
            np.zeros(len(time_ranges.run_stamps)),
        )

        lines_non_EV_net_profiles: list[pl.Series] = [
            zero_non_EV_demand.clone() for _ in line_powers_kW
        ]

        node_list_index: int = 0

        for line_index, nodes_for_this_line in enumerate(
            amounts_of_nodes_per_line
        ):
            for _ in range(nodes_for_this_line):
                lines_non_EV_net_profiles[line_index] += node_non_EV_profiles[
                    node_list_index
                ]
                lines_stationary_batteries[
                    line_index
                ] += nodes_stationary_batteries[node_list_index]
                node_list_index += 1

        return lines_non_EV_net_profiles, lines_stationary_batteries

    @staticmethod
    def get_line_stationary_batteries_for_EV_chargers(
        *,
        chargers: list[Charger],
        charger_line_indices: list[int],
        line_stationary_batteries: list[StationaryBattery],
        grid_parameters: Box,
        random_generator: np.random.Generator,
        time_ranges: TimeRange,
    ) -> list[StationaryBattery]:

        for charger, charger_line_index in zip(
            chargers, charger_line_indices, strict=True
        ):
            if (
                random_generator.random()
                < grid_parameters.home_batteries.adoption_rate_for_EV_chargers
            ):
                charger_battery: StationaryBattery = (
                    StationaryBattery.for_EV_charger(
                        charger_charge_power_kW=charger.power_kW,
                        charger_reverse_power_kW=charger.discharge_power_kW,
                        reserve_hours=(
                            grid_parameters.home_batteries.EV_reserve_hours
                        ),
                        time_ranges=time_ranges,
                    )
                )
                line_stationary_batteries[
                    charger_line_index
                ] += charger_battery

        return line_stationary_batteries

    @classmethod
    def initialise(
        cls,
        *,
        users_pool: list[User],
        grid_parameters: Box,
        scenario: Box,
        time_ranges: TimeRange,
        time_constants: TimeConstants,
        random_generator: np.random.Generator,
    ) -> LocalGrid:

        transformer_capacity_kW: float = (
            grid_parameters.transformer_capacity_kW
        )
        beta_shape: float = scenario.monte_carlo.beta_shape

        # We set the home chargers (own driveway and street parking).
        chargers: list[Charger] = LocalGrid.create_chargers(
            users_pool=users_pool,
            grid_parameters=grid_parameters,
            scenario=scenario,
            random_generator=random_generator,
        )

        total_charging_power_kW: float = sum(
            charger.power_kW for charger in chargers
        )

        if total_charging_power_kW > transformer_capacity_kW:
            raise ValueError(
                f'The total charger power ({total_charging_power_kW:.2f} kW) '
                f'is larger than the transformer capacity '
                f'({transformer_capacity_kW:.2f} kW). '
                'Either increase the transformer capacity or reduce the total '
                'charger power. The latter can be done by reducing the '
                'nominal charger powers, increasing the proportion of street '
                'chargers (as these are shared), and/or decreasing the street '
                'charger connectivity.'
            )

        # We create the power lines.
        # First, we distribute the transformer capacity among the lines.
        # The resulting line capacities are subsequently used to distribute
        # chargers and household nodes among the lines.

        line_powers_kW: list[float] = LocalGrid.get_line_powers(
            grid_parameters=grid_parameters,
            random_generator=random_generator,
            beta_shape=beta_shape,
        )

        # Assign the chargers to the power lines.
        charger_line_indices: list[int] = LocalGrid.assign_chargers_to_lines(
            chargers=chargers,
            line_powers_kW=line_powers_kW,
            random_generator=random_generator,
        )

        empty_lines_stationary_batteries: list[StationaryBattery] = [
            StationaryBattery(
                capacity_kWh=0.0,
                charge_power_kW=0.0,
                discharge_power_kW=0.0,
                charge_level_kWh=pl.Series(
                    np.zeros(len(time_ranges.run_stamps))
                ),
                profile=pl.Series(np.zeros(len(time_ranges.run_stamps))),
            )
            for _ in line_powers_kW
        ]

        lines_stationary_batteries: list[StationaryBattery] = (
            LocalGrid.get_line_stationary_batteries_for_EV_chargers(
                chargers=chargers,
                charger_line_indices=charger_line_indices,
                line_stationary_batteries=empty_lines_stationary_batteries,
                grid_parameters=grid_parameters,
                random_generator=random_generator,
                time_ranges=time_ranges,
            )
        )

        # Assign the users connected to each charger to the same power line.
        line_EV_user_IDs: list[list[uuid.UUID]] = [[] for _ in line_powers_kW]

        for charger_line_index, charger in zip(
            charger_line_indices,
            chargers,
            strict=True,
        ):

            line_EV_user_IDs[charger_line_index].extend(charger.IDs_of_users)

        # We create the household nodes
        # We read the shape file to avoid doing it for each node:
        profiles_shapes_source_households: pl.DataFrame = pl.read_csv(
            Path(grid_parameters.households.profiles_shapes_source)
        )
        profiles_shapes_source_solar: pl.DataFrame = pl.read_csv(
            Path(grid_parameters.solar_panels.profile_shapes_source)
        )
        demand_shapes_source_heat: pl.DataFrame = pl.read_csv(
            Path(grid_parameters.heat_pumps.profiles_shape_source)
        )
        household_nodes: list[Node] = [
            Node.create(
                grid_parameters=grid_parameters,
                random_generator=random_generator,
                beta_shape=beta_shape,
                time_ranges=time_ranges,
                time_constants=time_constants,
                profiles_shapes_source_households=(
                    profiles_shapes_source_households
                ),
                profiles_shapes_source_solar=profiles_shapes_source_solar,
                demand_shapes_source_heat=demand_shapes_source_heat,
            )
            for _ in range(grid_parameters.amount_of_households)
        ]

        # We get the (net) non-EV demand profile per node
        node_non_EV_profiles: list[pl.Series] = [
            household_node.get_net_non_EV_profile()
            for household_node in household_nodes
        ]
        nodes_stationary_batteries: list[StationaryBattery] = [
            household_node.stationary_battery
            for household_node in household_nodes
        ]

        lines_non_EV_net_profiles, lines_stationary_batteries = (
            LocalGrid.assign_non_EV_demand_to_lines(
                node_non_EV_profiles=node_non_EV_profiles,
                line_powers_kW=line_powers_kW,
                grid_parameters=grid_parameters,
                time_ranges=time_ranges,
                lines_stationary_batteries=lines_stationary_batteries,
                nodes_stationary_batteries=nodes_stationary_batteries,
            )
        )
        lines_EV_matching_DFs: list[pl.DataFrame] = [
            PowerLine.create_EV_demand_matching_DF(
                non_EV_net_profile=non_EV_net_profile,
                run_range=time_ranges.run_stamps,
                matching_DF_settings=grid_parameters.EV_demand_matching_DF,
            )
            for non_EV_net_profile in lines_non_EV_net_profiles
        ]

        power_lines: list[PowerLine] = [
            PowerLine(
                index=line_index,
                capacity_kW=line_capacity_kW,
                non_EV_demand_profile=line_non_EV_net_profile,
                EV_users=line_EV_users,
                stationary_battery_for_line=line_stationary_battery,
                EV_demand_matching=line_EV_demand_matching_DF,
            )
            for line_index, (
                line_capacity_kW,
                line_non_EV_net_profile,
                line_EV_users,
                line_stationary_battery,
                line_EV_demand_matching_DF,
            ) in enumerate(
                zip(
                    line_powers_kW,
                    lines_non_EV_net_profiles,
                    line_EV_user_IDs,
                    lines_stationary_batteries,
                    lines_EV_matching_DFs,
                    strict=True,
                )
            )
        ]

        return cls(
            transformer_capacity_kW=transformer_capacity_kW,
            power_lines=power_lines,
        )


def compute_EV_matching(
    local_grid: LocalGrid,
    users_by_ID: dict[uuid.UUID, User],
    time_ranges: TimeRange,
    scenario: Box,
    grid_parameters: Box,
) -> None:
    '''
    Match residential EV charging demand to power lines.

    For each power line, aggregate the power drawn from the grid by EVs
    charging at home. Add this EV demand to the line's EV-demand-matching
    DataFrame and combine it with non-EV demand to determine whether
    the line capacity is exceeded at each timestep.

    For overloaded timesteps, also calculate the additional capacity required
    to accommodate the total demand. The results are stored in each power
    line's EV-demand-matching DataFrame.
    '''

    for power_line in local_grid.power_lines:
        line_EV_demand_from_grid: pl.Series = pl.Series(
            np.zeros(len(time_ranges.run_stamps))
        )
        for user_ID in power_line.EV_users:

            home_power: pl.Series = (
                users_by_ID[user_ID]
                .charge.with_columns(
                    pl.when(
                        pl.col(scenario.charging_dataframe.location_header)
                        == grid_parameters.home_location_name
                    )
                    .then(
                        pl.col(
                            scenario.charging_dataframe.power_from_grid_header  # noqa:E501
                        )
                    )
                    .otherwise(0.0)
                    .alias('home_power')
                )
                .get_column('home_power')
            )

            line_EV_demand_from_grid += home_power
        non_EV_header: str = (
            grid_parameters.EV_demand_matching_DF.non_EV_demand_header
        )
        EV_header: str = grid_parameters.EV_demand_matching_DF.EV_demand_header
        capacity_exceeded_header: str = (
            grid_parameters.EV_demand_matching_DF.capacity_exceeded_header
        )
        extra_capacity_needed_header: str = (
            grid_parameters.EV_demand_matching_DF.extra_capacity_needed_header  # noqa:E501
        )

        # First add the EV demand because subsequent
        # alculations depend on it.
        power_line.EV_demand_matching = (
            power_line.EV_demand_matching.with_columns(
                line_EV_demand_from_grid.alias(EV_header),
            )
        )

        # Determine whether total demand exceeds the line capacity.
        power_line.EV_demand_matching = (
            power_line.EV_demand_matching.with_columns(
                (
                    pl.col(non_EV_header) + pl.col(EV_header)
                    > power_line.capacity_kW
                ).alias(capacity_exceeded_header),
                pl.when(
                    pl.col(non_EV_header) + pl.col(EV_header)
                    > power_line.capacity_kW
                )
                .then(
                    pl.col(non_EV_header)
                    + pl.col(EV_header)
                    - power_line.capacity_kW
                )
                .otherwise(0.0)
                .alias(extra_capacity_needed_header),
            )
        )
