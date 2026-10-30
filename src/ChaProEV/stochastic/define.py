from dataclasses import dataclass
from datetime import date, datetime

import numpy as np
import polars as pl
from box import Box
from rich import print


@dataclass
class ChargingBehaviour:
    adaptive: bool
    charge_desire_proportion_trigger: float

    @staticmethod
    def read_parameters(charging_parameters: Box) -> ChargingBehaviour:
        return ChargingBehaviour(
            adaptive=charging_parameters.adaptive,
            charge_desire_proportion_trigger=charging_parameters.charge_desire_proportion_trigger,  # noqa:E501
        )


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
    # We need to provide the number of holliday weeks seprately,
    # as counting the elements of the list above might not work, such as
    # when the above list contains weeks 1 and 53 (which just represent
    # the fact that years don't necessarily start and/or end at the start/end
    # of a week).x

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
            number_of_holiday_weeks=time_parameters.number_of_holiday_weeks,  # noqa:E501
        )


@dataclass
class ActivityParameters:

    worked_hours_per_work_week: float
    worked_hours_per_year: float
    worked_days_per_work_week: int
    worked_weeks_per_year: int
    worked_weeks: list[int]
    non_worked_weeks: list[int]
    commute_days_per_week: int
    commuting_days: list[int]
    holiday_trip_weeks: list[int]

    @staticmethod
    def set_activities(
        activity_definitions: Box,
        random_generator: np.random.Generator,
        time_constants: TimeConstants,
    ) -> ActivityParameters:

        week_indices: list[int] = list(
            range(
                time_constants.first_week_index,
                time_constants.last_week_index + 1,
            )
        )

        worked_hours_per_work_week_mean: float = (
            activity_definitions.worked_hours_per_work_week_mean
        )
        worked_hours_per_work_week_standard_deviation: float = (
            activity_definitions.worked_hours_per_work_week_standard_deviation
        )
        worked_hours_per_work_week: float = random_generator.normal(
            loc=worked_hours_per_work_week_mean,
            scale=worked_hours_per_work_week_standard_deviation,
        )
        worked_days_per_work_week: int = round(
            worked_hours_per_work_week
            / activity_definitions.work_day_duration_hours
        )
        worked_hours_per_year_mean: float = (
            activity_definitions.worked_hours_per_year_mean
        )
        worked_hours_per_year_standard_deviation: float = (
            activity_definitions.worked_hours_per_year_standard_deviation
        )
        worked_hours_per_year: float = random_generator.normal(
            loc=worked_hours_per_year_mean,
            scale=worked_hours_per_year_standard_deviation,
        )

        worked_weeks_per_year: int = round(
            worked_hours_per_year / worked_hours_per_work_week
        )

        non_worked_weeks: list[int] = sorted(
            list(
                random_generator.choice(
                    time_constants.holiday_weeks,
                    size=(len(week_indices) - worked_weeks_per_year),
                    replace=False,
                )
            )
        )
        worked_weeks: list[int] = [
            week_index
            for week_index in week_indices
            if week_index not in non_worked_weeks
        ]
        commute_to_work_ratio_mean: float = (
            activity_definitions.commute_to_work_ratio_mean
        )
        commute_to_work_ratio_standard_deviation: float = (
            activity_definitions.commute_to_work_ratio_standard_deviation
        )

        commute_to_work_ratio: float = random_generator.normal(
            loc=commute_to_work_ratio_mean,
            scale=commute_to_work_ratio_standard_deviation,
        )

        commute_days_per_week: int = round(
            commute_to_work_ratio * worked_days_per_work_week
        )

        commute_days_indices: list[int] = (
            activity_definitions.commute_days_indices
        )
        weekday_commute_factor: list[float] = (
            activity_definitions.weekday_commute_factor
        )

        commuting_days: list[int] = sorted(
            list(
                random_generator.choice(
                    commute_days_indices,
                    commute_days_per_week,
                    p=weekday_commute_factor,
                    replace=False,
                )
            )
        )

        possible_amounts_of_holiday_trips: list[int] = (
            activity_definitions.possible_amounts_of_holiday_trips
        )
        holiday_trips_probabilities: list[float] = (
            activity_definitions.holiday_trips_probabilities
        )
        amount_of_holiday_trips_taken: int = int(
            random_generator.choice(
                possible_amounts_of_holiday_trips,
                p=holiday_trips_probabilities,
            )
        )
        holiday_trip_weeks: list[int] = sorted(
            list(
                random_generator.choice(
                    non_worked_weeks,
                    size=amount_of_holiday_trips_taken,
                    replace=False,
                )
            )
        )

        # Draw holiday trip day in weekend before and weekend of

        # draw if leisure (weekday and weekend: for WE not in holiday weekends or before, as travel)
        # THEN draw weekend and override

        # Fro draw weekend: draw weekday indices (not in holiday weekends or before, as travel)


        # IF work and leisure --> draw between the two trip types

        work_day_duration_hours: float = (
            activity_definitions.work_day_duration_hours
        )
        worked_days_per_year: float = (
            worked_hours_per_year / work_day_duration_hours
        )
        number_of_holiday_weeks: int = time_constants.number_of_holiday_weeks
        WEEKS_IN_A_YEAR: float = time_constants.WEEKS_IN_A_YEAR
        working_week_days: int = time_constants.DAYS_IN_A_WEEK - len(
            time_constants.weekend_day_numbers
        )

        return ActivityParameters(
            worked_hours_per_work_week=worked_hours_per_work_week,
            worked_hours_per_year=worked_hours_per_year,
            worked_days_per_work_week=worked_days_per_work_week,
            worked_weeks_per_year=worked_weeks_per_year,
            worked_weeks=worked_weeks,
            non_worked_weeks=non_worked_weeks,
            commute_days_per_week=commute_days_per_week,
            commuting_days=commuting_days,
            holiday_trip_weeks=holiday_trip_weeks,
        )


