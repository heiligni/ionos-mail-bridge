# Configuration

Requires Python 3.11 or newer and an IONOS mailbox password. The mailbox
address and password are different from IONOS customer account or developer API
credentials. Do not commit credentials. The `.env.example` file is only a field
reference. Use the `configure` command to store the password in the operating
system keyring; the account file stores only the email address and server region.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
ionos-mail configure --address you@example.com
# For mailboxes hosted on the German IONOS servers:
ionos-mail region de
```

The command prompts for the mailbox password without echoing it. Environment
variables `IONOS_MAIL_ADDRESS` and `IONOS_MAIL_PASSWORD` remain supported and
take precedence over the saved account. The default servers are `imap.ionos.com:993` with TLS and
`smtp.ionos.com:465` with TLS. `ionos-mail region de` saves the [German IONOS settings](https://www.ionos.de/hilfe/e-mail/allgemeine-themen/serverinformationen-fuer-imap-pop3-und-smtp/):
`imap.ionos.de:993` and `smtp.ionos.de:465`. Set `IONOS_SMTP_PORT=587` for STARTTLS.
Explicit `IONOS_IMAP_HOST` and `IONOS_SMTP_HOST` values override the saved region.

## Environment reference

Environment variables are optional overrides. `.env` files are not automatically
loaded. Set variables in the process that runs the CLI, HTTP server or MCP host.

| Variable | Default / behavior |
| --- | --- |
| `IONOS_MAIL_ADDRESS` | Overrides the address in the saved account |
| `IONOS_MAIL_PASSWORD` | Overrides the operating system keyring |
| `IONOS_IMAP_HOST` | `imap.ionos.com`, or the saved region |
| `IONOS_IMAP_PORT` | `993`, implicit TLS |
| `IONOS_SMTP_HOST` | `smtp.ionos.com`, or the saved region |
| `IONOS_SMTP_PORT` | `465`; `587` selects STARTTLS |
| `IONOS_DRAFTS_FOLDER` | Existing IMAP folder name; otherwise autodetected |
| `IONOS_API_TOKEN` | Required only for the local HTTP server |
| `XDG_CONFIG_HOME` | Optional base directory for the account configuration |

The saved configuration is `ionos-mail-bridge/account.json` below
`XDG_CONFIG_HOME`, or `~/Library/Application Support` on macOS, or `~/.config`
on other systems. It contains the mailbox address and region, never the password.
On Linux, configure an OS keyring backend before using `configure`, or supply
credentials through your process environment. Never use a plaintext keyring backend.

## Troubleshooting

- **Authentication fails:** check the mailbox password and region. IONOS hosting
  account credentials are different from mailbox credentials.
- **No Drafts folder:** run `ionos-mail folders`, then set
  `IONOS_DRAFTS_FOLDER` to an existing name returned by the server.
- **Encoded folder names:** IMAP can return names such as `Entw&APw-rfe`.
  Pass the exact returned name rather than translating it.
- **Sent draft remains:** inspect `draft_retained`. Without UIDPLUS, remove the
  sent draft in a mail client after confirming delivery. Do not resend it.
- **Delete refuses:** individual permanent deletion requires UIDPLUS. The tool
  deliberately refuses servers without it; use your mail client instead.
- **Keyring unavailable:** check your system keyring/session setup. The bridge
  does not silently fall back to storing a password in a file.
