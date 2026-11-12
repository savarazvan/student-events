# UBB Student Events

FastAPI + PostgreSQL backend for managing events of UBB student organizations.
The API reference for frontend developers is further below in this file.

## Running the project

### Option A — Docker (recommended)

Requirements: Docker Desktop.

```sh
cp .env.example .env        # Windows: copy .env.example .env
docker compose up --build
```

This starts PostgreSQL, applies the database migrations, seeds the initial data and starts
the API with auto-reload (the `backend/` folder is mounted into the container,
so code changes are picked up immediately).

- API: http://localhost:8000
- Interactive docs (Swagger): http://localhost:8000/docs
- DB health check: http://localhost:8000/health/db

Seeded super-admin account: `admin@ubbcluj.ro` / `Admin123456!`
(member of the `OSUBB` and `BEST Cluj-Napoca` organizations).

Stop with `Ctrl+C`; `docker compose down -v` also wipes the database.

### Option B — Local Python (no Docker for the API)

Requirements: **Python 3.12+** and a running PostgreSQL (for example only the
database container: `docker compose up -d db`).

```sh
cp .env.example .env        # set DATABASE_URL to your PostgreSQL (localhost:5432 by default)
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed          # applies migrations + initial data (safe to re-run)
uvicorn app.main:app --reload
```

The backend reads the `.env` file from the repository root automatically.

### Running the tests

The tests use an in-memory SQLite database, so no PostgreSQL is needed:

```sh
cd backend
pytest
```

### Configuration (`.env`)

| Variable | Purpose | Default |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Database credentials used by Docker | `postgres` / `postgrespassword` / `student_events_db` |
| `SECRET_KEY` | JWT signing key — **set a long random value** | dev-only value in Docker |
| `DATABASE_URL` | Only for running the API outside Docker | `postgresql+asyncpg://postgres:postgrespassword@localhost:5432/student_events_db` |
| `CORS_ORIGINS` | Comma-separated frontend origins | `http://localhost:3000,http://localhost:5173` |
| `SQL_ECHO` | Log every SQL query | `false` |
| `TICKET_SECRET` | Key that signs QR ticket tokens (changing it invalidates issued QR codes) | derived from `SECRET_KEY` |
| `CHECKIN_OPENS_MINUTES_BEFORE` | How early before the start organizers can scan tickets | `60` |

---

# UBB Student Events - Frontend API Integration Guide

This guide documents the authentication and super-admin endpoints currently
implemented by the FastAPI backend. Examples use `http://localhost:8000` as
the development base URL. Replace it with the deployed API origin in each
environment.

## 1. Authentication & Security Overview

### Login flow

The API uses a password-based credential exchange: the client submits a
user's email and password to `POST /api/v1/auth/login`, and the server returns
a signed JWT access token. The login operation follows the OAuth2 Password
flow conceptually, but **the current endpoint accepts JSON credentials**; it
does not accept standard OAuth2 `application/x-www-form-urlencoded`
`username`/`password` fields.

The access token expires after 30 minutes. There is no refresh-token endpoint;
when a token expires, prompt the user to sign in again.

### Authenticated requests

Send the access token on every protected request:

```http
Authorization: Bearer <access_token>
```

Do not include credentials in URLs or ship signing secrets in a frontend
application. Store tokens using the security approach appropriate to your
client (for browser apps, prefer secure, `HttpOnly`, `SameSite` cookies if the
backend is configured to support them; otherwise evaluate the risks of
browser storage).

### Roles

| Scope | Role | Meaning |
|---|---|---|
| Global | `USER` | Standard authenticated account |
| Global | `SUPER_ADMIN` | Can use every Admin endpoint |
| Organization | `ADMIN` | Admin-level organization membership |
| Organization | `ORGANIZER` | Organizer-level organization membership |
| Organization | `MEMBER` | Standard organization membership |

The current Python model defines `ADMIN` as an alias of `ORG_ADMIN`. The
persisted/API enum value is `ORG_ADMIN`; send and expect `ORG_ADMIN` in JSON
role fields.

