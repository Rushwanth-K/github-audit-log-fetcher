# GitHub Audit Log Fetcher

A Python tool to fetch and analyze repository activity and audit log events from the GitHub REST API. Built as part of an operational study on GitHub's log history feature — understanding who accessed what, when, and what changed.

---

## What This Project Does

GitHub exposes three different API endpoints to track repository activity. This project uses all three, generates a report summary in the console, and exports the data as both **JSON** and **CSV**.

| Endpoint | What it tracks |
|---|---|
| `GET /orgs/{org}/audit-log` | Security events — repo created/deleted, members added/removed, permissions changed |
| `GET /repos/{owner}/{repo}/events` | Activity feed — pushes, PRs, issues, forks, stars |
| `GET /orgs/{org}/repos` | Metadata of every repo in the org — name, visibility, created date |

---

## Project Structure

```
github-audit-log-project/
│
├── github_audit_log.py       # Main Python script (all 3 endpoints)
├── repo_events.json          # Sample output — repo events (seeded data)
├── repo_events.csv           # Sample output — same data in CSV format
├── audit_log_report.json     # Generated when you run the script
├── audit_log_report.csv      # Generated when you run the script
│
├── docs/
│   └── github_api_reference.md   # Full GitHub API docs reference (markdown)
│
├── .gitignore
└── README.md
```

---

## Prerequisites

- Python 3.10+
- A GitHub Personal Access Token (PAT)

Install the only dependency:

```bash
pip install requests
```

---

## Setup — GitHub Token

1. Go to [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **Generate new token (classic)**
3. Enable these scopes:

| Scope | Required for |
|---|---|
| `read:audit_log` | Org audit log endpoint |
| `repo` | Private repo events |
| `read:org` | Listing org repos |

4. Copy the token and export it:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
export GITHUB_ORG=your-org-name
```

---

## Usage

```bash
python github_audit_log.py
```

### What happens when you run it:

1. Fetches all pages of the org audit log (cursor-based pagination)
2. Prints a summary to the console:
   - Total events
   - Top 10 actions (e.g. `repo.create`, `member.add`)
   - Top 10 actors (who did the most actions)
   - Latest 10 events with timestamp, actor, action, repo
3. Saves `audit_log_report.json` and `audit_log_report.csv`

### Optional endpoints (uncomment in `main()`):

```python
# Fetch activity feed for a specific repo
REPO_NAME   = "your-repo-name"
repo_events = fetch_repo_events(ORG_NAME, REPO_NAME)

# List all repos in the org with metadata
repos = fetch_org_repos(ORG_NAME)
```

### Filter by action type:

```python
# In the CONFIG section at the top of the script:
ACTION_FILTER = "repo"      # only repo.* events
ACTION_FILTER = "member"    # only member.* events
ACTION_FILTER = ""          # all events (default)
```

---

## Key Concepts Learned

### Audit Log vs Repo Events — the difference

| | Org Audit Log | Repo Events |
|---|---|---|
| Endpoint | `/orgs/{org}/audit-log` | `/repos/{owner}/{repo}/events` |
| Tracks | Security & compliance | Developer activity |
| Examples | repo.create, member.add | PushEvent, PullRequestEvent |
| Who can access | Org owners only | Anyone with repo read |
| Token scope | `read:audit_log` | `public_repo` or `repo` |
| History limit | Up to 180 days | Last 300 events / 90 days |
| Pagination | Cursor-based (Link header) | Page-number based |

### Repo-specific audit log actions

These are the events inside the audit log that relate specifically to repositories:

| Action | Meaning |
|---|---|
| `repo.create` | Repository was created — includes timestamp and actor |
| `repo.destroy` | Repository was deleted |
| `repo.access` | Visibility changed (public ↔ private) |
| `repo.archived` | Repository was archived |
| `repo.transfer` | Repository moved to a different owner |
| `protected_branch.create` | A branch protection rule was added |
| `protected_branch.destroy` | A branch protection rule was removed |

### Key fields in each audit log event

| Field | Description |
|---|---|
| `@timestamp` | When the event happened (Unix milliseconds) |
| `actor` | GitHub username who performed the action |
| `action` | Event type string (e.g. `repo.create`) |
| `repo` | Full repo name affected (e.g. `org/repo-name`) |
| `org` | Organization name |
| `visibility` | `public` or `private` (for access change events) |

### Pagination — cursor-based vs page-based

The audit log uses **cursor-based pagination** via the `Link` response header:

```
Link: <https://api.github.com/orgs/my-org/audit-log?after=Y3Vyc29y...>; rel="next"
```

The script automatically follows this until there are no more pages.

---

## Sample Output

**Console summary:**

```
[*] Endpoint 1 — Org Audit Log: /orgs/my-org/audit-log
    Page 1: https://api.github.com/orgs/my-org/audit-log
    Got 100 events  (total: 100)
    Page 2: https://api.github.com/...?after=...
    Got 43 events   (total: 143)

[+] Org audit log total: 143 events

============================================================
  REPORT: ORG AUDIT LOG
============================================================

  Total events   : 143
  Unique actions : 12
  Unique actors  : 8

  --- Top 10 actions ---
      52  repo.create
      28  member.add
      18  protected_branch.create
      ...

  --- Latest 10 events ---
  Timestamp                 Actor                Action                              Repo
  ------------------------- -------------------- ----------------------------------- ------------------------------
  2026-05-10 15:09:10 UTC   Rushwanth-K          repo.create                         Rushwanth-K/kidlearn-app
```

**Seeded sample data** (`repo_events.json`):

The `repo_events.json` and `repo_events.csv` in this repo are real output from running Endpoint 2 (`/repos/{owner}/{repo}/events`) against the `Rushwanth-K/kidlearn-app` repository. They show:

- A `CreateEvent` — the `main` branch was created on `2026-05-10T14:44:49Z`
- A `PushEvent` — first commit pushed to `main` on `2026-05-10T15:09:10Z`

---

## Error Handling

| Error | Cause | Fix |
|---|---|---|
| `403 Forbidden` | Token missing `read:audit_log` scope or not an org owner | Regenerate token with correct scope |
| `404 Not Found` | Org name wrong or not accessible | Check `GITHUB_ORG` value |
| Rate limited | Too many requests | Script auto-waits using `X-RateLimit-Reset` header |

---

## References

- Full API reference: [`docs/github_api_reference.md`](docs/github_api_reference.md)
- GitHub REST API docs: [https://docs.github.com/en/rest](https://docs.github.com/en/rest)
- Audit log actions list: [https://docs.github.com/en/organizations/keeping-your-organization-secure/reviewing-the-audit-log-for-your-organization](https://docs.github.com/en/organizations/keeping-your-organization-secure/reviewing-the-audit-log-for-your-organization)
- Personal access tokens: [https://github.com/settings/tokens](https://github.com/settings/tokens)

---

## Author

**Rushwanth-K** — operational study on GitHub API log history and audit logging.
