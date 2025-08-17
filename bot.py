import os
import math
import discord
from discord import app_commands

# ---- Game constants (Large Spice Refinery baseline) ----
SAND_PER_BATCH = 10_000          # sand -> yields below
MELANGE_PER_BATCH = 200          # melange per 10k sand
WATER_PER_BATCH = 75_000         # water per 10k sand
SECONDS_PER_BATCH = 2_700        # seconds per 10k sand (45 min)

def hms(seconds: float) -> str:
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"

def calculate(spice_sand: float, players: int, processors: int):
    # Scale by batches
    scale = spice_sand / SAND_PER_BATCH

    total_melange = MELANGE_PER_BATCH * scale
    total_water = WATER_PER_BATCH * scale
    total_seconds_single = SECONDS_PER_BATCH * scale

    # Parallel processors: time = single_time / processors
    processors = max(1, processors)
    parallel_seconds = total_seconds_single / processors

    # Floor per-player melange; track remainder
    if players <= 0:
        raise ValueError("Players must be at least 1.")
    per_player_exact = total_melange / players
    per_player_floor = math.floor(per_player_exact)
    remainder = total_melange - (per_player_floor * players)

    water_per_processor = total_water / processors

    return {
        "total_melange": total_melange,
        "melange_per_player": per_player_floor,   # floored to whole units
        "melange_remainder": remainder,           # unallocated amount (can be fractional)
        "total_water": total_water,
        "water_per_processor": water_per_processor,
        "time_seconds_parallel": parallel_seconds
    }

class SpiceBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.none()  # no member/message content needed
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Sync commands globally (you can restrict to a guild for faster iteration)
        await self.tree.sync()

bot = SpiceBot()

@bot.tree.command(name="spice", description="Calculate Dune Awakening Spice Melange distribution")
@app_commands.describe(
    sand="Total Spice Sand collected (e.g., 25000)",
    players="Number of players sharing the Melange",
    processors="Number of processors/refineries running in parallel (default: 1)"
)
async def spice(interaction: discord.Interaction, sand: float, players: int, processors: int = 1):
    try:
        if sand <= 0:
            await interaction.response.send_message("❌ Sand must be > 0.", ephemeral=True)
            return
        if players < 1:
            await interaction.response.send_message("❌ Players must be at least 1.", ephemeral=True)
            return
        if processors < 1:
            await interaction.response.send_message("❌ Processors must be at least 1.", ephemeral=True)
            return

        result = calculate(sand, players, processors)

        total_melange = result["total_melange"]
        per_player = result["melange_per_player"]
        remainder = result["melange_remainder"]
        total_water = result["total_water"]
        water_per_proc = result["water_per_processor"]
        time_str = hms(result["time_seconds_parallel"])

        # Build a neat response (no long sentences in tables per your preference)
        msg_lines = [
            f"**Spice Sand:** {sand:,.0f}",
            f"**Players:** {players}",
            f"**Processors:** {processors}",
            "",
            f"**Total Melange:** {total_melange:,.2f}",
            f"**Melange per Player (floored):** {int(per_player):,}",
            f"**Unallocated Remainder:** {remainder:,.2f}",
            "",
            f"**Total Water Required:** {total_water:,.2f}",
            f"**Water per Processor:** {water_per_proc:,.2f}",
            f"**Processing Time (parallel):** {time_str}",
        ]
        await interaction.response.send_message("\n".join(msg_lines))
    except Exception as e:
        await interaction.response.send_message(f"⚠️ Error: {e}", ephemeral=True)

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Please set DISCORD_BOT_TOKEN environment variable.")
    bot.run(token)