## 2. Auth Endpoints (`/api/v1/auth`)

All Auth endpoints use JSON request bodies except `GET /me`, which has no
body.

| Method & path | Description | Required role | Request content type | Success |
|---|---|---|---|---|
| `POST /api/v1/auth/register` | Public student registration | Public | `application/json` | `201 Created` |
| `POST /api/v1/auth/login` | Exchange credentials for an access token | Public | `application/json` | `200 OK` |
| `GET /api/v1/auth/me` | Return the current profile and organization memberships | Authenticated | None | `200 OK` |

### `POST /api/v1/auth/register`

Creates a standard active account with global role `USER`. Email is trimmed
and lowercased; password must be at least 8 characters and no more than 72
UTF-8 bytes.

Request body:

```json
{
  "email": "student@ubbcluj.ro",
  "password": "Password123!",
  "full_name": "Ion Popescu"
}
```

Success response (`201 Created`):

```json
{
  "id": "8e4ba76e-55c8-4f5b-86a6-0669d128a442",
  "email": "student@ubbcluj.ro",
  "full_name": "Ion Popescu",
  "global_role": "USER",
  "is_active": true,
  "organization_memberships": []
}
```

`hashed_password` is never returned.

Common errors:

| Status | Meaning |
|---|---|
| `400 Bad Request` | An account with this email already exists |
| `422 Unprocessable Entity` | Missing/invalid email, password, or full name |

### `POST /api/v1/auth/login`

Authenticates an active user and returns a JWT. Despite the OAuth2-style
password credential exchange, this implementation requires a JSON body (not
`application/x-www-form-urlencoded`).

Request body:

```json
{
  "email": "student@ubbcluj.ro",
  "password": "Password123!"
}
```

Success response (`200 OK`):

```json
{
  "access_token": "<access_token>",
  "token_type": "bearer"
}
```

Use the returned token in the `Authorization` header for protected endpoints.

Common errors:

| Status | Meaning |
|---|---|
| `401 Unauthorized` | Incorrect email/password or account is inactive |
| `422 Unprocessable Entity` | Missing or invalid request fields |

### `GET /api/v1/auth/me`

Returns the profile for the authenticated account, including organization
memberships. Send `Authorization: Bearer <access_token>`. No query parameters
or request body are used.

Success response (`200 OK`):

```json
{
  "id": "8e4ba76e-55c8-4f5b-86a6-0669d128a442",
  "email": "student@ubbcluj.ro",
  "full_name": "Ion Popescu",
  "global_role": "USER",
  "is_active": true,
  "organization_memberships": [
    {
      "organization_id": "d44af106-f11e-40e0-8d70-09f38e73eaa8",
      "organization_name": "OSUBB",
      "role": "ORGANIZER"
    }
  ]
}
```

When the user has no memberships, `organization_memberships` is an empty
array.

Common errors:

| Status | Meaning |
|---|---|
| `401 Unauthorized` | Missing/invalid/expired token or inactive account |

## 3. Admin Endpoints (`/api/v1/admin`)

Every endpoint in this section requires a valid token for a user with the
global role `SUPER_ADMIN`. Organization roles and global roles are case
sensitive.

| Method & path | Description | Required role | Request content type | Success |
|---|---|---|---|---|
| `POST /api/v1/admin/organizations` | Create an organization | `SUPER_ADMIN` | `application/json` | `201 Created` |
| `GET /api/v1/admin/organizations` | List all organizations | `SUPER_ADMIN` | None | `200 OK` |
| `POST /api/v1/admin/organizations/{org_id}/members` | Create or update an organization's user membership | `SUPER_ADMIN` | `application/json` | `200 OK` |
| `PATCH /api/v1/admin/users/{user_id}/global-role` | Change a user's global role | `SUPER_ADMIN` | `application/json` | `200 OK` |

### `POST /api/v1/admin/organizations`

Creates an organization. Organization names must be unique. `description` is
optional and may be `null`; `contact_email` is required.

Request body:

