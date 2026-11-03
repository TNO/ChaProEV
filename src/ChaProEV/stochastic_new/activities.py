from dataclasses import dataclass

import numpy as np
from box import Box

from ChaProEV.stochastic_new.monte_carlo import draw_beta_value
from ChaProEV.stochastic_new.time import TimeConstants


@dataclass
class Activities:
    '''
    Tells us in which week or day number activities (commute,
    holiday trips, weekend trips, leisure trips) occur.
    Commuting and leisure activities use weekday numbers.
    Commuting weeks, weekend trips and holiday trips use week numbers.
    For commuting, we look at weekday numbers (1= Monday, 7= Sunday).
    '''

    commuting_weekday_numbers: list[int]
    holiday_trip_week_numbers: list[int]
    holiday_trip_week_before_numbers: list[int]
    weekend_trip_week_numbers: list[int]
    leisure_trip_weekday_numbers: list[int]
    commuting_week_numbers: list[int]
    weekday_occurrences_holiday_trips_outward: list[int]
    weekday_occurrences_holiday_trips_back: list[int]
    weekday_occurrences_weekend_trips: list[int]

    @staticmethod
    def draw_commuting_weekday_numbers(
        *,
        commuting_parameters: Box,
        random_generator: np.random.Generator,
    ) -> list[int]:

        work_days_parameters: Box = commuting_parameters.work_days

        possible_working_days: list[int] = list(
            map(int, work_days_parameters.keys())
        )
        possible_working_day_probabilities: list[float] = [
            work_days_parameters[str(day_amount)].probability
            for day_amount in possible_working_days
        ]
        if not np.isclose(sum(possible_working_day_probabilities), 1.0):
            raise ValueError(
                f'{possible_working_day_probabilities=} must add up to 1.0.'
            )

        worked_days_per_work_week: int = int(
            random_generator.choice(
                possible_working_days, p=possible_working_day_probabilities
            )
        )
        possible_amounts_commute_days: list[int] = work_days_parameters[
            str(worked_days_per_work_week)
        ].possible_amounts_commute_days
        if any(amount < 0 for amount in possible_amounts_commute_days):
            raise ValueError(
                f'All of {possible_amounts_commute_days=} ' 'must be >= zero.'
            )
        commute_days_probabilities: list[float] = work_days_parameters[
            str(worked_days_per_work_week)
        ].commute_days_probabilities
        if not np.isclose(sum(commute_days_probabilities), 1.0):
            raise ValueError(
                f'{commute_days_probabilities=} must add up to 1.0.'
            )
        if len(possible_amounts_commute_days) != len(
            commute_days_probabilities
        ):
            raise ValueError(
                f'{possible_amounts_commute_days=} and '
                f'{commute_days_probabilities=} '
                'must be of the same length'
            )
        commute_days_per_week: int = int(
            random_generator.choice(
                possible_amounts_commute_days,
                p=commute_days_probabilities,
            )
        )

        commute_days_indices: list[int] = (
            commuting_parameters.commute_days_indices
        )
        if len(commute_days_indices) != len(set(commute_days_indices)):
            raise ValueError(
                f'{commute_days_indices=} contains duplicate weekday numbers.'
            )
        if any(
            day_number < 1 or day_number > 7
            for day_number in commute_days_indices
        ):
            raise ValueError(
                f'{commute_days_indices=} contains an invalid weekday number.'
            )
        weekday_commute_factor: list[float] = (
            commuting_parameters.weekday_commute_factor
        )
        if not np.isclose(sum(weekday_commute_factor), 1.0):
            raise ValueError(f'{weekday_commute_factor=} must add up to 1.0.')
        if len(commute_days_indices) != len(weekday_commute_factor):
            raise ValueError(
                f'{commute_days_indices=} and {weekday_commute_factor=} '
                'must be of the same length'
            )

        if commute_days_per_week > len(commute_days_indices):
            raise ValueError(
                f'{commute_days_per_week=} exceeds the number of available '
                f'commute weekdays: {len(commute_days_indices)}.'
            )

        commuting_weekday_numbers: list[int] = sorted(
            int(day_number)
            for day_number in random_generator.choice(
                commute_days_indices,
                size=commute_days_per_week,
                p=weekday_commute_factor,
                replace=False,
            )
        )

        return commuting_weekday_numbers

    @staticmethod
    def draw_holiday_trip_week_numbers(
        *,
        holiday_parameters: Box,
        random_generator: np.random.Generator,
        time_constants: TimeConstants,
    ) -> tuple[list[int], list[int], list[int]]:

        week_indices: list[int] = list(
            range(
                time_constants.first_week_index,
                time_constants.last_week_index,
                # The last week (53 is only a day or two long)
            )
        )

        possible_amount_of_non_working_weeks: list[int] = (
            holiday_parameters.possible_amount_of_non_working_weeks
        )
        if any(amount < 0 for amount in possible_amount_of_non_working_weeks):
            raise ValueError(
                f'All of {possible_amount_of_non_working_weeks=} '
                'must be >= zero.'
            )
        probabilities_for_amount_of_non_working_weeks: list[float] = (
            holiday_parameters.probabilities_for_amount_of_non_working_weeks
        )
        if len(possible_amount_of_non_working_weeks) != len(
            probabilities_for_amount_of_non_working_weeks
        ):
            raise ValueError(
                f'{possible_amount_of_non_working_weeks=} and '
                f'{probabilities_for_amount_of_non_working_weeks=} '
                'must be of the same length.'
            )

        if not np.isclose(
            sum(probabilities_for_amount_of_non_working_weeks),
            1.0,
        ):
            raise ValueError(
                f'The sum of {probabilities_for_amount_of_non_working_weeks=} '
                ' be 1.0'
            )

        amount_of_non_working_weeks: int = int(
            random_generator.choice(
                possible_amount_of_non_working_weeks,
                p=probabilities_for_amount_of_non_working_weeks,
            )
        )
        if not 0 <= amount_of_non_working_weeks <= len(week_indices):
            raise ValueError(
                f'{amount_of_non_working_weeks=} must be between 0 and '
                f'{len(week_indices)}.'
            )
        amount_of_working_weeks: int = int(
            len(week_indices) - amount_of_non_working_weeks
        )

        increase_factor_working_in_work_week: float = (
            holiday_parameters.increase_factor_working_in_work_week
        )
        if increase_factor_working_in_work_week <= 0:
            raise ValueError(
                f'{increase_factor_working_in_work_week=} '
                'must be greater than zero.'
            )
        work_probabilities_per_week: list[float] = [
            (
                increase_factor_working_in_work_week
                if week_index not in time_constants.holiday_weeks
                else 1.0
            )
            for week_index in week_indices
        ]
        normalisation_factor_work: float = sum(work_probabilities_per_week)
        work_probabilities_per_week: list[float] = [
            probability / normalisation_factor_work
            for probability in work_probabilities_per_week
        ]

        commuting_week_numbers: list[int] = sorted(
            int(week_number)
            for week_number in random_generator.choice(
                week_indices,
                size=amount_of_working_weeks,
                p=work_probabilities_per_week,
                replace=False,
            )
        )

        non_working_week_indices: list[int] = sorted(
            [
                week_index
                for week_index in week_indices
                if week_index not in commuting_week_numbers
            ]
        )

        possible_amounts_of_holiday_trips: list[int] = (
            holiday_parameters.possible_amounts_of_holiday_trips
        )
        if any(amount < 0 for amount in possible_amounts_of_holiday_trips):
            raise ValueError(
                f'All of {possible_amounts_of_holiday_trips=} '
                'must be >= zero.'
            )
        holiday_trips_probabilities: list[float] = (
            holiday_parameters.holiday_trips_probabilities
        )
        if len(possible_amounts_of_holiday_trips) != len(
            holiday_trips_probabilities
        ):
            raise ValueError(
                f'{possible_amounts_of_holiday_trips=} and '
                f'{holiday_trips_probabilities=} must have the same length.'
            )

        if not np.isclose(sum(holiday_trips_probabilities), 1.0):
            raise ValueError(
                f'The sum of {holiday_trips_probabilities=} must be one.'
            )

        amount_of_holiday_trips_taken: int = int(
            random_generator.choice(
                possible_amounts_of_holiday_trips,
                p=holiday_trips_probabilities,
            )
        )

        if amount_of_holiday_trips_taken > len(non_working_week_indices):
            raise ValueError(
                f'{amount_of_holiday_trips_taken=} exceeds the number of '
                f'available non-working weeks: '
                f'{len(non_working_week_indices)}.'
            )

        if amount_of_holiday_trips_taken == 0:
            holiday_trip_week_numbers: list[int] = []
        else:
            increase_factor_holiday_trip_in_holiday_weeks: float = (
                holiday_parameters.increase_factor_holiday_trip_in_holiday_weeks  # noqa: E501
            )
            if increase_factor_holiday_trip_in_holiday_weeks <= 0:
                raise ValueError(
                    f'{increase_factor_holiday_trip_in_holiday_weeks=} '
                    'must be greater than zero.'
                )

            holiday_trips_probabilities_per_week: list[float] = [
                (
                    0.0
                    if week_index == time_constants.first_week_index
                    # We want to avoid holiday trips in the first week
                    # of the year, as the journey outward might be in the
                    # year before.
                    else (
                        increase_factor_holiday_trip_in_holiday_weeks
                        if week_index in time_constants.holiday_weeks
                        else 1.0
                    )
                )
                for week_index in non_working_week_indices
            ]
            normalisation_factor_holiday_trip: float = sum(
                holiday_trips_probabilities_per_week
            )
            holiday_trips_probabilities_per_week: list[float] = [
                probability / normalisation_factor_holiday_trip
                for probability in holiday_trips_probabilities_per_week
            ]

            holiday_trip_week_numbers: list[int] = sorted(
                int(week_number)
                for week_number in random_generator.choice(
                    non_working_week_indices,
                    size=amount_of_holiday_trips_taken,
                    p=holiday_trips_probabilities_per_week,
                    replace=False,
                )
            )

        return (
            holiday_trip_week_numbers,
            commuting_week_numbers,
            week_indices,
        )

    @staticmethod
    def draw_weekend_trip_week_numbers(
        *,
        holiday_trip_week_numbers: list[int],
        weekend_parameters: Box,
        random_generator: np.random.Generator,
        beta_shape: float,
        week_indices: list[int],
    ) -> tuple[list[int], list[int]]:

        amounts_of_weekend_trips_min: float = (
            weekend_parameters.amounts_of_weekend_trips_min
        )
        amounts_of_weekend_trips_typical: float = (
            weekend_parameters.amounts_of_weekend_trips_typical
        )
        amounts_of_weekend_trips_max: float = (
            weekend_parameters.amounts_of_weekend_trips_max
        )

        if amounts_of_weekend_trips_min < 0:
            raise ValueError(f'{amounts_of_weekend_trips_min=} must be >=0.')

        amounts_of_weekend_trips: int = round(
            draw_beta_value(
                minimum=amounts_of_weekend_trips_min,
                typical=amounts_of_weekend_trips_typical,
                maximum=amounts_of_weekend_trips_max,
                random_generator=random_generator,
                shape=beta_shape,
            )
        )
        holiday_trip_week_before_numbers: list[int] = [
            week_number - 1 for week_number in holiday_trip_week_numbers
        ]
        weeks_without_a_weekend_trip: list[int] = sorted(
            list(
                set(
                    holiday_trip_week_numbers
                    + holiday_trip_week_before_numbers
                )
            )
        )
        if amounts_of_weekend_trips > (
            len(week_indices) - len(weeks_without_a_weekend_trip)
        ):
            raise ValueError(
                f'There are not enough weeks for {amounts_of_weekend_trips=}.'
                f'You either have too many of these, of too many '
                f'{holiday_trip_week_numbers=}.'
            )
        possible_weekend_trip_week_numbers: list[int] = [
            week_number
            for week_number in week_indices
            if week_number not in weeks_without_a_weekend_trip
        ]

        weekend_trip_week_numbers: list[int] = sorted(
            int(week_number)
            for week_number in random_generator.choice(
                possible_weekend_trip_week_numbers,
                size=amounts_of_weekend_trips,
                replace=False,
            )
        )

        return weekend_trip_week_numbers, holiday_trip_week_before_numbers

    @staticmethod
    def draw_leisure_trip_weekday_numbers(
        *,
        leisure_parameters: Box,
        random_generator: np.random.Generator,
    ) -> list[int]:
        '''
        Draws on which week days leisure trips occur.
        Note that if there are two such trips on a weekend where either
        a holiday trip or a weekend trip occur, then one of the two leisure
        trips will be overwritten. Also note that if one leisure trip
        occurs on such a weekend, it takes precedence and forces the weekend
        trip or the holiday trip to be on the other weekend day.
        '''

        possible_amounts_leisure_trips: list[int] = (
            leisure_parameters.possible_amounts_leisure_trips
        )
        amount_probabilities: list[float] = (
            leisure_parameters.amount_probabilities
        )
        day_indices: list[int] = leisure_parameters.day_indices
        if any(day_index < 1 or day_index > 7 for day_index in day_indices):
            raise ValueError(
                f'{day_indices=} contains an invalid weekday number.'
            )
        if len(day_indices) != len(set(day_indices)):
            raise ValueError(
                f'{day_indices=} contains duplicate weekday numbers.'
            )

        day_weights: list[float] = leisure_parameters.day_weights
        if len(possible_amounts_leisure_trips) != len(amount_probabilities):
            raise ValueError(
                f'{possible_amounts_leisure_trips=} and '
                f'{amount_probabilities=} must have the same length.'
            )

        if len(day_indices) != len(day_weights):
            raise ValueError(
                f'{day_indices=} and {day_weights=} '
                'must have the same length.'
            )
        if any(
            probability < 0 for probability in amount_probabilities
        ) or not np.isclose(sum(amount_probabilities), 1.0):
            raise ValueError(
                f'{amount_probabilities=} must be >=0.0 and sum to 1.0'
            )
        if any(day_weight < 0 for day_weight in day_weights) or not np.isclose(
            sum(day_weights), 1.0
        ):
            raise ValueError(f'{day_weights=} must be >=0.0 and sum to 1.0')

        if any(amount < 0 for amount in possible_amounts_leisure_trips):
            raise ValueError(
                f'{possible_amounts_leisure_trips=} cannot contain '
                'negative values.'
            )

        amount_of_leisure_trips: int = int(
            random_generator.choice(
                possible_amounts_leisure_trips, p=amount_probabilities
            )
        )
        if amount_of_leisure_trips > len(day_indices):
            raise ValueError(
                f'{amount_of_leisure_trips=} exceeds the number of available '
                f'leisure weekdays: {len(day_indices)}.'
            )

        leisure_trip_weekday_numbers: list[int] = sorted(
            int(day_index)
            for day_index in random_generator.choice(
                day_indices,
                size=amount_of_leisure_trips,
                p=day_weights,
                replace=False,
            )
        )

        return leisure_trip_weekday_numbers

    @staticmethod
    def renormalisation_due_to_commute(
        *,
        day_indices: list[int],
        probabilities: list[float],
        commuting_weekday_numbers: list[int],
    ) -> tuple[list[int], list[float]]:

        cached_indices: list[int] = day_indices.copy()
        cached_probabilities: list[float] = probabilities.copy()

        day_indices = []
        probabilities = []

        for index, probability in zip(cached_indices, cached_probabilities):
            if index not in commuting_weekday_numbers:
                # Work commute takes precedence.
                # There is no need to overwrite as for leisure,
                # since there is no work in weekends (assumption)
                day_indices.append(index)
                probabilities.append(probability)

        if not day_indices:
            raise ValueError(
                'No weekday options remain after excluding commuting weekdays.'
                f' {commuting_weekday_numbers=}.'
            )

        normalisation_factor: float = sum(probabilities)

        if normalisation_factor <= 0:
            raise ValueError(
                'The remaining weekday probabilities must have a positive sum.'
            )
        # We need to normalise the probabilities
        probabilities = [
            probability / normalisation_factor for probability in probabilities
        ]

        return day_indices, probabilities

    @staticmethod
    def renormalisation_due_to_leisure(
        *,
        day_indices: list[int],
        probabilities: list[float],
        leisure_trip_weekday_numbers: list[int],
    ) -> tuple[list[int], list[float]]:

        if all(index in leisure_trip_weekday_numbers for index in day_indices):
            pass  # If all the remaining days are occupied by leisure trips,
            # we will have to overwrite one
        else:
            cached_indices = day_indices.copy()
            cached_probabilities = probabilities.copy()

            day_indices = []
            probabilities = []
            for index, probability in zip(
                cached_indices, cached_probabilities
            ):
                if index not in leisure_trip_weekday_numbers:
                    # Leisure takes precedence (if there is a possibility
                    # to have travel on another day)
                    day_indices.append(index)
                    probabilities.append(probability)

        if not day_indices:
            raise ValueError(
                'No weekday options remain after resolving activity conflicts.'
            )

        normalisation_factor: float = sum(probabilities)

        if normalisation_factor <= 0:
            raise ValueError(
                'The remaining weekday probabilities must have a positive sum.'
            )

        # We need to normalise the probabilities
        probabilities = [
            probability / normalisation_factor for probability in probabilities
        ]
        return day_indices, probabilities

    @staticmethod
    def renormalise_weekdays(
        day_indices: list[int],
        probabilities: list[float],
        commuting_weekday_numbers: list[int],
        leisure_trip_weekday_numbers: list[int],
    ) -> tuple[list[int], list[float]]:

        day_indices, probabilities = Activities.renormalisation_due_to_commute(
            day_indices=day_indices,
            probabilities=probabilities,
            commuting_weekday_numbers=commuting_weekday_numbers,
        )

        day_indices, probabilities = Activities.renormalisation_due_to_leisure(
            day_indices=day_indices,
            probabilities=probabilities,
            leisure_trip_weekday_numbers=leisure_trip_weekday_numbers,
        )

        return day_indices, probabilities

    @staticmethod
    def get_weekday_occurrences(
        *,
        occurrences: list[int],
        weekday_options: list[int],
        weekday_probabilities: list[float],
        commuting_weekday_numbers: list[int],
        leisure_trip_weekday_numbers: list[int],
        random_generator: np.random.Generator,
    ) -> list[int]:
        if not occurrences:
            return []

        if len(weekday_options) != len(weekday_probabilities):
            raise ValueError(
                f'{weekday_options=} and {weekday_probabilities=} '
                'must have the same length.'
            )

        if any(weekday < 1 or weekday > 7 for weekday in weekday_options):
            raise ValueError(
                f'{weekday_options=} contains an invalid weekday number.'
            )

        if len(weekday_options) != len(set(weekday_options)):
            raise ValueError(
                f'{weekday_options=} contains duplicate weekday numbers.'
            )

        if any(
            probability < 0 for probability in weekday_probabilities
        ) or not np.isclose(sum(weekday_probabilities), 1.0):
            raise ValueError(
                f'{weekday_probabilities=} must be non-negative '
                'and sum to 1.0.'
            )

        weekday_options, weekday_probabilities = (
            Activities.renormalise_weekdays(
                day_indices=weekday_options,
                probabilities=weekday_probabilities,
                commuting_weekday_numbers=commuting_weekday_numbers,
                leisure_trip_weekday_numbers=leisure_trip_weekday_numbers,
            )
        )
        weekday_occurrences: list[int] = [
            int(
                random_generator.choice(
                    weekday_options,
                    p=weekday_probabilities,
                )
            )
            for _ in occurrences
        ]

        return weekday_occurrences

    @staticmethod
    def draw(
        *,
        activity_parameters: Box,
        random_generator: np.random.Generator,
        beta_shape: float,
        time_constants: TimeConstants,
    ) -> Activities:

        commuting_parameters: Box = activity_parameters.commuting
        holiday_parameters: Box = activity_parameters.holiday
        weekend_parameters: Box = activity_parameters.weekend
        leisure_parameters: Box = activity_parameters.leisure

        commuting_weekday_numbers: list[int] = (
            Activities.draw_commuting_weekday_numbers(
                commuting_parameters=commuting_parameters,
                random_generator=random_generator,
            )
        )
        leisure_trip_weekday_numbers: list[int] = (
            Activities.draw_leisure_trip_weekday_numbers(
                leisure_parameters=leisure_parameters,
                random_generator=random_generator,
            )
        )

        (
            holiday_trip_week_numbers,
            commuting_week_numbers,
            week_indices,
        ) = Activities.draw_holiday_trip_week_numbers(
            holiday_parameters=holiday_parameters,
            random_generator=random_generator,
            time_constants=time_constants,
        )

        weekend_trip_week_numbers, holiday_trip_week_before_numbers = (
            Activities.draw_weekend_trip_week_numbers(
                holiday_trip_week_numbers=holiday_trip_week_numbers,
                weekend_parameters=weekend_parameters,
                random_generator=random_generator,
                beta_shape=beta_shape,
                week_indices=week_indices,
            )
        )
        weekday_occurrences_holiday_trips_outward: list[int] = (
            Activities.get_weekday_occurrences(
                occurrences=holiday_trip_week_before_numbers,
                weekday_options=(
                    holiday_parameters.possible_weekday_indices_outward
                ),
                weekday_probabilities=(
                    holiday_parameters.outward_day_probabilities
                ),
                commuting_weekday_numbers=commuting_weekday_numbers,
                leisure_trip_weekday_numbers=leisure_trip_weekday_numbers,
                random_generator=random_generator,
            )
        )

        weekday_occurrences_holiday_trips_back: list[int] = (
            Activities.get_weekday_occurrences(  # noqa:E501
                occurrences=holiday_trip_week_numbers,
                weekday_options=(
                    holiday_parameters.possible_weekday_indices_back
                ),
                weekday_probabilities=(
                    holiday_parameters.back_day_probabilities
                ),
                commuting_weekday_numbers=commuting_weekday_numbers,
                leisure_trip_weekday_numbers=leisure_trip_weekday_numbers,
                random_generator=random_generator,
            )
        )

        weekday_occurrences_weekend_trips: list[int] = (
            Activities.get_weekday_occurrences(  # noqa:E501
                occurrences=weekend_trip_week_numbers,
                weekday_options=(weekend_parameters.weekday_options),
                weekday_probabilities=(
                    weekend_parameters.weekday_probabilities
                ),
                commuting_weekday_numbers=commuting_weekday_numbers,
                leisure_trip_weekday_numbers=leisure_trip_weekday_numbers,
                random_generator=random_generator,
            )
        )

        return Activities(
            commuting_weekday_numbers=commuting_weekday_numbers,
            holiday_trip_week_numbers=holiday_trip_week_numbers,
            holiday_trip_week_before_numbers=holiday_trip_week_before_numbers,
            weekend_trip_week_numbers=weekend_trip_week_numbers,
            leisure_trip_weekday_numbers=leisure_trip_weekday_numbers,
            commuting_week_numbers=commuting_week_numbers,
            weekday_occurrences_holiday_trips_outward=(
                weekday_occurrences_holiday_trips_outward
            ),
            weekday_occurrences_holiday_trips_back=(
                weekday_occurrences_holiday_trips_back
            ),
            weekday_occurrences_weekend_trips=(
                weekday_occurrences_weekend_trips
            ),
        )
