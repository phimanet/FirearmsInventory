#!/usr/bin/env python3
"""
FirearmsInventory Backend Microservice
Provides REST API endpoints for:
- Full CRUD for Firearms, Optics, Suppressors, Accessories, and Maintenance logs
- Multi-image uploads saved to uploads/photos/
- Automated data snapshots / rolling backups every 10 minutes
- Code modification watcher with instant auto-reload
- Origin-based RFC1918 & Tailscale CORS validation
- Insurance summary calculation & export
"""

import os
import sys
import json
import time
import uuid
import base64
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Configuration & Paths
PORT = int(os.environ.get("PORT", 5000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Persistent directories (isolated from web root / git pulls)
if os.path.exists("/app/data"):
    DATA_DIR = "/app/data"
    UPLOADS_DIR = "/app/uploads/photos"
else:
    # Local fallback
    ROOT_DIR = os.path.dirname(BASE_DIR)
    DATA_DIR = os.path.join(ROOT_DIR, "data")
    UPLOADS_DIR = os.path.join(ROOT_DIR, "uploads", "photos")

BACKUPS_DIR = os.path.join(DATA_DIR, "backups")
DB_FILE = os.path.join(DATA_DIR, "firearms.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)

# Lock for thread-safe database file operations
db_lock = threading.Lock()

def get_seed_data():
    now_iso = datetime.now(timezone.utc).isoformat() + "Z"
    return {
        "firearms": [
            {
                "id": "fa-glock-19-gen5",
                "make": "Glock",
                "model": "19 Gen 5 MOS",
                "type": "Pistol",
                "caliber": "9x19mm Parabellum",
                "action": "Striker Fired",
                "barrelLength": "4.02 in",
                "serialNumber": "AFCD8923",
                "location": "Primary Safe - Shelf 1",
                "status": "Active",
                "purchaseDate": "2024-03-15",
                "purchasePrice": 620.00,
                "replacementValue": 850.00,
                "roundCount": 1450,
                "notes": "Everyday carry configuration. Runs reliably with standard 115gr, 124gr FMJ and Federal HST 124gr +P.",
                "images": [
                    "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=900&auto=format&fit=crop&q=80"
                ],
                "accessories": [
                    {"name": "Holosun 507C-X2 Red Dot", "type": "Optic", "serial": "HS507C-88192", "value": 310.00},
                    {"name": "Streamlight TLR-7A Weapon Light", "type": "Light", "serial": "", "value": 140.00}
                ],
                "sources": [
                    {"name": "Bass Pro Shops", "url": "https://www.basspro.com", "price": 620.00, "tags": ["New", "Local FFL"]}
                ],
                "maintenanceLogs": [
                    {"date": "2026-08-10", "type": "Cleaning", "roundsFired": 200, "notes": "Field stripped, cleaned barrel and slide rails, lubricated with Lucas Oil."},
                    {"date": "2026-04-02", "type": "Range Session", "roundsFired": 250, "notes": "Zeroed Holosun 507C at 25 yards."}
                ],
                "createdAt": now_iso,
                "updatedAt": now_iso
            },
            {
                "id": "fa-bcm-recce-16",
                "make": "BCM (Bravo Company)",
                "model": "Recce-16 MCMR",
                "type": "Rifle",
                "caliber": "5.56x45mm NATO / .223",
                "action": "Semi-Automatic (Direct Impingement)",
                "barrelLength": "16.0 in",
                "serialNumber": "BCM-99412A",
                "location": "Primary Safe - Rack Position 3",
                "status": "Active",
                "purchaseDate": "2023-11-20",
                "purchasePrice": 1490.00,
                "replacementValue": 2150.00,
                "roundCount": 2100,
                "notes": "Mid-length gas system, cold hammer forged barrel, BCM Mod 0 compensator.",
                "images": [
                    "https://images.unsplash.com/photo-1584281722572-886d38e21013?w=900&auto=format&fit=crop&q=80"
                ],
                "accessories": [
                    {"name": "Vortex Razor HD Gen II-E 1-6x24", "type": "Optic", "serial": "RZ6-44019", "value": 1399.00},
                    {"name": "Badger Ordnance Condition One 1.70 Mount", "type": "Mount", "serial": "", "value": 315.00},
                    {"name": "SureFire M640DF Scout Light Pro", "type": "Light", "serial": "", "value": 329.00}
                ],
                "sources": [
                    {"name": "Primary Arms", "url": "https://www.primaryarms.com", "price": 1490.00, "tags": ["New", "Online Sale"]}
                ],
                "maintenanceLogs": [
                    {"date": "2026-09-18", "type": "Inspection & Clean", "roundsFired": 300, "notes": "Checked gas rings, cleaned bolt carrier group and bore."}
                ],
                "createdAt": now_iso,
                "updatedAt": now_iso
            },
            {
                "id": "fa-beretta-a300-ultima",
                "make": "Beretta",
                "model": "A300 Ultima Patrol",
                "type": "Shotgun",
                "caliber": "12 Gauge (3 inch chamber)",
                "action": "Gas-Operated Semi-Automatic",
                "barrelLength": "19.1 in",
                "serialNumber": "BER-A300-5821",
                "location": "Primary Safe - Rack Position 1",
                "status": "Active",
                "purchaseDate": "2024-01-10",
                "purchasePrice": 999.00,
                "replacementValue": 1150.00,
                "roundCount": 350,
                "notes": "7+1 capacity, enlarged controls, ghost ring rear sight, M-LOK barrel clamp.",
                "images": [
                    "https://images.unsplash.com/photo-1589254065878-42c9da997008?w=900&auto=format&fit=crop&q=80"
                ],
                "accessories": [
                    {"name": "Esstac 7-Round Shotgun Card", "type": "Side Saddle", "serial": "", "value": 18.00},
                    {"name": "Magpul MS1 Padded Sling", "type": "Sling", "serial": "", "value": 45.00}
                ],
                "sources": [
                    {"name": "Sportsman's Warehouse", "url": "https://www.sportsmans.com", "price": 999.00, "tags": ["New", "In-Store Pick Up"]}
                ],
                "maintenanceLogs": [
                    {"date": "2026-07-04", "type": "Cleaning", "roundsFired": 100, "notes": "Cleaned gas piston assembly and magazine tube."}
                ],
                "createdAt": now_iso,
                "updatedAt": now_iso
            }
        ],
        "types": ["Pistol", "Rifle", "Shotgun", "NFA / Suppressor", "Receiver / Lower", "Other"],
        "locations": [
            "Primary Safe - Shelf 1",
            "Primary Safe - Shelf 2",
            "Primary Safe - Rack Position 1",
            "Primary Safe - Rack Position 2",
            "Primary Safe - Rack Position 3",
            "Range Bag",
            "Secure Lockbox"
        ],
        "deletedIds": []
    }

def load_db():
    with db_lock:
        if not os.path.exists(DB_FILE):
            default_data = get_seed_data()
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=2)
            return default_data

        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load DB: {e}")
            return {"firearms": [], "types": [], "locations": [], "deletedIds": []}

def save_db(data):
    with db_lock:
        data["updatedAt"] = datetime.now(timezone.utc).isoformat() + "Z"
        temp_file = DB_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, DB_FILE)

def backup_worker():
    """Runs periodic rolling snapshot backups every 10 minutes (600s), keeping up to 30 rolling versions."""
    while True:
        try:
            time.sleep(600)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUPS_DIR, f"firearms_{timestamp}.json")
            with db_lock:
                if os.path.exists(DB_FILE):
                    with open(DB_FILE, "r", encoding="utf-8") as src, open(backup_path, "w", encoding="utf-8") as dst:
                        dst.write(src.read())

            backups = sorted([f for f in os.listdir(BACKUPS_DIR) if f.startswith("firearms_") and f.endswith(".json")])
            if len(backups) > 30:
                for old in backups[:-30]:
                    try:
                        os.remove(os.path.join(BACKUPS_DIR, old))
                    except Exception:
                        pass
        except Exception as e:
            print(f"[BACKUP] Error: {e}")