@dataclass
class BaseTripProbabilities:
    '''
    An object to manage trip probabilities per day type.
    This also depends on the base we use
    '''

    base: str
    per_day_type: dict[str, dict[str, float]]


@dataclass
class Vehicle:
    name: str
    consumption_kWh_km: float
    battery_size_kWh: float
    has_one_trip_per_day_type: bool
    bases: list[str]
    driving_location_name: str


# def get_car_trip_probabilities_per_day_type(
#     base: str, activity_parameters: ActivityParameters
# ) -> dict[str, dict[str, float]]:
#     trip_probabilities_per_day_type: dict[str, dict[str, float]] = {}
#     # print('[magenta] Implement this!')
#     trip_probabilities_per_day_type['weekday_in_work_week'] = {}
#     trip_probabilities_per_day_type['weekday_in_work_week'][
#         'commute_to_work'
#     ] = 0.6
#     trip_probabilities_per_day_type['weekday_in_work_week'][
#         'commute_to_work_and_leisure'
#     ] = 0.2
#     trip_probabilities_per_day_type['weekday_in_work_week'][
#         'leisure_only'
#     ] = 0.15
#     trip_probabilities_per_day_type['weekday_in_work_week']['weekend_trip'] = 0
#     trip_probabilities_per_day_type['weekday_in_work_week'][
#         'stay_put_home'
#     ] = 0.05
#     trip_probabilities_per_day_type['weekend_in_work_week'] = {}
#     trip_probabilities_per_day_type['weekend_in_work_week'][
#         'commute_to_work'
#     ] = 0
#     trip_probabilities_per_day_type['weekend_in_work_week'][
#         'commute_to_work_and_leisure'
#     ] = 0
#     trip_probabilities_per_day_type['weekend_in_work_week'][
#         'leisure_only'
#     ] = 0.5
#     trip_probabilities_per_day_type['weekend_in_work_week'][
#         'weekend_trip'
#     ] = 0.125
#     trip_probabilities_per_day_type['weekend_in_work_week'][
#         'stay_put_home'
#     ] = 0.375
#     trip_probabilities_per_day_type['weekday_in_holiday_week'] = {}
#     trip_probabilities_per_day_type['weekday_in_holiday_week'][
#         'commute_to_work'
#     ] = 0.3
#     trip_probabilities_per_day_type['weekday_in_holiday_week'][
#         'commute_to_work_and_leisure'
#     ] = 0.1
#     trip_probabilities_per_day_type['weekday_in_holiday_week'][
#         'leisure_only'
#     ] = 0.3
#     trip_probabilities_per_day_type['weekday_in_holiday_week'][
#         'weekend_trip'
#     ] = 0
#     trip_probabilities_per_day_type['weekday_in_holiday_week'][
#         'stay_put_home'
#     ] = 0.3
#     trip_probabilities_per_day_type['weekend_in_holiday_week'] = {}
#     trip_probabilities_per_day_type['weekend_in_holiday_week'][
#         'commute_to_work'
#     ] = 0
#     trip_probabilities_per_day_type['weekend_in_holiday_week'][
#         'commute_to_work_and_leisure'
#     ] = 0
#     trip_probabilities_per_day_type['weekend_in_holiday_week'][
#         'leisure_only'
#     ] = 0.5
#     trip_probabilities_per_day_type['weekend_in_holiday_week'][
#         'weekend_trip'
#     ] = 0.125
#     trip_probabilities_per_day_type['weekend_in_holiday_week'][
#         'stay_put_home'
#     ] = 0.375
#     return trip_probabilities_per_day_type


