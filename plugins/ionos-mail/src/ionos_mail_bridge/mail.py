"""Mail transport; no dependency on the IONOS web interface."""

from __future__ import annotations

import imaplib
import os
import re
import smtplib
import ssl
import time
from dataclasses import dataclass
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import SMTP, default
from email.headerregistry import Address
from email.utils import formatdate, getaddresses, make_msgid

from .credentials import password_for, saved_address


@dataclass(frozen=True)
class Config:
    address: str
    password: str
    imap_host: str = "imap.ionos.com"
    imap_port: int = 993
    smtp_host: str = "smtp.ionos.com"
    smtp_port: int = 465
    drafts_folder: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        address = (os.getenv("IONOS_MAIL_ADDRESS", "") or saved_address()).strip()
        password = password_for(address) if address else ""
        if not address or not password:
            raise ValueError("Run 'ionos-mail configure' or set IONOS_MAIL_ADDRESS and IONOS_MAIL_PASSWORD")
        return cls(
            address=address,
            password=password,
            imap_host=os.getenv("IONOS_IMAP_HOST", "imap.ionos.com"),
            imap_port=int(os.getenv("IONOS_IMAP_PORT", "993")),
            smtp_host=os.getenv("IONOS_SMTP_HOST", "smtp.ionos.com"),
            smtp_port=int(os.getenv("IONOS_SMTP_PORT", "465")),
            drafts_folder=os.getenv("IONOS_DRAFTS_FOLDER") or None,
        )


def _address(value: str) -> str:
    if not isinstance(value, str) or "\r" in value or "\n" in value:
        raise ValueError("Email addresses must be single-line strings")
    try:
        parsed = Address(addr_spec=value.strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid email address: {value!r}") from exc
    if not parsed.username or not parsed.domain:
        raise ValueError(f"Invalid email address: {value!r}")
    return parsed.addr_spec


def _recipients(values: list[str] | None) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError("Recipients must be a list")
    return [_address(value) for value in values]


def compose(config: Config, *, to: list[str], subject: str, body: str,
            cc: list[str] | None = None, bcc: list[str] | None = None,
            draft: bool = False) -> tuple[EmailMessage, list[str]]:
    recipients = _recipients(to)
    copies = _recipients(cc)
    blind_copies = _recipients(bcc)
    if not recipients and not copies and not blind_copies:
        raise ValueError("At least one recipient is required")
    if not isinstance(subject, str) or "\r" in subject or "\n" in subject:
        raise ValueError("Subject must be a single-line string")
    if not isinstance(body, str):
        raise ValueError("Body must be text")
    msg = EmailMessage(policy=SMTP)
    msg["From"] = _address(config.address)
    if recipients:
        msg["To"] = ", ".join(recipients)
    if copies:
        msg["Cc"] = ", ".join(copies)
    if draft and blind_copies:
        msg["Bcc"] = ", ".join(blind_copies)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=_address(config.address).split("@", 1)[1])
    msg.set_content(body)
    return msg, recipients + copies + blind_copies


_LIST_RE = re.compile(rb'^\((?P<flags>[^)]*)\)\s+(?:"(?:[^"\\]|\\.)*"|NIL)\s+(?P<name>.+)$')


def _mailboxes(client: imaplib.IMAP4_SSL) -> list[tuple[bytes, bytes]]:
    status, lines = client.list()
    if status != "OK" or lines is None:
        raise RuntimeError("Could not list IMAP folders")
    boxes = []
    for line in lines:
        if not isinstance(line, bytes):
            continue
        match = _LIST_RE.match(line)
        if match:
            name = match.group("name")
            if name.startswith(b'"') and name.endswith(b'"'):
                name = name[1:-1].replace(b'\\"', b'"').replace(b'\\\\', b'\\')
            boxes.append((match.group("flags"), name))
    return boxes


def _drafts_folder(config: Config, client: imaplib.IMAP4_SSL) -> bytes:
    boxes = _mailboxes(client)
    if config.drafts_folder:
        requested = config.drafts_folder.encode("ascii")
        for _, name in boxes:
            if name == requested:
                return name
        raise ValueError(f"Configured drafts folder does not exist: {config.drafts_folder}")
    for flags, name in boxes:
        if re.search(rb'(?<!\S)\\Drafts(?!\S)', flags, re.I):
            return name
    for _, name in boxes:
        if name.lower() == b"drafts":
            return name
    raise RuntimeError("No Drafts folder found; set IONOS_DRAFTS_FOLDER after running 'ionos-mail folders'")