def code_reload_watcher():
    """Monitors server.py for changes and auto-restarts Python process instantly."""
    script_file = os.path.abspath(__file__)
    last_mtime = os.stat(script_file).st_mtime
    while True:
        try:
            time.sleep(3)
            current_mtime = os.stat(script_file).st_mtime
            if current_mtime != last_mtime:
                print("[RELOAD] Detected change in server.py! Restarting process...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:
            pass

class RequestHandler(BaseHTTPRequestHandler):
    def is_origin_allowed(self, origin):
        if not origin:
            return True
        origin_clean = origin.lower().split("://")[-1].split(":")[0]
        if origin_clean in ["localhost", "127.0.0.1", "dockermonster"]:
            return True
        if origin_clean.endswith(".local") or origin_clean.endswith(".lan"):
            return True
        # RFC1918 and Tailscale CGNAT
        if origin_clean.startswith("192.168.") or origin_clean.startswith("10."):
            return True
        if origin_clean.startswith("172."):
            try:
                second = int(origin_clean.split(".")[1])
                if 16 <= second <= 31:
                    return True
            except ValueError:
                pass
        if origin_clean.startswith("100."):  # Tailscale
            return True
        return False

    def send_cors_headers(self):
        origin = self.headers.get("Origin")
        if origin and self.is_origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Max-Age", "86400")
        elif not origin:
            self.send_header("Access-Control-Allow-Origin", "*")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status, message):
        self.send_json(status, {"success": False, "error": message})

    def parse_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw)
        except Exception:
            return None

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/")
        query = parse_qs(url.query)

        if path in ["/api", "/api/health"]:
            self.send_json(200, {
                "status": "ok",
                "service": "FirearmsInventory API",
                "time": datetime.now(timezone.utc).isoformat() + "Z"
            })
            return

        if path == "/api/firearms":
            db = load_db()
            items = db.get("firearms", [])
            type_filter = query.get("type", [None])[0]
            search = query.get("q", [None])[0]

            filtered = items
            if type_filter and type_filter != "All":
                filtered = [it for it in filtered if it.get("type") == type_filter]
            if search:
                s_lower = search.lower()
                filtered = [
                    it for it in filtered
                    if s_lower in it.get("make", "").lower()
                    or s_lower in it.get("model", "").lower()
                    or s_lower in it.get("caliber", "").lower()
                    or s_lower in it.get("serialNumber", "").lower()
                    or s_lower in it.get("location", "").lower()
                    or s_lower in it.get("notes", "").lower()
                    or any(s_lower in acc.get("name", "").lower() for acc in it.get("accessories", []))
                ]

            self.send_json(200, {
                "success": True,
                "firearms": filtered,
                "types": db.get("types", []),
                "locations": db.get("locations", []),
                "summary": self._calc_summary(items)
            })
            return

        if path.startswith("/api/firearms/"):
            item_id = path.split("/api/firearms/")[1]
            db = load_db()
            target = next((it for it in db.get("firearms", []) if it.get("id") == item_id), None)
            if target:
                self.send_json(200, {"success": True, "firearm": target})
            else:
                self.send_error_json(404, "Firearm not found")
            return

        if path == "/api/insurance-report":
            db = load_db()
            items = db.get("firearms", [])
            self.send_json(200, {
                "success": True,
                "reportDate": datetime.now(timezone.utc).isoformat() + "Z",
                "summary": self._calc_summary(items),
                "items": items
            })
            return

        if path == "/api/backups":
            backups = sorted([f for f in os.listdir(BACKUPS_DIR) if f.startswith("firearms_") and f.endswith(".json")], reverse=True)
            self.send_json(200, {"success": True, "backups": backups})
            return

        self.send_error_json(404, "Endpoint not found")

    def _calc_summary(self, items):
        total_items = len(items)
        total_purchase = sum(float(it.get("purchasePrice") or 0) for it in items)
        total_replacement = sum(float(it.get("replacementValue") or 0) for it in items)
        total_accessories_val = 0
        total_rounds = 0

        type_counts = {}
        for it in items:
            t = it.get("type", "Other")
            type_counts[t] = type_counts.get(t, 0) + 1
            total_rounds += int(it.get("roundCount") or 0)
            for acc in it.get("accessories", []):
                total_accessories_val += float(acc.get("value") or 0)

        return {
            "totalFirearms": total_items,
            "totalPurchaseCost": round(total_purchase, 2),
            "totalReplacementValue": round(total_replacement, 2),
            "totalAccessoriesValue": round(total_accessories_val, 2),
            "grandTotalInsuredValue": round(total_replacement + total_accessories_val, 2),
            "totalRoundsTracked": total_rounds,
            "typeCounts": type_counts
        }

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/")

        if path == "/api/firearms":
            body = self.parse_json_body()
            if not body or not body.get("make") or not body.get("model"):
                self.send_error_json(400, "Make and Model are required.")
                return

            db = load_db()
            item_id = body.get("id") or ("fa-" + str(uuid.uuid4())[:8])
            now_iso = datetime.now(timezone.utc).isoformat() + "Z"

            new_firearm = {
                "id": item_id,
                "make": body.get("make", "").strip(),
                "model": body.get("model", "").strip(),
                "type": body.get("type", "Pistol"),
                "caliber": body.get("caliber", "").strip(),
                "action": body.get("action", "").strip(),
                "barrelLength": body.get("barrelLength", "").strip(),
                "serialNumber": body.get("serialNumber", "").strip(),
                "location": body.get("location", "").strip(),
                "status": body.get("status", "Active"),
                "purchaseDate": body.get("purchaseDate", ""),
                "purchasePrice": float(body.get("purchasePrice") or 0),
                "replacementValue": float(body.get("replacementValue") or 0),
                "roundCount": int(body.get("roundCount") or 0),
                "notes": body.get("notes", "").strip(),
                "images": body.get("images", []),
                "accessories": body.get("accessories", []),
                "sources": body.get("sources", []),
                "maintenanceLogs": body.get("maintenanceLogs", []),
                "createdAt": now_iso,
                "updatedAt": now_iso
            }

            db.setdefault("firearms", []).insert(0, new_firearm)
            save_db(db)
            self.send_json(201, {"success": True, "firearm": new_firearm})
            return

        if path == "/api/upload-photo":
            body = self.parse_json_body()
            if not body or "image" not in body:
                self.send_error_json(400, "Missing image payload.")
                return

            try:
                data_str = body["image"]
                ext = "jpg"
                if "data:image/" in data_str and ";base64," in data_str:
                    header, base64_data = data_str.split(";base64,")
                    if "png" in header:
                        ext = "png"
                    elif "webp" in header:
                        ext = "webp"
                else:
                    base64_data = data_str

                img_bytes = base64.b64decode(base64_data)
                filename = f"fa_{int(time.time())}_{uuid.uuid4().hex[:6]}.{ext}"
                filepath = os.path.join(UPLOADS_DIR, filename)

                with open(filepath, "wb") as f:
                    f.write(img_bytes)

                public_url = f"/uploads/photos/{filename}"
                self.send_json(200, {"success": True, "url": public_url, "filename": filename})
            except Exception as e:
                self.send_error_json(500, f"Upload error: {str(e)}")
            return

        if path == "/api/snapshot":
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUPS_DIR, f"firearms_manual_{timestamp}.json")
            with db_lock:
                if os.path.exists(DB_FILE):
                    with open(DB_FILE, "r", encoding="utf-8") as src, open(backup_path, "w", encoding="utf-8") as dst:
                        dst.write(src.read())
            self.send_json(200, {"success": True, "snapshot": f"firearms_manual_{timestamp}.json"})
            return

        self.send_error_json(404, "Endpoint not found")

    def do_PUT(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/")

        if path.startswith("/api/firearms/"):
            item_id = path.split("/api/firearms/")[1]
            body = self.parse_json_body()
            if not body:
                self.send_error_json(400, "Invalid JSON payload.")
                return

            db = load_db()
            items = db.get("firearms", [])
            idx = next((i for i, it in enumerate(items) if it.get("id") == item_id), None)
            if idx is None:
                self.send_error_json(404, "Firearm not found.")
                return

            now_iso = datetime.now(timezone.utc).isoformat() + "Z"
            existing = items[idx]

            existing["make"] = body.get("make", existing.get("make", "")).strip()
            existing["model"] = body.get("model", existing.get("model", "")).strip()
            existing["type"] = body.get("type", existing.get("type", "Pistol"))
            existing["caliber"] = body.get("caliber", existing.get("caliber", "")).strip()
            existing["action"] = body.get("action", existing.get("action", "")).strip()
            existing["barrelLength"] = body.get("barrelLength", existing.get("barrelLength", "")).strip()
            existing["serialNumber"] = body.get("serialNumber", existing.get("serialNumber", "")).strip()
            existing["location"] = body.get("location", existing.get("location", "")).strip()
            existing["status"] = body.get("status", existing.get("status", "Active"))
            existing["purchaseDate"] = body.get("purchaseDate", existing.get("purchaseDate", ""))
            existing["purchasePrice"] = float(body.get("purchasePrice") if body.get("purchasePrice") is not None else existing.get("purchasePrice", 0))
            existing["replacementValue"] = float(body.get("replacementValue") if body.get("replacementValue") is not None else existing.get("replacementValue", 0))
            existing["roundCount"] = int(body.get("roundCount") if body.get("roundCount") is not None else existing.get("roundCount", 0))
            existing["notes"] = body.get("notes", existing.get("notes", "")).strip()

            if "images" in body:
                existing["images"] = body["images"]
            if "accessories" in body:
                existing["accessories"] = body["accessories"]
            if "sources" in body:
                existing["sources"] = body["sources"]
            if "maintenanceLogs" in body:
                existing["maintenanceLogs"] = body["maintenanceLogs"]

            existing["updatedAt"] = now_iso
            items[idx] = existing
            save_db(db)

            self.send_json(200, {"success": True, "firearm": existing})
            return

        self.send_error_json(404, "Endpoint not found")

    def do_DELETE(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/")

        if path.startswith("/api/firearms/"):
            item_id = path.split("/api/firearms/")[1]
            db = load_db()
            items = db.get("firearms", [])
            initial_count = len(items)
            db["firearms"] = [it for it in items if it.get("id") != item_id]

            if len(db["firearms"]) == initial_count:
                self.send_error_json(404, "Firearm not found.")
                return

            db.setdefault("deletedIds", []).append(item_id)
            save_db(db)
            self.send_json(200, {"success": True, "deleted": item_id})
            return

        self.send_error_json(404, "Endpoint not found")

def main():
    threading.Thread(target=backup_worker, daemon=True).start()
    threading.Thread(target=code_reload_watcher, daemon=True).start()
    server_address = ("0.0.0.0", PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"[FIREARMS INVENTORY] Running on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

if __name__ == "__main__":
    main()
