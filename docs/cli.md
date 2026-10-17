# Command-line interface

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
otherwise the result reports `draft_retained: true`. The tested German IONOS
mailbox did not advertise UIDPLUS, so its sent test draft remained in Drafts;
delete it through your mail client after confirming delivery. If no UID was returned,
find the draft with the MCP `messages` tool using the Drafts folder.
