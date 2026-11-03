import pickle
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import numpy as np
import polars as pl
from box import Box

from ChaProEV.stochastic_new.activities import Activities
from ChaProEV.stochastic_new.monte_carlo import draw_beta_value
from ChaProEV.stochastic_new.time import TimeConstants, TimeRange


@dataclass
class Vehicle:
    name: str
    consumption_kWh_km: float
    battery_size_kWh: float
    has_one_trip_per_day_type: bool
    bases: list[str]
    driving_location_name: str

    @staticmethod
    def draw(
        *,
        vehicle_settings: Box,
        random_generator: np.random.Generator,
        beta_shape: float,
    ) -> Vehicle:
        name: str = vehicle_settings.name
        has_one_trip_per_day_type: bool = (
            vehicle_settings.has_one_trip_per_day_type
        )
        driving_location_name: str = vehicle_settings.driving_location_name
        bases: list[str] = vehicle_settings.bases

        consumption_kWh_km_min: float = vehicle_settings.consumption_kWh_km_min
        consumption_kWh_km_typical: float = (
            vehicle_settings.consumption_kWh_km_typical
        )
        consumption_kWh_km_max: float = vehicle_settings.consumption_kWh_km_max
        if consumption_kWh_km_min <= 0:
            raise ValueError(
                f'{consumption_kWh_km_min=} must be larger than zero. '
            )
        consumption_kWh_km: float = draw_beta_value(
            minimum=consumption_kWh_km_min,
            typical=consumption_kWh_km_typical,
            maximum=consumption_kWh_km_max,
            random_generator=random_generator,
            shape=beta_shape,
        )

        battery_size_kWh_min: float = vehicle_settings.battery_size_kWh_min
        battery_size_kWh_typical: float = (
            vehicle_settings.battery_size_kWh_typical
        )
        battery_size_kWh_max: float = vehicle_settings.battery_size_kWh_max

        if battery_size_kWh_min <= 0:
            raise ValueError(
                f'{battery_size_kWh_min=} must be larger than zero.'
            )
        battery_size_kWh: float = draw_beta_value(
            minimum=battery_size_kWh_min,
            typical=battery_size_kWh_typical,
            maximum=battery_size_kWh_max,
            random_generator=random_generator,
            shape=beta_shape,
        )

        return Vehicle(
            name=name,
            consumption_kWh_km=consumption_kWh_km,
            battery_size_kWh=battery_size_kWh,
            has_one_trip_per_day_type=has_one_trip_per_day_type,
            bases=bases,
            driving_location_name=driving_location_name,
        )


@dataclass
class Location:
    '''
    This class defines the locations where the vehicles are
    and their properties,  from a scenario
    file that contains a list of instances and their properties.
    '''

    base: bool
    connectivity: float
    charging_power_kW: float
    charger_efficiency: float
    discharge_power_kW: float
    proportion_of_discharge_to_network: float
    time_modulation_factors: list[float]
    latitude: float
    longitude: float
    charging_price_eur_kWh: float
    charging_desirability: float

    @staticmethod
    def draw(
        *, location_parameters: Box, random_generator: np.random.Generator
    ) -> Location:
        base: bool = location_parameters.base
        latitude: float = location_parameters.latitude
        longitude: float = location_parameters.longitude

        has_variants: bool = location_parameters.has_variants

        if has_variants:

            variants: list[str] = location_parameters.variants
            variant_weights: list[float] = location_parameters.variant_weights
            if len(variants) != len(variant_weights):
                raise ValueError(
                    f'{variants=} and {variant_weights=} '
                    f'must have the same number of elements.'
                )
            if any(weight < 0 for weight in variant_weights):
                raise ValueError(f'Some {variant_weights=} are negative')
            if not np.isclose(sum(variant_weights), 1.0):
                raise ValueError(f'{variant_weights=} must add up to 1.0')
            chosen_variant: str = str(
                random_generator.choice(variants, p=variant_weights)
            )
            if chosen_variant not in location_parameters:
                raise KeyError(
                    f'{chosen_variant=} is not defined. '
                    f'Check that you have parameters for this variant.'
                )

            location_values: Box = location_parameters[chosen_variant]
        else:
            location_values = location_parameters

        connectivity: float = location_values.connectivity
        charging_power_kW: float = location_values.charging_power_kW
        charger_efficiency: float = location_values.charger_efficiency
        discharge_power_kW: float = location_values.discharge_power_kW
        proportion_of_discharge_to_network: float = (
            location_values.proportion_of_discharge_to_network
        )
        time_modulation_factors: list[float] = (
            location_values.time_modulation_factors
        )

        charging_price_eur_kWh: float = location_values.charging_price_eur_kWh
        charging_desirability: float = location_values.charging_desirability
        return Location(
            base=base,
            connectivity=connectivity,
            charging_power_kW=charging_power_kW,
            charger_efficiency=charger_efficiency,
            discharge_power_kW=discharge_power_kW,
            proportion_of_discharge_to_network=(
                proportion_of_discharge_to_network
            ),
            time_modulation_factors=time_modulation_factors,
            latitude=latitude,
            longitude=longitude,
            charging_price_eur_kWh=charging_price_eur_kWh,
            charging_desirability=charging_desirability,
        )


