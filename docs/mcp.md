# MCP tools and Codex plugin

The bundled plugin is at `plugins/ionos-mail/`. Its stdio server offers eight
tools: `folders`, `messages`, `search`, `read_message`, `save_draft`, `send`,
`send_draft`, and `delete_draft`.
Read tools use `BODY.PEEK` and a read-only IMAP folder selection so they do not
mark messages as read. Message bodies are limited to 100,000 characters in the
tool response; attachments are listed by filename but are not downloaded as
files. The bundled workflow calls `send` only when the user explicitly asks.

The plugin includes its Python runtime source. Its launcher uses `uv` to
install the MCP extra inside the installed plugin copy and start the server.
Install `uv` from its official distribution, then make sure
`python3` and `uv` are on Codex's `PATH`. As an alternative, install the package
with the MCP extra and put `ionos-mail-mcp` on `PATH`:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install '.[mcp]'
ionos-mail-mcp
```

The last command waits for an MCP host on stdio and normally prints nothing;
press Ctrl-C after confirming it starts. Run `ionos-mail configure` once from
the installed CLI, or set `IONOS_MAIL_ADDRESS` and `IONOS_MAIL_PASSWORD` in
the Codex process environment. The plugin reads the OS keyring when the
password environment variable is absent. It never stores the password in the
repository or plugin files.

The repository includes `.agents/plugins/marketplace.json` for local plugin
discovery. From this repository, run `codex plugin marketplace add .`, then
install **IONOS Mail** from the Plugins Directory in a new Codex chat. The
plugin runs locally; it is not a hosted ChatGPT plugin or a public MCP service.

## Threaded replies

`save_draft` and `send` accept optional `reply_to_uid` and `reply_to_folder`
(default `INBOX`). Read the original message first and provide its reply recipient,
subject and your reply body. The bridge fetches the original headers read-only
and adds `In-Reply-To` and `References`. No mail is sent by `save_draft`.
The original must have a valid Message-ID. CLI and HTTP remain unchanged.

## Deleting drafts

`delete_draft(uid)` permanently removes exactly one UID from the detected Drafts
folder using UID EXPUNGE. It requires UIDPLUS and refuses without modifying mail
when the server lacks it. Verify the draft UID before deletion. Ordinary EXPUNGE
is never used. CLI and HTTP remain unchanged.

## Reply example

1. Use `folders` or `search` to locate the original message.
2. Read the message with its UID and the same folder.
3. Call `save_draft` with the original Reply-To (or From) as recipient:

```json
{
  "to": ["person@example.org"],
  "subject": "Re: Tasting notes",
  "body": "Thank you for the notes!",
  "reply_to_uid": "123",
  "reply_to_folder": "INBOX"
}
```

4. Review the draft before explicitly asking to send it. `send_draft` takes
   the returned **Drafts-folder UID**, not the original message UID.

The skill describes the assistant workflow; it is not a technical authorization
barrier. Only connect the server to trusted MCP clients. See [security](../SECURITY.md).
