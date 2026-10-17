# Security

## Reporting a vulnerability

Do not post credentials, private messages or exploitable vulnerability details
in public issues. Use the repository's GitHub Security tab to submit a private
vulnerability report if that option is enabled. If unavailable, contact the
maintainer privately before disclosing details. There is no guaranteed response
or remediation time.

## Trust and credentials

The bridge runs locally and grants its MCP host access to the configured mailbox.
Only connect trusted hosts. The workflow skill asks for explicit user direction
before sending or deleting, but those instructions are not a server-side approval
mechanism. Any client with tool access can invoke these operations.

Passwords use the operating system keyring, or explicit environment overrides.
The account file contains the address and region. Never commit account files,
mail exports, credentials or tool output containing private messages. The included
`.env.example` contains placeholders and is not loaded automatically.

IMAP and SMTP use verified TLS. The optional HTTP API binds to loopback, requires
a bearer token for mail endpoints and must not be exposed to the Internet.
Local HTTP is unencrypted; use it only on a trusted machine.

## Destructive operations and retries

`delete_draft` permanently deletes the selected Drafts-folder UID and requires
UIDPLUS. It never falls back to ordinary EXPUNGE. UIDs belong to a specific
folder; verify the intended draft before deletion. If UID EXPUNGE fails after
STORE succeeds, the draft can remain marked Deleted.

SMTP acceptance does not prove delivery. Do not retry sending after an uncertain
result without checking delivery. Sent drafts can remain in Drafts when UIDPLUS
is unavailable; inspect `draft_retained` and do not send them twice.
