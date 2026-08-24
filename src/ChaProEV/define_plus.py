from dataclasses import dataclass
from box import Box
from ETS_CookBook import ETS_CookBook as cook
from rich import print
from pathlib import Path
import numpy as np
import polars as pl
from datetime import date, datetime, timedelta


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
            speed_kph=speed_kph
        )


@dataclass
class TimeRange:
    '''
    The time ranges we use (boith for dates and time stamps), both
    for computation and display
    '''

    run_dates: pl.Series | pl.Expr
    display_dates: pl.Series | pl.Expr
    run_stamps: pl.Series | pl.Expr
    display_stamps: pl.Series | pl.Expr

    @staticmethod
    def set_ranges(run_parameters: Box) -> TimeRange:
        start: Box = run_parameters.start
        end: Box = run_parameters.end
        display_start: Box = run_parameters.display_start
        display_end: Box = run_parameters.display_end
        run_frequency_settings: Box = run_parameters.frequency
        display_frequency_settings: Box = run_parameters.display_frequency

        run_frequency: str = (
            f'{run_frequency_settings.size}{run_frequency_settings.type}'
        )
        display_frequency: str = f'{display_frequency_settings.size}{display_frequency_settings.type}'  # noqa:E501

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

        run_dates: pl.Series | pl.Expr = pl.date_range(
            start=start_date,
            end=end_date,
            eager=True,
            closed='left',
        )
        display_dates: pl.Series | pl.Expr = pl.date_range(
            display_start_date,
            end=display_end_date,
            eager=True,
            closed='left',
        )
        run_stamps: pl.Series | pl.Expr = pl.datetime_range(
            start=start_datetime,
            end=end_datetime,
            interval=run_frequency,
            eager=True,
            closed='left',
        )
        display_stamps: pl.Series | pl.Expr = pl.datetime_range(
            start=display_start_datetime,
            end=display_end_datetime,
            interval=display_frequency,
            eager=True,
            closed='left',
        )

        return TimeRange(
            run_dates=run_dates,
            display_dates=display_dates,
            run_stamps=run_stamps,
            display_stamps=display_stamps,
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
        time_modulation_factors: list[
            float
        ] = location_parameters.time_modulation_factors
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
    def read_parameters(leg_parameters: Box) -> Leg:
        distance_km: float = leg_parameters.distance_km
        duration_hours: float = leg_parameters.duration_hours
        start_location: str = leg_parameters.start_location
        end_location: str = leg_parameters.end_location

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

    base: str
    trip_steps: list[TripStep]
    # start_time_hours: float
    # time_steps: pl.Series
    # location_names: pl.Series

    # Add BaseTransitions
    # start_base end_base distance duration

    # elsewhere: range of dates where it can occur and drawn (first, time at second)

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
    # plus transitions between bases  (so holiday outwrad anbd back are not trips
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
    ) -> float:
        start_time_hours: float = np.random.normal(
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
        driving_location_name: str,
    ) -> list[TripStep]:
        step_start_time: float = start_time_hours

        trip_steps: list[TripStep] = []
        for leg_name, parked_hours in zip(leg_names, time_between_legs_hours):
            leg_duration_hours: float = legs[leg_name].duration_hours
            leg_length_kilometers: float = legs[leg_name].distance_km
            driving_step: TripStep = TripStep.get_step(
                start_time_hours=step_start_time,
                duration_hours=leg_duration_hours,
                location_name=driving_location_name,
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

        if len(leg_names) > 0 :
            last_leg_name: str = leg_names[-1]
            # The last leg brings us to the base and does
            # not have a corrersponding parking time, by defintion
            print('[magenta] Document legs and parked times')
            last_step: TripStep = TripStep.get_step(
                start_time_hours=step_start_time,
                duration_hours=legs[last_leg_name].duration_hours,
                location_name=driving_location_name,
                leg_length_kilometers=legs[last_leg_name].distance_km,
            )

            trip_steps.append(last_step)
        return trip_steps

    @staticmethod
    def get_leg_info(trip_parameters: Box) -> tuple[list[str], list[float]]:
        leg_names: list[str] = trip_parameters.legs
        time_between_legs_hours: list[
            float
        ] = trip_parameters.time_between_legs_hours
        print('[magenta]Add repetitions stuff')

        return leg_names, time_between_legs_hours

    @staticmethod
    def define_user_trip(
        trip_parameters: Box, legs: dict[str, Leg], driving_location_name: str
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
        )
        base: str = trip_parameters.base

        leg_names, time_between_legs_hours = Trip.get_leg_info(
            trip_parameters=trip_parameters
        )

        trip_steps: list[TripStep] = Trip.get_steps(
            start_time_hours=start_time_hours,
            leg_names=leg_names,
            time_between_legs_hours=time_between_legs_hours,
            legs=legs,
            driving_location_name=driving_location_name,
        )

        return Trip(base=base, trip_steps=trip_steps)

    # Create Transition class (put holifday there)
    # Add leisure holiday trips
    # remove holiday trips
    # Add base locations (locations that have is_base=True)

    # Add Transitions first then trips (drwan per base adn day type in mobility)
    # add location per time unity (minute?)
    # set base location for all times and change them with trips
    # holiday chnages for the holiday duration in days
    # Get trip duration from parameters
    # Then have a series of trip moments (hours from midnight)
    # and series of location_names (of the same size)


if __name__ == '__main__':
    scenario_path: Path = Path('scenarios/plus/test.toml')
    scenario: Box = cook.parameters_from_TOML(scenario_path)
    driving_location_name: str = scenario.general.driving_location_name

    run_parameters: Box = scenario.run
    time_ranges: TimeRange = TimeRange.set_ranges(
        run_parameters=run_parameters
    )
    locations_definitions: Box = scenario.locations

    locations: dict[str, Location] = {
        location_name: Location.read_parameters(location_parameters)
        for location_name, location_parameters in locations_definitions.items()
    }

    base_locations: dict[str, Location] = {
        location_name: Location.read_parameters(location_parameters)
        for location_name, location_parameters in locations_definitions.items()
        if location_parameters.base
    }

    legs_definitions: Box = scenario.legs

    legs: dict[str, Leg] = {
        leg_name: Leg.read_parameters(leg_parameters)
        for leg_name, leg_parameters in legs_definitions.items()
    }
    trips_definitions: Box = scenario.trips
    user_trips: dict[str, Trip] = {
        trip_name: Trip.define_user_trip(
            trip_parameters=trip_parameters,
            legs=legs,
            driving_location_name=driving_location_name,
        )
        for trip_name, trip_parameters in trips_definitions.items()
    }
    base_trips: dict[str, dict[str, Trip]] = {}
    for base_name in base_locations.keys():
        base_trips[base_name] = {
            trip_name: trip
            for trip_name, trip in user_trips.items()
            if trip.base == base_name
        }
    print(base_trips)
    exit()
    print(locations)
    print(base_locations)
    exit()
    print(legs)
    print(user_trips)
    print('Draw trips for base pool  ')

# transitions are back an d foreth?

# @dataclass
# class Extrapolate:
#     do_run: bool
#     column_prefix: str
#     input_start_year: int
#     input_end_year: int
#     extrapolation_end_year: int
#     initial_guess_maximum: float
#     initial_guess_exponent_factor: float
#     initial_guess_midpoint: float
#     increase_proportion: bool
#     extra_increase_proportion: float
#     maxfev: int

#     @staticmethod
#     def read_parameters(extrapolation_settings: box.Box) -> Extrapolate:
#         do_run: bool = extrapolation_settings.do_run
#         column_prefix: str = extrapolation_settings.column_prefix
#         input_start_year: int = extrapolation_settings.input_start_year
#         input_end_year: int = extrapolation_settings.input_end_year
#         extrapolation_end_year: int = (
#             extrapolation_settings.extrapolation_end_year
#         )
#         initial_guess_maximum: float = (
#             extrapolation_settings.initial_guess_maximum
#         )
#         initial_guess_exponent_factor: float = (
#             extrapolation_settings.initial_guess_exponent_factor
#         )
#         initial_guess_midpoint: float = (
#             extrapolation_settings.initial_guess_midpoint
#         )
#         increase_proportion: bool = extrapolation_settings.increase_proportion
#         extra_increase_proportion: float = (
#             extrapolation_settings.extra_increase_proportion
#         )
#         maxfev: int = extrapolation_settings.maxfev

#         return Extrapolate(
#             do_run=do_run,
#             column_prefix=column_prefix,
#             input_start_year=input_start_year,
#             input_end_year=input_end_year,
#             extrapolation_end_year=extrapolation_end_year,
#             initial_guess_maximum=initial_guess_maximum,
#             initial_guess_exponent_factor=initial_guess_exponent_factor,
#             initial_guess_midpoint=initial_guess_midpoint,
#             increase_proportion=increase_proportion,
#             extra_increase_proportion=extra_increase_proportion,
#             maxfev=maxfev,
#         )
