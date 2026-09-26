# IONOS Mail Bridge

A CLI, local HTTP API, and Codex MCP plugin for IONOS Mail Basic and Mail Business. It uses
the standard mail protocols that IONOS documents: IMAP over TLS for drafts and
SMTP over TLS for sending. No browser session or Playwright dependency is needed.

## Why IMAP and SMTP?

IONOS's published hosting APIs cover DNS, domains, and SSL, but do not document
mail draft or send endpoints. Its mail service does document IMAP and SMTP. IMAP
`APPEND` saves an RFC 5322 message in the server's Drafts folder with the
`\Draft` flag; SMTP submits outgoing mail. The implementation can also work
with another provider by overriding the host and port environment variables.

References: [IONOS mail settings](https://www.ionos.com/help/email/general-topics/ionos-mail-server-details-for-imap-pop3-and-smtp/),
[IONOS developer APIs](https://www.ionos.com/help/hosting/ionos-apis/ionos-developer-apis/),
[IMAP special-use folders (RFC 6154)](https://www.rfc-editor.org/rfc/rfc6154.html),
[IMAP APPEND (RFC 9051)](https://www.rfc-editor.org/rfc/rfc9051.html),
[TLS for mail access and submission (RFC 8314)](https://www.rfc-editor.org/rfc/rfc8314.html).

## Setup

Requires Python 3.11 or newer and an IONOS mailbox password. The mailbox
address and password are different from IONOS customer account or developer API
credentials. Do not commit credentials. The `.env.example` file is only a field
reference; the program reads actual environment variables.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
export IONOS_MAIL_ADDRESS='you@example.com'
read -s 'IONOS_MAIL_PASSWORD?Mailbox password: '
export IONOS_MAIL_PASSWORD
```

The `read -s` example is for zsh. You can use your shell's preferred secret
manager. The default servers are `imap.ionos.com:993` with TLS and
`smtp.ionos.com:465` with TLS. Set `IONOS_SMTP_PORT=587` for STARTTLS.

## CLI

```sh
ionos-mail folders
ionos-mail draft --to person@example.org --subject 'Hello' --body-file message.txt
ionos-mail send --to person@example.org --subject 'Hello' --body-file message.txt
ionos-mail send-draft --uid 456
```

Use repeated `--to`, `--cc`, and `--bcc` options for multiple recipients.
`--body 'Text'` or piped standard input also work. `draft` saves to an existing
IMAP folder marked `\Drafts`, or an existing folder named `Drafts`. Run
`folders` and set `IONOS_DRAFTS_FOLDER` if the server uses a different name.
The command will not create an arbitrary folder.

`send` submits a new message to SMTP. Its success result means the SMTP server
accepted the message, not that a recipient received it. It does not add a copy
to Sent because server behavior has not been verified. `send-draft` submits an
existing draft by its UID (when the server reports one after creation). After
SMTP acceptance, it removes only that UID when the server supports UIDPLUS;
otherwise the result reports `draft_retained: true`. If no UID was returned,
find the draft with the MCP `messages` tool using the Drafts folder.

## Local HTTP API

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

Both POST endpoints accept JSON fields `to` (array), `cc` (array), `bcc`
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

## Codex MCP plugin

The bundled plugin is at `plugins/ionos-mail/`. Its stdio server offers seven
tools: `folders`, `messages`, `search`, `read_message`, `save_draft`, `send`, and
`send_draft`.
Read tools use `BODY.PEEK` and a read-only IMAP folder selection so they do not
mark messages as read. Message bodies are limited to 100,000 characters in the
tool response; attachments are listed by filename but are not downloaded as
files. The bundled workflow calls `send` only when the user explicitly asks.

The plugin launcher uses `uv` to install the MCP extra in the checkout and
start the server. Install `uv` from its official distribution, then make sure
`python3` and `uv` are on Codex's `PATH`. As an alternative, install the package
with the MCP extra and put `ionos-mail-mcp` on `PATH`:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install '.[mcp]'
ionos-mail-mcp
```

The last command waits for an MCP host on stdio and normally prints nothing;
press Ctrl-C after confirming it starts. Set `IONOS_MAIL_ADDRESS` and
`IONOS_MAIL_PASSWORD` in the Codex process environment. The plugin manifest
forwards those names to the MCP subprocess. It does not store the password.

The repository includes `.agents/plugins/marketplace.json` for local plugin
discovery. From this repository, run `codex plugin marketplace add .`, then
install **IONOS Mail** from the Plugins Directory in a new Codex chat. The
plugin runs locally; it is not a hosted ChatGPT plugin or a public MCP service.
Its Python launcher resolves the project root from the plugin's checkout, so
keep the repository intact when installing the plugin.

## Validation

```sh
python -m unittest discover -s tests -v
```

Automated tests mock the mail servers. MCP tool discovery was tested over
stdio. A live IONOS account has not been used to confirm folder naming or
message delivery.
