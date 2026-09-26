"""Local stdio MCP server for IONOS Mail."""

from __future__ import annotations

from mcp.server import MCPServer

from .mail import (Config, create_draft, get_message, list_folders, list_messages,
                   search_messages, send_message)


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
               cc: list[str] | None = None, bcc: list[str] | None = None) -> dict[str, str]:
    """Save a new draft in the mailbox's existing Drafts folder. Does not send it."""
    return create_draft(Config.from_env(), to=to, subject=subject, body=body,
                        cc=cc, bcc=bcc)


@mcp.tool()
def send(to: list[str], subject: str, body: str,
         cc: list[str] | None = None, bcc: list[str] | None = None) -> dict[str, str]:
    """Send a new email via IONOS SMTP. Call only when the user explicitly asks to send."""
    return send_message(Config.from_env(), to=to, subject=subject, body=body,
                        cc=cc, bcc=bcc)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