```json
{
  "name": "Student Volunteers",
  "description": "Volunteer activities for students",
  "contact_email": "contact@ubbcluj.ro"
}
```

Success response (`201 Created`):

```json
{
  "id": "d44af106-f11e-40e0-8d70-09f38e73eaa8",
  "name": "Student Volunteers",
  "description": "Volunteer activities for students",
  "contact_email": "contact@ubbcluj.ro"
}
```

Common errors:

| Status | Meaning |
|---|---|
| `400 Bad Request` | An organization with this name already exists |
| `401 Unauthorized` | Missing/invalid/expired token |
| `403 Forbidden` | Caller does not have `SUPER_ADMIN` |
| `422 Unprocessable Entity` | Invalid or missing request fields |

### `GET /api/v1/admin/organizations`

Returns all organizations, ordered by name. No query parameters or request
body are used.

Success response (`200 OK`):

```json
[
  {
    "id": "97f8b29d-8a0d-4c45-9158-86f6f76625ba",
    "name": "BEST Cluj-Napoca",
    "description": null,
    "contact_email": null
  },
  {
    "id": "d44af106-f11e-40e0-8d70-09f38e73eaa8",
    "name": "OSUBB",
    "description": null,
    "contact_email": null
  }
]
```

The response is `[]` if no organizations exist.

Common errors:

| Status | Meaning |
|---|---|
| `401 Unauthorized` | Missing/invalid/expired token |
| `403 Forbidden` | Caller does not have `SUPER_ADMIN` |

### `POST /api/v1/admin/organizations/{org_id}/members`

Creates a membership or updates the existing role for the given user and
organization. Replace `{org_id}` with the organization's UUID. `user_id` must
refer to an existing account.

Request body:

```json
{
  "user_id": "8e4ba76e-55c8-4f5b-86a6-0669d128a442",
  "role": "ORGANIZER"
}
```

Supported `role` values: `ORG_ADMIN`, `ORGANIZER`, `MEMBER`.

Success response (`200 OK`):

```json
{
  "id": "56dc31cd-0c54-4381-a938-29a1bd16bdfe",
  "user_id": "8e4ba76e-55c8-4f5b-86a6-0669d128a442",
  "organization_id": "d44af106-f11e-40e0-8d70-09f38e73eaa8",
  "role_in_org": "ORGANIZER"
}
```

Common errors:

| Status | Meaning |
|---|---|
| `401 Unauthorized` | Missing/invalid/expired token |
| `403 Forbidden` | Caller does not have `SUPER_ADMIN` |
| `404 Not Found` | Organization or user does not exist |
| `422 Unprocessable Entity` | Invalid UUID or membership role/body |

### `PATCH /api/v1/admin/users/{user_id}/global-role`

Changes a user's global role. Replace `{user_id}` with the account UUID.

Request body:

```json
{
  "global_role": "SUPER_ADMIN"
}
```

Supported `global_role` values: `USER`, `SUPER_ADMIN`.

Success response (`200 OK`):

```json
{
  "id": "8e4ba76e-55c8-4f5b-86a6-0669d128a442",
  "email": "student@ubbcluj.ro",
  "full_name": "Ion Popescu",
  "global_role": "SUPER_ADMIN",
  "is_active": true
}
```

Common errors:

| Status | Meaning |
|---|---|
| `401 Unauthorized` | Missing/invalid/expired token |
| `403 Forbidden` | Caller does not have `SUPER_ADMIN` |
| `404 Not Found` | User does not exist |
| `422 Unprocessable Entity` | Invalid UUID or global role/body |

## 4. Event Endpoints (`/api/v1/events`)

