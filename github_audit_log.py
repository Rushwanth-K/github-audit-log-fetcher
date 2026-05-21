import os
import json
import csv
import time
import requests
from datetime import datetime, timezone


# put your token and org here, or set them as env variables
TOKEN = os.getenv("GITHUB_TOKEN", "")
ORG   = os.getenv("GITHUB_ORG", "Rushwanth-K")

PAGE_SIZE     = 100
ACTION_FILTER = ""  # e.g. "repo" or "member", leave empty for everything

JSON_OUT = "audit_log.json"
CSV_OUT  = "audit_log.csv"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def get_org_audit_log(org, action_filter=""):
    url = f"https://api.github.com/orgs/{org}/audit-log"
    params = {"include": "all", "per_page": PAGE_SIZE}
    if action_filter:
        params["phrase"] = f"action:{action_filter}"

    events = []
    page = 0

    print(f"Fetching audit log for: {org}")

    while url:
        page += 1
        print(f"  page {page}...")

        r = requests.get(url, headers=HEADERS, params=params if page == 1 else {})
        check_rate_limit(r)

        if r.status_code == 403:
            print("403 — token might be missing read:audit_log scope, or you're not an org owner.")
            break
        elif r.status_code == 404:
            print(f"404 — can't find org '{org}'.")
            break
        elif r.status_code != 200:
            print(f"Unexpected error {r.status_code}: {r.text}")
            break

        batch = r.json()
        if not batch:
            break

        events.extend(batch)
        print(f"  got {len(batch)} events ({len(events)} total)")
        url = get_next_url(r)

    print(f"Done. {len(events)} events fetched.\n")
    return events


def get_repo_events(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/events"
    events = []
    page = 1

    print(f"Fetching events for {owner}/{repo}")

    while True:
        r = requests.get(url, headers=HEADERS, params={"per_page": 100, "page": page})
        check_rate_limit(r)

        if r.status_code != 200:
            print(f"Error {r.status_code}: {r.text}")
            break

        batch = r.json()
        if not batch:
            break

        events.extend(batch)
        print(f"  page {page}: {len(batch)} events")
        page += 1

        if len(batch) < 100:
            break

    print(f"Done. {len(events)} events total.\n")
    return events


def get_next_url(response):
    link = response.headers.get("Link", "")
    for part in link.split(","):
        url_part, rel_part = part.strip().split(";")
        if 'rel="next"' in rel_part:
            return url_part.strip().strip("<>")
    return None


def check_rate_limit(response):
    remaining = int(response.headers.get("X-RateLimit-Remaining", 1))
    reset_at   = int(response.headers.get("X-RateLimit-Reset", 0))

    if response.status_code == 429 or (response.status_code == 403 and remaining == 0):
        wait = max(reset_at - int(time.time()), 0) + 5
        print(f"Rate limited. Waiting {wait}s...")
        time.sleep(wait)


def ms_to_str(ts_ms):
    if not ts_ms:
        return "N/A"
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def print_summary(events, label="audit log"):
    print("=" * 55)
    print(f"  {label.upper()}")
    print("=" * 55)

    if not events:
        print("  No events.")
        return

    actions = {}
    actors  = {}

    for ev in events:
        action = ev.get("action") or ev.get("type") or "unknown"
        actor = ev.get("actor", {}).get("login", "unknown") if isinstance(ev.get("actor"), dict) else ev.get("actor") or "unknown"
        actions[action] = actions.get(action, 0) + 1
        actors[actor]   = actors.get(actor, 0) + 1

    print(f"\n  Events  : {len(events)}")
    print(f"  Actions : {len(actions)} unique")
    print(f"  Actors  : {len(actors)} unique")

    print("\n  Top 10 actions:")
    for action, count in sorted(actions.items(), key=lambda x: -x[1])[:10]:
        print(f"    {count:>5}  {action}")

    print("\n  Top 10 actors:")
    for actor, count in sorted(actors.items(), key=lambda x: -x[1])[:10]:
        print(f"    {count:>5}  {actor}")

    print("\n  Latest 10 events:")
    print(f"  {'Timestamp':<25} {'Actor':<20} {'Action':<35} {'Repo'}")
    print(f"  {'-'*25} {'-'*20} {'-'*35} {'-'*30}")

    for ev in events[:10]:
        ts     = ms_to_str(ev.get("@timestamp") or ev.get("created_at_ms"))
        actor  = str(ev.get("actor", "N/A"))[:19]
        action = str(ev.get("action") or ev.get("type", "N/A"))[:34]
        repo   = str(ev.get("repo", "N/A"))[:29]
        print(f"  {ts:<25} {actor:<20} {action:<35} {repo}")
    print()


def save_json(events, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, default=str)
    print(f"Saved JSON → {path} ({len(events)} events)")


def save_csv(events, path):
    if not events:
        print("No events to save.")
        return

    fields = sorted({k for ev in events for k in ev.keys()})

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for ev in events:
            row = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in ev.items()}
            writer.writerow(row)

    print(f"Saved CSV  → {path} ({len(events)} rows)")

def main():
    repo_events = get_repo_events("Rushwanth-K", "kidlearn-app")
    print_summary(repo_events, label="repo events")
    save_json(repo_events, "repo_events.json")
    save_csv(repo_events, "repo_events.csv")


if __name__ == "__main__":
    main()