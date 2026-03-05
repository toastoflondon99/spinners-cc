#!/usr/bin/env python3
"""Spinners Cycling Club — Vercel Serverless API with Turso (HTTP API)"""
import json
import os
import sqlite3
import urllib.request
import urllib.error
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler

TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")


# ── Turso HTTP API client (zero dependencies) ──

def _turso_http_url():
    """Convert libsql:// URL to https:// pipeline URL."""
    url = TURSO_URL
    url = url.replace("libsql://", "https://")
    url = url.replace("ws://", "http://")
    url = url.replace("wss://", "https://")
    if not url.startswith("http"):
        url = "https://" + url
    return url.rstrip("/") + "/v2/pipeline"


def _turso_request(requests_body):
    """Send a pipeline request to Turso HTTP API and return parsed JSON."""
    url = _turso_http_url()
    data = json.dumps({"requests": requests_body}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {TURSO_TOKEN}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def turso_execute(sql, args=None):
    """Execute a single SQL statement via Turso HTTP API. Returns rows as list of dicts."""
    stmt = {"sql": sql}
    if args:
        stmt["args"] = [{"type": "text" if isinstance(a, str) else
                          "integer" if isinstance(a, int) else
                          "float" if isinstance(a, float) else
                          "null", "value": str(a) if a is not None else None}
                         for a in args]
    body = [
        {"type": "execute", "stmt": stmt},
        {"type": "close"}
    ]
    resp = _turso_request(body)
    results = resp.get("results", [])
    if not results:
        return []
    result = results[0]
    if result.get("type") == "error":
        raise Exception(f"Turso error: {result.get('error', {}).get('message', 'unknown')}")
    response = result.get("response", {})
    res = response.get("result", {})
    cols = [c["name"] for c in res.get("cols", [])]
    rows_raw = res.get("rows", [])
    rows = []
    for row in rows_raw:
        d = {}
        for i, col in enumerate(cols):
            cell = row[i]
            val = cell.get("value")
            if cell.get("type") == "integer" and val is not None:
                val = int(val)
            elif cell.get("type") == "float" and val is not None:
                val = float(val)
            d[col] = val
        rows.append(d)
    return rows


def turso_execute_many(statements):
    """Execute multiple statements in one pipeline request."""
    body = []
    for sql, args in statements:
        stmt = {"sql": sql}
        if args:
            stmt["args"] = [{"type": "text" if isinstance(a, str) else
                              "integer" if isinstance(a, int) else
                              "float" if isinstance(a, float) else
                              "null", "value": str(a) if a is not None else None}
                             for a in args]
        body.append({"type": "execute", "stmt": stmt})
    body.append({"type": "close"})
    return _turso_request(body)


def turso_insert(sql, args=None):
    """Execute an INSERT and return last_insert_rowid."""
    stmt = {"sql": sql}
    if args:
        stmt["args"] = [{"type": "text" if isinstance(a, str) else
                          "integer" if isinstance(a, int) else
                          "float" if isinstance(a, float) else
                          "null", "value": str(a) if a is not None else None}
                         for a in args]
    body = [
        {"type": "execute", "stmt": stmt},
        {"type": "close"}
    ]
    resp = _turso_request(body)
    results = resp.get("results", [])
    if results and results[0].get("type") != "error":
        return results[0].get("response", {}).get("result", {}).get("last_insert_rowid", 0)
    return 0


# ── Local SQLite fallback (for dev without Turso) ──

def local_execute(sql, args=None):
    conn = sqlite3.connect("/tmp/spinners.db", check_same_thread=False)
    cur = conn.execute(sql, args or [])
    if cur.description:
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    else:
        rows = []
    conn.commit()
    conn.close()
    return rows


def local_insert(sql, args=None):
    conn = sqlite3.connect("/tmp/spinners.db", check_same_thread=False)
    cur = conn.execute(sql, args or [])
    conn.commit()
    rowid = cur.lastrowid
    conn.close()
    return rowid


# ── Unified DB interface ──

def use_turso():
    return bool(TURSO_URL and TURSO_TOKEN)


def db_execute(sql, args=None):
    if use_turso():
        return turso_execute(sql, args)
    return local_execute(sql, args)


def db_insert(sql, args=None):
    if use_turso():
        return turso_insert(sql, args)
    return local_insert(sql, args)


def db_modify(sql, args=None):
    """Execute an UPDATE/DELETE."""
    if use_turso():
        turso_execute(sql, args)
    else:
        local_execute(sql, args)


# ── Init DB ──

def init_db():
    stmts = [
        ("CREATE TABLE IF NOT EXISTS riders (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, target_distance INTEGER DEFAULT 110, fitness_level TEXT DEFAULT 'intermediate', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)", None),
        ("CREATE TABLE IF NOT EXISTS rides (id INTEGER PRIMARY KEY AUTOINCREMENT, rider_id INTEGER NOT NULL, ride_date DATE NOT NULL, distance_km REAL NOT NULL, duration_mins INTEGER, ride_type TEXT DEFAULT 'group', notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (rider_id) REFERENCES riders(id))", None),
        ("CREATE TABLE IF NOT EXISTS training_completions (id INTEGER PRIMARY KEY AUTOINCREMENT, rider_id INTEGER NOT NULL, week_number INTEGER NOT NULL, day_key TEXT NOT NULL, completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(rider_id, week_number, day_key))", None),
    ]

    riders = [
        "Andrew M", "Andrew P", "Dan", "Dan C",
        "Daniel C", "Daryll J", "Dirk V", "Matt T",
        "Michael", "Michael O", "Robert G", "Shapz", "Tim D",
        "Paul M", "Ben H", "James L", "Lachlan T",
        "Mikey H", "Not Paul", "Shannon M", "Jayden V"
    ]
    for name in riders:
        stmts.append(("INSERT OR IGNORE INTO riders (name) VALUES (?)", [name]))

    if use_turso():
        turso_execute_many(stmts)
    else:
        conn = sqlite3.connect("/tmp/spinners.db", check_same_thread=False)
        for sql, args in stmts:
            try:
                conn.execute(sql, args or [])
            except Exception:
                pass
        conn.commit()
        conn.close()


_db_initialized = False

def ensure_db():
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True


# ── Training plan generator ──

def generate_training_plan(target_distance, fitness_level):
    event_date = date(2026, 4, 12)
    today = date.today()
    weeks_to_event = max(1, (event_date - today).days // 7)
    plan_weeks = min(weeks_to_event, 6)
    is_110 = target_distance >= 100

    if fitness_level == "beginner":
        long_ride_start = 30 if is_110 else 25
        long_ride_peak = 85 if is_110 else 65
    elif fitness_level == "advanced":
        long_ride_start = 50 if is_110 else 40
        long_ride_peak = 100 if is_110 else 75
    else:
        long_ride_start = 40 if is_110 else 30
        long_ride_peak = 90 if is_110 else 70

    plan = []
    for week in range(1, plan_weeks + 1):
        is_taper = week == plan_weeks
        is_recovery = week == 3 and plan_weeks >= 5
        progress = week / max(plan_weeks - 1, 1)
        long_ride_km = round(long_ride_start + (long_ride_peak - long_ride_start) * min(progress, 1))

        if is_taper:
            long_ride_km = round(long_ride_km * 0.5)
        elif is_recovery:
            long_ride_km = round(long_ride_km * 0.7)

        week_plan = {
            "week": week,
            "week_start": (today + timedelta(weeks=week - 1)).isoformat(),
            "theme": "",
            "days": {}
        }

        if is_taper:
            week_plan["theme"] = "TAPER WEEK \u2014 Fresh legs for race day"
            week_plan["days"] = {
                "tue": {"title": "Easy Spin", "description": "30-40 min easy spin. Keep the legs moving, nothing hard.", "duration": "30-40 min", "type": "easy", "zone": "Zone 1-2"},
                "thu": {"title": "Short Openers", "description": "30 min easy with 4x30 sec hard efforts. Rest 2 min between. Flush out the legs.", "duration": "30 min", "type": "intervals", "zone": "Zone 2 + Zone 5 spikes"},
                "sat": {"title": "Shakeout Ride", "description": f"Easy {long_ride_km}km ride. Relaxed pace, maybe ride part of the course if you can. Check your bike, tyres, nutrition plan.", "duration": f"{long_ride_km}km", "type": "long", "zone": "Zone 1-2"},
                "sun": {"title": "RACE DAY \u2014 Tour de Brisbane", "description": f"{'110km' if is_110 else '80km'} Tour de Brisbane! Pace yourself on the first half. Save energy for Mt Coot-tha. Eat every 30-40 min. Drink before you're thirsty. Smash it boys!", "duration": f"{'110' if is_110 else '80'}km", "type": "event", "zone": "Race pace"}
            }
        elif is_recovery:
            week_plan["theme"] = "RECOVERY WEEK \u2014 Absorb the gains"
            week_plan["days"] = {
                "tue": {"title": "Easy Recovery Ride", "description": "45 min easy spin. Conversational pace. Coffee stop mandatory.", "duration": "45 min", "type": "easy", "zone": "Zone 1-2"},
                "thu": {"title": "Light Tempo", "description": "50 min with 2x8 min tempo (Zone 3). Easy between. Nothing heroic.", "duration": "50 min", "type": "tempo", "zone": "Zone 2-3"},
                "sat": {"title": f"Steady Long Ride \u2014 {long_ride_km}km", "description": f"Reduced distance this week. {long_ride_km}km at comfortable pace. Good group ride day.", "duration": f"~{round(long_ride_km / 25)}h", "type": "long", "zone": "Zone 2"}
            }
        else:
            if week <= 2:
                week_plan["theme"] = f"BUILD PHASE {week} \u2014 Base & endurance"
                tue_session = {"title": "Spiked Efforts", "description": f"90 min ride with {week + 1}x10 min blocks of Zone 3 effort. Include a 20-sec spike to Zone 5 every 2 minutes within each block. Zone 2 between blocks. Great for building race fitness.", "duration": "90 min", "type": "intervals", "zone": "Zone 3 + Zone 5 spikes"}
                thu_session = {"title": "Threshold Ramps", "description": f"90 min ride with {week + 1}x12 min threshold ramps. Start each in Zone 2, ramp up through Zone 3-4 to Zone 5 by the end. Strong but controlled. Zone 2 recovery between.", "duration": "90 min", "type": "threshold", "zone": "Zone 2-5 progressive"}
            elif week <= 5:
                week_plan["theme"] = "PEAK PHASE \u2014 Race simulation"
                tue_session = {"title": "Hill Repeats", "description": f"90 min with {min(week, 5)}x5 min hill efforts (Zone 4-5). Find a steep climb \u2014 think Mt Coot-tha prep. Seated for 3 min, standing for 2 min. Zone 2 recovery descents.", "duration": "90 min", "type": "hills", "zone": "Zone 4-5"}
                thu_session = {"title": "Race Pace Blocks", "description": "90 min with 2x20 min at target race pace (Zone 3-4). This is what it'll feel like on the day. Practice eating and drinking during efforts.", "duration": "90 min", "type": "tempo", "zone": "Zone 3-4"}
            else:
                week_plan["theme"] = "SHARPEN \u2014 Fine-tuning"
                tue_session = {"title": "Short Sharp Efforts", "description": "75 min with 6x3 min at Zone 4-5 with 3 min recovery. Keep the top end sharp without digging deep.", "duration": "75 min", "type": "intervals", "zone": "Zone 4-5"}
                thu_session = {"title": "Tempo + Openers", "description": "60 min with 15 min Zone 3 tempo, then 4x30 sec sprints. Keeping the engine running without fatigue.", "duration": "60 min", "type": "tempo", "zone": "Zone 3 + sprints"}

            week_plan["days"] = {
                "tue": tue_session,
                "wed": {"title": "Group Ride \u2014 Spinners!", "description": "Morning group ride with the boys. Solid pace, practice riding in a bunch. Communication, drafting, rotating through. This is what it's all about.", "duration": "60-90 min", "type": "group", "zone": "Zone 2-3"},
                "thu": thu_session,
                "sat": {"title": f"Long Ride \u2014 {long_ride_km}km", "description": f"Build that endurance. {long_ride_km}km at a steady Zone 2 pace. Practice your race day nutrition \u2014 aim to eat something every 30-40 min after the first hour. {'Include Mt Coot-tha if possible.' if week >= 4 and is_110 else 'Steady and consistent.'}", "duration": f"~{round(long_ride_km / 25, 1)}h", "type": "long", "zone": "Zone 2"}
            }

        plan.append(week_plan)

    nutrition = {
        "race_day": [
            "Big breakfast 3 hours before start \u2014 oats, banana, toast with peanut butter",
            "Eat every 30-40 minutes on the bike \u2014 gels, bars, bananas",
            "Drink 500-750ml per hour \u2014 more if it's hot",
            "Start eating early \u2014 don't wait until you're hungry",
            "Caffeine gel or flat Coke at km 60+ for the final push"
        ],
        "training": [
            "Protein shake or meal within 30 min of finishing a ride",
            "Carb load 2 days before the event \u2014 pasta, rice, bread",
            "Stay hydrated all week, not just on ride days",
            "Good sleep is the best performance enhancer"
        ]
    }

    coottha = {
        "gradient": "2km at 9% average",
        "tips": [
            "Pace yourself \u2014 it comes at km 67 on the 110km, you'll be fatigued",
            "Stay seated for the first half to save your legs",
            "Find a rhythm \u2014 don't surge and blow up",
            "Gear down early, don't wait until you're grinding",
            "The descent is technical \u2014 don't cook it on the way down"
        ]
    }

    return {
        "plan": plan,
        "nutrition": nutrition,
        "coottha": coottha,
        "target_distance": target_distance,
        "fitness_level": fitness_level,
        "weeks_to_event": weeks_to_event,
        "event_date": "2026-04-12"
    }


# ── Request handler ──

def json_response(self, data, status=200):
    self.send_response(status)
    self.send_header("Content-Type", "application/json")
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type")
    self.end_headers()
    self.wfile.write(json.dumps(data).encode())

def read_body(self):
    length = int(self.headers.get("Content-Length", 0))
    if length:
        return json.loads(self.rfile.read(length))
    return {}

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        ensure_db()
        path = self.path.split("?")[0]
        params = {}
        if "?" in self.path:
            for p in self.path.split("?")[1].split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k] = v

        try:
            if path == "/api/index":
                rows = db_execute("SELECT * FROM riders ORDER BY name")
                json_response(self, rows)

            elif path.startswith("/api/index") and "/rider/" in path:
                rider_id = int(path.split("/rider/")[1])
                rows = db_execute("SELECT * FROM riders WHERE id = ?", [rider_id])
                if not rows:
                    json_response(self, {"error": "Rider not found"}, 404)
                else:
                    json_response(self, rows[0])

            elif path == "/api/rides":
                rider_id = params.get("rider_id")
                if rider_id:
                    rows = db_execute("""
                        SELECT r.*, ri.name as rider_name
                        FROM rides r JOIN riders ri ON r.rider_id = ri.id
                        WHERE r.rider_id = ?
                        ORDER BY r.ride_date DESC
                    """, [int(rider_id)])
                else:
                    rows = db_execute("""
                        SELECT r.*, ri.name as rider_name
                        FROM rides r JOIN riders ri ON r.rider_id = ri.id
                        ORDER BY r.ride_date DESC
                        LIMIT 100
                    """)
                json_response(self, rows)

            elif path == "/api/stats":
                rider_stats = db_execute("""
                    SELECT
                        ri.id, ri.name, ri.target_distance, ri.fitness_level,
                        COUNT(r.id) as total_rides,
                        COALESCE(SUM(r.distance_km), 0) as total_km,
                        COALESCE(SUM(r.duration_mins), 0) as total_mins,
                        MAX(r.ride_date) as last_ride,
                        COUNT(DISTINCT r.ride_date) as ride_days
                    FROM riders ri
                    LEFT JOIN rides r ON ri.id = r.rider_id
                    GROUP BY ri.id
                    ORDER BY total_km DESC
                """)

                this_week = db_execute("""
                    SELECT DISTINCT ri.name, ri.id
                    FROM rides r JOIN riders ri ON r.rider_id = ri.id
                    WHERE r.ride_date >= date('now', 'weekday 0', '-7 days')
                    ORDER BY ri.name
                """)

                json_response(self, {
                    "rider_stats": rider_stats,
                    "this_week_riders": this_week,
                    "event_date": "2026-04-12",
                    "total_riders": len(rider_stats)
                })

            elif path.startswith("/api/training/"):
                rider_id = int(path.split("/api/training/")[1])
                riders = db_execute("SELECT * FROM riders WHERE id = ?", [rider_id])
                if not riders:
                    json_response(self, {"error": "Rider not found"}, 404)
                else:
                    rider = riders[0]
                    completions = db_execute(
                        "SELECT week_number, day_key FROM training_completions WHERE rider_id = ?",
                        [rider_id]
                    )
                    plan = generate_training_plan(rider["target_distance"], rider["fitness_level"])
                    plan["completed"] = [{"week": c["week_number"], "day": c["day_key"]} for c in completions]
                    plan["rider"] = rider
                    json_response(self, plan)

            else:
                json_response(self, {"error": "Not found"}, 404)
        except Exception as e:
            json_response(self, {"error": str(e)}, 500)

    def do_POST(self):
        ensure_db()
        path = self.path.split("?")[0]
        body = read_body(self)

        try:
            if path == "/api/rides":
                # Collect all rider IDs — the logger plus anyone they tagged
                all_rider_ids = [body["rider_id"]]
                extra_ids = body.get("additional_rider_ids", [])
                for rid in extra_ids:
                    if rid and rid != body["rider_id"] and rid not in all_rider_ids:
                        all_rider_ids.append(rid)

                created = []
                for rid in all_rider_ids:
                    lastid = db_insert(
                        "INSERT INTO rides (rider_id, ride_date, distance_km, duration_mins, ride_type, notes) VALUES (?, ?, ?, ?, ?, ?)",
                        [rid, body["ride_date"], body["distance_km"],
                         body.get("duration_mins"), body.get("ride_type", "group"), body.get("notes", "")]
                    )
                    rows = db_execute("""
                        SELECT r.*, ri.name as rider_name
                        FROM rides r JOIN riders ri ON r.rider_id = ri.id
                        WHERE r.id = ?
                    """, [lastid])
                    if rows:
                        created.append(rows[0])
                json_response(self, created if len(created) != 1 else created[0], 201)

            elif path == "/api/training/complete":
                db_modify(
                    "INSERT OR REPLACE INTO training_completions (rider_id, week_number, day_key) VALUES (?, ?, ?)",
                    [body["rider_id"], body["week_number"], body["day_key"]]
                )
                json_response(self, {"status": "completed"}, 201)

            else:
                json_response(self, {"error": "Not found"}, 404)
        except Exception as e:
            json_response(self, {"error": str(e)}, 500)

    def do_PUT(self):
        ensure_db()
        path = self.path.split("?")[0]
        body = read_body(self)

        try:
            if "/rider/" in path:
                rider_id = int(path.split("/rider/")[1])
                db_modify("UPDATE riders SET target_distance = ?, fitness_level = ? WHERE id = ?",
                          [body.get("target_distance", 110), body.get("fitness_level", "intermediate"), rider_id])
                rows = db_execute("SELECT * FROM riders WHERE id = ?", [rider_id])
                json_response(self, rows[0] if rows else {})
            else:
                json_response(self, {"error": "Not found"}, 404)
        except Exception as e:
            json_response(self, {"error": str(e)}, 500)

    def do_DELETE(self):
        ensure_db()
        path = self.path.split("?")[0]
        params = {}
        if "?" in self.path:
            for p in self.path.split("?")[1].split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k] = v

        try:
            if path.startswith("/api/rides/"):
                ride_id = int(path.split("/api/rides/")[1])
                db_modify("DELETE FROM rides WHERE id = ?", [ride_id])
                json_response(self, {"deleted": ride_id})

            elif path == "/api/training/complete":
                rider_id = params.get("rider_id")
                week_number = params.get("week_number")
                day_key = params.get("day_key")
                db_modify(
                    "DELETE FROM training_completions WHERE rider_id = ? AND week_number = ? AND day_key = ?",
                    [rider_id, week_number, day_key]
                )
                json_response(self, {"status": "uncompleted"})

            else:
                json_response(self, {"error": "Not found"}, 404)
        except Exception as e:
            json_response(self, {"error": str(e)}, 500)