| Method & path | Description | Required role | Success |
|---|---|---|---|
| `GET /api/v1/events` | List events, filtered by organization, status, category, date range or keyword | Public; non-published visibility is restricted | `200 OK` |
| `POST /api/v1/events` | Create an event in an organization | `SUPER_ADMIN` or organization `ORG_ADMIN`/`ORGANIZER` | `201 Created` |
| `GET /api/v1/events/{event_id}` | Get an event by UUID | Public (`DRAFT`/`SUBMITTED` only for the organization's managers) | `200 OK` |
| `PUT /api/v1/events/{event_id}` | Update event details | `SUPER_ADMIN` or event organization `ORG_ADMIN`/`ORGANIZER` | `200 OK` |
| `PATCH /api/v1/events/{event_id}/status` | Move the event through its lifecycle | Depends on the transition (see below) | `200 OK` |
| `GET /api/v1/events/{event_id}/register` | The current user's registration for this event | Authenticated | `200 OK` |
| `POST /api/v1/events/{event_id}/register` | Register (and receive a ticket) or join the waitlist | Authenticated | `201 Created` |
| `DELETE /api/v1/events/{event_id}/register` | Cancel registration, revoke the ticket, promote the next waitlisted user | Authenticated | `200 OK` |
| `GET /api/v1/events/{event_id}/attendees` | List non-cancelled registrants with check-in time | `SUPER_ADMIN` or event organization `ORG_ADMIN`/`ORGANIZER` | `200 OK` |
| `POST /api/v1/events/{event_id}/check-in` | Check in a scanned QR ticket | `SUPER_ADMIN` or event organization `ORG_ADMIN`/`ORGANIZER` | `200 OK` |
| `POST /api/v1/events/{event_id}/check-in/manual` | Check in an attendee by user id (QR fallback) | `SUPER_ADMIN` or event organization `ORG_ADMIN`/`ORGANIZER` | `200 OK` |
| `DELETE /api/v1/events/{event_id}/check-in/{ticket_id}` | Undo a mistaken check-in | `SUPER_ADMIN` or event organization `ORG_ADMIN`/`ORGANIZER` | `204 No Content` |
| `GET /api/v1/events/{event_id}/attendance` | Attendance statistics | `SUPER_ADMIN` or event organization `ORG_ADMIN`/`ORGANIZER` | `200 OK` |

The student's own schedule and tickets are under `/api/v1/me` (section 5).

Protected endpoints require `Authorization: Bearer <access_token>`. Requests
with a JSON body use `Content-Type: application/json`.

### `GET /api/v1/events`

Optional query parameters:

| Parameter | Type | Description |
|---|---|---|
| `organization_id` | UUID | Restrict results to one organization |
| `status` | `DRAFT`, `SUBMITTED`, `PUBLISHED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` | Restrict results to a status when the caller can view that status |
| `category` | `WORKSHOP`, `CONFERENCE`, `TRAINING`, `SOCIAL`, `VOLUNTEERING`, `COMPETITION`, `OTHER` | Restrict results to one category |
| `starts_after` | ISO 8601 datetime | Events starting at or after this moment |
| `starts_before` | ISO 8601 datetime | Events starting before this moment |
| `search` | string | Case-insensitive substring search in title or description |
| `page` | integer, default `1` | 1-based page number |
| `size` | integer, default `20`, range `1`–`100` | Number of results per page |

Unauthenticated and regular users only receive `PUBLISHED` and `IN_PROGRESS`
events, even when requesting another status. A super admin may view any status. An organization
admin or organizer may view all statuses for their organization when they
provide its `organization_id`.

Example:

```http
GET /api/v1/events?organization_id=d44af106-f11e-40e0-8d70-09f38e73eaa8&status=PUBLISHED
```

Success response (`200 OK`) is an object containing pagination metadata and an
`items` array of event objects:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "size": 20
}
```

### `POST /api/v1/events`

Creates an event in `DRAFT` state. The creator is taken from the access token;
clients do not send `created_by_id` or `status`.

Request body:

```json
{
  "title": "Student Tech Meetup",
  "description": "A meetup for student developers.",
  "location": "UBB Main Building",
  "start_time": "2026-12-01T10:00:00Z",
  "end_time": "2026-12-01T12:00:00Z",
  "capacity": 100,
  "organization_id": "d44af106-f11e-40e0-8d70-09f38e73eaa8",
  "image_url": "https://cdn.example.com/posters/tech-meetup.webp",
  "category": "WORKSHOP",
  "registration_deadline": "2026-11-30T22:00:00Z"
}
```

`category` defaults to `OTHER`. `registration_deadline` is optional and must
not be after `start_time`; when it is `null`, registration closes when the
event starts. `description` and `image_url` are optional; either may be `null`. Image URLs
must be absolute HTTP(S) URLs ending in `.png`, `.jpg`, `.jpeg`, or `.webp`.
Base64 data images are limited to 5 MB and must match their declared image
type and file signature. The reusable direct-upload validator also checks
extension, MIME type, file signature, and the 5 MB limit; there is not
currently a multipart upload endpoint. The API does not download remote URLs
to inspect their content or size.

Success response (`201 Created`):

```json
{
  "id": "ec34db1a-957d-4c36-937a-a1e899df8951",
  "title": "Student Tech Meetup",
  "description": "A meetup for student developers.",
  "location": "UBB Main Building",
  "start_time": "2026-12-01T10:00:00Z",
  "end_time": "2026-12-01T12:00:00Z",
  "capacity": 100,
  "status": "DRAFT",
  "organization_id": "d44af106-f11e-40e0-8d70-09f38e73eaa8",
  "created_by_id": "8e4ba76e-55c8-4f5b-86a6-0669d128a442",
  "created_at": "2026-11-08T15:00:00Z",
  "image_url": "https://cdn.example.com/posters/tech-meetup.webp",
  "category": "WORKSHOP",
  "registration_deadline": "2026-11-30T22:00:00Z"
}
```

Common errors: `400` invalid image URL/data; `401` missing/invalid token;
`403` insufficient organization role; `404` organization not found; `422`
invalid event body.

### `GET /api/v1/events/{event_id}`

Replace `{event_id}` with the event UUID. No body is required. Returns an
event object using the response shape above.

`DRAFT` and `SUBMITTED` events are only returned to the organization's
admins/organizers (and super admins); everyone else gets `404`.

Common errors: `404` event not found; `422` malformed UUID.

### `PUT /api/v1/events/{event_id}`

Updates event details. Send one or more fields from the event create schema;
omitted fields remain unchanged. `description` can be set to `null`.

Example request body:

```json
{
  "title": "Student Tech Meetup - Updated",
  "description": null,
  "capacity": 120,
  "image_url": null
}
```

Raising `capacity` on a published event immediately promotes waitlisted
students (oldest first) and issues their tickets. Lowering it below the number
of confirmed registrations is refused. `COMPLETED` and `CANCELLED` events can
no longer be edited.

Success response: `200 OK` with the full updated event object.

Common errors: `401` missing/invalid token; `403` insufficient organization
role; `400` unsupported image URL; `404` event not found; `409` event is
completed/cancelled or capacity below confirmed registrations; `422` invalid
fields, end time not after start time, or deadline after start time.

### `PATCH /api/v1/events/{event_id}/status`

Events follow a fixed lifecycle:

```
DRAFT ──▶ SUBMITTED ──▶ PUBLISHED ──▶ IN_PROGRESS ──▶ COMPLETED
  │  ◀──────┘  │            │              │
  └────────────┴────────────┴──────────────┴──▶ CANCELLED