def draw_legs_references(
    *,
    legs_references: Box,
    random_generator: np.random.Generator,
    beta_shape: float,
) -> Box:
    '''
    Draws leg distances and speeds and calculates durations.
    We assume that legs outward and back have the same distance and duration.
    '''
    drawn_legs_references: Box = Box()
    for reference_name, reference in legs_references.items():
        drawn_legs_references[reference_name] = Box()

        distance_km_min: float = reference.distance_km_min
        distance_km_typical: float = reference.distance_km_typical
        distance_km_max: float = reference.distance_km_max
        if distance_km_min <= 0:
            raise ValueError(
                f'{distance_km_min=} for {reference_name=} '
                'is negative or zero. '
            )
        distance_km: float = draw_beta_value(
            minimum=distance_km_min,
            typical=distance_km_typical,
            maximum=distance_km_max,
            random_generator=random_generator,
            shape=beta_shape,
        )

        speed_kph_min: float = reference.speed_kph_min
        speed_kph_typical: float = reference.speed_kph_typical
        speed_kph_max: float = reference.speed_kph_max
        if speed_kph_min <= 0:
            raise ValueError(
                f'{speed_kph_min=} for {reference_name=} '
                'is negative or zero. '
            )
        speed_kph: float = draw_beta_value(
            minimum=speed_kph_min,
            typical=speed_kph_typical,
            maximum=speed_kph_max,
            random_generator=random_generator,
            shape=beta_shape,
        )

        duration_hours: float = distance_km / speed_kph
        drawn_legs_references[reference_name].distance_km = distance_km
        drawn_legs_references[reference_name].duration_hours = duration_hours

    return drawn_legs_references


@dataclass
class Leg:
    '''
    This class defines the legs and their properties, from a scenario
    file that contains a list of instances and their properties.
    Legs are point-to-point vehicle movements (i.e. movements where
    the vehicle goes from a start location and ends/stops at an end location).
    '''

    distance_km: float
    duration_hours: float
    start_location: str
    end_location: str

    @staticmethod
    def set_values(
        *, this_leg_definition: Box, drawn_legs_references: Box
    ) -> Leg:

        reference: str = this_leg_definition.reference
        this_leg_references: Box = drawn_legs_references[reference]

        distance_km: float = this_leg_references.distance_km
        duration_hours: float = this_leg_references.duration_hours
        start_location: str = this_leg_definition.start_location
        end_location: str = this_leg_definition.end_location

        return Leg(
            distance_km=distance_km,
            duration_hours=duration_hours,
            start_location=start_location,
            end_location=end_location,
        )


@dataclass
class TripStep:
    '''
    Steps in a trip. Contains travel legs and parked moments
    '''

    start_hour: float  # In hours from midnight
    end_hour: float  # In hours from midnight
    location_name: str
    length_kilometers: float
    duration_hours: float
    speed_kph: float

    @staticmethod
    def get_step(
        start_time_hours: float,
        duration_hours: float,
        location_name: str,
        leg_length_kilometers: float,
    ) -> TripStep:
        if duration_hours == 0:
            speed_kph: float = 0
        else:
            speed_kph = leg_length_kilometers / duration_hours
        return TripStep(
            start_hour=start_time_hours,
            end_hour=start_time_hours + duration_hours,
            location_name=location_name,
            length_kilometers=leg_length_kilometers,
            duration_hours=duration_hours,
            speed_kph=speed_kph,
        )


