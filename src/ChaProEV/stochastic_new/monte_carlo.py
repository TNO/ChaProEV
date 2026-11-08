from dataclasses import dataclass

import numpy as np


@dataclass
class MonteCarlo:
    use_seed: bool
    seed: int


@dataclass
class RandomGenerators:
    define: np.random.Generator
    mobility: np.random.Generator
    charging: np.random.Generator

    @staticmethod
    def create_generators(monte_carlo: MonteCarlo) -> RandomGenerators:

        if monte_carlo.use_seed:
            run_seed: int | None = monte_carlo.seed
        else:
            run_seed = None

        seed_sequence: np.random.SeedSequence = np.random.SeedSequence(
            run_seed
        )

        define_seed, mobility_seed, charging_seed = seed_sequence.spawn(3)

        return RandomGenerators(
            define=np.random.default_rng(seed=define_seed),
            mobility=np.random.default_rng(seed=mobility_seed),
            charging=np.random.default_rng(seed=charging_seed),
        )


def draw_beta_value(
    *,
    minimum: float,
    typical: float,
    # The central value: half of the draws are below it and half are above it.
    maximum: float,
    random_generator: np.random.Generator,
    shape: float,
) -> float:
    '''
    Draws a bounded value using a symmetric beta distribution.

    The typical value is the median: half of the draws are below it
    and half are above it.
    Note:
    Therandom draw is also performed when ``minimum == maximum``.
    Skipping it would shift the random-number stream and could change
    subsequent results that should not depend on this parameter.
    '''
    if shape <= 0:
        raise ValueError(f'{shape=} must be greater than zero.')
    if not minimum <= typical <= maximum:
        raise ValueError(
            f'You need to have {minimum=} <= {typical=} <= {maximum}.'
        )
    draw: float = random_generator.beta(a=shape, b=shape)

    if draw <= 0.5:
        return minimum + 2 * (draw * (typical - minimum))
    else:
        return typical + 2 * (draw - 0.5) * (maximum - typical)
