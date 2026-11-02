import pickle
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import numpy as np
import polars as pl
from box import Box


@dataclass
class TimeConstants:
    SECONDS_PER_HOUR: int
    MINUTES_PER_HOUR: int
    HOURS_IN_A_DAY: int
    MONTHS_IN_A_YEAR: int
    MAX_DAYS_IN_A_MONTH: int
    DAYS_IN_A_YEAR: float
    DAYS_IN_A_WEEK: int
    WEEKS_IN_A_YEAR: float
    first_hour_number: int
    first_week_index: int
    last_week_index: int
    weekend_day_numbers: list[int]
    holiday_weeks: list[int]
    holiday_week_blocks: list[list[int]]
    number_of_holiday_weeks: int
    # We need to provide the number of holiday weeks separately,
    # as counting the elements of the list above might not work, such as
    # when the above list contains weeks 1 and 53 (which just represent
    # the fact that years don't necessarily start and/or end at the start/end
    # of a week).

    @staticmethod
    def read_parameters(time_parameters: Box) -> TimeConstants:
        holiday_week_blocks: list[list[int]] = (
            time_parameters.holiday_week_blocks
        )
        holiday_weeks: list[int] = [
            week for block in holiday_week_blocks for week in block
        ]
        return TimeConstants(
            SECONDS_PER_HOUR=time_parameters.SECONDS_PER_HOUR,
            MINUTES_PER_HOUR=time_parameters.MINUTES_PER_HOUR,
            HOURS_IN_A_DAY=time_parameters.HOURS_IN_A_DAY,
            MONTHS_IN_A_YEAR=time_parameters.MONTHS_IN_A_YEAR,
            MAX_DAYS_IN_A_MONTH=time_parameters.MAX_DAYS_IN_A_MONTH,
            DAYS_IN_A_YEAR=time_parameters.DAYS_IN_A_YEAR,
            DAYS_IN_A_WEEK=time_parameters.DAYS_IN_A_WEEK,
            WEEKS_IN_A_YEAR=time_parameters.DAYS_IN_A_YEAR
            / time_parameters.DAYS_IN_A_WEEK,
            first_hour_number=time_parameters.first_hour_number,
            first_week_index=time_parameters.first_week_index,
            last_week_index=time_parameters.last_week_index,
            weekend_day_numbers=time_parameters.weekend_day_numbers,
            holiday_weeks=holiday_weeks,
            holiday_week_blocks=holiday_week_blocks,
            number_of_holiday_weeks=time_parameters.number_of_holiday_weeks,
        )


