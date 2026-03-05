#!/usr/bin/env python3
"""Spinners Cycling Club — Vercel Serverless API"""
import sqlite3
import json
import os
from datetime import datetime, date, timedelta
from http.server import BaseHTTPRequestHandler

DB_PATH = "/tmp/spinners.db"

def get_db():
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS riders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            target_distance INTEGER DEFAULT 110,
            fitness_level TEXT DEFAULT 'intermediate',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rider_id INTEGER NOT NULL,
            ride_date DATE NOT NULL,
            distance_km REAL NOT NULL,
            duration_mins INTEGER,
            ride_type TEXT DEFAULT 'group',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rider_id) REFERENCES riders(id)
        );

        CREATE TABLE IF NOT EXISTS training_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rider_id INTEGER NOT NULL,
            week_number INTEGER NOT NULL,
            day_key TEXT NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rider_id) REFERENCES riders(id),
            UNIQUE(rider_id, week_number, day_key)
        );
    """)

    riders = [
        "Andrew Mackintosh", "Andrew Parkinson", "Dan", "Dan Crilly",
        "Daniel", "Daryll Johnston", "Dirk van Velden", "Matt T",
        "Michael", "Michael Owen", "Robert Godino", "Shapz", "Tim Donkin",
        "Paul McLean", "Ben Hegerty", "James Lewis", "Lachlan Turner",
        "Mikey Hart Riding", "Not Paul", "Shannon Mccormick", "Jayden V"
    ]
    for name in riders:
        try:
            db.execute("INSERT OR IGNORE INTO riders (name) VALUES (?)", [name])
        except Exception:
            pass
    db.commit()
    db.close()

init_db()

# ── Training plan generator ──

def generate_training_plan(target_distance, fitness_level):
    event_date = date(2026, 4, 12)
    today = date.today()
    weeks_to_event = max(1, (event_date - today).days // 7)
    plan_weeks = min(weeks_to_event, 6)
    is_110 = target_distance >= 100

    if fitness_level == "beginner":
        base_weekly_hours = 4
        long_ride_start = 30 if is_110 else 25
        long_ride_peak = 85 if is_110 else 65
    elif fitness_level == "advanced":
        base_weekly_hours = 8
        long_ride_start = 50 if is_110 else 40
        long_ride_peak = 100 if is_110 else 75
    else:
        base_weekly_hours = 6
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
            week_plan["theme"] = "TAPER WEEK — Fresh legs for race day"
            week_plan["days"] = {
                "tue": {"title": "Easy Spin", "description": "30-40 min easy spin. Keep the legs moving, nothing hard.", "duration": "30-40 min", "type": "easy", "zone": "Zone 1-2"},
                "thu": {"title": "Short Openers", "description": "30 min easy with 4x30 sec hard efforts. Rest 2 min between. Flush out the legs.", "duration": "30 min", "type": "intervals", "zone": "Zone 2 + Zone 5 spikes"},
                "sat": {"title": "Shakeout Ride", "description": f"Easy {long_ride_km}km ride. Relaxed pace, maybe ride part of the course if you can. Check your bike, tyres, nutrition plan.", "duration": f"{long_ride_km}km", "type": "long", "zone": "Zone 1-2"},
                "sun": {"title": "RACE DAY — Tour de Brisbane", "description": f"{'110km' if is_110 else '80km'} Tour de Brisbane! Pace yourself on the first half. Save energy for Mt Coot-tha. Eat every 30-40 min. Drink before you're thirsty. Smash it boys!", "duration": f"{'110' if is_110 else '80'}km", "type": "event", "zone": "Race pace"}
            }
        elif is_recovery:
            week_plan["theme"] = "RECOVERY WEEK — Absorb the gains"
            week_plan["days"] = {
                "tue": {"title": "Easy Recovery Ride", "description": "45 min easy spin. Conversational pace. Coffee stop mandatory.", "duration": "45 min", "type": "easy", "zone": "Zone 1-2"},
                "thu": {"title": "Light Tempo", "description": "50 min with 2x8 min tempo (Zone 3). Easy between. Nothing heroic.", "duration": "50 min", "type": "tempo", "zone": "Zone 2-3"},
                "sat": {"title": f"Steady Long Ride — {long_ride_km}km", "description": f"Reduced distance this week. {long_ride_km}km at comfortable pace. Good group ride day.", "duration": f"~{round(long_ride_km / 25)}h", "type": "long", "zone": "Zone 2"}
            }
        else:
            if week <= 2:
                week_plan["theme"] = f"BUILD PHASE {week} — Base & endurance"
                tue_session = {"title": "Spiked Efforts", "description": f"90 min ride with {week + 1}x10 min blocks of Zone 3 effort. Include a 20-sec spike to Zone 5 every 2 minutes within each block. Zone 2 between blocks. Great for building race fitness.", "duration": "90 min", "type": "intervals", "zone": "Zone 3 + Zone 5 spikes"}
                thu_session = {"title": "Threshold Ramps", "description": f"90 min ride with {week + 1}x12 min threshold ramps. Start each in Zone 2, ramp up through Zone 3-4 to Zone 5 by the end. Strong but controlled. Zone 2 recovery between.", "duration": "90 min", "type": "threshold", "zone": "Zone 2-5 progressive"}
            elif week <= 5:
                week_plan["theme"] = "PEAK PHASE — Race simulation"
                tue_session = {"title": "Hill Repeats", "description": f"90 min with {min(week, 5)}x5 min hill efforts (Zone 4-5). Find a steep climb — think Mt Coot-tha prep. Seated for 3 min, standing for 2 min. Zone 2 recovery descents.", "duration": "90 min", "type": "hills", "zone": "Zone 4-5"}
                thu_session = {"title": "Race Pace Blocks", "description": "90 min with 2x20 min at target race pace (Zone 3-4). This is what it'll feel like on the day. Practice eating and drinking during efforts.", "duration": "90 min", "type": "tempo", "zone": "Zone 3-4"}
            else:
                week_plan["theme"] = "SHARPEN — Fine-tuning"
                tue_session = {"title": "Short Sharp Efforts", "description": "75 min with 6x3 min at Zone 4-5 with 3 min recovery. Keep the top end sharp without digging deep.", "duration": "75 min", "type": "intervals", "zone": "Zone 4-5"}
                thu_session = {"title": "Tempo + Openers", "description": "60 min with 15 min Zone 3 tempo, then 4x30 sec sprints. Keeping the engine running without fatigue.", "duration": "60 min", "type": "tempo", "zone": "Zone 3 + sprints"}

            week_plan["days"] = {
                "tue": tue_session,
                "wed": {"title": "Group Ride — Spinners!", "description": "Morning group ride with the boys. Solid pace, practice riding in a bunch. Communication, drafting, rotating through. This is what it's all about.", "duration": "60-90 min", "type": "group", "zone": "Zone 2-3"},
                "thu": thu_session,
                "sat": {"title": f"Long Ride — {long_ride_km}km", "description": f"Build that endurance. {long_ride_km}km at a steady Zone 2 pace. Practice your race day nutrition — aim to eat something every 30-40 min after the first hour. {'Include Mt Coot-tha if possible.' if week >= 4 and is_110 else 'Steady and consistent.'}", "duration": f"~{round(long_ride_km / 25, 1)}h", "type": "long", "zone": "Zone 2"}
            }

        plan.append(week_plan)

    nutrition = {
        "race_day": [
            "Big breakfast 3 hours before start — oats, banana, toast with peanut butter",
            "Eat every 30-40 minutes on the bike — gels, bars, bananas",
            "Drink 500-750ml per hour — more if it's hot",
            "Start eating early — don't wait until you're hungry",
            "Caffeine gel or flat Coke at km 60+ for the final push"
        ],
        "training": [
            "Protein shake or meal within 30 min of finishing a ride",
            "Carb load 2 days before the event — pasta, rice, bread",
            "Stay hydrated all week, not just on ride days",
            "Good sleep is the best performance enhancer"
        ]
    }

    coottha = {
        "gradient": "2km at 9% average",
        "tips": [
            "Pace yourself — it comes at km 67 on the 110km, you'll be fatigued",
            "Stay seated for the first half to save your legs",
            "Find a rhythm — don't surge and blow up",
            "Gear down early, don't wait until you're grinding",
            "The descent is technical — don't cook it on the way down"
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
        path = self.path.split("?")[0]
        params = {}
        if "?" in self.path:
            for p in self.path.split("?")[1].split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k] = v

        db = get_db()

        try:
            if path == "/api/index":
                # Riders list
                rows = db.execute("SELECT * FROM riders ORDER BY name").fetchall()
                json_response(self, [dict(r) for r in rows])

            elif path.startswith("/api/index") and "/rider/" in path:
                # Single rider: /api/index/rider/10
                rider_id = int(path.split("/rider/")[1])
                row = db.execute("SELECT * FROM riders WHERE id = ?", [rider_id]).fetchone()
                if not row:
                    json_response(self, {"error": "Rider not found"}, 404)
                else:
                    json_response(self, dict(row))

            elif path == "/api/rides":
                rider_id = params.get("rider_id")
                if rider_id:
                    rows = db.execute("""
                        SELECT r.*, ri.name as rider_name
                        FROM rides r JOIN riders ri ON r.rider_id = ri.id
                        WHERE r.rider_id = ?
                        ORDER BY r.ride_date DESC
                    """, [int(rider_id)]).fetchall()
                else:
                    rows = db.execute("""
                        SELECT r.*, ri.name as rider_name
                        FROM rides r JOIN riders ri ON r.rider_id = ri.id
                        ORDER BY r.ride_date DESC
                        LIMIT 100
                    """).fetchall()
                json_response(self, [dict(r) for r in rows])

            elif path == "/api/stats":
                rider_stats = db.execute("""
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
                """).fetchall()

                this_week = db.execute("""
                    SELECT DISTINCT ri.name, ri.id
                    FROM rides r JOIN riders ri ON r.rider_id = ri.id
                    WHERE r.ride_date >= date('now', 'weekday 0', '-7 days')
                    ORDER BY ri.name
                """).fetchall()

                json_response(self, {
                    "rider_stats": [dict(r) for r in rider_stats],
                    "this_week_riders": [dict(r) for r in this_week],
                    "event_date": "2026-04-12",
                    "total_riders": len(rider_stats)
                })

            elif path.startswith("/api/training/"):
                rider_id = int(path.split("/api/training/")[1])
                rider = db.execute("SELECT * FROM riders WHERE id = ?", [rider_id]).fetchone()
                if not rider:
                    json_response(self, {"error": "Rider not found"}, 404)
                else:
                    completions = db.execute(
                        "SELECT week_number, day_key FROM training_completions WHERE rider_id = ?",
                        [rider_id]
                    ).fetchall()
                    plan = generate_training_plan(rider["target_distance"], rider["fitness_level"])
                    plan["completed"] = [{"week": c["week_number"], "day": c["day_key"]} for c in completions]
                    plan["rider"] = dict(rider)
                    json_response(self, plan)

            else:
                json_response(self, {"error": "Not found"}, 404)
        finally:
            db.close()

    def do_POST(self):
        path = self.path.split("?")[0]
        body = read_body(self)
        db = get_db()

        try:
            if path == "/api/rides":
                cur = db.execute(
                    "INSERT INTO rides (rider_id, ride_date, distance_km, duration_mins, ride_type, notes) VALUES (?, ?, ?, ?, ?, ?)",
                    [body["rider_id"], body["ride_date"], body["distance_km"],
                     body.get("duration_mins"), body.get("ride_type", "group"), body.get("notes", "")]
                )
                db.commit()
                row = db.execute("""
                    SELECT r.*, ri.name as rider_name
                    FROM rides r JOIN riders ri ON r.rider_id = ri.id
                    WHERE r.id = ?
                """, [cur.lastrowid]).fetchone()
                json_response(self, dict(row), 201)

            elif path == "/api/training/complete":
                db.execute(
                    "INSERT OR REPLACE INTO training_completions (rider_id, week_number, day_key) VALUES (?, ?, ?)",
                    [body["rider_id"], body["week_number"], body["day_key"]]
                )
                db.commit()
                json_response(self, {"status": "completed"}, 201)

            else:
                json_response(self, {"error": "Not found"}, 404)
        finally:
            db.close()

    def do_PUT(self):
        path = self.path.split("?")[0]
        body = read_body(self)
        db = get_db()

        try:
            if "/rider/" in path:
                rider_id = int(path.split("/rider/")[1])
                db.execute("UPDATE riders SET target_distance = ?, fitness_level = ? WHERE id = ?",
                           [body.get("target_distance", 110), body.get("fitness_level", "intermediate"), rider_id])
                db.commit()
                row = db.execute("SELECT * FROM riders WHERE id = ?", [rider_id]).fetchone()
                json_response(self, dict(row))
            else:
                json_response(self, {"error": "Not found"}, 404)
        finally:
            db.close()

    def do_DELETE(self):
        path = self.path.split("?")[0]
        params = {}
        if "?" in self.path:
            for p in self.path.split("?")[1].split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k] = v

        db = get_db()

        try:
            if path.startswith("/api/rides/"):
                ride_id = int(path.split("/api/rides/")[1])
                db.execute("DELETE FROM rides WHERE id = ?", [ride_id])
                db.commit()
                json_response(self, {"deleted": ride_id})

            elif path == "/api/training/complete":
                rider_id = params.get("rider_id")
                week_number = params.get("week_number")
                day_key = params.get("day_key")
                db.execute(
                    "DELETE FROM training_completions WHERE rider_id = ? AND week_number = ? AND day_key = ?",
                    [rider_id, week_number, day_key]
                )
                db.commit()
                json_response(self, {"status": "uncompleted"})

            else:
                json_response(self, {"error": "Not found"}, 404)
        finally:
            db.close()
