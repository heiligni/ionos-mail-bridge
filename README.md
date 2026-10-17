# IONOS Mail Bridge

Read mail, prepare drafts and send replies from local tools using IMAP and SMTP.
Use it as a command-line application, a local HTTP API or a Codex MCP plugin.
No browser automation or hosted service is required.

Independent community project. Not affiliated with or endorsed by IONOS.
Early-stage software, licensed under [MIT](LICENSE).

## Quick start

Requires Python 3.11+ and an IONOS mailbox. Run these commands from a checkout:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
ionos-mail configure --address you@example.com
# For German IONOS mailboxes:
ionos-mail region de
ionos-mail folders
ionos-mail draft --to person@example.org --subject 'Hello' --body 'A draft to review.'
```

`configure` prompts for the mailbox password and stores it in your operating
system keyring. The last command saves a draft; it does not send mail.
See [configuration](docs/configuration.md) for regions, environment overrides
and troubleshooting, or [MCP setup](docs/mcp.md) to use the tools in Codex.

## What it does

| Feature | CLI | HTTP | MCP |
| --- | --- | --- | --- |
| List folders | Yes | Yes | Yes |
| Search and read mail | No | No | Yes |
| Create drafts and send mail | Yes | Yes | Yes |
| Send a saved draft | Yes | Yes | Yes |
| Threaded replies | No | No | Yes |
| Delete a draft | No | No | Yes, requires UIDPLUS |

Read operations leave messages unread. Replies include `In-Reply-To` and
`References` so mail clients can keep the conversation together. Message bodies
are plain text; attachments are listed on reads, but sending attachments and
HTML composition are not implemented.

SMTP acceptance does not confirm delivery. Sent drafts may remain in Drafts
when the server lacks UIDPLUS; do not resend them. Permanent draft deletion is
also unavailable without UIDPLUS. See [security and operational limits](SECURITY.md).

## Documentation

- [Configuration](docs/configuration.md): credentials, regions, environment and troubleshooting
- [CLI](docs/cli.md): draft and send commands
- [Local HTTP API](docs/http-api.md): endpoints, payloads and responses
- [MCP and Codex](docs/mcp.md): tools, installation and reply workflow
- [Architecture](docs/architecture.md): repository map, module responsibilities and verification scope
- [Contributing](CONTRIBUTING.md): development setup and tests
- [Security](SECURITY.md): trust model and vulnerability reporting

## Development

```sh
python -m pip install -e '.[mcp]'
python -m unittest discover -s tests -v
```

Tests run offline with fake mail servers and need no credentials. GitHub Actions
runs the suite on Python 3.11, 3.12 and 3.13. Live German IONOS/Gmail checks have
confirmed delivery and reply threading; other providers and live UIDPLUS deletion
remain unverified. This project has no guaranteed support response time.

## Protocols

The bridge uses IMAP over TLS for mailbox operations and SMTP over TLS for
submission. Other providers can be configured through host/port overrides.

References: [IONOS settings](https://www.ionos.com/help/email/general-topics/ionos-mail-server-details-for-imap-pop3-and-smtp/),
[German IONOS settings](https://www.ionos.de/hilfe/e-mail/allgemeine-themen/serverinformationen-fuer-imap-pop3-und-smtp/),
[IMAP special-use folders](https://www.rfc-editor.org/rfc/rfc6154.html),
[IMAP](https://www.rfc-editor.org/rfc/rfc9051.html),
[mail TLS](https://www.rfc-editor.org/rfc/rfc8314.html).
