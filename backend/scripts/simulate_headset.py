"""Simulated VR headset: plays one training session against the API over HTTP.

Usage (API running on localhost:8000):
    python scripts/simulate_headset.py --email lukas@alpine.demo --module gowning --skill 0.6

Open the session in the dashboard while this runs to watch it live.
"""

import argparse
import random
import time

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--email", default="lukas@alpine.demo")
    parser.add_argument("--password", default="demo1234")
    parser.add_argument("--module", default="gowning", choices=["gowning", "aseptic_intervention"])
    parser.add_argument("--skill", type=float, default=0.6, help="0 = beginner, 1 = expert")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between events")
    args = parser.parse_args()

    with httpx.Client(base_url=args.api, timeout=10) as api:
        token = api.post("/api/auth/login", data={"username": args.email, "password": args.password})
        token.raise_for_status()
        api.headers["Authorization"] = f"Bearer {token.json()['access_token']}"

        modules = {m["code"]: m for m in api.get("/api/modules").json()}
        module = modules[args.module]
        session = api.post("/api/sessions", json={"module": args.module}).json()
        print(f"Session {session['id']} started: {module['title']}")

        mistake_chance = 0.15 * (1 - args.skill)
        for step in module["steps"]:
            for deviation in module["deviations"]:
                if random.random() < mistake_chance:
                    event = {"kind": "deviation", "step": step["code"], "deviation": deviation["code"]}
                    send(api, session["id"], event)
                    time.sleep(args.delay)
            send(api, session["id"], {"kind": "step", "step": step["code"]})
            time.sleep(args.delay)

        result = api.post(f"/api/sessions/{session['id']}/finish").json()
        print(f"Finished: score {result['score']}, passed: {result['passed']}")
        if result["certificate_code"]:
            print(f"Certificate: {result['certificate_code']}")


def send(api: httpx.Client, session_id: int, event: dict) -> None:
    response = api.post(f"/api/sessions/{session_id}/events", json=event)
    response.raise_for_status()
    label = event.get("deviation") or event["step"]
    print(f"  {event['kind']:<9} {label}")


if __name__ == "__main__":
    main()
