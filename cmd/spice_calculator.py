"""
spice_calculator.py

This script helps players of **Dune Awakening** calculate how much Spice
Melange each participant should receive after a guild harvesting operation.

The game’s large Spice Refinery converts Spice Sand into Spice Melange at a
specific rate. According to current game data, processing a full batch of
10 000 Spice Sand yields 200 Spice Melange, consumes 75 000 units of water and
takes 2 700 seconds (45 minutes) to complete【796140701293488†L128-L149】. These
parameters are used to compute the required water, processing time and per‑player
share for any given amount of Spice Sand.

Usage:

    python3 spice_calculator.py

The script will prompt you for the total Spice Sand collected and the number of
players involved. It will then display the water required, the processing
duration in a human‑readable format and the amount of Spice Melange each
participant receives.

Feel free to integrate this module into other tools by importing the
``calculate_spice_distribution`` function.
"""

from __future__ import annotations

import math

def calculate_spice_distribution(spice_sand: float, players: int) -> dict[str, float | tuple[int, int, int]]:
    """Calculate water, processing time and melange per player based on Spice Sand.

    Parameters
    ----------
    spice_sand : float
        Total amount of Spice Sand collected during the operation.
    players : int
        Number of players sharing the final Spice Melange. Must be greater than zero.

    Returns
    -------
    dict
        A dictionary containing:

        ``water_required``
            Total water required to process the given sand (same units as in‑game).
        ``time``
            A tuple ``(hours, minutes, seconds)`` representing the processing duration.
        ``melange_per_player``
            The amount of Spice Melange each player receives.

    Raises
    ------
    ValueError
        If ``players`` is less than or equal to zero, or if ``spice_sand`` is negative.

    Notes
    -----
    The calculations assume the large Spice Refinery ratios:

    * 10 000 sand → 200 melange
    * 75 000 water → 200 melange
    * 2 700 seconds → 200 melange

    These figures are derived from current information about **Dune Awakening**
    refineries【796140701293488†L128-L149】. Should future game updates change the
    ratios, update the constants in this function accordingly.
    """

    if players <= 0:
        raise ValueError("Number of players must be greater than zero.")
    if spice_sand < 0:
        raise ValueError("Amount of spice sand cannot be negative.")

    # Conversion ratios for the large spice refinery
    SAND_PER_BATCH = 10_000.0        # sand units per full batch
    MELANGE_PER_BATCH = 200.0        # melange units per full batch
    WATER_PER_BATCH = 75_000.0       # water units per full batch
    TIME_PER_BATCH_SEC = 2_700.0     # seconds per full batch

    # Compute scaling factors
    batch_fraction = spice_sand / SAND_PER_BATCH
    total_melange = batch_fraction * MELANGE_PER_BATCH
    water_required = batch_fraction * WATER_PER_BATCH
    total_time_seconds = batch_fraction * TIME_PER_BATCH_SEC

    # Distribute melange among players
    melange_per_player = total_melange / players

    # Convert time into hours, minutes, seconds
    hours = int(total_time_seconds // 3600)
    minutes = int((total_time_seconds % 3600) // 60)
    seconds = int(round(total_time_seconds % 60))

    return {
        "water_required": water_required,
        "time": (hours, minutes, seconds),
        "melange_per_player": melange_per_player,
    }


def format_time(hours: int, minutes: int, seconds: int) -> str:
    """Return a human‑readable string for a time tuple.

    Parameters
    ----------
    hours : int
        Number of hours.
    minutes : int
        Number of minutes.
    seconds : int
        Number of seconds.

    Returns
    -------
    str
        Formatted string "Hh Mm Ss". Components are omitted if zero hours or
        minutes but seconds are always shown.
    """
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if hours or minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def main() -> None:
    """Prompt the user for inputs and display the calculated distribution."""
    try:
        spice_input = input("Enter total Spice Sand collected: ").strip()
        players_input = input("Enter number of players: ").strip()

        # Convert to numeric values
        spice_sand = float(spice_input)
        players = int(players_input)

        result = calculate_spice_distribution(spice_sand, players)

        hours, minutes, seconds = result["time"]
        time_str = format_time(hours, minutes, seconds)

        print("\nResults:")
        print(f"Water Required: {result['water_required']:.2f}")
        print(f"Time: {time_str}")
        print(f"Spice Melange per player: {result['melange_per_player']:.2f}")

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()