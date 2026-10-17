# Local HTTP API

Set a random bearer token and start the server:

```sh
export IONOS_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
ionos-mail serve --port 8765
```

The server binds only to `127.0.0.1`. All mail endpoints need
`Authorization: Bearer <IONOS_API_TOKEN>`. Endpoints:

| Method | Path | Action |
| --- | --- | --- |
| GET | `/health` | Process health only |
| GET | `/v1/folders` | List IMAP folders and flags |
| POST | `/v1/drafts` | Save a draft via IMAP |
| POST | `/v1/drafts/send` | Send an existing draft by `uid` |
| POST | `/v1/messages` | Submit mail via SMTP |

The `/v1/drafts` and `/v1/messages` endpoints accept JSON fields `to` (array), `cc` (array), `bcc`
(array), `subject` (string), and `body` (string). At least one recipient is
required. For example:

```sh
curl -fsS http://127.0.0.1:8765/v1/drafts \
  -H "Authorization: Bearer $IONOS_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"to":["person@example.org"],"subject":"Hello","body":"Draft text"}'
```

Switch the path to `/v1/messages` to send. A draft's `bcc` is saved in its
message for later editing; a sent message uses Bcc only in the SMTP envelope.
Do not expose this local API to the public Internet. POST requests are not
idempotent; retrying after an uncertain network failure can create a duplicate
draft or send a duplicate message.

`POST /v1/drafts/send` accepts only `{"uid":"456"}`. It does not accept a
message body or recipients. The UID is scoped to the detected Drafts folder.

Responses use JSON. Successful draft creation returns HTTP 201; other successful
mail operations return 200. Invalid payloads return 400, missing or incorrect
authorization returns 401, unsupported paths return 404, invalid body size returns
413 and transport failures return 502. `/health` does not require authorization
and does not check mailbox connectivity. Replies and deletion are MCP-only.
