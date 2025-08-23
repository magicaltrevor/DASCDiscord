import os
import math
import discord
from discord import app_commands
import json
from pathlib import Path
from uuid import uuid4

# =========================
# Simple RUN TRACKER (with JSON persistence)
# =========================
RUNS_PATH = Path("runs.json")
RUN_TYPES = ("spice", "plastanium", "stravidium")
AMOUNT_FIELDS = ("spice", "plastanium", "stravidium", "titanium")  # titanium optional; helpful for reports
def _load_runs() -> dict:
    if RUNS_PATH.exists():
        try:
            return json.loads(RUNS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_runs(data: dict) -> None:
    RUNS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

RUNS = _load_runs()

def _new_run_id() -> str:
    # Short, friendly ID
    return uuid4().hex[:8]

def _parse_players_csv(csv_str: str) -> list[str]:
    return [p.strip() for p in csv_str.split(",") if p.strip()]

def _get_run_or_err(run_id: str):
    run = RUNS.get(run_id)
    if not run:
        raise ValueError("Run ID not found.")
    return run

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
        "**/run** kind:<spice|plastanium|stravidium> players_csv:<Player1,Player2,...> → create a tracked run will return a run ID",
        "**/run_update** run_id:<id> field:<players|spice|plastanium|stravidium|titanium> [value:<PlayerName>] [amount:<number>] → update a run",
        "**/run_calculate** run_id:<id> processors:<count> → calculate cuts for a run",
        "**/run_view** run_id:<id> → view current state of a run",
        "**/run_delete** run_id:<id> → delete a run (creator or admin only)",
    ]
    await interaction.response.send_message("\n".join(msg), ephemeral=True)

# ---------------- /run ----------------
@bot.tree.command(name="run", description="Start a tracked run and get a run ID.")
@app_commands.describe(
    kind="spice | plastanium | stravidium",
    players_csv="Comma-delimited player names (e.g., Alice,Bob,Charlie)"
)
async def run_start(interaction: discord.Interaction, kind: str, players_csv: str):
    kind = kind.lower().strip()
    if kind not in RUN_TYPES:
        await interaction.response.send_message("❌ kind must be one of: spice, plastanium, stravidium", ephemeral=True)
        return

    players = list(dict.fromkeys(_parse_players_csv(players_csv)))  # dedupe, preserve order
    if not players:
        await interaction.response.send_message("❌ Provide at least one player in players_csv.", ephemeral=True)
        return

    run_id = _new_run_id()
    RUNS[run_id] = {
        "kind": kind,
        "players": players,                 # list[str]
        "amounts": {                        # numeric accumulators
            "spice": 0.0,
            "plastanium": 0.0,
            "stravidium": 0.0,
            "titanium": 0.0,
        },
        "created_by": interaction.user.id,
        "created_at": interaction.created_at.isoformat() if hasattr(interaction, "created_at") else "",
    }
    _save_runs(RUNS)

    await interaction.response.send_message(
        f"✅ Run created: **{run_id}**\n"
        f"Type: **{kind}**\n"
        f"Players: {', '.join(players)}"
    )

# -------------- /run-update --------------
@bot.tree.command(name="run_update", description="Update players or amounts for a run.")
@app_commands.describe(
    run_id="ID returned by /run",
    field="players | spice | plastanium | stravidium | titanium",
    value="If field=players, provide the player name to add",
    amount="If field is a resource, provide the numeric amount to add (can be decimal)"
)
async def run_update(interaction: discord.Interaction,
                     run_id: str,
                     field: str,
                     value: str | None = None,
                     amount: float | None = None):
    try:
        run = _get_run_or_err(run_id)
        field = field.lower().strip()

        if field == "players":
            if not value:
                await interaction.response.send_message("❌ Provide value=<PlayerName> when field=players.", ephemeral=True)
                return
            name = value.strip()
            if not name:
                await interaction.response.send_message("❌ Player name cannot be empty.", ephemeral=True)
                return
            if name in run["players"]:
                await interaction.response.send_message(f"ℹ️ Player **{name}** is already on the roster.", ephemeral=True)
                return
            run["players"].append(name)
            _save_runs(RUNS)
            await interaction.response.send_message(
                f"✅ Added **{name}** to run **{run_id}**.\n"
                f"Roster: {', '.join(run['players'])}"
            )
            return

        # Resource update
        if field not in AMOUNT_FIELDS:
            await interaction.response.send_message(
                "❌ field must be one of: players | spice | plastanium | stravidium | titanium",
                ephemeral=True
            )
            return
        if amount is None:
            await interaction.response.send_message("❌ Provide amount=<number> for resource updates.", ephemeral=True)
            return

        run["amounts"][field] = float(run["amounts"].get(field, 0.0)) + float(amount)
        _save_runs(RUNS)
        await interaction.response.send_message(
            f"✅ Updated **{field}** for run **{run_id}**.\n"
            f"New total {field}: {run['amounts'][field]:,}"
        )

    except ValueError as e:
        await interaction.response.send_message(f"❌ {e}", ephemeral=True)

