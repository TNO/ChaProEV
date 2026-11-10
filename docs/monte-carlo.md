# Monte Carlo simulations

The model uses Monte Carlo simulation to represent variation in model inputs and behaviour. Instead of assigning every modelled user or process the same fixed values, selected parameters can be drawn from probability distributions.

The Monte Carlo configuration determines whether these random draws are reproducible. Separate random-number generators are used for different parts of the model, while bounded beta distributions can be used to draw values around specified typical values.

## Monte Carlo configuration

The `MonteCarlo` class contains the configuration used to initialise the random-number generation for a model run. It contains two parameters:

- `use_seed` determines whether the model uses a fixed seed.
- `seed` specifies the fixed seed used when seeding is enabled.

When `use_seed` is `True`, the configured seed produces the same sequence of random draws each time the model is run. Provided that the rest of the model is deterministic, this makes the complete model run reproducible.

Reproducible random draws make it possible to compare model configurations without introducing unrelated differences in random sampling. For example, the effect of changing a charging parameter can be examined while retaining the same randomly generated characteristics and mobility behaviour.

When `use_seed` is `False`, the configured value of `seed` is not used. NumPy then supplies non-deterministic entropy to initialise the seed sequence. Repeated model runs can consequently produce different sequences of random draws.

## Independent random-number generators

The `RandomGenerators` class contains separate NumPy random-number generators for different parts of the model:

- `define` is used when defining model inputs and characteristics.
- `mobility` is used for random processes related to mobility.
- `charging` is used for random processes related to vehicle charging.
- `transformers` is used for random processes related to transformers and power lines
= `households`  is used for randome processes related to household consumption (outside elelectric vehicles), including heat pumps, home batteries, and solr panels.

Separating the random-number generators prevents a change in one part of the model from unnecessarily shifting the random-number stream used by another part. For example, adding an extra charging-related draw should not change the mobility draws merely because both processes would otherwise consume values from the same random-number sequence.

The generators are created by the `RandomGenerators.create_generators()` method. This method first creates a NumPy `SeedSequence` from the configured Monte Carlo seed. It then uses `SeedSequence.spawn()` to create three child seed sequences, one for each random-number generator.

When seeding is enabled, the same root seed produces the same child seed sequences and therefore the same three random-number streams. The streams remain separate but are reproducible as a group. When seeding is disabled, the root seed sequence is initialised using non-deterministic entropy.

## Drawing bounded parameter values

The `draw_beta_value()` function draws a value within a specified range. The function requires a minimum value, a typical value, a maximum value, a random-number generator, and a beta-distribution shape parameter.

The input values must satisfy:

```text
minimum <= typical <= maximum
```

The returned value is therefore bounded by `minimum` and `maximum`. The `typical` value defines the central value around which the draws are distributed.

A bounded distribution is useful for model parameters for which values outside the specified range would be physically impossible, behaviourally implausible, or inconsistent with the scenario definition.

## Beta distribution and transformation

The function first draws a value from a symmetric beta distribution:

```text
Beta(shape, shape)
```

This produces a value between zero and one. Because both beta shape parameters are equal, the distribution is symmetric around `0.5`.

The beta draw is subsequently transformed in two parts:

1. A beta draw between `0` and `0.5` is mapped to the interval from `minimum` to `typical`.
2. A beta draw between `0.5` and `1` is mapped to the interval from `typical` to `maximum`.

For draws at or below `0.5`, the transformation is:

```text
minimum + 2 * draw * (typical - minimum)
```

For draws above `0.5`, the transformation is:

```text
typical + 2 * (draw - 0.5) * (maximum - typical)
```

This piecewise transformation allows the typical value to be positioned anywhere between the minimum and maximum. The distance from the minimum to the typical value does not need to equal the distance from the typical value to the maximum.

## Interpretation of the typical value

The `typical` value is a median of the resulting distribution. When `minimum < typical < maximum`, half of the generated values are below the typical value and half are above it.

This does not necessarily make the typical value the arithmetic mean of the resulting distribution. When the intervals below and above the typical value have different widths, the resulting distribution is asymmetric in terms of the modelled parameter. The typical value remains the median, but the mean may lie above or below it.

For example, consider:

```text
minimum = 10
typical = 20
maximum = 50
```

Half of the draws are located between 10 and 20, while the other half are located between 20 and 50. The upper half covers a wider interval. Consequently, the mean of the resulting values will be greater than 20 even though 20 is the median.

This makes it possible to specify a typical value independently of the width of the ranges on either side of it.

## Effect of the shape parameter

The `shape` parameter controls how strongly draws are concentrated around the typical value.

Values greater than 1 produce a concentration around the typical value. As `shape` increases, the symmetric beta distribution becomes increasingly concentrated around `0.5`. After transformation, this results in a stronger concentration of draws around `typical`.

A `shape` value of 1 produces a uniform beta draw between zero and one. Half of these draws are mapped uniformly to the interval between `minimum` and `typical`, and the other half are mapped uniformly to the interval between `typical` and `maximum`. The resulting distribution over the full range is therefore only uniform when `typical` is halfway between `minimum` and `maximum`.

Values below 1 increasingly favour the minimum and maximum. The underlying beta distribution becomes increasingly concentrated near zero and one, which correspond to the minimum and maximum after transformation.

The `shape` parameter must be greater than zero.

## Validation

Before drawing a value, `draw_beta_value()` verifies that the shape parameter is greater than zero and that the minimum, typical, and maximum values are correctly ordered.

A `ValueError` is raised when:

```text
shape <= 0
```

A `ValueError` is also raised when the following condition is not satisfied:

```text
minimum <= typical <= maximum
```

These checks prevent invalid beta-distribution parameters and incorrectly specified value ranges from being silently accepted.

## Fixed and degenerate ranges

The function also supports cases in which two or all three of the range values are equal.

For example:

```text
minimum = typical < maximum
```

means that beta draws in the lower half of the distribution all result in the typical value, while draws in the upper half are distributed between the typical value and the maximum.

Similarly:

```text
minimum < typical = maximum
```

causes draws in the upper half to result in the typical value, while draws in the lower half are distributed between the minimum and typical values.

When:

```text
minimum = typical = maximum
```

the returned value is always equal to this fixed value.

Importantly, a random beta draw is still performed in this final case even though it cannot affect the returned value.

## Maintaining the random-number stream

Performing a random draw when `minimum == maximum` is deliberate. Skipping the draw only when a parameter has a fixed value would shift all subsequent draws from the same random-number generator.

This could cause later model results to change merely because an earlier parameter happened to have a fixed value, even when those later results should otherwise be independent of that parameter.

By consuming one beta draw on every call, including when `minimum == maximum`, the position within the random-number stream is preserved relative to another run that calls the function at the same point with a non-degenerate range. This makes controlled comparisons between model configurations easier because making this parameter fixed does not, by itself, shift subsequent draws from the same generator.

## Reproducibility

A fixed Monte Carlo seed makes the random-number streams reproducible. Complete model results are reproducible when stochastic operations consistently use the provided generators and the remainder of the calculation behaves deterministically.

Random operations should therefore use the appropriate generator from `RandomGenerators`:

- definition-related draws use `define`;
- mobility-related draws use `mobility`;
- charging-related draws use `charging`.

Keeping these random streams separate also limits the effect of changes within one part of the model. A change in the number of charging draws, for example, can alter subsequent draws from the `charging` generator, but does not shift the sequence produced by the `mobility` or `define` generators.

For reproducible simulations, random draws should consistently use these generators rather than an independent or global random-number state.