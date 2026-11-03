import pickle
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import polars as pl
from box import Box

from ChaProEV.stochastic_new.activities import Activities
from ChaProEV.stochastic_new.monte_carlo import draw_beta_value
from ChaProEV.stochastic_new.time import TimeConstants, TimeRange


@dataclass
class RunMetrics:
    kilometrage: float = 0.0
    consumption_kWh: float = 0.0
    purchased_electricity_kWh: float = 0.0
    charge_spending_eur: float = 0.0
    electricity_sold_kWh: float = 0.0
    discharge_income_eur: float = 0.0
    average_hourly_power_from_network_kW: pl.Series = field(
        default_factory=lambda: pl.Series(
            'Average hourly power from network (kW)',
            [0.0] * 24,
            dtype=pl.Float64,
        )
    )


@dataclass
class Vehicle:
    name: str
    consumption_kWh_km: float
    battery_size_kWh: float
    has_one_trip_per_day_type: bool
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
    mobility: pl.DataFrame
    charging_behaviour: ChargingBehaviour
    charge: pl.DataFrame
    run_metrics: RunMetrics

    @staticmethod
    def draw_characteristics(
        *,
        scenario: Box,
        random_generator: np.random.Generator,
        time_constants: TimeConstants,
        time_ranges: TimeRange,
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
                time_ranges=time_ranges,
            )

        charging_behaviour_parameters: Box = scenario.charging_behaviour
        charging_behaviour: ChargingBehaviour = ChargingBehaviour.draw(
            charging_behaviour_parameters=charging_behaviour_parameters,
            random_generator=random_generator,
            beta_shape=beta_shape,
        )
        return vehicle, locations, legs, trips, activities, charging_behaviour

    @staticmethod
    def get_trip_from_date(
        *,
        run_date: date,
        activities: Activities,
        activity_trip_settings: Box,
        random_generator: np.random.Generator,
    ) -> str:

        # Start with trips that have dates already
        if run_date in activities.holiday_outward_trip_dates:
            return activity_trip_settings.holiday_outward_trip
        if run_date in activities.holiday_back_trip_dates:
            return activity_trip_settings.holiday_back_trip
        if run_date in activities.weekend_trip_dates:
            return activity_trip_settings.weekend_trip

        # Then trips in days away/on holiday
        if run_date in activities.away_dates:
            if (
                run_date.isoweekday()
                in activities.leisure_trip_weekday_numbers
            ):
                return activity_trip_settings.away_leisure_trip
            else:
                return activity_trip_settings.default_trip_away

        # Then working days
        if (
            run_date.isoweekday() in activities.commuting_weekday_numbers
            and run_date.isocalendar().week
            in activities.commuting_week_numbers
        ):
            if (
                run_date.isoweekday()
                not in activities.leisure_trip_weekday_numbers
            ):
                return activity_trip_settings.work_only_trip
            else:
                # Work and leisure
                work_and_leisure_trips: list[str] = (
                    activity_trip_settings.work_and_leisure_trips
                )
                work_and_leisure_trip_split: list[float] = (
                    activity_trip_settings.work_and_leisure_trip_split
                )

                if len(work_and_leisure_trips) != len(
                    work_and_leisure_trip_split
                ):
                    raise ValueError(
                        f'{work_and_leisure_trips=} and '
                        f'{work_and_leisure_trip_split=} must have the '
                        'same length.'
                    )

                if any(
                    probability < 0
                    for probability in work_and_leisure_trip_split
                ) or not np.isclose(
                    sum(work_and_leisure_trip_split),
                    1.0,
                ):
                    raise ValueError(
                        f'{work_and_leisure_trip_split=} must be non-negative '
                        'and sum to 1.0.'
                    )
                chosen_combined_trip: str = random_generator.choice(
                    work_and_leisure_trips, p=work_and_leisure_trip_split
                )
                return chosen_combined_trip

        if run_date.isoweekday() in activities.leisure_trip_weekday_numbers:
            return activity_trip_settings.leisure_only_at_home_trip

        return activity_trip_settings.default_trip

    @staticmethod
    def get_activity_run_trips(
        *,
        activities: Activities,
        time_ranges: TimeRange,
        activity_trip_settings: Box,
        random_generator: np.random.Generator,
    ) -> pl.Series:

        run_dates: list[date] = list(time_ranges.run_dates)

        run_trip_list: list[str] = [
            User.get_trip_from_date(
                run_date=run_date,
                activities=activities,
                activity_trip_settings=activity_trip_settings,
                random_generator=random_generator,
            )
            for run_date in run_dates
        ]
        run_trips: pl.Series = pl.Series('trip_name', run_trip_list)
        return run_trips

    @staticmethod
    def get_run_trips(
        *,
        activities: Activities | None,
        trips: dict[str, Trip],
        time_ranges: TimeRange,
        scenario: Box,
        random_generator: np.random.Generator,
    ) -> pl.Series:
        '''
        Tells us which trip occurs on each day of our run.
        '''
        if activities is not None:
            run_trips: pl.Series = User.get_activity_run_trips(
                activities=activities,
                time_ranges=time_ranges,
                activity_trip_settings=scenario.activity_parameters.trips,
                random_generator=random_generator,
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

        selected_trip_names: set[str] = set(run_trips.unique().to_list())
        trip_names: set[str] = set(trips)

        missing_trip_names: set[str] = selected_trip_names - trip_names

        if missing_trip_names:
            raise ValueError(
                f'{missing_trip_names=} occur in run_trips but are not '
                'defined in scenario.trips.'
            )

        return run_trips

    @staticmethod
    def create_trip_step_record(
        *,
        trip_date: date,
        trip_step: TripStep,
        run_time_resolution_hours: float,
    ) -> dict[str, object]:
        midnight: datetime = datetime.combine(date=trip_date, time=time.min)

        start_step: int = int(
            np.floor(trip_step.start_hour / run_time_resolution_hours + 0.5)
        )
        # Using floor + 0.5 raather than round to consistently round up instead
        # of having rounding changingon evenness of value
        end_step: int = int(
            np.floor(trip_step.end_hour / run_time_resolution_hours + 0.5)
        )
        # Using floor + 0.5 raather than round to consistently round up instead
        # of having rounding changingon evenness of value
        number_of_steps: int = max(1, end_step - start_step)

        step_start: datetime = midnight + timedelta(
            hours=start_step * run_time_resolution_hours
        )
        step_end: datetime = midnight + timedelta(
            hours=(start_step + number_of_steps) * run_time_resolution_hours
        )

        return {
            'Step start': step_start,
            'Step end': step_end,
            'Location': trip_step.location_name,
            'Kilometers driven': trip_step.length_kilometers / number_of_steps,
        }

    @staticmethod
    def get_mobility_matrix(
        *,
        run_trips: pl.Series,
        time_ranges: TimeRange,
        mobility_settings: Box,
        activities: Activities | None,
        vehicle: Vehicle,
        time_constants: TimeConstants,
        trips: dict[str, Trip],
    ) -> pl.DataFrame:
        MINUTES_PER_HOUR: int = time_constants.MINUTES_PER_HOUR

        if time_ranges.frequency_type != 'm':
            raise ValueError('You need to use minutes for the frequency!')
        run_frequency_size: int = time_ranges.frequency_size
        run_time_resolution_hours: float = (
            run_frequency_size / MINUTES_PER_HOUR
        )

        time_index_name: str = mobility_settings.time_index_name
        location_header: str = mobility_settings.location_header
        driven_header: str = mobility_settings.driven_header
        consumption_header: str = mobility_settings.consumption_header
        time_at_location_header: str = (
            mobility_settings.time_at_location_header
        )
        base: str = mobility_settings.base

        # We initialise the mobility matrix
        mobility_matrix: pl.DataFrame = time_ranges.run_stamps.to_frame(
            time_index_name
        ).with_columns(
            pl.lit(base).alias(location_header),
            pl.lit(0.0).alias(driven_header),
        )

        # We assign the away location to away days and back days
        # (who start away)
        if activities is not None:
            away_location: str = mobility_settings.away_location
            mobility_matrix = mobility_matrix.with_columns(
                pl.when(
                    (pl.col(time_index_name).dt.date()).is_in(
                        activities.away_dates
                        + activities.holiday_back_trip_dates
                    )
                )
                .then(pl.lit(away_location))
                .otherwise(pl.col(location_header))
                .alias(location_header)
            )
        trip_step_records: list[dict[str, object]] = []
        for trip_date, trip_name in zip(
            time_ranges.run_dates, run_trips, strict=True
        ):
            trip: Trip = trips[trip_name]
            for step_index, trip_step in enumerate(trip.trip_steps):
                trip_step_record: dict[str, object] = (
                    User.create_trip_step_record(
                        trip_date=trip_date,
                        trip_step=trip_step,
                        run_time_resolution_hours=run_time_resolution_hours,
                    )
                )

                trip_step_records.append(trip_step_record)

                # We want to manage the case where there is a base change
                # (only for vehicles that have activities, such as cars)
                # happens. We want to add a trip step after the last one

                # We check that we went through all the trip steps
                if step_index == len(trip.trip_steps) - 1:
                    # We check that there are acivities
                    if activities is not None:
                        base_transfer_trips: list[str] = (
                            mobility_settings.base_transfer_trips
                        )
                        transfer_end_locations: list[str] = (
                            mobility_settings.transfer_end_locations
                        )
                        end_location_dict: dict[str, str] = dict(
                            zip(base_transfer_trips, transfer_end_locations)
                        )
                        # We check that it is a base transfer
                        if trip_name in base_transfer_trips:
                            end_location: str = end_location_dict[trip_name]
                            # We check that we haven't crossesd midnight
                            # (if so, then the location already is given by
                            # the new base, since we set that when changing the
                            # location on away and holiday back trips

                            if (
                                trip_step_record['Step end'].date()
                                == trip_date
                            ):

                                extra_trip_step: TripStep = TripStep(
                                    start_hour=trip_step.end_hour,
                                    end_hour=24.0,
                                    location_name=end_location,
                                    length_kilometers=0.0,
                                    duration_hours=24.0 - trip_step.end_hour,
                                    speed_kph=0.0,
                                )
                                extra_trip_step_record: dict[str, object] = (
                                    User.create_trip_step_record(
                                        trip_date=trip_date,
                                        trip_step=extra_trip_step,
                                        run_time_resolution_hours=(
                                            run_time_resolution_hours
                                        ),
                                    )
                                )
                                trip_step_records.append(
                                    extra_trip_step_record
                                )

        if not trip_step_records:
            return mobility_matrix

        trip_steps: pl.DataFrame = pl.DataFrame(trip_step_records)
        trip_step_stamps: pl.DataFrame = (
            trip_steps.with_columns(
                pl.datetime_ranges(
                    start='Step start',
                    end='Step end',
                    interval=(
                        f'{run_frequency_size}{time_ranges.frequency_type}'
                    ),
                    closed='left',
                ).alias(time_index_name)
            )
            .explode(time_index_name)
            .select(time_index_name, location_header, driven_header)
        )

        duplicate_time_stamps: pl.DataFrame = (
            trip_step_stamps.group_by(time_index_name)
            .len()
            .filter(pl.col('len') > 1)
        )

        if duplicate_time_stamps.height > 0:
            raise ValueError(
                'Multiple trip steps modify the same time stamp.',
                'You need to resolve overlaps explicitely',
            )

        mobility_matrix = (
            mobility_matrix.join(
                trip_step_stamps,
                on=time_index_name,
                how='left',
                suffix='_trip',
                # maintain_order='left',
            )
            .with_columns(
                pl.coalesce('Location_trip', location_header).alias(
                    location_header
                ),
                pl.coalesce('Kilometers driven_trip', driven_header).alias(
                    driven_header
                ),
            )
            .drop(
                'Location_trip', 'Kilometers driven_trip'
            )  # .sort(time_index_name)
        )
        mobility_matrix = mobility_matrix.with_columns(
            (pl.col(driven_header) * vehicle.consumption_kWh_km).alias(
                consumption_header
            )
        )
        mobility_matrix = (
            mobility_matrix.with_columns(
                (pl.col(location_header) != pl.col(location_header).shift(1))
                .fill_null(True)
                .cum_sum()
                .alias('location_run_ID')
            )
            .with_columns(
                pl.len().over('location_run_ID').alias('location_run_rows')
            )
            .with_columns(
                (
                    pl.col('location_run_rows') * run_time_resolution_hours
                ).alias(time_at_location_header)
            )
            .drop('location_run_ID', 'location_run_rows')
        )

        return mobility_matrix

    @staticmethod
    def create_charging_dataframe(*, time_ranges: TimeRange) -> pl.DataFrame:
        charging_dataframe = pl.DataFrame(
            {
                'Time Stamp': time_ranges.run_stamps,
            },
            schema={
                'Time Stamp': pl.Datetime('us'),
            },
        )

        charging_dataframe = charging_dataframe.with_columns(
            pl.lit(None, dtype=pl.Float64).alias('Battery charge level (kWh)'),
            pl.lit(None, dtype=pl.Float64).alias('Power to vehicle (kW)'),
            pl.lit(None, dtype=pl.Float64).alias(
                'Power drawn from network (kW)'
            ),
            pl.lit(None, dtype=pl.Float64).alias('Charge to vehicle (kWh)'),
            pl.lit(None, dtype=pl.Float64).alias(
                'Charge drawn from network (kWh)'
            ),
        )

        return charging_dataframe

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
                time_ranges=time_ranges,
            )
        )
        run_trips: pl.Series = User.get_run_trips(
            activities=activities,
            trips=trips,
            time_ranges=time_ranges,
            scenario=scenario,
            random_generator=random_generator,
        )
        mobility_settings: Box = scenario.mobility

        mobility: pl.DataFrame = User.get_mobility_matrix(
            run_trips=run_trips,
            time_ranges=time_ranges,
            mobility_settings=mobility_settings,
            activities=activities,
            vehicle=vehicle,
            time_constants=time_constants,
            trips=trips,
        )

        charge: pl.DataFrame = User.create_charging_dataframe(
            time_ranges=time_ranges
        )

        run_metrics: RunMetrics = RunMetrics(
            kilometrage=mobility[mobility_settings.driven_header].sum(),
            consumption_kWh=mobility[
                mobility_settings.consumption_header
            ].sum(),
        )
        return User(
            ID=ID,
            vehicle=vehicle,
            locations=locations,
            legs=legs,
            trips=trips,
            activities=activities,
            run_trips=run_trips,
            charging_behaviour=charging_behaviour,
            mobility=mobility,
            charge=charge,
            run_metrics=run_metrics,
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
