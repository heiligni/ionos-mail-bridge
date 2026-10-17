"""Local stdio MCP server for IONOS Mail."""

from __future__ import annotations

from mcp.server import MCPServer

from .mail import (Config, create_draft, delete_saved_draft, get_message, list_folders, list_messages,
                   search_messages, send_message, send_saved_draft)


mcp = MCPServer("ionos-mail")


@mcp.tool()
def folders() -> list[dict[str, str]]:
    """List mailbox folders and special-use flags. Read only."""
    return list_folders(Config.from_env())


@mcp.tool()
def messages(folder: str = "INBOX", limit: int = 20,
             unread_only: bool = False) -> list[dict[str, str]]:
    """List recent message headers by stable IMAP UID without marking mail as read."""
    return list_messages(Config.from_env(), folder=folder, limit=limit,
                         unread_only=unread_only)


@mcp.tool()
def search(query: str, folder: str = "INBOX", limit: int = 20) -> list[dict[str, str]]:
    """Search message text in a folder and return headers. Query is ASCII text."""
    return search_messages(Config.from_env(), query, folder=folder, limit=limit)


@mcp.tool()
def read_message(uid: str, folder: str = "INBOX") -> dict:
    """Read one message by IMAP UID without marking it as read. Text body is capped at 100k characters."""
    return get_message(Config.from_env(), uid, folder=folder)


@mcp.tool()
def save_draft(to: list[str], subject: str, body: str,
               cc: list[str] | None = None, bcc: list[str] | None = None,
               reply_to_uid: str | None = None, reply_to_folder: str = "INBOX") -> dict[str, str]:
    """Save a new draft in the mailbox's existing Drafts folder. Does not send it. For replies, pass the original UID and folder; keep its subject with Re: and use Reply-To or From as recipient."""
    return create_draft(Config.from_env(), to=to, subject=subject, body=body,
                        cc=cc, bcc=bcc, reply_to_uid=reply_to_uid,
                        reply_to_folder=reply_to_folder)


@mcp.tool()
def send(to: list[str], subject: str, body: str,
         cc: list[str] | None = None, bcc: list[str] | None = None,
               reply_to_uid: str | None = None, reply_to_folder: str = "INBOX") -> dict[str, str]:
    """Send a new email via IONOS SMTP. Call only when the user explicitly asks to send. For replies pass the original UID and folder, reply subject and recipient."""
    return send_message(Config.from_env(), to=to, subject=subject, body=body,
                        cc=cc, bcc=bcc, reply_to_uid=reply_to_uid,
                        reply_to_folder=reply_to_folder)


@mcp.tool()
def send_draft(uid: str) -> dict[str, str | bool]:
    """Send an existing draft by UID. Call only when the user explicitly asks to send it."""
    return send_saved_draft(Config.from_env(), uid)


@mcp.tool()
def delete_draft(uid: str) -> dict[str, str]:
    """Permanently delete one Drafts-folder UID. Only when user requests deletion. Refuses without UIDPLUS; never expunges unrelated mail."""
    return delete_saved_draft(Config.from_env(), uid)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
