"""Command-line interface for draft creation, sending, and the local API."""

from __future__ import annotations

import argparse
import getpass
import imaplib
import json
import os
import smtplib
import sys
from pathlib import Path

from .api import serve
from .credentials import save_account, set_region
from .mail import Config, _address, create_draft, list_folders, send_message, send_saved_draft


def _body(args: argparse.Namespace) -> str:
    if args.body is not None:
        return args.body
    if args.body_file is not None:
        return Path(args.body_file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ValueError("Provide --body, --body-file, or pipe the body via stdin")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ionos-mail", description="IONOS Mail CLI using IMAP and SMTP")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("folders", help="List IMAP folders and special-use flags")
    setup = commands.add_parser("configure", help="Store mailbox credentials in the OS keyring")
    setup.add_argument("--address", required=True)
    setup.add_argument("--password-stdin", action="store_true", help="Read one password from stdin without echoing it")
    region = commands.add_parser("region", help="Save the IONOS server region without changing credentials")
    region.add_argument("name", choices=("com", "de"))
    for name in ("draft", "send"):
        command = commands.add_parser(name, help=f"{name.capitalize()} an email")
        command.add_argument("--to", action="append", default=[], metavar="ADDRESS")
        command.add_argument("--cc", action="append", default=[], metavar="ADDRESS")
        command.add_argument("--bcc", action="append", default=[], metavar="ADDRESS")
        command.add_argument("--subject", required=True)
        body = command.add_mutually_exclusive_group()
        body.add_argument("--body")
        body.add_argument("--body-file", metavar="PATH")
    api = commands.add_parser("serve", help="Start the local HTTP API")
    api.add_argument("--port", type=int, default=8765)
    existing = commands.add_parser("send-draft", help="Send an existing IMAP draft by UID")
    existing.add_argument("--uid", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "configure":
            if args.password_stdin:
                password = sys.stdin.readline(4098).rstrip("\r\n")
            else:
                password = getpass.getpass("Mailbox password: ")
            address = _address(args.address)
            save_account(address, password)
            print(f"Configured {address} in the OS keyring")
            return 0
        if args.command == "region":
            set_region(args.name)
            print(f"Saved IONOS server region: {args.name}")
            return 0
        config = Config.from_env()
        if args.command == "folders":
            result = list_folders(config)
        elif args.command == "draft":
            result = create_draft(config, to=args.to, cc=args.cc, bcc=args.bcc,
                                  subject=args.subject, body=_body(args))
        elif args.command == "send":
            result = send_message(config, to=args.to, cc=args.cc, bcc=args.bcc,
                                  subject=args.subject, body=_body(args))
        elif args.command == "send-draft":
            result = send_saved_draft(config, args.uid)
        else:
            serve(config, os.getenv("IONOS_API_TOKEN", ""), args.port)
            return 0
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, imaplib.IMAP4.error, smtplib.SMTPException) as exc:
        print(f"ionos-mail: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
