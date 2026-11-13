from dataclasses import dataclass

import numpy as np

'''
Configuration and random-number generation for Monte Carlo simulations.
'''


@dataclass
class MonteCarlo:
    '''
    Parameters for running Monte Carlo simulations.

    Using a seed produces the same sequence of random draws between runs.
    This makes results reproducible and allows the effect of changing a
    model parameter to be examined while keeping the random draws unchanged.

    '''

    use_seed: bool
    seed: int


@dataclass
class RandomGenerators:
    '''
    Independent random-number generators for different parts of the model.

    The generators are spawned from a common seed sequence, allowing the
    random streams for definition, mobility, and charging to remain
    independent while keeping seeded runs reproducible.

    '''

    define: np.random.Generator
    mobility: np.random.Generator
    charging: np.random.Generator
    local_grid: np.random.Generator

    @classmethod
    def create_generators(cls, *, monte_carlo: MonteCarlo) -> RandomGenerators:
        '''
        Create independent random-number generators for a Monte Carlo run.

        If seeding is enabled, the generators are derived reproducibly from
        the configured seed. Otherwise, NumPy supplies non-deterministic
        entropy for the seed sequence.
        '''

        if monte_carlo.use_seed:
            run_seed: int | None = monte_carlo.seed
        else:
            run_seed = None

        seed_sequence: np.random.SeedSequence = np.random.SeedSequence(
            run_seed
        )

        (
            define_seed,
            mobility_seed,
            charging_seed,
            local_grid_seed,
        ) = seed_sequence.spawn(4)

        return cls(
            define=np.random.default_rng(seed=define_seed),
            mobility=np.random.default_rng(seed=mobility_seed),
            charging=np.random.default_rng(seed=charging_seed),
            local_grid=np.random.default_rng(seed=local_grid_seed)
        )


def draw_beta_value(
    *,
    minimum: float,
    typical: float,
    maximum: float,
    random_generator: np.random.Generator,
    shape: float,
) -> float:
    '''
    Draw a bounded value around a specified typical value.

    A symmetric beta distribution is used to determine the relative position
    of the draw. Values below the beta distribution's median are scaled to
    the interval from ``minimum`` to ``typical``, and values above it are
    scaled to the interval from ``typical`` to ``maximum``.

    The ``typical`` value is therefore a median of the resulting distribution.
    When ``minimum < typical < maximum``, half of the draws are below the
    typical value and half are above it.

    ``shape`` controls how strongly draws are concentrated around the typical
    value. Values greater than 1 produce a concentration around the typical
    value, a value of 1 produces a uniform beta draw, and values below 1
    increasingly favour the minimum and maximum.

    Note:
        The random draw is also performed when ``minimum == maximum``.
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
