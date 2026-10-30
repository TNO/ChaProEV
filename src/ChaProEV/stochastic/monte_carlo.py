from dataclasses import dataclass

import numpy as np
from box import Box

'''
Monte Carlo
'''


@dataclass
class MonteCarlo:
    use_seed: bool
    seed: int
    iterations: int


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