@dataclass
class Trip:
    '''
    A collection of travel and parking steps that takes place on a given day.
    Each trip starts and ends at a base. Its steps contain times expressed
    as hours from midnight on the trip day.
    '''

    start_base: str
    end_base: str
    base_transition: bool
    trip_steps: list[TripStep]

    @staticmethod
    def get_steps(
        *,
        start_time_hours: float,
        leg_names: list[str],
        time_between_legs_hours: list[float],
        legs: dict[str, Leg],
        vehicle: Vehicle,
    ) -> list[TripStep]:
        step_start_time: float = start_time_hours
        expected_number_of_parking_durations: int = max(len(leg_names) - 1, 0)

        if (
            len(time_between_legs_hours)
            != expected_number_of_parking_durations
        ):
            raise ValueError(
                f'{len(leg_names)=} requires '
                f'{expected_number_of_parking_durations} values in '
                f'time_between_legs_hours, but '
                f'{len(time_between_legs_hours)} were provided.'
            )
        if any(parked_hours < 0 for parked_hours in time_between_legs_hours):
            raise ValueError(
                f'{time_between_legs_hours=} contains one or more '
                'negative parking durations.'
            )

        trip_steps: list[TripStep] = []
        unknown_leg_names = [
            leg_name for leg_name in leg_names if leg_name not in legs
        ]
        if unknown_leg_names:
            raise KeyError(
                f'{unknown_leg_names=} are not defined in scenario.legs.'
            )
        for previous_leg_name, next_leg_name in zip(
            leg_names,
            leg_names[1:],
        ):
            previous_end_location = legs[previous_leg_name].end_location
            next_start_location = legs[next_leg_name].start_location

            if previous_end_location != next_start_location:
                raise ValueError(
                    f'{previous_leg_name=} ends at '
                    f'{previous_end_location!r}, but {next_leg_name=} starts '
                    f'at {next_start_location!r}.'
                )

        for leg_name, parked_hours in zip(
            leg_names,
            time_between_legs_hours,
            strict=False,
            # time_between_legs_hours has one less element than leg_names,
            # by design
        ):
            leg_duration_hours: float = legs[leg_name].duration_hours
            leg_length_kilometers: float = legs[leg_name].distance_km
            driving_step: TripStep = TripStep.get_step(
                start_time_hours=step_start_time,
                duration_hours=leg_duration_hours,
                location_name=vehicle.driving_location_name,
                leg_length_kilometers=leg_length_kilometers,
            )
            trip_steps.append(driving_step)
            parking_location_name: str = legs[leg_name].end_location
            step_start_time += leg_duration_hours
            parking_step: TripStep = TripStep.get_step(
                start_time_hours=step_start_time,
                duration_hours=parked_hours,
                location_name=parking_location_name,
                leg_length_kilometers=0,
            )
            trip_steps.append(parking_step)
            step_start_time += parked_hours

        if len(leg_names) > 0:
            last_leg_name: str = leg_names[-1]
            # The last leg brings us to the base and does
            # not have a corresponding parking time, by definition
            last_step: TripStep = TripStep.get_step(
                start_time_hours=step_start_time,
                duration_hours=legs[last_leg_name].duration_hours,
                location_name=vehicle.driving_location_name,
                leg_length_kilometers=legs[last_leg_name].distance_km,
            )

            trip_steps.append(last_step)
        return trip_steps

    @staticmethod
    def get_leg_info(trip_parameters: Box) -> tuple[list[str], list[float]]:
        leg_names: list[str] = trip_parameters.legs
        time_between_legs_hours: list[float] = (
            trip_parameters.time_between_legs_hours
        )
        return leg_names, time_between_legs_hours

    @staticmethod
    def draw(
        *,
        trip_parameters: Box,
        legs: dict[str, Leg],
        random_generator: np.random.Generator,
        beta_shape: float,
        vehicle: Vehicle,
    ) -> Trip:
        '''
        Creates a user-specific trip by drawing its start time.
        '''
        start_time_hours_min: float = trip_parameters.start_time_hours_min
        start_time_hours_typical: float = (
            trip_parameters.start_time_hours_typical
        )
        start_time_hours_max: float = trip_parameters.start_time_hours_max
        if start_time_hours_min < 0 or start_time_hours_max >= 24:
            raise ValueError(
                f'Trip start-time bounds must fall within [0.0, 24.0). '
                f'{start_time_hours_min=}, {start_time_hours_max=}.'
            )
        start_time_hours: float = draw_beta_value(
            minimum=start_time_hours_min,
            typical=start_time_hours_typical,
            maximum=start_time_hours_max,
            random_generator=random_generator,
            shape=beta_shape,
        )

        start_base: str = trip_parameters.start_base
        end_base: str = trip_parameters.end_base
        base_transition: bool = start_base != end_base

        leg_names, time_between_legs_hours = Trip.get_leg_info(
            trip_parameters=trip_parameters
        )

        trip_steps: list[TripStep] = Trip.get_steps(
            start_time_hours=start_time_hours,
            leg_names=leg_names,
            time_between_legs_hours=time_between_legs_hours,
            legs=legs,
            vehicle=vehicle,
        )
        if not leg_names and start_base != end_base:
            raise ValueError(
                f'A trip without legs cannot move between bases: '
                f'{start_base=}, {end_base=}.'
            )
        if leg_names:
            first_leg_name: str = leg_names[0]
            last_leg_name: str = leg_names[-1]

            if legs[first_leg_name].start_location != start_base:
                raise ValueError(
                    f'{first_leg_name=} starts at '
                    f'{legs[first_leg_name].start_location!r}, '
                    f'which does not match {start_base=}.'
                )

            if legs[last_leg_name].end_location != end_base:
                raise ValueError(
                    f'{last_leg_name=} ends at '
                    f'{legs[last_leg_name].end_location!r}, '
                    f'which does not match {end_base=}.'
                )

        return Trip(
            start_base=start_base,
            end_base=end_base,
            base_transition=base_transition,
            trip_steps=trip_steps,
        )