def _existing_folder(client: imaplib.IMAP4_SSL, folder: str) -> bytes:
    if not isinstance(folder, str) or not folder or "\r" in folder or "\n" in folder:
        raise ValueError("Invalid folder")
    try:
        requested = folder.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("Use the IMAP folder name returned by list_folders") from exc
    for _, name in _mailboxes(client):
        if requested == name or (requested.upper() == b"INBOX" and name.upper() == b"INBOX"):
            return name
    raise ValueError(f"IMAP folder does not exist: {folder}")


def _quote_mailbox(folder: bytes) -> bytes:
    return b'"' + folder.replace(b'\\', b'\\\\').replace(b'"', b'\\"') + b'"'


def _connect_imap(config: Config) -> imaplib.IMAP4_SSL:
    client = imaplib.IMAP4_SSL(config.imap_host, config.imap_port, ssl_context=ssl.create_default_context())
    try:
        client.login(config.address, config.password)
    except Exception:
        client.logout()
        raise
    return client


def _summary(uid: str, raw: bytes) -> dict[str, str]:
    msg = BytesParser(policy=default).parsebytes(raw, headersonly=True)
    return {"uid": uid, "from": str(msg.get("From", "")), "to": str(msg.get("To", "")),
            "subject": str(msg.get("Subject", "")), "date": str(msg.get("Date", "")),
            "message_id": str(msg.get("Message-ID", ""))}


def _uid_fetch(client: imaplib.IMAP4_SSL, uid: str, part: str) -> bytes:
    if not isinstance(uid, str) or not uid.isascii() or not uid.isdigit():
        raise ValueError("UID must be a decimal string")
    status, data = client.uid("FETCH", uid, part)
    if status != "OK" or not data:
        raise RuntimeError(f"IMAP FETCH failed for UID {uid}")
    for item in data:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            return item[1]
    raise ValueError(f"Message UID {uid} not found")


def _selected(config: Config, folder: str, action):
    with _connect_imap(config) as client:
        selected = _existing_folder(client, folder)
        status, _ = client.select(_quote_mailbox(selected), readonly=True)
        if status != "OK":
            raise RuntimeError(f"Could not select IMAP folder {folder}")
        return action(client)


def list_messages(config: Config, *, folder: str = "INBOX", limit: int = 20,
                  unread_only: bool = False) -> list[dict[str, str]]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be 1 to 100")

    def action(client):
        status, data = client.uid("SEARCH", None, "UNSEEN" if unread_only else "ALL")
        if status != "OK" or not data:
            raise RuntimeError("IMAP SEARCH failed")
        ids = data[0].split()[-limit:]
        results = []
        for uid in reversed(ids):
            text_uid = uid.decode("ascii")
            raw = _uid_fetch(client, text_uid, "(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE MESSAGE-ID)])")
            results.append(_summary(text_uid, raw))
        return results

    return _selected(config, folder, action)


def search_messages(config: Config, query: str, *, folder: str = "INBOX",
                    limit: int = 20) -> list[dict[str, str]]:
    if not isinstance(query, str) or not query or not query.isascii() or any(c in query for c in '\r\n'):
        raise ValueError("Search query must be nonempty ASCII text without line breaks")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be 1 to 100")
    criterion = '"' + query.replace('\\', '\\\\').replace('"', '\\"') + '"'

    def action(client):
        status, data = client.uid("SEARCH", None, "TEXT", criterion)
        if status != "OK" or not data:
            raise RuntimeError("IMAP SEARCH failed")
        results = []
        for uid in reversed(data[0].split()[-limit:]):
            text_uid = uid.decode("ascii")
            raw = _uid_fetch(client, text_uid, "(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE MESSAGE-ID)])")
            results.append(_summary(text_uid, raw))
        return results

    return _selected(config, folder, action)


def get_message(config: Config, uid: str, *, folder: str = "INBOX") -> dict[str, str]:
    def action(client):
        raw = _uid_fetch(client, uid, "(BODY.PEEK[])")
        msg = BytesParser(policy=default).parsebytes(raw)
        result = _summary(uid, raw)
        result["cc"] = str(msg.get("Cc", ""))
        result["bcc"] = str(msg.get("Bcc", ""))
        result["reply_to"] = str(msg.get("Reply-To", ""))
        bodies = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and part.get_content_disposition() != "attachment":
                bodies.append(part.get_content())
        result["body"] = "\n".join(bodies)[:100_000]
        result["truncated"] = len("\n".join(bodies)) > 100_000
        result["attachments"] = [part.get_filename() or "unnamed" for part in msg.walk()
                                 if part.get_content_disposition() == "attachment"]
        return result

    return _selected(config, folder, action)