# ------------ /run-calculate ------------
@bot.tree.command(name="run_calculate", description="Calculate cuts for a run.")
@app_commands.describe(
    run_id="ID returned by /run",
    processors="(For SPICE only) number of Spice refineries running in parallel",
    chem_refineries="(For STRAVIDIUM/PLASTANIUM) number of Medium Chemical Refineries",
    large_refineries="(For PLASTANIUM) number of Large Ore Refineries"
)
async def run_calculate(
    interaction: discord.Interaction,
    run_id: str,
    processors: int = 1,
    chem_refineries: int = 1,
    large_refineries: int = 1
):
    try:
        run = _get_run_or_err(run_id)
        players = run["players"]
        if not players:
            await interaction.response.send_message("❌ No players in this run.", ephemeral=True)
            return

        n_players = len(players)
        kind = run["kind"]
        amounts = run["amounts"]

        # ---------- SPICE ----------
        if kind == "spice":
            sand = float(amounts.get("spice", 0.0))
            if sand <= 0:
                await interaction.response.send_message("❌ No spice sand recorded for this run.", ephemeral=True)
                return
            proc = max(1, processors)
            result = calculate_spice(sand, n_players, proc)
            msg = [
                f"**Run {run_id}** — Type: **spice**",
                f"Players ({n_players}): {', '.join(players)}",
                f"Spice Sand: {sand:,.0f} | Spice Refineries: {proc}",
                "",
                f"**Total Melange:** {result['total_melange']:.2f}",
                f"**Melange per Player (floored):** {int(result['melange_per_player']):,}",
                f"**Unallocated Remainder:** {result['melange_remainder']:.2f}",
                "",
                f"**Total Water:** {result['total_water']:.2f}",
                f"**Water per Refinery:** {result['water_per_processor']:.2f}",
                f"**Processing Time (parallel):** {hms(result['time_seconds_parallel'])}",
            ]
            await interaction.response.send_message("\n".join(msg))
            return

        # ------ STRAVIDIUM (Mass -> Fiber) ------
        if kind == "stravidium":
            mass = int(amounts.get("stravidium", 0.0))
            if mass <= 0:
                await interaction.response.send_message("❌ No stravidium mass recorded for this run.", ephemeral=True)
                return
            chem = max(1, chem_refineries)
            stageA = compute_fibers(mass, chem)
            fibers_total = int(stageA["fibers"])
            per_player_fibers = fibers_total // n_players
            remainder = fibers_total - per_player_fibers * n_players
            msg = [
                f"**Run {run_id}** — Type: **stravidium**",
                f"Players ({n_players}): {', '.join(players)}",
                f"Stravidium Mass: {mass:,} | Chemical Refineries: {chem}",
                "",
                f"**Total Fibers:** {fibers_total:,}",
                f"**Fibers per Player (floored):** {per_player_fibers:,}",
                f"**Unallocated Remainder:** {remainder:,}",
                "",
                f"**Water per Chemical Refinery:** {stageA['water_per_refinery']:.0f} mL",
                f"**Time per Chemical Refinery:** {hms(stageA['time_per_refinery_sec'])}",
            ]
            await interaction.response.send_message("\n".join(msg))
            return

        # ------ PLASTANIUM (Mass -> Fiber -> Plastanium) ------
        if kind == "plastanium":
            # REQUIRE both stravidium mass and titanium ore
            mass = int(amounts.get("stravidium", 0.0))
            titanium = int(amounts.get("titanium", 0.0))
            if mass <= 0 or titanium <= 0:
                await interaction.response.send_message(
                    "❌ Plastanium runs require both **stravidium** mass and **titanium** amounts. "
                    "Use /run_update to add them.",
                    ephemeral=True
                )
                return

            chem = max(1, chem_refineries)
            large = max(1, large_refineries)

            # Stage A: Mass -> Fiber (Medium Chemical Refinery)
            stageA = compute_fibers(mass, chem)
            fibers_total = int(stageA["fibers"])

            # Stage B: Fiber + Titanium -> Plastanium (Large Ore Refinery)
            stageB = compute_plastanium_large(fibers_total, titanium, large)
            plastanium_total = int(stageB["pieces"])
            per_player = plastanium_total // n_players
            remainder = plastanium_total - per_player * n_players

            msg = [
                f"**Run {run_id}** — Type: **plastanium**",
                f"Players ({n_players}): {', '.join(players)}",
                f"Inputs — Stravidium Mass: {mass:,}, Titanium Ore: {titanium:,}",
                f"Chem Refineries: {chem} | Large Ore Refineries: {large}",
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
            return

        await interaction.response.send_message("❌ Unknown run type.", ephemeral=True)

    except ValueError as e:
        await interaction.response.send_message(f"❌ {e}", ephemeral=True)
        
# ------------- /run-view -------------
@bot.tree.command(name="run_view", description="View the current state of a run.")
@app_commands.describe(
    run_id="ID returned by /run"
)
async def run_view(interaction: discord.Interaction, run_id: str):
    try:
        run = _get_run_or_err(run_id)
        players = run.get("players", [])
        amounts = run.get("amounts", {})
        kind = run.get("kind", "?")
        created_by = run.get("created_by", None)
        created_at = run.get("created_at", "")

        # Pretty amounts (show only nonzero or all?)
        def fmt_amount(k):
            v = float(amounts.get(k, 0))
            # Show as int if it's whole; otherwise show with 2 decimals.
            return f"{int(v):,}" if abs(v - int(v)) < 1e-9 else f"{v:,.2f}"

        amount_lines = [
            f"- spice: {fmt_amount('spice')}",
            f"- plastanium: {fmt_amount('plastanium')}",
            f"- stravidium: {fmt_amount('stravidium')}",
            f"- titanium: {fmt_amount('titanium')}",
        ]

        creator_str = f"<@{created_by}>" if created_by else "(unknown)"
        roster_str = ", ".join(players) if players else "(none)"

        msg = [
            f"**Run {run_id}**",
            f"Type: **{kind}**",
            f"Created by: {creator_str}",
            f"Created at: {created_at or '(n/a)'}",
            "",
            f"**Players ({len(players)}):** {roster_str}",
            "",
            "**Recorded amounts:**",
            *amount_lines,
        ]
        await interaction.response.send_message("\n".join(msg))
    except ValueError as e:
        await interaction.response.send_message(f"❌ {e}", ephemeral=True)

# ----------- /run-delete -----------
@bot.tree.command(name="run_delete", description="Delete a run (creator or admin only).")
@app_commands.describe(
    run_id="ID returned by /run"
)
async def run_delete(interaction: discord.Interaction, run_id: str):
    try:
        run = _get_run_or_err(run_id)

        # Permission check: creator OR user with Administrator permission
        is_creator = (interaction.user.id == run.get("created_by"))
        is_admin = getattr(getattr(interaction.user, "guild_permissions", None), "administrator", False)

        if not (is_creator or is_admin):
            await interaction.response.send_message(
                "❌ You must be the run creator or a server administrator to delete this run.",
                ephemeral=True
            )
            return

        # Delete and persist
        del RUNS[run_id]
        _save_runs(RUNS)

        await interaction.response.send_message(f"🗑️ Run **{run_id}** deleted.")
    except ValueError as e:
        await interaction.response.send_message(f"❌ {e}", ephemeral=True)

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Please set DISCORD_BOT_TOKEN environment variable.")
    bot.run(token)