@dataclass
class ChargingBehaviour:
    adaptive: bool
    charge_desire_proportion_trigger: float

    @staticmethod
    def draw(
        *,
        charging_behaviour_parameters: Box,
        random_generator: np.random.Generator,
        beta_shape: float,
    ) -> ChargingBehaviour:
        adaptive_proportion: float = (
            charging_behaviour_parameters.adaptive_proportion
        )
        if not 0.0 <= adaptive_proportion <= 1.0:
            raise ValueError(
                f'{adaptive_proportion=} must be between 0.0 '
                'and 1.0 (inclusive)'
            )

        charge_desire_proportion_trigger_min: float = (
            charging_behaviour_parameters.charge_desire_proportion_trigger_min
        )
        charge_desire_proportion_trigger_typical: float = (
            charging_behaviour_parameters.charge_desire_proportion_trigger_typical  # noqa:E501
        )
        charge_desire_proportion_trigger_max: float = (
            charging_behaviour_parameters.charge_desire_proportion_trigger_max
        )
        if (
            charge_desire_proportion_trigger_min < 0.0
            or charge_desire_proportion_trigger_max > 1.0
        ):
            raise ValueError(
                'The charge_desire_proportion_trigger needs to be between 0.0 '
                'and 1.0 (inclusive).'
            )

        adaptive: bool = bool(
            random_generator.choice(
                [True, False], p=[adaptive_proportion, 1 - adaptive_proportion]
            )
        )
        charge_desire_proportion_trigger: float = draw_beta_value(
            minimum=charge_desire_proportion_trigger_min,
            typical=charge_desire_proportion_trigger_typical,
            maximum=charge_desire_proportion_trigger_max,
            random_generator=random_generator,
            shape=beta_shape,
        )

        return ChargingBehaviour(
            adaptive=adaptive,
            charge_desire_proportion_trigger=charge_desire_proportion_trigger,
        )