def list_folders(config: Config) -> list[dict[str, str]]:
    with imaplib.IMAP4_SSL(config.imap_host, config.imap_port, ssl_context=ssl.create_default_context()) as client:
        client.login(config.address, config.password)
        return [{"flags": flags.decode("ascii", "replace"),
                 "name": name.decode("ascii", "replace")} for flags, name in _mailboxes(client)]


def create_draft(config: Config, *, to: list[str], subject: str, body: str,
                 cc: list[str] | None = None, bcc: list[str] | None = None) -> dict[str, str]:
    msg, _ = compose(config, to=to, subject=subject, body=body, cc=cc, bcc=bcc, draft=True)
    with imaplib.IMAP4_SSL(config.imap_host, config.imap_port, ssl_context=ssl.create_default_context()) as client:
        client.login(config.address, config.password)
        folder = _drafts_folder(config, client)
        status, data = client.append(_quote_mailbox(folder), "\\Draft", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
        if status != "OK":
            raise RuntimeError(f"IMAP APPEND failed: {data!r}")
        result = {"message_id": str(msg["Message-ID"]), "folder": folder.decode("ascii", "replace")}
        _, uid_data = client.response("APPENDUID")
        if uid_data and uid_data[0]:
            # APPENDUID is an optional server extension; the result is often "uidvalidity uid".
            parts = uid_data[0].split()
            if len(parts) >= 2 and parts[-1].isdigit():
                result["uid"] = parts[-1].decode("ascii")
        return result


def send_message(config: Config, *, to: list[str], subject: str, body: str,
                 cc: list[str] | None = None, bcc: list[str] | None = None) -> dict[str, str]:
    msg, recipients = compose(config, to=to, subject=subject, body=body, cc=cc, bcc=bcc)
    _submit(config, msg, recipients)
    return {"message_id": str(msg["Message-ID"]), "status": "accepted_by_smtp"}


def _submit(config: Config, msg: EmailMessage, recipients: list[str]) -> None:
    context = ssl.create_default_context()
    if config.smtp_port == 465:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, context=context, timeout=30) as client:
            client.login(config.address, config.password)
            client.send_message(msg, from_addr=config.address, to_addrs=recipients)
    elif config.smtp_port == 587:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as client:
            client.ehlo()
            client.starttls(context=context)
            client.ehlo()
            client.login(config.address, config.password)
            client.send_message(msg, from_addr=config.address, to_addrs=recipients)
    else:
        raise ValueError("Supported SMTP ports are 465 (TLS) and 587 (STARTTLS)")


def send_saved_draft(config: Config, uid: str) -> dict[str, str | bool]:
    """Submit an existing draft, then remove only its own UID if UIDPLUS is available."""
    if not isinstance(uid, str) or not uid.isascii() or not uid.isdigit():
        raise ValueError("UID must be a decimal string")
    with _connect_imap(config) as client:
        folder = _drafts_folder(config, client)
        status, _ = client.select(_quote_mailbox(folder), readonly=True)
        if status != "OK":
            raise RuntimeError("Could not open Drafts folder")
        raw = _uid_fetch(client, uid, "(BODY.PEEK[])")
        msg = BytesParser(policy=SMTP).parsebytes(raw)
        recipients = []
        for field in ("To", "Cc", "Bcc"):
            recipients.extend(_address(addr) for _, addr in getaddresses(msg.get_all(field, [])))
        if not recipients:
            raise ValueError("Draft has no recipients")
        if "Bcc" in msg:
            del msg["Bcc"]
        if "From" in msg:
            del msg["From"]
        msg["From"] = _address(config.address)
        if "Date" in msg:
            del msg["Date"]
        msg["Date"] = formatdate(localtime=True)
        if "Message-ID" not in msg:
            msg["Message-ID"] = make_msgid(domain=_address(config.address).split("@", 1)[1])
        _submit(config, msg, recipients)
        result: dict[str, str | bool] = {
            "message_id": str(msg["Message-ID"]), "status": "accepted_by_smtp",
            "draft_retained": True,
        }
        # Ordinary EXPUNGE could delete unrelated messages. UID EXPUNGE is safe when UIDPLUS exists.
        if b"UIDPLUS" in client.capabilities:
            try:
                status, _ = client.select(_quote_mailbox(folder), readonly=False)
                if status == "OK":
                    status, _ = client.uid("STORE", uid, "+FLAGS.SILENT", "(\\Deleted)")
                    if status == "OK":
                        status, _ = client.uid("EXPUNGE", uid)
                        result["draft_retained"] = status != "OK"
            except Exception:
                # SMTP acceptance is already final: report it rather than implying a retry is safe.
                pass
        return result