```

| From | Allowed targets | Who |
|---|---|---|
| `DRAFT` | `SUBMITTED` | Organizer or org admin |
| `DRAFT` | `PUBLISHED`, `CANCELLED` | Org admin |
| `SUBMITTED` | `DRAFT` (withdraw / send back) | Organizer or org admin |
| `SUBMITTED` | `PUBLISHED`, `CANCELLED` | Org admin |
| `PUBLISHED` | `IN_PROGRESS`, `CANCELLED` | Org admin |
| `IN_PROGRESS` | `COMPLETED`, `CANCELLED` | Org admin |
| `COMPLETED`, `CANCELLED` | — (final) | — |

Super admins may perform every allowed transition. Setting the current status
again is a no-op. Cancelling an event revokes every ticket issued for it. An
event that has already ended cannot be published.

Request body:

```json
{
  "status": "PUBLISHED"
}
```

Success response: `200 OK` with the full event object and updated status.

Common errors: `401` missing/invalid token; `403` role not allowed for this
transition; `404` event not found; `409` transition not allowed; `422` invalid
status.

### `POST /api/v1/events/{event_id}/register`

Requires a valid access token for the registering user. No body is required.
Registrations are unique per event and user. Registration is only possible
while the event is `PUBLISHED` and before its `registration_deadline` (or its
start time when there is no deadline). If the event has fewer confirmed
registrations than its capacity, the registration is `CONFIRMED` and a ticket
is issued (`ticket_id`); otherwise the user joins the `WAITLIST` and gets a
ticket when promoted. The event row is locked during the capacity check
(`SELECT ... FOR UPDATE`), so concurrent sign-ups can never overbook.

Success response (`201 Created`):

```json
{
  "id": "56dc31cd-0c54-4381-a938-29a1bd16bdfe",
  "event_id": "ec34db1a-957d-4c36-937a-a1e899df8951",
  "user_id": "8e4ba76e-55c8-4f5b-86a6-0669d128a442",
  "status": "WAITLIST",
  "registered_at": "2026-11-08T15:00:00Z",
  "ticket_id": null
}
```

`GET /api/v1/events/{event_id}/register` returns the same object for the
current user (useful to render the button state), or `404` when the user is
not registered.

Repeating a registration that is already active returns the existing
registration. A cancelled registration can be reactivated and is assigned a
confirmed or waitlist status based on available capacity.

Common errors: `401` missing/invalid token; `404` event not found; `409`
event not published or registration closed.

### `DELETE /api/v1/events/{event_id}/register`

Cancels the current user's registration and revokes their ticket. When a
confirmed user cancels, the oldest waitlisted registration is promoted to
`CONFIRMED` and receives a ticket. A user who has already checked in, or whose
event is `COMPLETED`, cannot cancel (`409`). No body is required.

Success response (`200 OK`) returns the cancelling user's registration with
`"status": "CANCELLED"`.

Common errors: `401` missing/invalid token; `404` event or registration not
found.

### `GET /api/v1/events/{event_id}/attendees`

Requires super-admin or organizer/admin membership in the event's
organization. No body is required. Returns confirmed and waitlisted users;
cancelled registrations are excluded.

Success response (`200 OK`):

```json
[
  {
    "user_id": "8e4ba76e-55c8-4f5b-86a6-0669d128a442",
    "full_name": "Ion Popescu",
    "email": "student@ubbcluj.ro",
    "registered_at": "2026-11-08T15:00:00Z",
    "status": "CONFIRMED",
    "ticket_id": "0b5e2a6e-3c1d-4f7e-9a51-2f6a1c0e8d11",
    "checked_in_at": null
  }
]
```

Common errors: `401` missing/invalid token; `403` insufficient organization
role; `404` event not found.

### `POST /api/v1/events/{event_id}/check-in`

Used by the organizer's scanner. Send the text decoded from the attendee's QR
code:

```json
{ "token": "<qr_token>" }
```

The token is signed by the server, so forged or altered codes are rejected.
Check-in is possible while the event is `PUBLISHED` or `IN_PROGRESS`, from
`CHECKIN_OPENS_MINUTES_BEFORE` minutes (default 60) before the start until the
end time. Each ticket can be checked in once; simultaneous scans of the same
ticket are serialized by a row lock.

Success response (`200 OK`) — show the name to the person at the door:

```json
{
  "ticket_id": "0b5e2a6e-3c1d-4f7e-9a51-2f6a1c0e8d11",
  "user_id": "8e4ba76e-55c8-4f5b-86a6-0669d128a442",
  "full_name": "Ion Popescu",
  "email": "student@ubbcluj.ro",
  "checked_in_at": "2026-12-01T09:52:10Z",
  "checked_in_by_id": "81be345b-35c2-4796-ba80-de8b7f0612c0"
}
```

| Status | Meaning (`detail` text is safe to display) |
|---|---|
| `400` | Invalid/forged ticket, ticket for a different event, or ticket revoked |
| `403` | Caller is not an admin/organizer of the event's organization |
| `409` | Ticket already checked in (includes the time), check-in not open yet / closed, or event not in a check-in state |

`POST /api/v1/events/{event_id}/check-in/manual` with `{ "user_id": "<uuid>" }`
checks in a confirmed attendee without a QR code (same response and rules;
`404` when the user has no valid ticket). `DELETE
/api/v1/events/{event_id}/check-in/{ticket_id}` reverts a mistaken check-in
(`204`).

### `GET /api/v1/events/{event_id}/attendance`

Attendance statistics for admins/organizers of the event's organization:

```json
{
  "event_id": "ec34db1a-957d-4c36-937a-a1e899df8951",
  "capacity": 100,
  "confirmed": 80,
  "waitlisted": 12,
  "cancelled": 5,
  "checked_in": 64,
  "not_checked_in": 16,
  "attendance_rate": 0.8,
  "spots_left": 20
}
```

## 5. My Schedule & Tickets (`/api/v1/me`)

All endpoints require the student's access token.

| Method & path | Description | Success |
|---|---|---|
| `GET /api/v1/me/registrations` | The student's registrations with event summary and ticket state | `200 OK` |
| `GET /api/v1/me/tickets/{ticket_id}` | Ticket details including the QR token | `200 OK` |
| `GET /api/v1/me/tickets/{ticket_id}/qr.svg` | Ready-made QR code image (`image/svg+xml`) | `200 OK` |

### `GET /api/v1/me/registrations`

Query parameters: `upcoming` (boolean, default `false`) — only events that have
not ended; `include_cancelled` (boolean, default `false`). Ordered by start
time.

```json
[
  {
    "id": "56dc31cd-0c54-4381-a938-29a1bd16bdfe",
    "status": "CONFIRMED",
    "registered_at": "2026-11-08T15:00:00Z",
    "ticket_id": "0b5e2a6e-3c1d-4f7e-9a51-2f6a1c0e8d11",
    "ticket_state": "VALID",
    "checked_in_at": null,
    "event": {
      "id": "ec34db1a-957d-4c36-937a-a1e899df8951",
      "title": "Student Tech Meetup",
      "location": "UBB Main Building",
      "start_time": "2026-12-01T10:00:00Z",
      "end_time": "2026-12-01T12:00:00Z",
      "status": "PUBLISHED",
      "category": "WORKSHOP",
      "organization_id": "d44af106-f11e-40e0-8d70-09f38e73eaa8"
    }
  }
]
```

`ticket_state` is `VALID`, `USED` (checked in) or `REVOKED`; it is `null` for
waitlisted registrations, which have no ticket yet.

### `GET /api/v1/me/tickets/{ticket_id}`

Returns `id`, `registration_id`, `state`, `issued_at`, `checked_in_at`, the
`event` summary and `qr_token`. Encode `qr_token` in a QR code (or simply use
`qr.svg` below). `qr_token` is `null` once the ticket is revoked. Another
user's ticket returns `404`.

### `GET /api/v1/me/tickets/{ticket_id}/qr.svg`

Returns the QR code as an SVG image (`410 Gone` when the ticket is revoked).
Because it needs the `Authorization` header, fetch it with your HTTP client and
display it via a blob/object URL rather than a plain `<img src>`.

## 6. Frontend Integration Notes

- Send `Content-Type: application/json` with every JSON request.
- Send the Bearer token on `/api/v1/auth/me`, all `/api/v1/admin` requests,
  and protected event mutations.
- Use the role strings exactly as listed in the request examples. The
  organization admin role's API enum value is `ORG_ADMIN` (`ADMIN` is a
  Python-side alias).
- Treat `422` as a request validation error and surface field-level feedback
  where possible. FastAPI returns validation details in the `detail` array.
- Treat `401` as an authentication failure; clear the expired/invalid token
  and ask the user to sign in again. A `403` means the authenticated account
  lacks permission for that operation.
