#!/usr/bin/env python3
"""
LEONIDA LIVE — Terminal Flag Dashboard (stdlib only, no pip install).

Toggle Flagsmith flags across environments without leaving the terminal.
Talks to the mock API (default http://localhost:8001) or a real Flagsmith
instance (--api http://localhost:8000/api/v1).

Usage:
  python3 cli/leonida.py                          # interactive dashboard
  python3 cli/leonida.py --list                   # list flags (production)
  python3 cli/leonida.py --list --env staging
  python3 cli/leonida.py --toggle leonida_expansion --env production
  python3 cli/leonida.py --toggle double_xp_weekend --on --env staging
  python3 cli/leonida.py --reset
  python3 cli/leonida.py --events

Keyboard (interactive): number = toggle flag, e = switch env, r = reset, q = quit
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

API = os.environ.get("LEONIDA_API", "http://localhost:8001")
ENVS = ["production", "staging", "dev"]


def req(method, path, payload=None, base=API):
    url = base.rstrip("/") + path
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.URLError as e:
        print(f"\n❌ Can't reach {base} ({e.reason}).")
        print("   Start the mock API first:  python3 mock/server.py")
        print("   Or point at real Flagsmith:  --api http://localhost:8000/api/v1")
        sys.exit(1)


def get_flags(env):
    return req("GET", f"/api/v1/flags/?environment={env}")


def toggle(name, env, enabled=None):
    payload = {"environment": env, "actor": "terminal"}
    if enabled is not None:
        payload["enabled"] = enabled
    return req("POST", f"/api/v1/flags/{name}/toggle", payload)


def render(flags, env, selected=0):
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 72)
    print("  🌴 LEONIDA LIVE — Terminal Flag Dashboard".ljust(72))
    print(f"  GTA VI Live-Ops  •  Environment: {env.upper()}  •  API: {API}")
    print("=" * 72)
    print(f"  {'#':<4}{'FLAG':<26}{'STATUS':<10}{'ROLLOUT':<9}DESCRIPTION")
    print("  " + "-" * 68)
    for i, f in enumerate(flags):
        mark = "▶" if i == selected else " "
        status = "🟢 ON " if f["enabled"] else "⚪ OFF"
        desc = (f.get("description") or "")[:34]
        print(f"  {mark} {i+1:<3}{f['name']:<26}{status:<10}{str(f.get('rollout',100))+'%':<9}{desc}")
    print("  " + "-" * 68)
    print("  [number] toggle   [e] switch env   [r] reset   [q] quit")
    print("  Tip: flip a flag here, watch the web dashboard change in <2s. 🔥")


def interactive():
    env = "production"
    selected = 0
    while True:
        flags = get_flags(env)
        render(flags, env, selected)
        try:
            cmd = input("\n  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nBye, Vice City. 🌴")
            return
        if cmd in ("q", "quit", "exit"):
            print("Bye, Vice City. 🌴")
            return
        if cmd == "e":
            idx = ENVS.index(env)
            env = ENVS[(idx + 1) % len(ENVS)]
            continue
        if cmd == "r":
            req("POST", "/api/v1/flags/reset", {"environment": env})
            print("  ↺ Reset to seed values.")
            time.sleep(0.8)
            continue
        if cmd.isdigit():
            n = int(cmd) - 1
            if 0 <= n < len(flags):
                f = flags[n]
                out = toggle(f["name"], env)
                print(f"  ⚡ {f['name']} → {'ON' if out['enabled'] else 'OFF'} ({env})")
                time.sleep(0.8)
            else:
                print("  Invalid number.")
                time.sleep(0.8)


def main():
    global API
    ap = argparse.ArgumentParser(description="LEONIDA LIVE terminal flag dashboard")
    ap.add_argument("--api", default=API, help="Flagsmith/mock API base URL")
    ap.add_argument("--env", default="production", choices=ENVS)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--toggle", metavar="FLAG")
    ap.add_argument("--on", action="store_true", help="force ON (default: flip)")
    ap.add_argument("--off", action="store_true", help="force OFF")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--events", action="store_true")
    args = ap.parse_args()
    API = args.api

    if args.list:
        flags = get_flags(args.env)
        print(f"\n🌴 LEONIDA LIVE — {args.env.upper()} ({len(flags)} flags)\n")
        for f in flags:
            print(f"  {'🟢 ON ' if f['enabled'] else '⚪ OFF'}  {f['name']:<26} {f.get('rollout',100)}%  {f.get('description','')}")
        print()
        return
    if args.toggle:
        enabled = True if args.on else (False if args.off else None)
        out = toggle(args.toggle, args.env, enabled)
        print(f"⚡ {out['name']} → {'ON' if out['enabled'] else 'OFF'} ({args.env})")
        return
    if args.reset:
        req("POST", "/api/v1/flags/reset", {"environment": args.env})
        print("↺ Reset to seed values.")
        return
    if args.events:
        for e in req("GET", "/api/v1/events/"):
            ts = time.strftime("%H:%M:%S", time.localtime(e["ts"]))
            print(f"  {ts}  {e['flag']:<26} → {e['enabled']}  ({e['environment']}) by {e.get('actor','?')}")
        return
    interactive()


if __name__ == "__main__":
    main()
