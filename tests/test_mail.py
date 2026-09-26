import unittest
from unittest.mock import patch

from ionos_mail_bridge.mail import Config, _drafts_folder, compose, create_draft, get_message, list_messages, search_messages, send_message


CONFIG = Config("sender@example.com", "test-password")


class FakeIMAP:
    appended = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def login(self, *args):
        return "OK", [b"logged in"]

    def list(self):
        return "OK", [b'(\\HasNoChildren) "/" "INBOX"',
                      b'(\\HasNoChildren \\Drafts) "/" "Saved Drafts"']

    def append(self, folder, flags, date, message):
        self.appended = folder, flags, message
        return "OK", [b"done"]

    def response(self, code):
        return "APPENDUID", [b"123 456"]

    def select(self, folder, readonly=False):
        self.selected = folder, readonly
        return "OK", [b"1"]

    def uid(self, command, *args):
        if command == "SEARCH":
            return "OK", [b"12 15"]
        if command == "FETCH":
            return "OK", [(b"1 (UID 15 BODY[] {100}",
                            b"From: sender@example.com\r\nTo: reader@example.org\r\nSubject: Example\r\n\r\nHello"), b")"]
        raise AssertionError(command)


class FakeSMTP:
    sent = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def login(self, *args):
        pass

    def send_message(self, message, *, from_addr, to_addrs):
        self.sent = message, from_addr, to_addrs


class MailTests(unittest.TestCase):
    def test_draft_selects_special_use_and_preserves_bcc(self):
        fake = FakeIMAP()
        with patch("ionos_mail_bridge.mail.imaplib.IMAP4_SSL", return_value=fake):
            result = create_draft(CONFIG, to=["to@example.org"],
                                  bcc=["hidden@example.org"], subject="Hi", body="Hello")
        self.assertEqual(result["uid"], "456")
        self.assertEqual(fake.appended[0], b'"Saved Drafts"')
        self.assertEqual(fake.appended[1], "\\Draft")
        self.assertIn(b"Bcc: hidden@example.org", fake.appended[2])

    def test_send_keeps_bcc_out_of_message_but_in_envelope(self):
        fake = FakeSMTP()
        with patch("ionos_mail_bridge.mail.smtplib.SMTP_SSL", return_value=fake):
            result = send_message(CONFIG, to=["to@example.org"],
                                  bcc=["hidden@example.org"], subject="Hi", body="Hello")
        self.assertEqual(result["status"], "accepted_by_smtp")
        message, sender, recipients = fake.sent
        self.assertNotIn("Bcc", message)
        self.assertEqual(sender, "sender@example.com")
        self.assertEqual(recipients, ["to@example.org", "hidden@example.org"])

    def test_rejects_header_injection(self):
        with self.assertRaises(ValueError):
            compose(CONFIG, to=["to@example.org"], subject="Hi\r\nBcc: someone@example.org", body="Hello")

    def test_missing_drafts_folder_does_not_create_arbitrary_folder(self):
        class NoDrafts(FakeIMAP):
            def list(self):
                return "OK", [b'(\\HasNoChildren) "/" "INBOX"']
        with self.assertRaises(RuntimeError):
            _drafts_folder(CONFIG, NoDrafts())

    def test_list_and_read_do_not_mark_message_read(self):
        fake = FakeIMAP()
        with patch("ionos_mail_bridge.mail.imaplib.IMAP4_SSL", return_value=fake):
            listed = list_messages(CONFIG, limit=1)
            found = search_messages(CONFIG, "Example", limit=1)
            message = get_message(CONFIG, "15")
        self.assertEqual(fake.selected, (b'"INBOX"', True))
        self.assertEqual(listed[0]["uid"], "15")
        self.assertEqual(found[0]["subject"], "Example")
        self.assertEqual(message["body"], "Hello")


if __name__ == "__main__":
    unittest.main()
