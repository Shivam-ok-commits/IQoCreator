# IQoCreator API Contract

> Sprint 4A freeze — do not modify without updating this document.

---

## Base URL

- **Development:** `http://localhost:8000`
- **Production:** TBD

All endpoints return JSON unless noted otherwise.  
Authentication is session-based via `session` cookie (httpOnly).

---

## Endpoints

### 1. Health Check

`GET /health`

No auth required.

**Response `200`**

```json
{
  "status": "ok"
}
```

---

### 2. OAuth Login

`GET /api/auth/login`

Initiates Google OAuth 2.0 flow. Redirects the browser to Google's consent screen.

Sets `oauth_state` cookie (httpOnly, same-site, secure).

**Response `302`** — Redirect to Google accounts URL.

---

### 3. OAuth Callback

`GET /api/auth/callback?code={code}&state={state}`

Exchanges OAuth code for tokens, upserts the user / connected account / creator profile, and creates a session.

**Query Parameters**

| Name    | Type   | Required | Description                  |
|---------|--------|----------|------------------------------|
| `code`  | string | yes      | Authorization code from Google |
| `state` | string | yes      | CSRF state token (from cookie) |
| `error` | string | no       | Google OAuth error            |

**Response `302`** — Redirect to `http://localhost:3000/connected` on success.

**Error responses**

| Code | Condition        | Redirect URL                       |
|------|------------------|------------------------------------|
| 400  | OAuth error      | — (JSON body)                      |
| 302  | Invalid state    | `/?error=invalid_state`            |
| 302  | Missing code     | `/?error=missing_code`             |
| 302  | No access token  | `/?error=no_token`                 |
| 302  | No subject       | `/?error=no_subject`               |

---

### 4. Logout

`POST /api/auth/logout`

No request body. Clears the `session` cookie.

**Response `200`**

```json
{
  "ok": true
}
```

---

### 5. Get Current User

`GET /api/auth/me`

Requires valid `session` cookie.

**Response `200`**

```json
{
  "user": {
    "id": "uuid",
    "email": "string",
    "display_name": "string | null",
    "avatar_url": "string | null"
  },
  "connected_account": {
    "provider": "google | null",
    "has_token": true
  },
  "creator_profile": {
    "name": "string",
    "handle": "string | null",
    "thumbnail_url": "string | null",
    "subscriber_count": "number | null",
    "total_views": "number | null"
  },
  "channel_metrics": {
    "subscriber_count": "number | null",
    "total_views": "number | null",
    "total_videos": "number | null"
  }
}
```

**Notes**

- `creator_profile` is `null` if the user hasn't connected YouTube.
- `channel_metrics` is `null` if no import has run yet.
- `channel_metrics` returns the single most recent `ChannelMetrics` snapshot (ordered by `recorded_at DESC`).
- `subscriber_count` and `total_views` appear in **both** `creator_profile` and `channel_metrics` during Sprint 4A. The frontend prefers `channel_metrics` as the source of truth for numerical metrics and falls back to `creator_profile`.

**Error `401`**

```json
{
  "detail": "Not authenticated"
}
```

---

### 6. Import Channel

`POST /api/import/channel`

Requires valid `session` cookie. Triggers a full channel import from YouTube Data API (snippet, statistics, brandingSettings). Idempotent — subsequent calls upsert `CreatorProfile` and insert a new `ChannelMetrics` row.

**Response `200`**

```json
{
  "success": true,
  "imported": 1,
  "updated": 0,
  "duration_ms": 1234,
  "error": null
}
```

| Field        | Type    | Description                                        |
|-------------|---------|----------------------------------------------------|
| `success`   | boolean | Whether the import completed without hard errors   |
| `imported`  | int     | Number of new records created (1 = first import)   |
| `updated`   | int     | Number of existing records updated                 |
| `duration_ms` | int   | Total wall-clock time in milliseconds              |
| `error`     | string? | Human-readable error message if `success` is false |

**Error `401`**

```json
{
  "detail": "Not authenticated"
}
```

**Error `400`**

```json
{
  "detail": "No connected YouTube account found"
}
```

---

### 7. Get Import Status

`GET /api/import/status`

Requires valid `session` cookie. Returns whether an import has ever been run, when, and a list of all attempts.

**Response `200`**

```json
{
  "imported": true,
  "last_imported_at": "2025-06-15T12:34:56Z",
  "runs": [
    {
      "id": "uuid",
      "status": "completed",
      "videos_imported": 12,
      "videos_failed": 0,
      "error_message": null,
      "started_at": "2025-06-15T12:34:56Z",
      "completed_at": "2025-06-15T12:35:10Z"
    }
  ]
}
```

| Field              | Type      | Description                                 |
|-------------------|-----------|---------------------------------------------|
| `imported`        | boolean   | True if at least one successful import exists |
| `last_imported_at` | string?  | ISO 8601 timestamp of the most recent import  |
| `runs`            | array     | Ordered by `started_at` DESC                 |

Each run:

| Field            | Type      | Description                               |
|------------------|-----------|-------------------------------------------|
| `id`             | string    | UUID                                      |
| `status`         | string    | `pending`, `running`, `completed`, `failed` |
| `videos_imported` | int      | Videos imported in this run                |
| `videos_failed`  | int       | Videos that failed                         |
| `error_message`  | string?   | Error detail if the run failed             |
| `started_at`     | string?   | ISO 8601                                   |
| `completed_at`   | string?   | ISO 8601                                   |

---

## Data Model (relevant fields)

### CreatorProfile

| Column              | Type      | Source             |
|---------------------|-----------|--------------------|
| `name`              | string    | YouTube snippet    |
| `handle`            | string?   | YouTube snippet    |
| `description`       | string?   | YouTube snippet    |
| `thumbnail_url`     | string?   | YouTube snippet    |
| `banner_url`        | string?   | YouTube branding   |
| `country`           | string?   | YouTube snippet    |
| `platform`          | string    | `"youtube"`        |
| `platform_creator_id` | string  | YouTube channel ID |
| `subscriber_count`  | bigint?   | YouTube statistics |
| `total_views`       | bigint?   | YouTube statistics |

### ChannelMetrics (time-series)

| Column               | Type      | Source             |
|----------------------|-----------|--------------------|
| `subscriber_count`   | bigint?   | YouTube statistics |
| `total_views`        | bigint?   | YouTube statistics |
| `total_videos`       | int?      | YouTube statistics |
| `recorded_at`        | datetime  | Import timestamp   |

---

## Version History

| Version | Date       | Author | Changes                        |
|---------|------------|--------|--------------------------------|
| 1.0     | 2025-06-15 | —      | Sprint 4A freeze               |

## Change Rule

Any API response change (new field, removed field, type change, status code change, renamed field) **must** update this document in the same commit.
