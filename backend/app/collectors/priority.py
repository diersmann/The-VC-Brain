"""Pure functions for collection priority math.

Priority determines which task the dispatcher picks next.
Formula::

    priority = info_gain * staleness_factor * deadline_factor / cost

All values are floats in [0, 1] or positive scalars.
"""

from __future__ import annotations

import math


def info_gain(
    signal_score: float,
    staleness_days: float,
    deadline_pressure: float = 0.0,
) -> float:
    """Estimate the expected information gain from collecting this person.

    * Low signal → higher gain (we know little).
    * High staleness → higher gain (data may be stale).
    * Deadline pressure → higher gain (opportunity is time-sensitive).

    Returns a value in [0, 1].
    """
    # Inverse sigmoid: gain is highest when signal is low or moderate.
    signal_factor = 1.0 - (2.0 / (1.0 + math.exp(-3.0 * signal_score)) - 1.0)

    # Staleness: linear ramp from 0 (fresh) to 1 (very stale).
    staleness_factor = min(1.0, staleness_days / 90.0)

    # Deadline: linear ramp from 0 (no deadline) to 1 (urgent).
    deadline_factor = min(1.0, deadline_pressure)

    # Weighted combination (tunable).
    return 0.5 * signal_factor + 0.3 * staleness_factor + 0.2 * deadline_factor


def priority(
    info_gain: float,
    cost: float,
    authority: float,
) -> float:
    """Compute the final priority score for a collection task.

    Higher priority = should be collected sooner.
    Cost is inverted so cheaper tasks get a boost.
    Authority amplifies high-quality sources.
    """
    if cost <= 0:
        cost = 0.01
    cost_factor = 1.0 / cost
    return info_gain * cost_factor * (0.5 + 0.5 * authority)
