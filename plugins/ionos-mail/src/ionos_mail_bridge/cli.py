"""Command-line interface for draft creation, sending, and the local API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .api import serve
from .mail import Config, create_draft, list_folders, send_message, send_saved_draft


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
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ionos-mail: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
