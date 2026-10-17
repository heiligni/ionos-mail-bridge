# Architecture and repository map

The bridge is a local Python application with three adapters: CLI, loopback HTTP
and stdio MCP. They share the same mail transport and credential handling.

```text
CLI (cli.py) ─────┐
HTTP (api.py) ────┼── mail.py ── IMAP / SMTP over verified TLS
MCP (mcp_server.py)┘      └───── credentials.py ── OS keyring + account settings
```

## Source of truth

```text
ionos-mail-bridge/
├── README.md                    # Overview and quick start
├── CONTRIBUTING.md              # Development and contribution workflow
├── SECURITY.md                  # Trust model and disclosure guidance
├── LICENSE                      # MIT
├── pyproject.toml               # CLI/API distribution and optional MCP extra
├── uv.lock                      # Locked root development dependencies
├── docs/                        # Configuration, interfaces, architecture
├── tests/                       # Offline regression and MCP contract tests
├── .github/workflows/           # CI
├── .agents/plugins/             # Local marketplace descriptor
└── plugins/ionos-mail/
    ├── .codex-plugin/plugin.json # Plugin identity and UI metadata
    ├── .mcp.json                # Local stdio launch configuration
    ├── pyproject.toml           # Self-contained plugin runtime package
    ├── uv.lock                  # Plugin dependency lock
    ├── scripts/run_mcp.py       # Runtime launcher
    ├── skills/mail/SKILL.md     # Assistant workflow instructions
    └── src/ionos_mail_bridge/
        ├── mail.py             # Message composition and IMAP/SMTP operations
        ├── credentials.py      # Keyring access and saved region/address
        ├── cli.py              # Command-line adapter
        ├── api.py              # Local HTTP adapter
        └── mcp_server.py       # MCP tool adapter
```

There is one Python implementation, deliberately inside the plugin directory.
Codex installs a copy of that directory, so moving runtime source outside it
would break a standalone plugin installation. The root package discovers this
same source; it does not maintain a duplicate implementation. The two package
manifests serve different installation contexts.

Virtual environments, Python metadata and caches are ignored local build
artifacts. They are not part of the project structure or distribution sources.
Change source files here, then reinstall the plugin to refresh its cached copy.
Never edit the installed cache as the source of truth.

## Mail invariants

- Reads select folders read-only and use BODY.PEEK.
- Drafts are appended only to an existing Drafts folder.
- Reply headers come from the original message's folder-scoped UID.
- SMTP acceptance and recipient delivery are distinct states.
- Draft deletion uses UID EXPUNGE, never ordinary EXPUNGE.
- No mailbox state is mutated when deletion is refused without UIDPLUS.
- The HTTP and CLI feature sets are documented separately from MCP.

## Verification scope

Offline tests use fake IMAP/SMTP transports. They cover credentials, message
composition, threading, draft deletion failure paths and MCP tool contracts.
They do not prove provider compatibility. Live checks on a German IONOS mailbox
confirmed reads, draft creation, SMTP submission, Gmail delivery and Gmail reply
threading. Successful deletion on a live UIDPLUS server is still unverified.
