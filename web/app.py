# app.py
import json, math, os
from pathlib import Path
from uuid import uuid4
from flask import Flask, request, redirect, url_for, render_template_string, flash
from jinja2 import DictLoader

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret")  # set a real secret in prod

# ---------------------------
# Ratios / constants
# ---------------------------
# Spice (Large Spice Refinery)
SAND_PER_BATCH = 10_000
MELANGE_PER_BATCH = 200
WATER_PER_BATCH = 75_000
SEC_PER_BATCH = 2_700

# Stravidium Fiber (Medium Chemical Refinery)
STRAV_MASS_PER_FIBER = 3
WATER_PER_FIBER = 100
SEC_PER_FIBER = 10

# Plastanium (Large Ore Refinery)
TI_PER_PLASTANIUM_LARGE = 4
FIBER_PER_PLASTANIUM = 1
WATER_PER_PLASTANIUM = 1250
SEC_PER_PLASTANIUM_LARGE = 20

# Run persistence
RUNS_PATH = Path("runs_web.json")

def load_runs():
    if RUNS_PATH.exists():
        try:
            return json.loads(RUNS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_runs(data):
    RUNS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

RUNS = load_runs()

# ---------------------------
# Helpers
# ---------------------------
def hms(seconds: float) -> str:
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

def calc_spice(sand: float, players: int, processors: int):
    scale = sand / SAND_PER_BATCH
    total_melange = MELANGE_PER_BATCH * scale
    total_water = WATER_PER_BATCH * scale
    total_seconds_single = SEC_PER_BATCH * scale
    processors = max(1, processors)
    parallel_seconds = total_seconds_single / processors
    per_player_floor = math.floor(total_melange / max(1, players))
    remainder = total_melange - (per_player_floor * max(1, players))
    return dict(
        total_melange=total_melange,
        melange_per_player=per_player_floor,
        melange_remainder=remainder,
        total_water=total_water,
        water_per_processor=total_water / processors,
        time_seconds_parallel=parallel_seconds,
    )

def compute_fibers(strav_mass: int, chem_refineries: int):
    """Mass -> Fibers stage. Includes raw consumption & leftovers."""
    chem_refineries = max(1, chem_refineries)
    fibers = strav_mass // STRAV_MASS_PER_FIBER
    raw_consumed = fibers * STRAV_MASS_PER_FIBER
    raw_leftover = strav_mass - raw_consumed
    water_total = fibers * WATER_PER_FIBER
    time_single = fibers * SEC_PER_FIBER
    return dict(
        fibers=fibers,
        raw_consumed=raw_consumed,
        raw_leftover=raw_leftover,
        water_total=water_total,
        water_per_refinery=water_total / chem_refineries,
        time_per_refinery_sec=time_single / chem_refineries,
    )

def compute_plastanium_large(fibers_avail: int, titanium_ore: int, large_refineries: int):
    """
    Fiber + Titanium -> Plastanium (Large Ore Refinery).
    Includes material usage & leftovers.
    """
    large_refineries = max(1, large_refineries)
    max_by_fiber = fibers_avail // FIBER_PER_PLASTANIUM
    max_by_titanium = titanium_ore // TI_PER_PLASTANIUM_LARGE
    pieces = min(max_by_fiber, max_by_titanium)

    fiber_used = pieces * FIBER_PER_PLASTANIUM
    titanium_used = pieces * TI_PER_PLASTANIUM_LARGE
    fiber_leftover = fibers_avail - fiber_used
    titanium_leftover = titanium_ore - titanium_used

    water_total = pieces * WATER_PER_PLASTANIUM
    time_single = pieces * SEC_PER_PLASTANIUM_LARGE
    return dict(
        pieces=pieces,
        water_total=water_total,
        water_per_refinery=water_total / large_refineries,
        time_per_refinery_sec=time_single / large_refineries,
        # usage/leftovers
        fiber_used=fiber_used,
        fiber_leftover=fiber_leftover,
        titanium_used=titanium_used,
        titanium_leftover=titanium_leftover,
    )

# ---------------------------
# UI (Dune-styled)
# ---------------------------
BASE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Dune Ops Tools</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root{
      --bg:#0b0e12; --surface:#12161d; --surface-2:#171c24; --border:#29303a;
      --text:#e7e2d6; --muted:#b9b2a3; --gold:#c8a86a; --gold-2:#a8823e;
      --warn:#e0b156; --error:#d46a6a; --r-sm:.5rem; --r-md:.75rem; --r-lg:1rem;
      --pad:1rem; --shadow:0 6px 20px rgba(0,0,0,.35);
    }
    html,body{background:radial-gradient(1200px 800px at 60% -10%, #121720 0%, #0b0e12 60%, #0b0e12 100%) fixed;
      color:var(--text); font-family:Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; line-height:1.55; margin:0;}
    a{color:var(--gold); text-decoration:none;} a:hover{color:var(--gold-2); text-decoration:underline;}
    header{padding:1.2rem 1rem 0; max-width:1100px; margin:0 auto;}
    main{padding:1rem; max-width:1100px; margin:0 auto;}
    footer{max-width:1100px; margin:0 auto; padding:1rem; color:var(--muted);}
    h1,h2,h3{font-family:Cinzel,serif; letter-spacing:.02em; margin:0 0 .6rem 0; color:var(--text); text-shadow:0 1px 0 rgba(0,0,0,.3);}
    h1{font-weight:700; font-size:clamp(1.6rem,3.6vw,2.4rem);}
    h2{font-weight:600; font-size:clamp(1.2rem,2.8vw,1.6rem); color:var(--gold);}
    h3{font-weight:600; font-size:1.1rem; color:var(--gold);}
    p,li,small{color:var(--text);} .muted{color:var(--muted);}
    .grid{display:grid; gap:1rem; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));}
    .split{display:flex; gap:1rem; flex-wrap:wrap; align-items:flex-start;}
    .mono{font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;}
    .card{background:linear-gradient(180deg, rgba(200,168,106,.06), rgba(200,168,106,0) 20%), var(--surface);
      border:1px solid var(--border); border-radius:var(--r-lg); box-shadow:var(--shadow); padding:var(--pad);}
    .badge{display:inline-block; margin-left:.5rem; padding:.2rem .55rem; border-radius:999px; border:1px solid var(--gold); color:var(--gold); font-size:.8rem;}
    hr{border:none; height:1px; background:linear-gradient(90deg, rgba(200,168,106,.0), rgba(200,168,106,.6), rgba(200,168,106,.0)); margin:1rem 0;}
    form label{display:block; font-size:.95rem; margin:.6rem 0 .2rem; color:var(--muted);}
    input,select,button,textarea{font:inherit; border-radius:var(--r-sm);}
    input,select,textarea{background:var(--surface-2); border:1px solid var(--border); color:var(--text); padding:.7rem .8rem; width:100%; outline:none; transition:border-color .15s, box-shadow .15s;}
    input:focus,select:focus,textarea:focus{border-color:var(--gold); box-shadow:0 0 0 3px rgba(200,168,106,.2);}
    button{margin-top:.8rem; background:linear-gradient(180deg, var(--gold), var(--gold-2)); color:#1b140a; font-weight:600; border:1px solid var(--gold-2); padding:.65rem 1rem; cursor:pointer;
      box-shadow:inset 0 1px 0 rgba(255,255,255,.25), 0 6px 14px rgba(0,0,0,.35);}
    button:hover{filter:brightness(1.02);}
    button.warn{background:linear-gradient(180deg, #f0c06f, #b98024); border-color:#a36c1d; color:#1b140a;}
    button.danger{background:linear-gradient(180deg, #e06161, #a02020); border:1px solid #7f1616; color:#fff; box-shadow:inset 0 1px 0 rgba(255,255,255,.15), 0 6px 14px rgba(0,0,0,.35);}
    button.danger:hover{filter:brightness(1.02);}
    pre{background:#0f131a; border:1px solid var(--border); border-left:3px solid var(--gold); border-radius:var(--r-md); padding:.9rem 1rem; color:var(--text); overflow-x:auto;}
    nav a{display:inline-block; margin-right:.8rem; padding-bottom:.15rem; border-bottom:2px solid transparent;}
    nav a:hover{border-bottom-color:var(--gold);}
    .hidden{display:none !important;}
    h2.section-title{position:relative; padding-bottom:.4rem;}
    h2.section-title::after{content:""; position:absolute; left:0; bottom:-.2rem; width:96px; height:2px; background:linear-gradient(90deg, var(--gold), transparent); border-radius:2px; opacity:.9;}
  </style>
</head>
<body>
<header>
  <h1>Dune Ops Tools <span class="badge">Spice • Stravidium • Plastanium</span></h1>
  <p class="muted">Calculators + Run Tracker for guild ops.</p>
  <nav>
    <a href="{{ url_for('index') }}">Calculators</a> ·
    <a href="{{ url_for('runs') }}">Run Tracker</a>
  </nav>
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <ul>
        {% for m in messages %}<li class="warn">{{ m }}</li>{% endfor %}
      </ul>
    {% endif %}
  {% endwith %}
  <hr/>
</header>
<main>
  {% block content %}{% endblock %}
</main>
<footer>
  <hr/>
  <small class="muted">Fly-ready • Flask on port 8080 • Data: runs_web.json</small>
</footer>

<script>
  // Toggle Update Run inputs based on field selection
  document.addEventListener('DOMContentLoaded', function () {
    const fieldSel   = document.getElementById('update-field');
    const valueRow   = document.getElementById('update-row-value');
    const amountRow  = document.getElementById('update-row-amount');
    const valueInput = document.getElementById('update-value');
    const amtInput   = document.getElementById('update-amount');

    function sync() {
      if (!fieldSel) return;
      if (fieldSel.value === 'players') {
        valueRow.classList.remove('hidden');
        amountRow.classList.add('hidden');
        valueInput.required = true;
        amtInput.required   = false;
        amtInput.value      = '';
      } else {
        valueRow.classList.add('hidden');
        amountRow.classList.remove('hidden');
        valueInput.required = false;
        amtInput.required   = true;
        valueInput.value    = '';
      }
    }
    if (fieldSel) {
      fieldSel.addEventListener('change', sync);
      sync(); // initialize on load
    }
  });
</script>
</body>
</html>
"""

INDEX_HTML = """
{% extends "base.html" %}
{% block content %}
<h2 class="section-title">Calculators</h2>

<div class="grid">
  <section class="card">
    <h3>Spice</h3>
    <form method="post" action="{{ url_for('calc_spice_route') }}">
      <label>Spice Sand <input type="number" name="sand" step="any" required></label>
      <label>Players <input type="number" name="players" value="4" min="1" required></label>
      <label>Processors (Spice Refineries) <input type="number" name="processors" value="1" min="1" required></label>
      <button>Calculate</button>
    </form>
    {% if spice %}
      <hr/>
      <pre class="mono">
Total Melange: {{ '%.2f'|format(spice.total_melange) }}
Melange per Player (floored): {{ spice.melange_per_player }}
Unallocated Remainder: {{ '%.2f'|format(spice.melange_remainder) }}

Total Water: {{ '%.2f'|format(spice.total_water) }}
Water per Processor: {{ '%.2f'|format(spice.water_per_processor) }}
Processing Time (parallel): {{ spice.time_hms }}
      </pre>
    {% endif %}
  </section>

  <section class="card">
    <h3>Plastanium — Raw Split</h3>
    <form method="post" action="{{ url_for('calc_plast_raw_route') }}">
      <label>Stravidium Mass <input type="number" name="strav_mass" min="0" required></label>
      <label>Titanium Ore <input type="number" name="titanium" min="0" required></label>
      <label>Players <input type="number" name="players" value="4" min="1" required></label>
      <label>Chem Refineries (Medium) <input type="number" name="chem" value="1" min="1" required></label>
      <button>Calculate</button>
    </form>
    {% if plast_raw %}
      <hr/>
      <pre class="mono">
Total Fibers: {{ plast_raw.fibers_total }}
Water per Chem Refinery: {{ plast_raw.water_per_refinery|int }} mL
Time per Chem Refinery: {{ plast_raw.time_hms }}

Fibers per Player (floored): {{ plast_raw.fibers_per_player }}
Titanium per Player (floored): {{ plast_raw.titanium_per_player }}

Raw Stravidium Consumed: {{ plast_raw.raw_consumed }}
Raw Stravidium Leftover: {{ plast_raw.raw_leftover }}
      </pre>
    {% endif %}
  </section>

  <section class="card">
    <h3>Plastanium — Full Craft</h3>
    <form method="post" action="{{ url_for('calc_plast_full_route') }}">
      <label>Stravidium Mass <input type="number" name="strav_mass" min="0" required></label>
      <label>Titanium Ore <input type="number" name="titanium" min="0" required></label>
      <label>Players <input type="number" name="players" value="4" min="1" required></label>
      <label>Chem Refineries (Medium) <input type="number" name="chem" value="1" min="1" required></label>
      <label>Large Ore Refineries <input type="number" name="large" value="1" min="1" required></label>
      <button>Calculate</button>
    </form>
    {% if plast_full %}
      <hr/>
      <pre class="mono">
Fiber Stage (Medium Chemical Refinery)
  Water per Chem Refinery: {{ plast_full.stageA_water|int }} mL
  Time  per Chem Refinery: {{ plast_full.stageA_time_hms }}
  Raw Stravidium Consumed: {{ plast_full.raw_consumed }}
  Raw Stravidium Leftover: {{ plast_full.raw_leftover }}

Plastanium Stage (Large Ore Refinery)
  Water per Large Ore Refinery: {{ plast_full.stageB_water|int }} mL
  Time  per Large Ore Refinery: {{ plast_full.stageB_time_hms }}
  Fiber Used: {{ plast_full.fiber_used }}
  Fiber Leftover: {{ plast_full.fiber_leftover }}
  Titanium Used: {{ plast_full.titanium_used }}
  Titanium Leftover: {{ plast_full.titanium_leftover }}

Total Plastanium: {{ plast_full.plast_total }}
Plastanium per Player (floored): {{ plast_full.per_player }}
Unallocated Remainder: {{ plast_full.remainder }}
      </pre>
    {% endif %}
  </section>
</div>
{% endblock %}
"""

RUNS_HTML = """
{% extends "base.html" %}
{% block content %}
<h2 class="section-title">Run Tracker</h2>
<div class="split">
  <section class="card" style="flex:1 1 360px;">
    <h3>Create Run</h3>
    <form method="post" action="{{ url_for('run_create') }}">
      <label>Type
        <select name="kind" required>
          <option value="spice">spice</option>
          <option value="stravidium">stravidium</option>
          <option value="plastanium">plastanium</option>
        </select>
      </label>
      <label>Players CSV <input name="players" placeholder="Alice,Bob,Charlie" required></label>
      <button>Create</button>
    </form>

    <h3 style="margin-top:2rem">Update Run</h3>
    <form method="post" action="{{ url_for('run_update') }}">
      <label>Run ID <input name="run_id" required></label>
      <label>Field
        <select id="update-field" name="field" required>
          <option value="players">players</option>
          <option value="spice">spice</option>
          <option value="stravidium">stravidium</option>
          <option value="titanium">titanium</option>
          <option value="plastanium">plastanium</option>
        </select>
      </label>

      <div id="update-row-value">
        <label>Value (player name)
          <input id="update-value" name="value" placeholder="NewPlayer">
        </label>
      </div>

      <div id="update-row-amount" class="hidden">
        <label>Amount
          <input id="update-amount" name="amount" type="number" step="any" placeholder="e.g., 25000">
        </label>
      </div>

      <button>Update</button>
    </form>

    <h3 style="margin-top:2rem">Calculate Run</h3>
    <form method="post" action="{{ url_for('run_calculate') }}">
      <label>Run ID <input name="run_id" required></label>
      <div class="row" style="display:flex; gap:.6rem; flex-wrap:wrap;">
        <label>Processors (Spice) <input name="processors" type="number" min="1" value="1"></label>
        <label>Chem Refineries (Medium) <input name="chem" type="number" min="1" value="1"></label>
        <label>Large Ore Refineries <input name="large" type="number" min="1" value="1"></label>
      </div>
      <button>Calculate</button>
    </form>

    <h3 style="margin-top:2rem">View / Delete Run</h3>
    <form id="viewdel" class="row" style="gap:.6rem; align-items:flex-end;">
      <label style="flex:1 1 220px;">
        Run ID
        <input id="vd-runid" name="run_id" required>
      </label>
      <div style="display:flex; gap:.6rem; flex-wrap:wrap;">
        <button formaction="{{ url_for('run_view') }}" formmethod="get">View</button>
        <button class="danger" formaction="{{ url_for('run_delete') }}" formmethod="post"
                onclick="return confirm('Delete this run?');">Delete</button>
      </div>
    </form>
  </section>

  <section class="card" style="flex:2 1 520px;">
    <h3>Output</h3>
    {% if out %}
      <pre class="mono">{{ out }}</pre>
    {% else %}
      <p class="muted">Results and run details will appear here after you submit a form.</p>
    {% endif %}
  </section>
</div>
{% endblock %}
"""

# Register templates
app.jinja_loader = DictLoader({"base.html": BASE_HTML, "index.html": INDEX_HTML, "runs.html": RUNS_HTML})

# ---------------------------
# Routes - Calculators
# ---------------------------
@app.get("/")
def index():
    return render_template_string(INDEX_HTML, spice=None, plast_raw=None, plast_full=None)

@app.post("/calc/spice")
def calc_spice_route():
    try:
        sand = float(request.form["sand"])
        players = int(request.form["players"])
        processors = int(request.form["processors"])
        res = calc_spice(sand, players, processors)
        res["time_hms"] = hms(res["time_seconds_parallel"])
        return render_template_string(INDEX_HTML, spice=res, plast_raw=None, plast_full=None)
    except Exception as e:
        flash(f"Error: {e}")
        return redirect(url_for("index"))

@app.post("/calc/plast_raw")
def calc_plast_raw_route():
    try:
        strav_mass = int(request.form["strav_mass"])
        titanium = int(request.form["titanium"])
        players = int(request.form["players"])
        chem = int(request.form["chem"])
        stageA = compute_fibers(strav_mass, chem)
        fibers_total = int(stageA["fibers"])
        out = dict(
            fibers_total=fibers_total,
            water_per_refinery=stageA["water_per_refinery"],
            time_hms=hms(stageA["time_per_refinery_sec"]),
            fibers_per_player=fibers_total // players,
            titanium_per_player=titanium // players,
            raw_consumed=stageA["raw_consumed"],
            raw_leftover=stageA["raw_leftover"],
        )
        return render_template_string(INDEX_HTML, spice=None, plast_raw=out, plast_full=None)
    except Exception as e:
        flash(f"Error: {e}")
        return redirect(url_for("index"))

@app.post("/calc/plast_full")
def calc_plast_full_route():
    try:
        strav_mass = int(request.form["strav_mass"])
        titanium = int(request.form["titanium"])
        players = int(request.form["players"])
        chem = int(request.form["chem"])
        large = int(request.form["large"])

        stageA = compute_fibers(strav_mass, chem)
        fibers_total = int(stageA["fibers"])
        stageB = compute_plastanium_large(fibers_total, titanium, large)

        plast_total = int(stageB["pieces"])
        out = dict(
            stageA_water=stageA["water_per_refinery"],
            stageA_time_hms=hms(stageA["time_per_refinery_sec"]),
            stageB_water=stageB["water_per_refinery"],
            stageB_time_hms=hms(stageB["time_per_refinery_sec"]),
            plast_total=plast_total,
            per_player=plast_total // players,
            remainder=plast_total - (plast_total // players) * players,
            # leftovers/usage
            raw_consumed=stageA["raw_consumed"],
            raw_leftover=stageA["raw_leftover"],
            fiber_used=stageB["fiber_used"],
            fiber_leftover=stageB["fiber_leftover"],
            titanium_used=stageB["titanium_used"],
            titanium_leftover=stageB["titanium_leftover"],
        )
        return render_template_string(INDEX_HTML, spice=None, plast_raw=None, plast_full=out)
    except Exception as e:
        flash(f"Error: {e}")
        return redirect(url_for("index"))

# ---------------------------
# Routes - Runs
# ---------------------------
@app.get("/runs")
def runs():
    return render_template_string(RUNS_HTML, out=None)

@app.post("/run/create")
def run_create():
    kind = request.form.get("kind", "").strip().lower()
    players_csv = request.form.get("players", "")
    if kind not in ("spice", "stravidium", "plastanium"):
        flash("kind must be spice|stravidium|plastanium")
        return redirect(url_for("runs"))
    players = [p.strip() for p in players_csv.split(",") if p.strip()]
    if not players:
        flash("Provide at least one player.")
        return redirect(url_for("runs"))
    run_id = uuid4().hex[:8]
    RUNS[run_id] = dict(
        kind=kind,
        players=players,
        amounts=dict(spice=0.0, stravidium=0.0, titanium=0.0, plastanium=0.0),
    )
    save_runs(RUNS)
    return render_template_string(RUNS_HTML, out=f"Run created: {run_id}\nType: {kind}\nPlayers: {', '.join(players)}")

@app.post("/run/update")
def run_update():
    run_id = request.form.get("run_id", "").strip()
    field = request.form.get("field", "").strip().lower()
    value = request.form.get("value", "").strip()
    amount = request.form.get("amount", "")
    run = RUNS.get(run_id)
    if not run:
        flash("Run not found.")
        return redirect(url_for("runs"))

    if field == "players":
        if not value:
            flash("Provide Value when field=players.")
            return redirect(url_for("runs"))
        if value in run["players"]:
            return render_template_string(RUNS_HTML, out=f"Player already in roster: {value}")
        run["players"].append(value)
        save_runs(RUNS)
        return render_template_string(RUNS_HTML, out=f"Added player: {value}\nRoster: {', '.join(run['players'])}")

    if field not in ("spice", "stravidium", "titanium", "plastanium"):
        flash("Invalid field. Use players|spice|stravidium|titanium|plastanium.")
        return redirect(url_for("runs"))
    try:
        amt = float(amount)
    except:
        flash("Amount must be a number.")
        return redirect(url_for("runs"))

    run["amounts"][field] = float(run["amounts"].get(field, 0.0)) + amt
    save_runs(RUNS)
    return render_template_string(RUNS_HTML, out=f"Updated {field}. New total: {run['amounts'][field]}")

@app.get("/run/view")
def run_view():
    run_id = request.args.get("run_id", "").strip()
    run = RUNS.get(run_id)
    if not run:
        flash("Run not found.")
        return redirect(url_for("runs"))
    out = [
        f"Run {run_id}",
        f"Type: {run['kind']}",
        f"Players ({len(run['players'])}): {', '.join(run['players']) or '(none)'}",
        "Amounts:",
        f"  spice: {run['amounts'].get('spice', 0)}",
        f"  stravidium: {run['amounts'].get('stravidium', 0)}",
        f"  titanium: {run['amounts'].get('titanium', 0)}",
        f"  plastanium: {run['amounts'].get('plastanium', 0)}",
    ]
    return render_template_string(RUNS_HTML, out="\n".join(out))

@app.post("/run/delete")
def run_delete():
    run_id = request.form.get("run_id", "").strip()
    if run_id in RUNS:
        del RUNS[run_id]
        save_runs(RUNS)
        return render_template_string(RUNS_HTML, out=f"Deleted run {run_id}")
    flash("Run not found.")
    return redirect(url_for("runs"))

@app.post("/run/calculate")
def run_calculate():
    run_id = request.form.get("run_id", "").strip()
    processors = int(request.form.get("processors", "1") or "1")
    chem = int(request.form.get("chem", "1") or "1")
    large = int(request.form.get("large", "1") or "1")
    run = RUNS.get(run_id)
    if not run:
        flash("Run not found.")
        return redirect(url_for("runs"))

    players = run["players"]
    n_players = max(1, len(players))
    kind = run["kind"]
    amounts = run["amounts"]

    # SPICE
    if kind == "spice":
        sand = float(amounts.get("spice", 0.0))
        if sand <= 0:
            return render_template_string(RUNS_HTML, out="No spice sand recorded.")
        res = calc_spice(sand, n_players, max(1, processors))
        out = [
            f"Run {run_id} — SPICE",
            f"Players ({n_players}): {', '.join(players)}",
            f"Spice Sand: {sand:,.0f} | Spice Refineries: {processors}",
            "",
            f"Total Melange: {res['total_melange']:.2f}",
            f"Melange per Player (floored): {int(res['melange_per_player'])}",
            f"Unallocated Remainder: {res['melange_remainder']:.2f}",
            "",
            f"Total Water: {res['total_water']:.2f}",
            f"Water per Refinery: {res['water_per_processor']:.2f}",
            f"Processing Time (parallel): {hms(res['time_seconds_parallel'])}",
        ]
        return render_template_string(RUNS_HTML, out="\n".join(out))

    # STRAVIDIUM (Mass -> Fiber)
    if kind == "stravidium":
        mass = int(amounts.get("stravidium", 0.0))
        if mass <= 0:
            return render_template_string(RUNS_HTML, out="No stravidium mass recorded.")
        stageA = compute_fibers(mass, max(1, chem))
        fibers_total = int(stageA["fibers"])
        per_player = fibers_total // n_players
        remainder = fibers_total - per_player * n_players
        out = [
            f"Run {run_id} — STRAVIDIUM",
            f"Players ({n_players}): {', '.join(players)}",
            f"Stravidium Mass: {mass:,} | Chem Refineries: {chem}",
            "",
            f"Total Fibers: {fibers_total:,}",
            f"Fibers per Player (floored): {per_player:,}",
            f"Unallocated Remainder: {remainder:,}",
            "",
            f"Water per Chem Refinery: {int(stageA['water_per_refinery'])} mL",
            f"Time per Chem Refinery: {hms(stageA['time_per_refinery_sec'])}",
            "",
            "Leftovers After Fiber Stage",
            f"  Raw Stravidium Consumed: {stageA['raw_consumed']:,}",
            f"  Raw Stravidium Leftover: {stageA['raw_leftover']:,}",
        ]
        return render_template_string(RUNS_HTML, out="\n".join(out))

    # PLASTANIUM (Mass -> Fiber -> Plastanium)
    if kind == "plastanium":
        mass = int(amounts.get("stravidium", 0.0))
        titanium = int(amounts.get("titanium", 0.0))
        if mass <= 0 or titanium <= 0:
            return render_template_string(RUNS_HTML, out="Plastanium run requires both stravidium mass and titanium.")
        chem_ref = max(1, chem)
        large_ref = max(1, large)

        stageA = compute_fibers(mass, chem_ref)
        fibers_total = int(stageA["fibers"])
        stageB = compute_plastanium_large(fibers_total, titanium, large_ref)
        plast_total = int(stageB["pieces"])
        per_player = plast_total // n_players
        remainder = plast_total - per_player * n_players

        out = [
            f"Run {run_id} — PLASTANIUM",
            f"Players ({n_players}): {', '.join(players)}",
            f"Inputs — Stravidium Mass: {mass:,}, Titanium Ore: {titanium:,}",
            f"Chem Refineries: {chem_ref} | Large Ore Refineries: {large_ref}",
            "",
            "Fiber Stage (Medium Chemical Refinery)",
            f"  Water per Chem Refinery: {int(stageA['water_per_refinery'])} mL",
            f"  Time  per Chem Refinery: {hms(stageA['time_per_refinery_sec'])}",
            f"  Raw Stravidium Consumed: {stageA['raw_consumed']:,}",
            f"  Raw Stravidium Leftover: {stageA['raw_leftover']:,}",
            "",
            "Plastanium Stage (Large Ore Refinery)",
            f"  Water per Large Ore Refinery: {int(stageB['water_per_refinery'])} mL",
            f"  Time  per Large Ore Refinery: {hms(stageB['time_per_refinery_sec'])}",
            f"  Fiber Used: {stageB['fiber_used']:,}",
            f"  Fiber Leftover: {stageB['fiber_leftover']:,}",
            f"  Titanium Used: {stageB['titanium_used']:,}",
            f"  Titanium Leftover: {stageB['titanium_leftover']:,}",
            "",
            f"Total Plastanium: {plast_total:,}",
            f"Plastanium per Player (floored): {per_player:,}",
            f"Unallocated Remainder: {remainder:,}",
        ]
        return render_template_string(RUNS_HTML, out="\n".join(out))

    return render_template_string(RUNS_HTML, out="Unknown run type.")

if __name__ == "__main__":
    # Bind to 0.0.0.0:8080 for Fly
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