@dataclass
class TimeRange:
    '''
    The time ranges used for dates and timestamps, both for
    computation and display.

    '''

    run_dates: pl.Series
    display_dates: pl.Series
    run_stamps: pl.Series
    display_stamps: pl.Series
    day_types: pl.Series
    frequency: str
    frequency_type: str
    frequency_size: int

    @staticmethod
    def set_ranges(
        run_parameters: Box,
        time_constants: TimeConstants,
    ) -> TimeRange:
        start: Box = run_parameters.start
        end: Box = run_parameters.end

        if (
            start.hour != 0
            or start.minute != 0
            or end.hour != 0
            or end.minute != 0
        ):
            raise ValueError(
                'The run must start and end at midnight because trips are '
                'assigned per complete run day. The display period may have '
                'different start and end times, but the underlying run must '
                'be extended to start and end at midnight.'
            )

        display_start: Box = run_parameters.display_start
        display_end: Box = run_parameters.display_end
        run_frequency_settings: Box = run_parameters.frequency
        display_frequency_settings: Box = run_parameters.display_frequency

        run_frequency: str = (
            f'{run_frequency_settings.size}{run_frequency_settings.type}'
        )
        display_frequency: str = (
            f'{display_frequency_settings.size}'
            f'{display_frequency_settings.type}'
        )
        if (
            run_frequency_settings.size <= 0
            or display_frequency_settings.size <= 0
        ):
            raise ValueError(
                f'Both {run_frequency_settings.size=} and '
                f'{display_frequency_settings.size=} must be positive.'
            )

        start_date: date = date(
            year=start.year, month=start.month, day=start.day
        )
        end_date: date = date(year=end.year, month=end.month, day=end.day)

        start_datetime: datetime = datetime(
            year=start.year,
            month=start.month,
            day=start.day,
            hour=start.hour,
            minute=start.minute,
        )
        end_datetime: datetime = datetime(
            year=end.year,
            month=end.month,
            day=end.day,
            hour=end.hour,
            minute=end.minute,
        )
        display_start_datetime: datetime = datetime(
            year=display_start.year,
            month=display_start.month,
            day=display_start.day,
            hour=display_start.hour,
            minute=display_start.minute,
        )
        display_end_datetime: datetime = datetime(
            year=display_end.year,
            month=display_end.month,
            day=display_end.day,
            hour=display_end.hour,
            minute=display_end.minute,
        )
        if start_datetime >= end_datetime:
            raise ValueError(
                f'{start_datetime=} must be before {end_datetime=}'
            )
        if display_start_datetime >= display_end_datetime:
            raise ValueError(
                f'{display_start_datetime=} must be before '
                f'{display_end_datetime=}'
            )

        if display_start_datetime < start_datetime:
            raise ValueError(
                f'{display_start_datetime=} must be later or '
                f'at the same time as {start_datetime=}'
            )
        if display_end_datetime > end_datetime:
            raise ValueError(
                f'{display_end_datetime=} must be earlier or '
                f'at the same time as {end_datetime=}'
            )

        run_dates: pl.Series = pl.date_range(
            start=start_date,
            end=end_date,
            eager=True,
            closed='left',
        ).rename('date')

        run_stamps: pl.Series = pl.datetime_range(
            start=start_datetime,
            end=end_datetime,
            interval=run_frequency,
            eager=True,
            closed='left',
        ).rename('timestamp')
        display_stamps: pl.Series = pl.datetime_range(
            start=display_start_datetime,
            end=display_end_datetime,
            interval=display_frequency,
            eager=True,
            closed='left',
        ).rename('timestamp')
        display_dates: pl.Series = (
            display_stamps.dt.date().unique(maintain_order=True).rename('date')
        )
        # Derived from display_stamps because a display range with non-midnight
        # boundaries may cover more dates than an equivalent closed-left
        # date range.

        day_types: pl.Series = pl.DataFrame({'date': run_dates}).with_columns(
            pl.concat_str(
                [
                    pl.when(
                        pl.col('date')
                        .dt.weekday()
                        .is_in(time_constants.weekend_day_numbers)
                    )
                    .then(pl.lit('weekend'))
                    .otherwise(pl.lit('weekday')),
                    pl.lit('_in_'),
                    pl.when(
                        pl.col('date')
                        .dt.week()
                        .is_in(time_constants.holiday_weeks)
                    )
                    .then(pl.lit('holiday'))
                    .otherwise(pl.lit('work')),
                    pl.lit('_week'),
                ]
            ).alias('day_type')
        )['day_type']

        return TimeRange(
            run_dates=run_dates,
            display_dates=display_dates,
            run_stamps=run_stamps,
            display_stamps=display_stamps,
            day_types=day_types,
            frequency=run_frequency,
            frequency_type=run_frequency_settings.type,
            frequency_size=run_frequency_settings.size,
        )


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
    We assume that legs outward and back have the same distance and duration.
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
    def draw_start_time_hours(
        *,
        start_time_hours_mean: float,
        start_time_hours_standard_deviation: float,
        random_generator: np.random.Generator,
    ) -> float:
        '''
        Draws the start time of the trip.
        '''
        start_time_hours: float = random_generator.normal(
            loc=start_time_hours_mean,
            scale=start_time_hours_standard_deviation,
        )
        if start_time_hours < 0 or start_time_hours >= 24:
            raise ValueError(
                f'Drawn {start_time_hours=} is negative or >=24, '
                'making the trip start in another day. '
                f'Please check/adjust {start_time_hours_mean=} '
                f'and {start_time_hours_standard_deviation=}'
            )
        return start_time_hours

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
        vehicle: Vehicle,
    ) -> Trip:
        '''
        Creates a user-specific trip by drawing its start time.
        '''
        start_time_hours_mean: float = trip_parameters.start_time_hours_mean
        start_time_hours_standard_deviation: float = (
            trip_parameters.start_time_hours_standard_deviation
        )
        start_time_hours: float = Trip.draw_start_time_hours(
            start_time_hours_mean=start_time_hours_mean,
            start_time_hours_standard_deviation=(
                start_time_hours_standard_deviation
            ),
            random_generator=random_generator,
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
class Activities:
    '''
    Tells us in which week or day number activities (commute,
    holiday trips, weekend trips, leisure trips) occur.
    For commuting, we look at weekday numbers (1= Monday, 7= Sunday).
    The same holds for leisure trips.
    Weekend trips and holiday trips get a week number (1 to 53)

    '''

    holiday_trip_week_numbers: list[int]
    weekend_trip_week_numbers: list[int]
    leisure_trip_weekday_numbers: list[int]
    commuting_weekday_numbers: list[int]

    @staticmethod
    def draw_holiday_trip_week_numbers(
        *,
        holiday_parameters: Box,
        commuting_parameters: Box,
        random_generator: np.random.Generator,
        time_constants: TimeConstants,
    ) -> tuple[list[int], list[int]]:

        holiday_trip_week_numbers: list[int] = []

        working_weeks: list[int] = []

        return holiday_trip_week_numbers, working_weeks

    @staticmethod
    def draw_weekend_trip_week_numbers(
        *,
        holiday_trip_week_numbers: list[int],
        weekend_parameters: Box,
        random_generator: np.random.Generator,
        time_constants: TimeConstants,
    ) -> list[int]:

        weekend_trip_week_numbers: list[int] = []

        return weekend_trip_week_numbers

    @staticmethod
    def draw_leisure_trip_weekday_numbers(
        *,
        weekend_trip_week_numbers: list[int],
        leisure_parameters: Box,
        random_generator: np.random.Generator,
        time_constants: TimeConstants,
    ) -> list[int]:

        leisure_trip_days: list[int] = []

        return leisure_trip_days

    @staticmethod
    def draw_commuting_weekday_numbers(
        *,
        working_weeks: list[int],
        commuting_parameters: Box,
        random_generator: np.random.Generator,
        time_constants: TimeConstants,
    ) -> list[int]:

        commuting_weekday_numbers: list[int] = []

        return commuting_weekday_numbers

    @staticmethod
    def draw(
        *,
        activity_parameters: Box,
        random_generator: np.random.Generator,
        time_constants: TimeConstants,
    ) -> Activities:

        commuting_parameters: Box = activity_parameters.commuting
        holiday_parameters: Box = activity_parameters.holiday
        weekend_parameters: Box = activity_parameters.weekend
        leisure_parameters: Box = activity_parameters.leisure

        holiday_trip_week_numbers, working_weeks = (
            Activities.draw_holiday_trip_week_numbers(
                holiday_parameters=holiday_parameters,
                commuting_parameters=commuting_parameters,
                random_generator=random_generator,
                time_constants=time_constants,
            )
        )

        weekend_trip_week_numbers: list[int] = (
            Activities.draw_weekend_trip_week_numbers(
                holiday_trip_week_numbers=holiday_trip_week_numbers,
                weekend_parameters=weekend_parameters,
                random_generator=random_generator,
                time_constants=time_constants,
            )
        )
        leisure_trip_weekday_numbers: list[int] = (
            Activities.draw_leisure_trip_weekday_numbers(
                weekend_trip_week_numbers=weekend_trip_week_numbers,
                leisure_parameters=leisure_parameters,
                random_generator=random_generator,
                time_constants=time_constants,
            )
        )

        commuting_weekday_numbers: list[int] = (
            Activities.draw_commuting_weekday_numbers(
                working_weeks=working_weeks,
                commuting_parameters=commuting_parameters,
                random_generator=random_generator,
                time_constants=time_constants,
            )
        )

        return Activities(
            commuting_weekday_numbers=commuting_weekday_numbers,
            holiday_trip_week_numbers=holiday_trip_week_numbers,
            weekend_trip_week_numbers=weekend_trip_week_numbers,
            leisure_trip_weekday_numbers=leisure_trip_weekday_numbers,
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

        trips_parameters: Box = scenario.trips
        trips: dict[str, Trip] = {
            trip_name: Trip.draw(
                trip_parameters=trip_parameters,
                legs=legs,
                random_generator=random_generator,
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
                time_constants=time_constants,
            )

        charging_behaviour_parameters: Box = scenario.charging_behaviour
        charging_behaviour: ChargingBehaviour = ChargingBehaviour.draw(
            charging_behaviour_parameters=charging_behaviour_parameters,
            random_generator=random_generator,
        )
        return vehicle, locations, legs, trips, activities, charging_behaviour

    @staticmethod
    def get_run_trips(
        *,
        activities: Activities | None,
        trips: dict[str, Trip],
        time_ranges: TimeRange,
    ) -> pl.Series:
        '''
        Tells us which trip occurs on each day of our run.
        '''
        if activities is not None:
            run_trips: pl.Series = pl.Series(
                name='trip_name', values=[], dtype=pl.String
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
            activities=activities, trips=trips, time_ranges=time_ranges
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
