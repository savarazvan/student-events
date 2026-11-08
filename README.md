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

## 4. Frontend Integration Notes

- Send `Content-Type: application/json` with every JSON request.
- Send the Bearer token on `/api/v1/auth/me` and all `/api/v1/admin` requests.
- Use the role strings exactly as listed in the request examples. The
  organization admin role's API enum value is `ORG_ADMIN` (`ADMIN` is a
  Python-side alias).
- Treat `422` as a request validation error and surface field-level feedback
  where possible. FastAPI returns validation details in the `detail` array.
- Treat `401` as an authentication failure; clear the expired/invalid token
  and ask the user to sign in again. A `403` means the authenticated account
  lacks permission for that operation.
