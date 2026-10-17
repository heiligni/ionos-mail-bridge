# IONOS Mail plugin runtime

Self-contained MCP runtime for the IONOS Mail Bridge. Includes its Python source,
launcher and assistant workflow skill so the plugin can run from an installed copy.

The source of truth is this repository. See the root README and `docs/` for setup,
configuration, interfaces and limitations. Source code lives in
`src/ionos_mail_bridge/`, workflow instructions in `skills/mail/SKILL.md`.

This directory is the Codex plugin package. Installing its Python distribution
provides the `ionos-mail-mcp` entry point; plugin metadata, launcher and skill are
used by the Codex plugin host. The root Python distribution additionally provides
the CLI entry point and uses this same source.

Independent community project; not affiliated with IONOS. Licensed under MIT.
