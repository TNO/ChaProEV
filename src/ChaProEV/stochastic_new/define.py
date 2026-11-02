import pickle
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
from box import Box


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
        *, vehicle_settings: Box, random_generator: np.random.Generator
    ) -> Vehicle:
        name: str = vehicle_settings.name
        has_one_trip_per_day_type: bool = (
            vehicle_settings.has_one_trip_per_day_type
        )
        driving_location_name: str = vehicle_settings.driving_location_name
        bases: list[str] = vehicle_settings.bases
        consumption_kWh_km_mean: float = (
            vehicle_settings.consumption_kWh_km_mean
        )
        consumption_kWh_km_standard_deviation: float = (
            vehicle_settings.consumption_kWh_km_standard_deviation
        )
        battery_size_kWh_mean: float = vehicle_settings.battery_size_kWh_mean
        battery_size_kWh_standard_deviation: float = (
            vehicle_settings.battery_size_kWh_standard_deviation
        )
        consumption_kWh_km: float = random_generator.normal(
            loc=consumption_kWh_km_mean,
            scale=consumption_kWh_km_standard_deviation,
        )
        if consumption_kWh_km <= 0:
            raise ValueError(
                f'Drawn {consumption_kWh_km=} is negative or zero. '
                f'Check {consumption_kWh_km_mean=} and '
                f'{consumption_kWh_km_standard_deviation=}'
            )
        battery_size_kWh: float = random_generator.normal(
            loc=battery_size_kWh_mean,
            scale=battery_size_kWh_standard_deviation,
        )
        if battery_size_kWh <= 0:
            raise ValueError(
                f'Drawn {battery_size_kWh=} is negative or zero. '
                f'Check {battery_size_kWh_mean=} and '
                f'{battery_size_kWh_standard_deviation=}'
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
    *, legs_references: Box, random_generator: np.random.Generator
) -> Box:
    '''
    Draws leg distances and speeds and calculates durations.
    Outward and return legs that share a reference have the same
    distance and duration.
    We assume that legs outward and back have the same characteristics,
    '''
    drawn_legs_references: Box = Box()
    for reference_name, reference in legs_references.items():
        drawn_legs_references[reference_name] = Box()
        mean_distance_km: float = reference.mean_distance_km
        standard_deviation_distance: float = (
            reference.standard_deviation_distance
        )
        mean_speed_kph: float = reference.mean_speed_kph
        standard_deviation_speed: float = reference.standard_deviation_speed
        distance_km: float = random_generator.normal(
            loc=mean_distance_km,
            scale=standard_deviation_distance,
        )
        if distance_km <= 0:
            raise ValueError(
                f'Drawn {distance_km=} for {reference_name=} '
                'is negative or zero. '
                f'Please check {mean_distance_km=} and '
                f'{standard_deviation_distance=}'
            )
        speed_kph: float = random_generator.normal(
            loc=mean_speed_kph,
            scale=standard_deviation_speed,
        )
        if speed_kph <= 0:
            raise ValueError(
                f'Drawn {speed_kph=} for {reference_name=} '
                'is negative or zero. '
                f'Please check {mean_speed_kph=} and '
                f'{standard_deviation_speed=}'
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
class ChargingBehaviour:
    adaptive: bool
    charge_desire_proportion_trigger: float

    @staticmethod
    def draw(
        *,
        charging_behaviour_parameters: Box,
        random_generator: np.random.Generator,
    ) -> ChargingBehaviour:
        adaptive_proportion: float = (
            charging_behaviour_parameters.adaptive_proportion
        )
        if not 0.0 <= adaptive_proportion <= 1.0:
            raise ValueError(
                f'{adaptive_proportion=} must be between 0.0 '
                'and 1.0 (inclusive)'
            )
        adaptive: bool = bool(
            random_generator.choice(
                [True, False], p=[adaptive_proportion, 1 - adaptive_proportion]
            )
        )
        charge_desire_proportion_trigger_mean: float = (
            charging_behaviour_parameters.charge_desire_proportion_trigger_mean
        )
        if not 0.0 <= charge_desire_proportion_trigger_mean <= 1.0:
            raise ValueError(
                f'{charge_desire_proportion_trigger_mean=} must be between '
                '0.0 and 1.0 (inclusive)'
            )
        charge_desire_proportion_trigger_standard_deviation: float = (
            charging_behaviour_parameters.charge_desire_proportion_trigger_standard_deviation  # noqa: E501
        )
        if charge_desire_proportion_trigger_standard_deviation < 0:
            raise ValueError(
                f'{charge_desire_proportion_trigger_standard_deviation=} '
                'cannot be negative.'
            )

        if (
            charge_desire_proportion_trigger_standard_deviation == 0
            or charge_desire_proportion_trigger_mean == 0.0
            or charge_desire_proportion_trigger_mean == 1.0
            # If set at exactly 0.0 or 1.0, the standard deviation
            # will be ignored.
        ):
            charge_desire_proportion_trigger: float = (
                charge_desire_proportion_trigger_mean
            )
        else:
            # We use a beta distribution
            # https://en.wikipedia.org/wiki/Beta_distribution

            maximum_standard_deviation: float = np.sqrt(
                charge_desire_proportion_trigger_mean
                * (1 - charge_desire_proportion_trigger_mean)
            )
            if (
                charge_desire_proportion_trigger_standard_deviation
                >= maximum_standard_deviation
            ):
                raise ValueError(
                    f'{charge_desire_proportion_trigger_standard_deviation=} '
                    f'is too large for '
                    f'{charge_desire_proportion_trigger_mean=}.'
                    f' It must be smaller than {maximum_standard_deviation=}.'
                )

            trigger_variance: float = (
                charge_desire_proportion_trigger_standard_deviation**2
            )
            trigger_common: float = (
                charge_desire_proportion_trigger_mean
                * (1 - charge_desire_proportion_trigger_mean)
                / trigger_variance
            ) - 1

            trigger_alpha: float = (
                charge_desire_proportion_trigger_mean * trigger_common
            )
            trigger_beta: float = (
                1 - charge_desire_proportion_trigger_mean
            ) * trigger_common

            charge_desire_proportion_trigger = random_generator.beta(
                trigger_alpha, trigger_beta
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
    # trips: dict[str, Trip]
    # activities: Activities
    # run_trips: pl.Series
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
        *, scenario: Box, random_generator: np.random.Generator
    ) -> tuple[
        Vehicle, dict[str, Location], dict[str, Leg], ChargingBehaviour
    ]:
        vehicle_settings: Box = scenario.vehicle
        vehicle: Vehicle = Vehicle.draw(
            vehicle_settings=vehicle_settings,
            random_generator=random_generator,
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
            legs_references=legs_references, random_generator=random_generator
        )
        legs: dict[str, Leg] = {
            leg_name: Leg.set_values(
                this_leg_definition=this_leg_definition,
                drawn_legs_references=drawn_legs_references,
            )
            for leg_name, this_leg_definition in legs_definitions.items()
        }
        charging_behaviour_parameters: Box = scenario.charging_behaviour
        charging_behaviour: ChargingBehaviour = ChargingBehaviour.draw(
            charging_behaviour_parameters=charging_behaviour_parameters,
            random_generator=random_generator,
        )
        return vehicle, locations, legs, charging_behaviour

    @staticmethod
    def create(
        *, scenario: Box, random_generator: np.random.Generator
    ) -> User:
        ID: uuid.UUID = uuid.uuid4()
        vehicle, locations, legs, charging_behaviour = (
            User.draw_characteristics(
                scenario=scenario, random_generator=random_generator
            )
        )
        # Create empties
        # Compute mobility
        # create empty charging and metrics
        return User(
            ID=ID,
            vehicle=vehicle,
            locations=locations,
            legs=legs,
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

    users_pool: list[User] = [
        User.create(scenario=scenario, random_generator=random_generator)
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
