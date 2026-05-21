# GitHub REST API — Reference Guide

> Copied and structured from the official GitHub REST API documentation.  
> Source: [https://docs.github.com/en/rest](https://docs.github.com/en/rest)  
> Version: 2022-11-28 (latest stable)

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Versioning](#versioning)
4. [Rate Limiting](#rate-limiting)
5. [Pagination](#pagination)
6. [Endpoint: Org Audit Log](#endpoint-org-audit-log)
7. [Endpoint: Repo Events](#endpoint-repo-events)
8. [Endpoint: List Org Repos](#endpoint-list-org-repos)
9. [Audit Log Action Types](#audit-log-action-types)
10. [Event Types (Repo Events)](#event-types-repo-events)
11. [Common Response Fields](#common-response-fields)
12. [Error Codes](#error-codes)
13. [Token Scopes Reference](#token-scopes-reference)

---

## Overview

The GitHub REST API lets you interact with GitHub programmatically — repositories, users, organizations, issues, pull requests, and audit logs.

**Base URL:**
```
https://api.github.com
```

**Request format:**
- All requests must use HTTPS
- Request bodies must be JSON (`Content-Type: application/json`)
- Responses are JSON

**Required headers for every request:**
```http
Authorization: Bearer YOUR_TOKEN
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
```

---

## Authentication

### Personal Access Token (Classic)

Generate at: [https://github.com/settings/tokens](https://github.com/settings/tokens)

```http
Authorization: Bearer ghp_xxxxxxxxxxxxxxxxxxxx
```

### Fine-Grained Personal Access Token

Generate at: [https://github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta)

Fine-grained tokens give per-repository and per-permission control. They expire and cannot be used for org-level audit logs without org approval.

### GitHub App Installation Token

Used for server-to-server automation. Generated via JWT → installation token exchange.

```http
Authorization: Bearer ghs_xxxxxxxxxxxxxxxxxxxx
```

### OAuth App Token

For user-authorized applications. Generated via OAuth 2.0 flow.

```http
Authorization: Bearer gho_xxxxxxxxxxxxxxxxxxxx
```

---

## Versioning

GitHub requires the API version header on all requests:

```http
X-GitHub-Api-Version: 2022-11-28
```

If omitted, GitHub uses the default version for your token type. Always specify it explicitly to avoid breaking changes.

---

## Rate Limiting

### Limits by authentication type

| Auth type | Requests per hour |
|---|---|
| Authenticated (PAT, OAuth) | 5,000 |
| GitHub App (installation) | 15,000 |
| Unauthenticated | 60 |
| Search API (authenticated) | 30 |
| Audit log API | 1,750 |

### Rate limit headers in every response

```http
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4987
X-RateLimit-Reset: 1714652400
X-RateLimit-Used: 13
X-RateLimit-Resource: core
```

- `X-RateLimit-Reset` is a Unix timestamp (seconds). Wait until this time before retrying.
- When remaining hits 0, GitHub returns `403 Forbidden` with body `{"message": "API rate limit exceeded..."}`

### Secondary rate limits

GitHub also enforces secondary limits on:
- Too many concurrent requests
- Too many requests to a single endpoint in a short window
- Large response payloads

These return `429 Too Many Requests` or `403 Forbidden` with a `Retry-After` header.

### Handling rate limits in code

```python
import time

def handle_rate_limit(response):
    remaining = int(response.headers.get("X-RateLimit-Remaining", 1))
    reset_at  = int(response.headers.get("X-RateLimit-Reset", 0))
    if response.status_code in (429, 403) and remaining == 0:
        wait = max(reset_at - int(time.time()), 0) + 5
        print(f"Rate limited. Waiting {wait}s...")
        time.sleep(wait)
```

---

## Pagination

GitHub uses two pagination styles depending on the endpoint.

### Page-number pagination

Used by most endpoints (repos, issues, users, etc.)

**Query parameters:**
- `per_page` — results per page (default 30, max 100)
- `page` — page number to fetch (default 1)

```
GET /orgs/{org}/repos?per_page=100&page=2
```

### Cursor-based pagination

Used by the **audit log** endpoint. Does not use page numbers.

GitHub returns a `Link` header with the cursor URL for the next page:

```http
Link: <https://api.github.com/orgs/my-org/audit-log?per_page=100&after=Y3Vyc29y...>; rel="next"
```

**Parsing the Link header:**

```python
def get_next_page_url(response):
    link_header = response.headers.get("Link", "")
    for part in link_header.split(","):
        url_part, rel_part = part.strip().split(";")
        if 'rel="next"' in rel_part:
            return url_part.strip().strip("<>")
    return None  # no more pages
```

**Fetching all pages (cursor-based):**

```python
url    = "https://api.github.com/orgs/my-org/audit-log"
params = {"per_page": 100, "include": "all"}
all_events = []

while url:
    resp   = requests.get(url, headers=HEADERS, params=params)
    params = {}  # params only needed on first request; cursor URL has them baked in
    all_events.extend(resp.json())
    url = get_next_page_url(resp)
```

---

## Endpoint: Org Audit Log

### `GET /orgs/{org}/audit-log`

Returns the audit log for an organization — all security and compliance events.

**Who can call this:** Organization owners and security managers only.

**Required token scope:** `read:audit_log`

#### Path parameters

| Parameter | Type | Description |
|---|---|---|
| `org` | string | The organization name (required) |

#### Query parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `phrase` | string | — | Filter phrase. Use `action:repo.create` syntax |
| `include` | string | `web` | `web`, `git`, or `all` (recommended: `all`) |
| `after` | string | — | Cursor for next page (from Link header) |
| `before` | string | — | Cursor for previous page |
| `order` | string | `desc` | `asc` or `desc` |
| `per_page` | integer | 30 | Results per page (max 100) |

#### Example request

```http
GET /orgs/my-org/audit-log?include=all&per_page=100&phrase=action:repo.create
Authorization: Bearer ghp_xxxxx
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
```

#### Example Python call

```python
import requests

HEADERS = {
    "Authorization":        "Bearer ghp_xxxxx",
    "Accept":               "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

resp = requests.get(
    "https://api.github.com/orgs/my-org/audit-log",
    headers=HEADERS,
    params={"include": "all", "per_page": 100, "phrase": "action:repo.create"}
)

events = resp.json()
for event in events:
    print(event["@timestamp"], event["actor"], event["action"], event.get("repo"))
```

#### Response — array of audit log event objects

```json
[
  {
    "@timestamp": 1715356150000,
    "action": "repo.create",
    "actor": "rushwanth-k",
    "actor_id": 261791037,
    "org": "my-org",
    "org_id": 12345,
    "repo": "my-org/new-repo",
    "repo_id": 987654,
    "visibility": "private",
    "created_at": 1715356150000,
    "_document_id": "abc123"
  }
]
```

#### Key response fields

| Field | Type | Description |
|---|---|---|
| `@timestamp` | integer | Unix timestamp in milliseconds |
| `action` | string | Event type (e.g. `repo.create`, `member.add`) |
| `actor` | string | GitHub login of who performed the action |
| `actor_id` | integer | Numeric user ID of the actor |
| `org` | string | Organization name |
| `repo` | string | Full repo name (`org/repo`) |
| `repo_id` | integer | Numeric repo ID |
| `visibility` | string | `public` or `private` (on access change events) |
| `created_at` | integer | Same as `@timestamp` |
| `_document_id` | string | Unique ID for this audit event |

---

## Endpoint: Repo Events

### `GET /repos/{owner}/{repo}/events`

Returns the public activity timeline for a specific repository.

**Who can call this:** Anyone with read access to the repo.

**Required token scope:** `public_repo` (for public repos) or `repo` (for private repos)

**Limits:** Last 300 events, up to 90 days of history.

#### Path parameters

| Parameter | Type | Description |
|---|---|---|
| `owner` | string | Repository owner login (required) |
| `repo` | string | Repository name (required) |

#### Query parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `per_page` | integer | 30 | Results per page (max 100) |
| `page` | integer | 1 | Page number |

#### Example request

```http
GET /repos/Rushwanth-K/kidlearn-app/events?per_page=100
Authorization: Bearer ghp_xxxxx
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
```

#### Example Python call

```python
resp = requests.get(
    "https://api.github.com/repos/Rushwanth-K/kidlearn-app/events",
    headers=HEADERS,
    params={"per_page": 100, "page": 1}
)

for event in resp.json():
    print(event["created_at"], event["actor"]["login"], event["type"])
```

#### Response — real data from `repo_events.json`

```json
[
  {
    "id": "11658412667",
    "type": "PushEvent",
    "actor": {
      "id": 261791037,
      "login": "Rushwanth-K",
      "display_login": "Rushwanth-K",
      "gravatar_id": "",
      "url": "https://api.github.com/users/Rushwanth-K",
      "avatar_url": "https://avatars.githubusercontent.com/u/261791037?"
    },
    "repo": {
      "id": 1234691167,
      "name": "Rushwanth-K/kidlearn-app",
      "url": "https://api.github.com/repos/Rushwanth-K/kidlearn-app"
    },
    "payload": {
      "repository_id": 1234691167,
      "push_id": 33949519828,
      "ref": "refs/heads/main",
      "head": "e81b16049dfbba84b84c2fc0787046043b5af1a1",
      "before": "cb340ca0cd843dffd804283cb92d015adb3a9a7c"
    },
    "public": true,
    "created_at": "2026-05-10T15:09:10Z"
  },
  {
    "id": "11657811651",
    "type": "CreateEvent",
    "actor": {
      "id": 261791037,
      "login": "Rushwanth-K",
      "display_login": "Rushwanth-K",
      "gravatar_id": "",
      "url": "https://api.github.com/users/Rushwanth-K",
      "avatar_url": "https://avatars.githubusercontent.com/u/261791037?"
    },
    "repo": {
      "id": 1234691167,
      "name": "Rushwanth-K/kidlearn-app",
      "url": "https://api.github.com/repos/Rushwanth-K/kidlearn-app"
    },
    "payload": {
      "ref": "main",
      "ref_type": "branch",
      "master_branch": "main",
      "description": null,
      "pusher_type": "user"
    },
    "public": true,
    "created_at": "2026-05-10T14:44:49Z"
  }
]
```

#### Key response fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique event ID |
| `type` | string | Event type (e.g. `PushEvent`, `CreateEvent`) |
| `actor.login` | string | GitHub username who triggered the event |
| `actor.id` | integer | Numeric user ID |
| `repo.name` | string | Full repo name (`owner/repo`) |
| `repo.id` | integer | Numeric repo ID |
| `payload` | object | Event-specific data (varies by type) |
| `public` | boolean | Whether the event is public |
| `created_at` | string | ISO 8601 timestamp |

---

## Endpoint: List Org Repos

### `GET /orgs/{org}/repos`

Lists all repositories in an organization.

**Required token scope:** `read:org` (for private repo metadata: `repo`)

#### Query parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `type` | string | `all` | `all`, `public`, `private`, `forks`, `sources`, `member` |
| `sort` | string | `created` | `created`, `updated`, `pushed`, `full_name` |
| `direction` | string | `asc` | `asc` or `desc` |
| `per_page` | integer | 30 | Max 100 |
| `page` | integer | 1 | Page number |

#### Example Python call

```python
resp = requests.get(
    "https://api.github.com/orgs/my-org/repos",
    headers=HEADERS,
    params={"type": "all", "per_page": 100, "page": 1}
)

for repo in resp.json():
    print(repo["name"], repo["created_at"], repo["visibility"])
```

#### Key response fields per repo

| Field | Type | Description |
|---|---|---|
| `id` | integer | Unique repo ID |
| `name` | string | Repo name (without owner) |
| `full_name` | string | `owner/repo` |
| `private` | boolean | Is the repo private? |
| `owner.login` | string | Owner's GitHub username |
| `created_at` | string | ISO 8601 — when the repo was created |
| `updated_at` | string | ISO 8601 — last metadata update |
| `pushed_at` | string | ISO 8601 — last push to any branch |
| `visibility` | string | `public`, `private`, or `internal` |
| `default_branch` | string | Default branch name (usually `main`) |
| `size` | integer | Repo size in kilobytes |
| `stargazers_count` | integer | Number of stars |
| `forks_count` | integer | Number of forks |
| `language` | string | Primary language detected |

---

## Audit Log Action Types

All action strings follow the format `category.action`. Filter using `phrase=action:repo.create`.

### Repository actions

| Action | Description |
|---|---|
| `repo.create` | Repository created |
| `repo.destroy` | Repository deleted |
| `repo.rename` | Repository renamed |
| `repo.transfer` | Repository transferred to another owner |
| `repo.access` | Repository visibility changed |
| `repo.archived` | Repository archived |
| `repo.unarchived` | Repository unarchived |
| `repo.add_member` | Collaborator added directly to the repo |
| `repo.remove_member` | Collaborator removed from the repo |
| `repo.config.disable_anonymous_git_access` | Anonymous Git access disabled |
| `repo.config.enable_anonymous_git_access` | Anonymous Git access enabled |

### Member / org actions

| Action | Description |
|---|---|
| `member.add` | User added to the org |
| `member.remove` | User removed from the org |
| `member.change_role` | User role changed (member ↔ owner) |
| `org.invite_member` | Org invitation sent |
| `org.cancel_invitation` | Org invitation cancelled |
| `org.block_user` | User blocked from org |
| `org.unblock_user` | User unblocked |

### Team actions

| Action | Description |
|---|---|
| `team.create` | Team created |
| `team.destroy` | Team deleted |
| `team.add_member` | User added to team |
| `team.remove_member` | User removed from team |
| `team.add_repository` | Repo added to team |
| `team.remove_repository` | Repo removed from team |
| `team.change_parent_team` | Team moved in hierarchy |

### Branch protection actions

| Action | Description |
|---|---|
| `protected_branch.create` | Branch protection rule created |
| `protected_branch.destroy` | Branch protection rule deleted |
| `protected_branch.update_admin_enforced` | Admin enforcement toggled |
| `protected_branch.update_require_code_owner_review` | Code owner review requirement changed |
| `protected_branch.required_status_checks_policy_override` | Status checks override |

### Webhook / hook actions

| Action | Description |
|---|---|
| `hook.create` | Webhook created |
| `hook.destroy` | Webhook deleted |
| `hook.config_changed` | Webhook configuration changed |
| `hook.events_changed` | Webhook subscribed events changed |

### OAuth / token actions

| Action | Description |
|---|---|
| `oauth_access.create` | OAuth access granted |
| `oauth_access.destroy` | OAuth access revoked |
| `personal_access_token.access_granted` | PAT granted org access |
| `personal_access_token.access_revoked` | PAT revoked |

---

## Event Types (Repo Events)

These are the `type` values returned by `GET /repos/{owner}/{repo}/events`.

| Event type | Triggered when |
|---|---|
| `PushEvent` | Commits are pushed to a branch |
| `CreateEvent` | A branch or tag is created |
| `DeleteEvent` | A branch or tag is deleted |
| `PullRequestEvent` | A PR is opened, closed, merged, or edited |
| `IssuesEvent` | An issue is opened, closed, or edited |
| `IssueCommentEvent` | A comment is added to an issue or PR |
| `ForkEvent` | Repository is forked |
| `WatchEvent` | Repository is starred |
| `ReleaseEvent` | A release is published |
| `PublicEvent` | Repository is made public |
| `MemberEvent` | A collaborator is added or removed |
| `CommitCommentEvent` | A comment is added to a commit |
| `GollumEvent` | A wiki page is created or updated |

### PushEvent payload fields

```json
{
  "push_id": 33949519828,
  "ref": "refs/heads/main",
  "head": "e81b16049dfbba84b84c2fc0787046043b5af1a1",
  "before": "cb340ca0cd843dffd804283cb92d015adb3a9a7c",
  "commits": [
    {
      "sha": "e81b160...",
      "author": { "name": "Rushwanth", "email": "user@example.com" },
      "message": "Initial commit",
      "url": "https://api.github.com/repos/owner/repo/commits/e81b160..."
    }
  ],
  "distinct_size": 1,
  "size": 1
}
```

### CreateEvent payload fields

```json
{
  "ref": "main",
  "ref_type": "branch",
  "master_branch": "main",
  "description": null,
  "pusher_type": "user"
}
```

`ref_type` can be `branch`, `tag`, or `repository`.

---

## Common Response Fields

These appear in both audit log events and repo events:

| Field | Format | Example |
|---|---|---|
| Audit log timestamp | Unix ms integer | `1715356150000` |
| Repo event timestamp | ISO 8601 string | `"2026-05-10T15:09:10Z"` |
| User login | string | `"Rushwanth-K"` |
| User ID | integer | `261791037` |
| Repo name | `owner/repo` | `"Rushwanth-K/kidlearn-app"` |
| Repo ID | integer | `1234691167` |

**Converting audit log timestamp to readable:**

```python
from datetime import datetime, timezone

ts_ms = 1715356150000
dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
print(dt.strftime("%Y-%m-%d %H:%M:%S UTC"))
# → 2024-05-10 15:09:10 UTC
```

**Converting repo event timestamp:**

```python
from datetime import datetime, timezone

iso_str = "2026-05-10T15:09:10Z"
dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
print(dt.strftime("%Y-%m-%d %H:%M:%S UTC"))
# → 2026-05-10 15:09:10 UTC
```

---

## Error Codes

| HTTP Status | Meaning | Common cause |
|---|---|---|
| `200 OK` | Success | — |
| `201 Created` | Resource created | — |
| `204 No Content` | Success, no body | DELETE operations |
| `301 Moved Permanently` | Resource URL changed | Update your URL |
| `304 Not Modified` | No changes since last request | ETags / conditional requests |
| `400 Bad Request` | Malformed request | Check JSON body or query params |
| `401 Unauthorized` | Missing or invalid token | Check `Authorization` header |
| `403 Forbidden` | Token lacks scope or rate limited | Check token scopes or wait for reset |
| `404 Not Found` | Resource doesn't exist or not accessible | Check org/repo name and token permissions |
| `409 Conflict` | Resource state conflict | e.g. deleting a non-empty branch |
| `422 Unprocessable` | Validation failed | Check request body values |
| `429 Too Many Requests` | Secondary rate limit | Check `Retry-After` header and wait |
| `500 Internal Server Error` | GitHub server error | Retry after a short wait |
| `503 Service Unavailable` | GitHub maintenance | Check status.github.com |

### Error response body

```json
{
  "message": "API rate limit exceeded for user ID 261791037.",
  "documentation_url": "https://docs.github.com/rest/overview/rate-limits-for-the-rest-api"
}
```

---

## Token Scopes Reference

| Scope | Grants access to |
|---|---|
| `repo` | Full control of private repositories |
| `public_repo` | Public repositories only |
| `read:org` | Read org membership, teams, and repos |
| `write:org` | Manage org membership and teams |
| `admin:org` | Full admin access to org |
| `read:audit_log` | Read org audit log |
| `read:user` | Read user profile data |
| `user:email` | Access user email addresses |
| `read:packages` | Download packages from GitHub Packages |
| `write:packages` | Upload packages to GitHub Packages |
| `workflow` | Update GitHub Actions workflow files |
| `notifications` | Access notifications |
| `gist` | Create and edit gists |

---

## Further Reading

- REST API overview: [https://docs.github.com/en/rest/overview](https://docs.github.com/en/rest/overview)
- Audit log REST API: [https://docs.github.com/en/rest/orgs/orgs#get-the-audit-log-for-an-organization](https://docs.github.com/en/rest/orgs/orgs#get-the-audit-log-for-an-organization)
- Repo events API: [https://docs.github.com/en/rest/activity/events](https://docs.github.com/en/rest/activity/events)
- List org repos: [https://docs.github.com/en/rest/repos/repos#list-organization-repositories](https://docs.github.com/en/rest/repos/repos#list-organization-repositories)
- Audit log actions list: [https://docs.github.com/en/organizations/keeping-your-organization-secure/reviewing-the-audit-log-for-your-organization#audit-log-actions](https://docs.github.com/en/organizations/keeping-your-organization-secure/reviewing-the-audit-log-for-your-organization#audit-log-actions)
- Rate limits: [https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api](https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api)
- Token scopes: [https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps)