# def get_trip_probabilities(
#     activity_parameters: ActivityParameters,
#     random_generator: np.random.Generator,
# ) -> dict[str, BaseTripProbabilities]:

#     trip_probabilities: dict[str, BaseTripProbabilities] = {}

#     base = 'home'
#     base = 'holiday'
#     # relevant  day types

#     # holiday trip can be in week-end and such,
#     # so still prob for leisure from holiday in work weekend
#     # draw going to work, going to leisure per day type

#     # We first get the base

#     # 1) Set start bases (with transitions)
#     # 2) Keep track of dates with transitions
#     # 3) Iterate through dates. If not in kept_track --> draw (based on base) otherwise, use transition

#     # def draw_trip(date: date, base: base, activity_parameters: ActivityParameters) -> str

#     # Compute amount_of_non_working_weeks
#     # Draw this amount in holiday weeks : In these, there is no going o work.
#     # Draw possible holiday trips in these weeks. choose([0, 1, 2, ...], p=[.....])
#     # The transition needs to be in one of these

#     # THe rest have the same prob of going to work.

#     # Add a home working factor? Higher on some days of the week?
#     # Draw N non-working weeks in holiday weeks (based on yeralu work). There gong_to_work is always false

#     # Base transitions --> changes base, but also sets trip and bans others from settin trip
#     # is BaseTripProbabilities still needed if we draw stuff?
#     # DO IT IN FUNC Thta selcts trip per day, not as prob!
#     # Do go to work
#     # Do go to leisure

#     # goo = random_generator.choice([True, False], p=[0.43, 0.57])
#     # print(goo)
#     # goo = random_generator.choice([True, False], p=[0.43, 0.57])
#     # print(goo)
#     exit()

#     transition_dates: list[date] = []
#     transition_trips: dict[date, str] = {}

#     # We then compute the trip probabilities per base
#     return trip_probabilities