@dataclass
class User:
    ID: uuid.UUID
    vehicle: Vehicle
    locations: dict[str, Location]
    legs: dict[str, Leg]
    trips: dict[str, Trip]
    activities: Activities | None
    run_trips: pl.Series
    # mobility: pl.DataFrame <-because computing
    charging_behaviour: ChargingBehaviour
    # charge: pl.DataFrame <- because computing in prev version,
    # using it to store the sum, but we can do it by summing the DFs we keep
    # metrics: Metrics
    # For charge, simply put the schema. Maybe also for mobility,
    # though the computation of mobility is straightforward,
    # so maybe set schema as for mobility and then compute?
    # Do charge compuation and mobility computation
    # need to be class methods? Probably not for charge.
    # Metrics set to None. Then assert at the end?

    @staticmethod
    def draw_characteristics(
        *,
        scenario: Box,
        random_generator: np.random.Generator,
        time_constants: TimeConstants,
    ) -> tuple[
        Vehicle,
        dict[str, Location],
        dict[str, Leg],
        dict[str, Trip],
        Activities | None,
        ChargingBehaviour,
    ]:
        beta_shape: float = scenario.monte_carlo.beta_shape
        vehicle_settings: Box = scenario.vehicle
        vehicle: Vehicle = Vehicle.draw(
            vehicle_settings=vehicle_settings,
            random_generator=random_generator,
            beta_shape=beta_shape,
        )
        locations_parameters: Box = scenario.locations
        locations: dict[str, Location] = {
            location_name: Location.draw(
                location_parameters=location_parameters,
                random_generator=random_generator,
            )
            for location_name, location_parameters in (
                locations_parameters.items()
            )
        }

        legs_definitions: Box = scenario.legs
        legs_references: Box = scenario.legs_references

        drawn_legs_references: Box = draw_legs_references(
            legs_references=legs_references,
            random_generator=random_generator,
            beta_shape=beta_shape,
        )
        legs: dict[str, Leg] = {
            leg_name: Leg.set_values(
                this_leg_definition=this_leg_definition,
                drawn_legs_references=drawn_legs_references,
            )
            for leg_name, this_leg_definition in legs_definitions.items()
        }

        trips_parameters: Box = scenario.trips
        trips: dict[str, Trip] = {
            trip_name: Trip.draw(
                trip_parameters=trip_parameters,
                legs=legs,
                random_generator=random_generator,
                beta_shape=beta_shape,
                vehicle=vehicle,
            )
            for trip_name, trip_parameters in trips_parameters.items()
        }
        if vehicle.has_one_trip_per_day_type:
            activities: Activities | None = None
        else:
            activity_parameters: Box = scenario.activity_parameters
            activities = Activities.draw(
                activity_parameters=activity_parameters,
                random_generator=random_generator,
                beta_shape=beta_shape,
                time_constants=time_constants,
            )

        charging_behaviour_parameters: Box = scenario.charging_behaviour
        charging_behaviour: ChargingBehaviour = ChargingBehaviour.draw(
            charging_behaviour_parameters=charging_behaviour_parameters,
            random_generator=random_generator,
            beta_shape=beta_shape,
        )
        return vehicle, locations, legs, trips, activities, charging_behaviour

    @staticmethod
    def get_activity_run_trips(
        *,
        activities: Activities,
        trips: dict[str, Trip],
        time_ranges: TimeRange,
        time_constants: TimeConstants,
    ) -> pl.Series:

        run_trips_df: pl.DataFrame = pl.DataFrame([time_ranges.run_dates])
        run_trips_df = run_trips_df.with_columns(
            (pl.col('date').dt.weekday()).alias('Week day'),
            (pl.col('date').dt.week()).alias('Week number'),
        )
        run_trips_df = run_trips_df.with_columns(
            (
                pl.when(
                    pl.col('Week day').is_in(
                        activities.commuting_weekday_numbers
                    )
                    & pl.col('Week number').is_in(
                        activities.commuting_week_numbers
                    )
                )
                .then(True)
                .otherwise(False)
            ).alias('Commute to work')
        )
        run_trips_df = run_trips_df.with_columns(
            (
                pl.when(
                    pl.col('Week day').is_in(
                        activities.leisure_trip_weekday_numbers
                    )
                )
                .then(True)
                .otherwise(False)
            ).alias('Possible leisure trip')
        )

        run_trips_df = run_trips_df.with_columns(
            (
                pl.when(
                    pl.col('Week day').is_in(
                        time_constants.weekend_day_numbers
                    )
                    & pl.col('Week number').is_in(
                        activities.holiday_trip_week_before_numbers
                    )
                )
                .then(True)
                .otherwise(False)
            ).alias('Holiday outward weekend'),
            (
                pl.when(
                    pl.col('Week day').is_in(
                        time_constants.weekend_day_numbers
                    )
                    & pl.col('Week number').is_in(
                        activities.holiday_trip_week_numbers
                    )
                )
                .then(True)
                .otherwise(False)
            ).alias('Holiday back weekend'),
        )
        run_trips_df = run_trips_df.with_columns(
            (
                pl.when(
                    pl.col('Week day').is_in(
                        time_constants.weekend_day_numbers
                    )
                    & pl.col('Week number').is_in(
                        activities.weekend_trip_week_numbers
                    )
                )
                .then(True)
                .otherwise(False)
            ).alias('Weekend trip'),
        )
        run_trips_df = run_trips_df.with_columns(
            pl.lit('Mazinger').alias('trip_name')
        )
        # SKip leisure on compting weekends? To avoid Sat/SUn issue but maybe feasible)
        # for each WE HOLIDAY trip, draw weekday (in WE) with a proportion in TOML. If both are leisure, this wins
        # If only one is leisure, leisure wins
        # Then add that too logic here.
        # Also ste base (home most o fthe time, hliday on holiday weeks)
        # Maybe drop base concept altogehter and just have a hliday week check to get leisure on holiday
        # NO! Base is needed for MObility Matrix
        # Then chain tests Holiday then WE theh Coomute and Leisure together Rest isstay put
        # print(run_trips_df)
        # exit()
        return run_trips_df['trip_name']

    @staticmethod
    def get_run_trips(
        *,
        activities: Activities | None,
        trips: dict[str, Trip],
        time_ranges: TimeRange,
        time_constants: TimeConstants,
    ) -> pl.Series:
        '''
        Tells us which trip occurs on each day of our run.
        '''
        if activities is not None:
            run_trips: pl.Series = User.get_activity_run_trips(
                activities=activities,
                trips=trips,
                time_ranges=time_ranges,
                time_constants=time_constants,
            )

        else:
            possible_day_types: set[str] = set(
                time_ranges.day_types.unique().to_list()
            )
            trip_names: set[str] = set(trips)
            missing_trip_names: set[str] = possible_day_types - trip_names
            if missing_trip_names:
                raise ValueError(
                    'If there is one trip per day type, each day type '
                    'occurring in the run must have a trip '
                    'with the same name. '
                    f'{missing_trip_names=}.'
                )

            run_trips = time_ranges.day_types.rename('trip_name')
            # Trips and day types have the same names, by convention

        if len(run_trips) != len(time_ranges.run_dates):
            raise ValueError(
                f'{len(run_trips)=} does not match '
                f'{len(time_ranges.run_dates)=}.'
            )

        return run_trips

    @staticmethod
    def create(
        *,
        scenario: Box,
        random_generator: np.random.Generator,
        time_ranges: TimeRange,
        time_constants: TimeConstants,
    ) -> User:

        ID: uuid.UUID = uuid.uuid4()
        vehicle, locations, legs, trips, activities, charging_behaviour = (
            User.draw_characteristics(
                scenario=scenario,
                random_generator=random_generator,
                time_constants=time_constants,
            )
        )
        run_trips: pl.Series = User.get_run_trips(
            activities=activities,
            trips=trips,
            time_ranges=time_ranges,
            time_constants=time_constants,
        )

        # Create empties
        # Compute mobility
        # create empty charging and metrics
        return User(
            ID=ID,
            vehicle=vehicle,
            locations=locations,
            legs=legs,
            trips=trips,
            activities=activities,
            run_trips=run_trips,
            charging_behaviour=charging_behaviour,
        )


