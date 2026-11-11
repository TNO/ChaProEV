import numpy as np
import numpy.typing as npt

from ChaProEV.stochastic_new.grid import PowerLine


def get_non_EV_power_demand_per_line_kW(
    *, lines: list[PowerLine], amount_of_time_stamps: int
) -> npt.NDArray[np.float64]:

    line_non_EV_power_kW: npt.NDArray[np.float64] = np.zeros(
        (len(lines), amount_of_time_stamps)
    )

    # Go through lines and draw powers by:
    # setting an amount of connections per line
    # (ransdom draw between zero and line_power/power per connection)
    # Then for each connection, draw a yearly consumption adn profile
    # shape. The sum of these connections per line will then provide
    # line_non_EV_power_kW: npt.NDArray[np.float64] = np.zeros(
    # Note that we probably should introduce connections to the grid
    # (In addition to transformers and power lines)
    # maybe move all this to a grid.py module
    # Then we draw a connection within all connection when creating the users
    # (rather than drawing the characteristics as we do now)
    # It might be useful to have uuids for lines and connections too,
    # with conversions to indices.
    # This also means that we probably have to add the connection level
    # into the Grid object.
    # Does that mean that we can only update/work with connection level
    # power profiles sums and then do the go/no-go with
    # a triple check: connection ok, line ok, grid ok
    # where we need to do these checks only for the horizon at hand
    # and where all the non-EV parts are fixed anyway?
    # Also, this grid would be for the homes of the users.
    # We assume that other locations are fine (dedicated charging infrastrure)
    return line_non_EV_power_kW
