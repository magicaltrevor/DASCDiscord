import os
import math
import discord
from discord import app_commands

# =========================
# Game constants (Spice)
# =========================
# Large Spice Refinery
SAND_PER_BATCH = 10_000
MELANGE_PER_BATCH = 200
WATER_PER_BATCH = 75_000
SECONDS_PER_BATCH = 2_700

# =========================
# Game constants (Stravidium / Plastanium)
# =========================
# Stravidium Fiber @ Medium Chemical Refinery
STRAV_MASS_PER_FIBER = 3
WATER_PER_FIBER = 100
SEC_PER_FIBER = 10

# Plastanium @ Large Ore Refinery
TI_PER_PLASTANIUM_LARGE = 4
FIBER_PER_PLASTANIUM = 1
WATER_PER_PLASTANIUM = 1250
SEC_PER_PLASTANIUM_LARGE = 20

# Plastanium @ Medium Ore Refinery (unused)
TI_PER_PLASTANIUM_MED = 6
SEC_PER_PLASTANIUM_MED = 30

def hms(seconds: float) -> str:
    total = int(round(seconds))
    h, r = divmod(total, 3600)
    m, s = divmod(r, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

def calculate_spice(sand: float, players: int, processors: int):
    if sand <= 0 or players < 1 or processors < 1:
        raise ValueError("sand>0, players>=1, processors>=1 required")
    scale = sand / SAND_PER_BATCH
    total_melange = MELANGE_PER_BATCH * scale
    total_water = WATER_PER_BATCH * scale
    total_seconds_single = SECONDS_PER_BATCH * scale
    parallel_seconds = total_seconds_single / processors
    per_player_floor = math.floor(total_melange / players)
    remainder = total_melange - (per_player_floor * players)
    return {
        "total_melange": total_melange,
        "melange_per_player": per_player_floor,
        "melange_remainder": remainder,
        "total_water": total_water,
        "water_per_processor": total_water / processors,
        "time_seconds_parallel": parallel_seconds,
    }

def compute_fibers(strav_mass: int, chem_refineries: int):
    chem_refineries = max(1, chem_refineries)
    fibers = strav_mass // STRAV_MASS_PER_FIBER
    water_total = fibers * WATER_PER_FIBER
    time_single = fibers * SEC_PER_FIBER
    return {
        "fibers": fibers,
        "water_total": water_total,
        "water_per_refinery": water_total / chem_refineries,
        "time_per_refinery_sec": time_single / chem_refineries,
    }

def compute_plastanium_large(fibers_avail: int, titanium_ore: int, large_refineries: int):
    large_refineries = max(1, large_refineries)
    max_by_fiber = fibers_avail // FIBER_PER_PLASTANIUM
    max_by_titanium = titanium_ore // TI_PER_PLASTANIUM_LARGE
    pieces = min(max_by_fiber, max_by_titanium)
    water_total = pieces * WATER_PER_PLASTANIUM
    time_single = pieces * SEC_PER_PLASTANIUM_LARGE
    return {
        "pieces": pieces,
        "water_total": water_total,
        "water_per_refinery": water_total / large_refineries,
        "time_per_refinery_sec": time_single / large_refineries,
    }

class SpiceBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.none()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = SpiceBot()

# /spice
@bot.tree.command(name="spice", description="Calculate Spice Melange distribution from Spice Sand.")
@app_commands.describe(
    sand="Total Spice Sand collected",
    players="Number of players",
    processors="Number of processors/refineries"
)
async def spice(interaction: discord.Interaction, sand: float, players: int, processors: int = 1):
    try:
        result = calculate_spice(sand, players, processors)
        msg = [
            f"**Spice Sand:** {sand:,.0f}",
            f"**Players:** {players}",
            f"**Processors:** {processors}",
            "",
            f"**Total Melange:** {result['total_melange']:.2f}",
            f"**Melange per Player (floored):** {int(result['melange_per_player']):,}",
            f"**Unallocated Remainder:** {result['melange_remainder']:.2f}",
            "",
            f"**Total Water Required:** {result['total_water']:.2f}",
            f"**Water per Processor:** {result['water_per_processor']:.2f}",
            f"**Processing Time (parallel):** {hms(result['time_seconds_parallel'])}",
        ]
        await interaction.response.send_message("\n".join(msg))
    except Exception as e:
        await interaction.response.send_message(f"❌ {e}", ephemeral=True)

# /plastanium_raw
@bot.tree.command(name="plastanium_raw",
    description="Split raw Stravidium→Fiber + Titanium; show chem refinery water/time and per-player raw splits.")
@app_commands.describe(
    strav_mass="Total Stravidium Mass",
    titanium_ore="Total Titanium Ore",
    players="Number of players",
    chem_refineries="Number of Medium Chemical Refineries"
)
async def plastanium_raw(interaction: discord.Interaction,
    strav_mass: int, titanium_ore: int, players: int, chem_refineries: int):
    stageA = compute_fibers(strav_mass, chem_refineries)
    fibers = stageA["fibers"]
    fibers_per_player = fibers // players
    titanium_per_player = titanium_ore // players
    msg = [
        f"**Stravidium Mass:** {strav_mass:,} | **Titanium Ore:** {titanium_ore:,}",
        f"**Players:** {players} | **Chem Refineries:** {chem_refineries}",
        "",
        f"**Water per Chem Refinery:** {stageA['water_per_refinery']:.0f} mL",
        f"**Time per Chem Refinery:** {hms(stageA['time_per_refinery_sec'])}",
        "",
        f"**Stravidium Fibers per Player (floored):** {fibers_per_player:,}",
        f"**Titanium Ore per Player (floored):** {titanium_per_player:,}",
    ]
    await interaction.response.send_message("\n".join(msg))

# /plastanium
@bot.tree.command(name="plastanium",
    description="Mass→Fiber then Fiber+Titanium→Plastanium; per-refinery water/time + per-player plastanium.")
@app_commands.describe(
    strav_mass="Total Stravidium Mass",
    titanium_ore="Total Titanium Ore",
    players="Number of players",
    large_refineries="Number of Large Ore Refineries",
    chem_refineries="Number of Medium Chemical Refineries"
)
async def plastanium(interaction: discord.Interaction,
    strav_mass: int, titanium_ore: int, players: int, large_refineries: int, chem_refineries: int):
    stageA = compute_fibers(strav_mass, chem_refineries)
    fibers = stageA["fibers"]
    stageB = compute_plastanium_large(fibers, titanium_ore, large_refineries)
    plastanium_total = stageB["pieces"]
    per_player = plastanium_total // players
    remainder = plastanium_total - per_player * players
    msg = [
        f"**Inputs** — Stravidium Mass: {strav_mass:,}, Titanium Ore: {titanium_ore:,}",
        f"Players: {players} | Chem Refineries: {chem_refineries} | Large Ore Refineries: {large_refineries}",
        "",
        "**Fiber Stage (Medium Chemical Refinery)**",
        f"Water per Chem Refinery: {stageA['water_per_refinery']:.0f} mL",
        f"Time per Chem Refinery: {hms(stageA['time_per_refinery_sec'])}",
        "",
        "**Plastanium Stage (Large Ore Refinery)**",
        f"Water per Large Ore Refinery: {stageB['water_per_refinery']:.0f} mL",
        f"Time per Large Ore Refinery: {hms(stageB['time_per_refinery_sec'])}",
        "",
        f"**Total Plastanium:** {plastanium_total:,}",
        f"**Plastanium per Player (floored):** {per_player:,}",
        f"**Unallocated Remainder:** {remainder:,}",
    ]
    await interaction.response.send_message("\n".join(msg))

# /help_spicebot
@bot.tree.command(name="help_spicebot", description="Show usage for spice and plastanium commands.")
async def help_spicebot(interaction: discord.Interaction):
    msg = [
        "**Spice Distribution Bot — Commands**",
        "",
        "**/spice** sand:<amount> players:<count> processors:<count>",
        "**/plastanium_raw** strav_mass:<amount> titanium_ore:<amount> players:<count> chem_refineries:<count>",
        "**/plastanium** strav_mass:<amount> titanium_ore:<amount> players:<count> large_refineries:<count> chem_refineries:<count>",
    ]
    await interaction.response.send_message("\n".join(msg), ephemeral=True)

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Please set DISCORD_BOT_TOKEN environment variable.")
    bot.run(token)