def create_users(
    *, scenario: Box, random_generator: np.random.Generator
) -> list[User]:

    users_settings: Box = scenario.users

    users_pool_size: int = users_settings.users_pool_size

    if users_pool_size < 1:
        raise ValueError(
            'You need at least one user '
            '(users_pool_size in [users] in scenario toml)'
        )
    time_constants: TimeConstants = TimeConstants.read_parameters(
        scenario.time
    )
    run_parameters: Box = scenario.run
    time_ranges: TimeRange = TimeRange.set_ranges(
        run_parameters=run_parameters,
        time_constants=time_constants,
    )

    users_pool: list[User] = [
        User.create(
            scenario=scenario,
            random_generator=random_generator,
            time_ranges=time_ranges,
            time_constants=time_constants,
        )
        for _ in range(users_pool_size)
    ]
    if users_settings.pickle_users_pool:
        users_path: Path = (
            Path('users') / scenario.case_name / f'{scenario.name}_pool.p'
        )
        users_path.parent.mkdir(parents=True, exist_ok=True)
        with users_path.open('wb') as users_file:
            pickle.dump(users_pool, users_file)

    return users_pool


def read_users_pool(*, scenario: Box) -> list[User]:

    users_path: Path = (
        Path('users') / scenario.case_name / f'{scenario.name}_pool.p'
    )
    with users_path.open('rb') as users_file:
        users_pool: list[User] = pickle.load(users_file)

    return users_pool


def get_users_pool(
    *, scenario: Box, random_generator: np.random.Generator
) -> list[User]:

    users_settings: Box = scenario.users

    if users_settings.read_from_file:
        users_pool: list[User] = read_users_pool(scenario=scenario)
    else:
        users_pool: list[User] = create_users(
            scenario=scenario, random_generator=random_generator
        )
    return users_pool
