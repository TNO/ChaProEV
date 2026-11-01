import pickle
import uuid
from dataclasses import dataclass

import numpy as np
from box import Box


@dataclass
class User:
    ID: uuid.UUID

    @staticmethod
    def create(
        *, scenario: Box, define_generator: np.random.Generator
    ) -> User:
        ID: uuid.UUID = uuid.uuid4()

        return User(ID=ID)


def create_users(
    *, scenario: Box, define_generator: np.random.Generator
) -> list[User]:

    users_settings: Box = scenario.users

    users_pool_size: int = users_settings.users_pool_size

    if users_pool_size < 1:
        raise ValueError(
            'You need at least one user '
            '(users_pool_size in [monte_carlo] in scenario toml)'
        )

    users_pool: list[User] = [
        User.create(scenario=scenario, define_generator=define_generator)
        for _ in range(users_pool_size)
    ]
    if users_settings.pickle_users_pool:
        pickle.dump(
            users_pool,
            open(f'users/{scenario.case_name}/{scenario.name}.pool', 'wb'),
        )

    return users_pool


def read_users_pool(*, scenario: Box) -> list[User]:

    users_pool: list[User] = pickle.load(
        open(f'users/{scenario.case_name}/{scenario.name}.pool', 'rb')
    )

    return users_pool


def get_users_pool(
    *, scenario: Box, define_generator: np.random.Generator
) -> list[User]:

    users_settings: Box = scenario.users

    if users_settings.read_from_file:
        users_pool: list[User] = read_users_pool(scenario=scenario)
    else:
        users_pool: list[User] = create_users(
            scenario=scenario, define_generator=define_generator
        )
    return users_pool