@dataclass
class TripStep:
    '''
    Steps in a trip. Contains travel legs and parked moments
    '''

    start_hour: float  # In hourts from midnight
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
class TimeRange:
    '''
    The time ranges we use (boith for dates and time stamps), both
    for computation and display
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
        display_start: Box = run_parameters.display_start
        display_end: Box = run_parameters.display_end
        run_frequency_settings: Box = run_parameters.frequency
        display_frequency_settings: Box = run_parameters.display_frequency

        run_frequency: str = (
            f'{run_frequency_settings.size}{run_frequency_settings.type}'
        )
        display_frequency: str = (
            f'{display_frequency_settings.size}{display_frequency_settings.type}'  # noqa:E501
        )

        start_date: date = date(
            year=start.year, month=start.month, day=start.day
        )
        end_date: date = date(year=end.year, month=end.month, day=end.day)
        display_start_date: date = date(
            year=display_start.year,
            month=display_start.month,
            day=display_start.day,
        )
        display_end_date: date = date(
            year=display_end.year, month=display_end.month, day=display_end.day
        )

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

        run_dates: pl.Series = pl.date_range(
            start=start_date,
            end=end_date,
            eager=True,
            closed='left',
        )
        display_dates: pl.Series = pl.date_range(
            display_start_date,
            end=display_end_date,
            eager=True,
            closed='left',
        )
        run_stamps: pl.Series = pl.datetime_range(
            start=start_datetime,
            end=end_datetime,
            interval=run_frequency,
            eager=True,
            closed='left',
        )
        display_stamps: pl.Series = pl.datetime_range(
            start=display_start_datetime,
            end=display_end_datetime,
            interval=display_frequency,
            eager=True,
            closed='left',
        )

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
    def read_parameters(location_parameters: Box) -> Location:
        base: bool = location_parameters.base
        connectivity: float = location_parameters.connectivity
        charging_power_kW: float = location_parameters.charging_power_kW
        charger_efficiency: float = location_parameters.charger_efficiency
        discharge_power_kW: float = location_parameters.discharge_power_kW
        proportion_of_discharge_to_network: float = (
            location_parameters.proportion_of_discharge_to_network
        )
        time_modulation_factors: list[float] = (
            location_parameters.time_modulation_factors
        )
        latitude: float = location_parameters.latitude
        longitude: float = location_parameters.longitude
        charging_price_eur_kWh: float = (
            location_parameters.charging_price_eur_kWh
        )
        charging_desirability: float = (
            location_parameters.charging_desirability
        )
        return Location(
            base=base,
            connectivity=connectivity,
            charging_power_kW=charging_power_kW,
            charger_efficiency=charger_efficiency,
            discharge_power_kW=discharge_power_kW,
            proportion_of_discharge_to_network=proportion_of_discharge_to_network,  # noqa:E501
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
    Draws leg distances and speeds (and gives distances and durations)
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
        speed_kph: float = random_generator.normal(
            loc=mean_speed_kph,
            scale=standard_deviation_speed,
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
class Trip:
    '''
    This class defines the trips and their properties, from a scenario
    file that contains a list of instances and their properties.
    Trips are collections of legs that take place on a given day.
    It contains two series. One for the time steps (in hours from midnight
    for the day of the trip) and one for the location names where the vehicle
    is (including 'driving').
    '''

    start_base: str
    end_base: str
    base_transition: bool
    trip_steps: list[TripStep]
    # start_time_hours: float
    # time_steps: pl.Series
    # location_names: pl.Series

    # Add BaseTransitions
    # start_base end_base distance duration

    # elsewhere: range of dates where it can occur and drawn
    # (first, time at second)

    # round things to the time resolution
    # Add repetitions thing (maybe with a function placeholder first!)
    # first create a list of legs (leg_names)
    # a list of time between legs
    # and a list of driving start_time_hours

    # holiday trip flips home --> holiday (and adds 'driving' at start and end)
    # AdD holiday to leisure

    # Maybe organise it per base.
    # Each base has a list of trips

    # First do for first base for whole year

    # Then redo for times at each further base (for less time),
    # Need to set dates at each base
    # and draw trips fir these dates
    # plus transitions between bases
    # (so holiday outwrad anbd back are not trips
    # but transitions
    # )

    # draw moments when at other base or something?

    # strt with lists and then convert to Series (or keep list?)

    # location_names  append leg_duration X 'driving'
    # location_names append time_between X end_location of previous Leg

    # lesiure during holiday? (but then exclude work and weekend)

    # this gives the trip duration
    # then time series and location series

    # @staticmethod
    # def get_trip_duration_hours(
    #     legs: list[str], time_between_legs_hours: float,
    #     repeated_sequence: list[str],
    #     repetition_amounts: int,

    # ) -> float:
    #     return trip_duration_hours

    @staticmethod
    def get_start_time_hours(
        *,
        start_time_hours_mean: float,
        start_time_hours_standard_deviation: float,
        random_generator: np.random.Generator,
    ) -> float:
        start_time_hours: float = random_generator.normal(
            loc=start_time_hours_mean,
            scale=start_time_hours_standard_deviation,
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

        trip_steps: list[TripStep] = []
        for leg_name, parked_hours in zip(leg_names, time_between_legs_hours):
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
            # not have a corrersponding parking time, by defintion
            # print('[magenta] Document legs and parked times')
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
        # print('[magenta]Add repetitions stuff')

        return leg_names, time_between_legs_hours

    @staticmethod
    def define_user_trip(
        trip_parameters: Box,
        legs: dict[str, Leg],
        random_generator: np.random.Generator,
        vehicle: Vehicle,
    ) -> Trip:
        '''
        Creates a trip version for the user. It creates a vesion of the trip
        for a user by drawing a start time.
        '''
        start_time_hours_mean: float = trip_parameters.start_time_hours_mean
        start_time_hours_standard_deviation: float = (
            trip_parameters.start_time_hours_standard_deviation
        )
        start_time_hours: float = Trip.get_start_time_hours(
            start_time_hours_mean=start_time_hours_mean,
            start_time_hours_standard_deviation=start_time_hours_standard_deviation,  # noqa: E501
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

        return Trip(
            start_base=start_base,
            end_base=end_base,
            base_transition=base_transition,
            trip_steps=trip_steps,
        )

    # Create Transition class (put holifday there)
    # Add leisure holiday trips
    # remove holiday trips
    # Add base locations (locations that have is_base=True)

    # Add Transitions first then trips (drwan per base
    # adn day type in mobility)
    # add location per time unity (minute?)
    # set base location for all times and change them with trips
    # holiday chnages for the holiday duration in days
    # Get trip duration from parameters
    # Then have a series of trip moments (hours from midnight)
    # and series of location_names (of the same size)


def define_user(scenario: Box, random_generator: np.random.Generator) -> tuple[
    ChargingBehaviour,
    Vehicle,
    TimeRange,
    pl.Series,
    dict[str, dict[str, Trip]],
    dict[str, Location],
    ActivityParameters,
    TimeConstants,
]:
    charging_behaviour: ChargingBehaviour = ChargingBehaviour.read_parameters(
        scenario.charging
    )
    time_constants: TimeConstants = TimeConstants.read_parameters(
        scenario.time
    )

    run_parameters: Box = scenario.run
    time_ranges: TimeRange = TimeRange.set_ranges(
        run_parameters=run_parameters,
        time_constants=time_constants,
    )
    locations_definitions: Box = scenario.locations

    locations: dict[str, Location] = {
        location_name: Location.read_parameters(location_parameters)
        for location_name, location_parameters in locations_definitions.items()
    }

    bases: list[str] = [
        location_name
        for location_name, location_parameters in locations_definitions.items()
        if location_parameters.base
    ]

    vehicle_definition: Box = scenario.vehicle
    vehicle: Vehicle = Vehicle(
        name=vehicle_definition.name,
        consumption_kWh_km=vehicle_definition.consumption_kWh_km,
        battery_size_kWh=vehicle_definition.battery_size_kWh,
        has_one_trip_per_day_type=vehicle_definition.has_one_trip_per_day_type,
        bases=bases,
        driving_location_name=vehicle_definition.driving_location_name,
    )

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
    trips_definitions: Box = scenario.trips
    user_trips: dict[str, Trip] = {
        trip_name: Trip.define_user_trip(
            trip_parameters=trip_parameters,
            legs=legs,
            random_generator=random_generator,
            vehicle=vehicle,
        )
        for trip_name, trip_parameters in trips_definitions.items()
    }

    # START BASE

    # and end base?
    # or add transition bool to Trip

    # or have transition = (start_base==end_base) M

    base_trips: dict[str, dict[str, Trip]] = {}
    for base in bases:
        base_trips[base] = {
            trip_name: trip
            for trip_name, trip in user_trips.items()
            if (trip.start_base == base) and not trip.base_transition
        }
    print(user_trips)
    print(base_trips)

    if vehicle.has_one_trip_per_day_type:
        possible_day_types: set[str] = set(time_ranges.day_types.unique())
        trip_names: set[str] = set(user_trips.keys())

        if possible_day_types == trip_names:
            run_trips: pl.Series = time_ranges.day_types
            # Trips and day types have the same names, by convention
        else:
            raise ValueError(
                'If you only have one trip per day type, then the'
                'names of the trips and the names of day types have'
                'to bethe same.'
                f'{possible_day_types=}'
                f'{trip_names=}'
            )

    else:
        activity_definitions: Box = scenario.activity_parameters
        activity_parameters: ActivityParameters = (
            ActivityParameters.set_activities(
                activity_definitions=activity_definitions,
                random_generator=random_generator,
                time_constants=time_constants,
            )
        )
        print(activity_parameters)
        exit()
        trip_probabilities: dict[str, BaseTripProbabilities] = (
            get_trip_probabilities(
                activity_parameters=activity_parameters,
                random_generator=random_generator,
            )
        )
        trip_list: list[str] = []
    exit()
    print(run_trips)

    # Make a DF with time_ranges.day_types, is_transition
    exit()
    # first draw tarnsitions so that we know what base is.

    # base trip trip_probabilities are YES/YES, etc.

    trip_probabilities_per_day_type: dict[str, dict[str, float]] = (
        get_trip_probabilities_per_day_type(
            vehicle=vehicle,
            activity_parameters=scenario.time,
        )
    )
    # run trips now and after algorithm adjustment
    run_trips: pl.Series = pl.Series(
        'trip',
        [
            random_generator.choice(
                list(trip_probabilities_per_day_type[day_type].keys()),
                p=list(trip_probabilities_per_day_type[day_type].values()),
            )
            for day_type in time_ranges.day_types
        ],
    )
    print(run_trips)
    exit()
    return (
        charging_behaviour,
        vehicle,
        time_ranges,
        run_trips,
        base_trips,
        locations,
        activity_parameters,
        time_constants,
    )


# IF transition (drawen with given prob) Then redo trip prob only for that
# With there and bck set butmaybe do later
