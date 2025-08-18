"""
spice_calculator.py

Standalone CLI utility for Dune Awakening resource planning and fair splits.

It supports:
1) Spice Melange distribution (Spice Sand -> Melange) with multiple processors.
2) Plastanium RAW split (Mass -> Fiber at Medium Chemical Refineries; split Fiber & Titanium).
3) Plastanium CRAFT (Mass -> Fiber at Medium Chem; Fiber + Titanium -> Plastanium at Large Ore).

Formulas / Ratios (current community-known values):
- Spice (Large Spice Refinery):
  * 10,000 Spice Sand -> 200 Melange
  * 75,000 Water per 10,000 Sand
  * 2,700 seconds per 10,000 Sand

- Stravidium Fiber (Medium Chemical Refinery):
  * 3 Stravidium Mass + 100 mL Water -> 1 Fiber
  * 10 seconds per Fiber

- Plastanium (Large Ore Refinery):
  * 1 Fiber + 4 Titanium + 1,250 mL Water -> 1 Plastanium
  * 20 seconds per Plastanium
"""

from __future__ import annotations

import math


# ---------------------------
# Spice: Large Spice Refinery
# ---------------------------
def calculate_spice_distribution(
    spice_sand: float,
    players: int,
    processors: int = 1,
) -> dict[str, float | tuple[int, int, int]]:
    """Calculate water, processing time and melange per player based on Spice Sand."""
    if players <= 0:
        raise ValueError("Number of players must be greater than zero.")
    if processors <= 0:
        raise ValueError("Number of processors must be greater than zero.")
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

    # Distribute melange among players (floored)
    melange_per_player = math.floor(total_melange / players)

    # Water per processor; time scales inversely with processors (parallel)
    water_per_processor = water_required / processors
    time_seconds_per_processor = total_time_seconds / processors

    # Convert time
    hours = int(time_seconds_per_processor // 3600)
    minutes = int((time_seconds_per_processor % 3600) // 60)
    seconds = int(round(time_seconds_per_processor % 60))

    return {
        "total_melange": total_melange,
        "water_required": water_required,
        "water_per_processor": water_per_processor,
        "time": (hours, minutes, seconds),
        "melange_per_player": melange_per_player,
    }


# ---------------------------------------------------
# Stravidium Fiber: Medium Chemical Refinery (Stage A)
# Plastanium: Large Ore Refinery (Stage B)
# ---------------------------------------------------
# Constants for Stage A (Fibers)
STRAV_MASS_PER_FIBER = 3           # 3 mass -> 1 fiber
WATER_PER_FIBER = 100.0            # mL per fiber
SEC_PER_FIBER = 10.0               # seconds per fiber

# Constants for Stage B (Plastanium at Large Ore Refinery)
TI_PER_PLASTANIUM_LARGE = 4        # Titanium per plastanium
FIBER_PER_PLASTANIUM = 1           # Fiber per plastanium
WATER_PER_PLASTANIUM = 1250.0      # mL per plastanium
SEC_PER_PLASTANIUM_LARGE = 20.0    # seconds per plastanium


def compute_fibers_stage(strav_mass: int, chem_refineries: int) -> dict[str, float]:
    """Compute how many fibers we can make, plus per-chem-refinery water/time."""
    if strav_mass < 0:
        raise ValueError("Stravidium mass cannot be negative.")
    if chem_refineries <= 0:
        raise ValueError("Number of chemical refineries must be greater than zero.")

    fibers = strav_mass // STRAV_MASS_PER_FIBER
    water_total = fibers * WATER_PER_FIBER
    time_single = fibers * SEC_PER_FIBER

    return {
        "fibers": float(fibers),
        "water_total": water_total,
        "water_per_refinery": water_total / chem_refineries,
        "time_per_refinery_sec": time_single / chem_refineries,
    }


def compute_plastanium_large_stage(
    fibers_avail: int, titanium_ore: int, large_refineries: int
) -> dict[str, float]:
    """Compute plastanium craft totals and per-large-refinery water/time."""
    if titanium_ore < 0:
        raise ValueError("Titanium ore cannot be negative.")
    if large_refineries <= 0:
        raise ValueError("Number of large ore refineries must be greater than zero.")

    max_by_fiber = fibers_avail // FIBER_PER_PLASTANIUM
    max_by_titanium = titanium_ore // TI_PER_PLASTANIUM_LARGE
    pieces = int(min(max_by_fiber, max_by_titanium))

    water_total = pieces * WATER_PER_PLASTANIUM
    time_single = pieces * SEC_PER_PLASTANIUM_LARGE

    return {
        "pieces": float(pieces),
        "water_total": water_total,
        "water_per_refinery": water_total / large_refineries,
        "time_per_refinery_sec": time_single / large_refineries,
    }


# -----------------------
# CLI Formatting Helpers
# -----------------------
def format_time_hms(seconds: float) -> str:
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


def format_time(hours: int, minutes: int, seconds: int) -> str:
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if hours or minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


# ---------------
# CLI Entrypoint
# ---------------
def main() -> None:
    """CLI menu for Spice / Plastanium calculations."""
    print("Select mode:")
    print("  1) Spice (Spice Sand -> Melange)")
    print("  2) Plastanium RAW Split (Mass->Fiber + split Fiber & Titanium)")
    print("  3) Plastanium CRAFT (Mass->Fiber then Fiber+Titanium->Plastanium)")

    mode = input("Enter choice (1/2/3): ").strip()

    try:
        if mode == "1":
            # Spice workflow
            spice_input = input("Enter total Spice Sand collected: ").strip()
            players_input = input("Enter number of players: ").strip()
            processors_input = input("Enter number of processors (refineries): ").strip() or "1"

            spice_sand = float(spice_input)
            players = int(players_input)
            processors = int(processors_input)

            result = calculate_spice_distribution(spice_sand, players, processors)
            hours, minutes, seconds = result["time"]
            time_str = format_time(hours, minutes, seconds)

            print("\nResults:")
            print(f"Total Melange Produced: {result['total_melange']:.2f}")
            print(f"Total Water Required: {result['water_required']:.2f}")
            print(f"Water per Processor: {result['water_per_processor']:.2f}")
            print(f"Time: {time_str}")
            print(f"Spice Melange per player (floored): {int(result['melange_per_player'])}")

        elif mode == "2":
            # Plastanium RAW split (Stage A only; split Fiber & Titanium per player)
            strav_mass_input = input("Enter total Stravidium Mass collected: ").strip()
            titanium_input = input("Enter total Titanium Ore collected: ").strip()
            players_input = input("Enter number of players: ").strip()
            chem_input = input("Enter number of Medium Chemical Refineries: ").strip()

            strav_mass = int(strav_mass_input)
            titanium = int(titanium_input)
            players = int(players_input)
            chem_refineries = int(chem_input)
            if players <= 0:
                raise ValueError("Number of players must be greater than zero.")

            stageA = compute_fibers_stage(strav_mass, chem_refineries)
            fibers_total = int(stageA["fibers"])

            fibers_per_player = fibers_total // players
            titanium_per_player = titanium // players

            print("\nResults (RAW Split):")
            print(f"Total Fibers Produced: {fibers_total}")
            print(f"Water per Chemical Refinery: {stageA['water_per_refinery']:.0f} mL")
            print(f"Time  per Chemical Refinery: {format_time_hms(stageA['time_per_refinery_sec'])}")
            print(f"Stravidium Fibers per player (floored): {fibers_per_player}")
            print(f"Titanium Ore per player (floored): {titanium_per_player}")

        elif mode == "3":
            # Plastanium full craft (Stage A then Stage B)
            strav_mass_input = input("Enter total Stravidium Mass collected: ").strip()
            titanium_input = input("Enter total Titanium Ore collected: ").strip()
            players_input = input("Enter number of players: ").strip()
            chem_input = input("Enter number of Medium Chemical Refineries: ").strip()
            large_input = input("Enter number of Large Ore Refineries: ").strip()

            strav_mass = int(strav_mass_input)
            titanium = int(titanium_input)
            players = int(players_input)
            chem_refineries = int(chem_input)
            large_refineries = int(large_input)

            if players <= 0:
                raise ValueError("Number of players must be greater than zero.")

            # Stage A: make fibers
            stageA = compute_fibers_stage(strav_mass, chem_refineries)
            fibers_total = int(stageA["fibers"])

            # Stage B: plastanium via Large Ore Refineries
            stageB = compute_plastanium_large_stage(fibers_total, titanium, large_refineries)
            plastanium_total = int(stageB["pieces"])
            plastanium_per_player = plastanium_total // players
            remainder = plastanium_total - plastanium_per_player * players

            print("\nResults (Plastanium Craft):")
            print("Fiber Stage (Medium Chemical Refinery):")
            print(f"  Water per Chem Refinery: {stageA['water_per_refinery']:.0f} mL")
            print(f"  Time  per Chem Refinery: {format_time_hms(stageA['time_per_refinery_sec'])}")

            print("Plastanium Stage (Large Ore Refinery):")
            print(f"  Water per Large Ore Refinery: {stageB['water_per_refinery']:.0f} mL")
            print(f"  Time  per Large Ore Refinery: {format_time_hms(stageB['time_per_refinery_sec'])}")

            print(f"\nTotal Plastanium: {plastanium_total}")
            print(f"Plastanium per player (floored): {plastanium_per_player}")
            print(f"Unallocated remainder: {remainder}")

        else:
            print("Invalid choice. Please run the script again and enter 1, 2, or 3.")

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
