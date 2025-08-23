# Spice Distribution Discord Bot

A Discord bot for **Dune Awakening** guilds to calculate fair distributions for **Spice Melange**, **Stravidium Fibers**, and **Plastanium**.

## Commands
- **/spice** — convert Spice Sand to Melange and split among players (floored), with water and time per processor.
- **/plastanium_raw** — split raw **Stravidium Mass → Fiber** and **Titanium Ore** among players; includes water/time per **Medium Chemical Refinery**.
- **/plastanium** — convert **Mass → Fiber** and then **Fiber + Titanium → Plastanium** using **Large Ore Refineries**; shows water/time for each stage and per-player plastanium (floored).
- **/help_spicebot** — prints the quick usage guide.

## Ratios & Timing
- **Spice (Large Spice Refinery)**: 10,000 Sand → 200 Melange, needs 75,000 Water, takes 2,700 s.
- **Stravidium Fiber (Medium Chemical Refinery)**: 3 Mass + 100 mL Water → 1 Fiber, 10 s per Fiber.
- **Plastanium (Large Ore Refinery)**: 1 Fiber + 4 Titanium + 1250 mL Water → 1 Plastanium, 20 s per piece.


## Slash command
/spice sand:<amount> players:<count> processors:<count>
Example:
/spice sand:25000 players:4 processors:2
/plastanium_raw strav_mass:<amount> titanium_ore:<amount> players:<count> chem_refineries:<count>
Example:
/plastanium_raw strav_mass:100 players:4 chem_refineries:2
/plastanium strav_mass:<amount> titanium_ore:<amount> players:<count> large_refineries:<count> chem_refineries:<count>
Example:
/plastanium strav_mass:1000 titanium_ore:10000 players:4 large_refineries:2 chem_refineries:2
/run kind:<spice|plastanium|stravidium> players_csv:<Player1,Player2,...> -> create a run and will return a run id
Example:
/run kind:spice players_csv:Alice,Bob,Charlie
/run_update run_id:<id> field:<players|spice|plastanium|stravidium|titanium> [value:<PlayerName>] [amount:<number>] -> update a run
Example:
/run_update run_id:123 field:spice amount:50000
/run_update run_id:123 field:players value:Dave -> add a player
/run_calculate run_id:<id> processors:<count> -> calculate cuts for a run
Example:
/run_calculate run_id:123 processors:2
/run_view run_id:<id> -> view current state of a run
Example:
/run_view run_id:123
/run_delete run_id:<id> -> delete a run (creator or admin only)
Example:
/run_delete run_id:123
/help_spicebot


# Local run commandline (optional)
```bash
python .\cmd\spice_calculatorv3.py
```
# Deploy to Fly.io

Prereqs

Install Fly CLI: https://fly.io/docs/hands-on/install-flyctl/

Login:
```bash
flyctl auth login
```

1) Initialize the app (no HTTP service)
```bash
flyctl launch --no-deploy
# Answer "No" to databases and "No" to deploy now
```
2) fly.toml

Open the generated fly.toml and make it minimal:
```toml
# fly.toml app configuration file generated for dascdiscord on 2025-08-17T12:11:03-04:00
#
# See https://fly.io/docs/reference/configuration/ for information about how to use this file.
#

app = 'dascdiscord'
primary_region = 'mia'

[build]
  dockerfile = "Dockerfile"

[processes]
  app = "python bot.py"

[[vm]]
  memory = '256mb'
  cpu_kind = 'shared'
  cpus = 1

[experimental]
  auto_rollback = true

```
3) Secrets
```bash
flyctl secrets set DISCORD_BOT_TOKEN="YOUR_TOKEN"
```
4) Deploy
```bash
flyctl deploy
```
5) Monitor
```bash
flyctl logs
flyctl status
```
# Discord Setup

Create the bot in Discord

Go to https://discord.com/developers/applications → New Application → Bot → Reset Token (copy it).

Under Privileged Gateway Intents, you don’t need any for this bot. Leave them off.

Under OAuth2 → URL Generator, select bot and applications.commands, then give it minimal Bot Permissions (none needed for slash commands; sending messages happens via interactions). Copy the invite URL and add the bot to your server.

# Local command line version

To run the calculator locally on the command line (not a discord bot) from the root directory of the app run

```bash
python .\cmd\spice_calc_cmd.py
```
And follow the prompts.