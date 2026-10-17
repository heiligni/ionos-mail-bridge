# Contributing

Use Python 3.11 or newer. Create a virtual environment and install the package:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[mcp]'
python -m unittest discover -s tests -v
```

See [the architecture map](docs/architecture.md) for the repository layout.

The runtime source lives in `plugins/ionos-mail/src/ionos_mail_bridge/`.
`mail.py` owns IMAP/SMTP behavior; `mcp_server.py` exposes tools. The workflow
instructions live in `plugins/ionos-mail/skills/mail/SKILL.md`. CLI and HTTP
are separate entry points and do not expose every MCP feature.

Keep changes focused and add mocked regression tests for transport behavior.
Tests must never depend on a real mailbox or send real email. Live checks need
explicit authorization and accounts controlled by the tester. Never commit mail
contents, addresses from live checks, credentials or local environment files.

Open a pull request with a description of the behavior and checks performed.
For vulnerabilities, follow SECURITY.md instead of opening a public issue.
