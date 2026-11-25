#!/usr/bin/env python3
"""
LEONIDA LIVE — Mock Flagsmith API server (zero dependencies, stdlib only).

Mimics the Flagsmith REST API surface our app + CLI use, so the demo
works instantly without booting the full Flagsmith stack (Django+Postgres).

Endpoints:
  GET  /health                              -> {"status":"ok"}
  GET  /api/v1/environments/                -> list of environments
  GET  /api/v1/flags/?environment=prod     -> flags for an environment
  GET  /api/v1/flags/<name>/                -> single flag
  POST /api/v1/flags/<name>/toggle          -> {"enabled": bool, "environment": str}
  POST /api/v1/flags/reset                  -> reset to seed values
  GET  /api/v1/events/                      -> audit log of toggles

Run:
  python3 mock/server.py            # port 8001
  python3 mock/server.py --port 8001 --seed seed-flags.json

State persists to mock/state.json so a refresh / restart keeps your flips.
CORS is wide open for local dev (browser fetch from :3000 -> :8001).
"""
import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
DEFAULT_SEED = os.path.join(ROOT, "seed-flags.json")

lock = threading.Lock()
state = {"flags": {}, "events": [], "environments": ["production", "staging", "dev"]}


def load_seed(seed_path):
    with open(seed_path) as f:
        seed = json.load(f)
    flags = {}
    for fl in seed["flags"]:
        flags[fl["name"]] = {
            "name": fl["name"],
            "label": fl.get("label", fl["name"]),
            "icon": fl.get("icon", "🚩"),
            "description": fl.get("description", ""),
            "category": fl.get("category", "General"),
            "rollout": fl.get("rollout", 100),
            "affects": fl.get("affects", ""),
            "values": dict(fl.get("values", {})),
            "default": fl.get("default", False),
        }
    return flags, seed.get("environments", ["production", "staging", "dev"])


def load_state(seed_path):
    flags, envs = load_seed(seed_path)
    state["flags"] = flags
    state["environments"] = envs
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                saved = json.load(f)
            # Merge saved values over seed (so new flags still appear)
            for name, saved_flag in saved.get("flags", {}).items():
                if name in state["flags"]:
                    state["flags"][name]["values"] = saved_flag.get("values", state["flags"][name]["values"])
            state["events"] = saved.get("events", [])
        except Exception:
            pass


def save_state():
    try:
        with open(STATE_PATH, "w") as f:
            json.dump({"flags": state["flags"], "events": state["events"]}, f, indent=2)
    except Exception:
        pass


def flag_view(name, env):
    fl = state["flags"][name]
    enabled = fl["values"].get(env, fl["default"])
    return {
        "name": name,
        "label": fl["label"],
        "icon": fl["icon"],
        "description": fl["description"],
        "category": fl["category"],
        "rollout": fl["rollout"],
        "affects": fl["affects"],
        "enabled": bool(enabled),
        "environment": env,
        "default": fl["default"],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "LeonidaMock/1.0"

    def log_message(self, fmt, *args):
        pass  # quiet

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._json({}, 204)

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        qs = parse_qs(u.query)

        if path == "/health":
            return self._json({"status": "ok", "service": "leonida-mock-flagsmith", "flags": len(state["flags"])})

        if path == "/api/v1/environments":
            return self._json([{"name": e, "id": i + 1} for i, e in enumerate(state["environments"])])

        if path == "/api/v1/flags":
            env = (qs.get("environment") or ["production"])[0]
            if env not in state["environments"]:
                env = "production"
            with lock:
                flags = [flag_view(n, env) for n in state["flags"]]
            return self._json(flags)

        if path == "/api/v1/events":
            with lock:
                return self._json(list(reversed(state["events"]))[:50])

        if path.startswith("/api/v1/flags/"):
            name = path[len("/api/v1/flags/"):]
            env = (qs.get("environment") or ["production"])[0]
            with lock:
                if name not in state["flags"]:
                    return self._json({"error": "flag not found"}, 404)
                return self._json(flag_view(name, env))

        return self._json({"error": "not found", "path": path}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except Exception:
            payload = {}

        if path == "/api/v1/flags/reset":
            with lock:
                flags, _ = load_seed(self.server.seed_path)
                state["flags"] = flags
                state["events"].append({
                    "ts": time.time(), "flag": "*", "enabled": None,
                    "environment": payload.get("environment", "production"),
                    "actor": "cli", "note": "reset to seed",
                })
                save_state()
            return self._json({"status": "reset"})

        if path.startswith("/api/v1/flags/") and path.endswith("/toggle"):
            name = path[len("/api/v1/flags/"):-len("/toggle")].strip("/")
            env = payload.get("environment", "production")
            enabled = payload.get("enabled")
            with lock:
                if name not in state["flags"]:
                    return self._json({"error": "flag not found"}, 404)
                if env not in state["environments"]:
                    env = "production"
                if enabled is None:
                    enabled = not state["flags"][name]["values"].get(env, False)
                state["flags"][name]["values"][env] = bool(enabled)
                state["events"].append({
                    "ts": time.time(), "flag": name, "enabled": bool(enabled),
                    "environment": env, "actor": payload.get("actor", "dashboard"),
                })
                save_state()
                view = flag_view(name, env)
            return self._json(view)

        return self._json({"error": "not found"}, 404)


def main():
    ap = argparse.ArgumentParser(description="LEONIDA LIVE mock Flagsmith API")
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--seed", default=DEFAULT_SEED)
    args = ap.parse_args()

    load_state(args.seed)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.seed_path = args.seed
    print(f"🗺️  LEONIDA LIVE mock Flagsmith API on http://{args.host}:{args.port}")
    print(f"   Flags: {len(state['flags'])}  Envs: {', '.join(state['environments'])}")
    print(f"   Health: http://localhost:{args.port}/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye, Vice City. 🌴")


if __name__ == "__main__":
    main()
