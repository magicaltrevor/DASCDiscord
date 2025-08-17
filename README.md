# Spice Distribution Discord Bot

A Discord bot for **Dune Awakening** guilds to calculate fair distribution of **Spice Melange** from harvested **Spice Sand**.

## What it does
- Uses large refinery ratios:
  - 10,000 Spice Sand → 200 Spice Melange
  - 75,000 Water per 10,000 Sand
  - 2,700 seconds (45 minutes) per 10,000 Sand
- Supports multiple processors (refineries) running in parallel.
- Computes:
  - Total Melange
  - Melange per player (floored to whole units)
  - Unallocated remainder (if any)
  - Total Water required
  - Water per processor
  - Processing time with your processor count (parallel)

## Slash command
/spice sand:<amount> players:<count> processors:<count>
Example:
/spice sand:25000 players:4 processors:2
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