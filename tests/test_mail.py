import unittest
import os
import tempfile
from unittest.mock import patch

from ionos_mail_bridge.credentials import save_account, set_region
from ionos_mail_bridge.mail import Config, delete_saved_draft, _drafts_folder, compose, create_draft, get_message, list_messages, search_messages, send_message, send_saved_draft


CONFIG = Config("sender@example.com", "test-password")


class FakeIMAP:
    appended = None
    capabilities = (b"IMAP4rev1", b"UIDPLUS")

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
        if command in ("STORE", "EXPUNGE"):
            return "OK", [b"done"]
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
    def test_keyring_configuration_keeps_password_out_of_file(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"XDG_CONFIG_HOME": directory,
                                  "IONOS_MAIL_ADDRESS": "", "IONOS_MAIL_PASSWORD": ""}), \
             patch("ionos_mail_bridge.credentials.keyring.set_password") as saved, \
             patch("ionos_mail_bridge.credentials.keyring.get_password", return_value="secret"):
            save_account("sender@example.com", "secret")
            config = Config.from_env()
            self.assertEqual(config.address, "sender@example.com")
            self.assertEqual(config.password, "secret")
            with open(os.path.join(directory, "ionos-mail-bridge", "account.json"), encoding="utf-8") as handle:
                self.assertNotIn("secret", handle.read())
            saved.assert_called_once_with("ionos-mail-bridge", "sender@example.com", "secret")

    def test_saved_region_selects_german_servers_and_survives_reconfigure(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"XDG_CONFIG_HOME": directory,
                                  "IONOS_MAIL_ADDRESS": "", "IONOS_MAIL_PASSWORD": "",
                                  "IONOS_IMAP_HOST": "", "IONOS_SMTP_HOST": ""}), \
             patch("ionos_mail_bridge.credentials.keyring.set_password"), \
             patch("ionos_mail_bridge.credentials.keyring.get_password", return_value="secret"):
            set_region("de")
            save_account("sender@example.com", "secret")
            config = Config.from_env()
            self.assertEqual(config.imap_host, "imap.ionos.de")
            self.assertEqual(config.smtp_host, "smtp.ionos.de")

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

    def test_reply_draft_preserves_thread_and_uses_read_only_fetch(self):
        from email.parser import BytesParser
        from email.policy import default
        class ReplyIMAP(FakeIMAP):
            def uid(self, command, *args):
                self.fetch_args = args
                return "OK", [(b"header", b"Message-ID: <parent@example.org>\r\nReferences: <root@example.org>\r\n\r\n")]
        fake = ReplyIMAP()
        with patch("ionos_mail_bridge.mail.imaplib.IMAP4_SSL", return_value=fake):
            create_draft(CONFIG, to=["to@example.org"], subject="Re: Hi", body="Reply", reply_to_uid="15")
        msg = BytesParser(policy=default).parsebytes(fake.appended[2])
        self.assertEqual(msg["In-Reply-To"], "<parent@example.org>")
        self.assertEqual(msg["References"], "<root@example.org> <parent@example.org>")
        self.assertEqual(fake.selected, (b'"INBOX"', True))
        self.assertIn("BODY.PEEK", fake.fetch_args[1])

    def test_reply_without_message_id_is_not_sent(self):
        with patch("ionos_mail_bridge.mail.imaplib.IMAP4_SSL", return_value=FakeIMAP()), \
             patch("ionos_mail_bridge.mail._submit") as submit:
            with self.assertRaises(ValueError):
                send_message(CONFIG, to=["to@example.org"], subject="Re: Hi", body="Reply", reply_to_uid="15")
        submit.assert_not_called()

    def test_delete_draft_only_expunges_target(self):
        class DeleteIMAP(FakeIMAP):
            def uid(self, command, *args):
                self.calls.append((command, args))
                return super().uid(command, *args)
        fake = DeleteIMAP()
        fake.calls = []
        with patch("ionos_mail_bridge.mail._connect_imap", return_value=fake):
            result = delete_saved_draft(CONFIG, "15")
        self.assertEqual(result["status"], "deleted")
        self.assertEqual(fake.selected, (b'"Saved Drafts"', False))
        self.assertEqual(fake.calls[-1], ("EXPUNGE", ("15",)))
        self.assertEqual(fake.calls[-2], ("STORE", ("15", "+FLAGS.SILENT", "(\\Deleted)")))

    def test_delete_without_uidplus_does_not_modify_mail(self):
        fake = FakeIMAP()
        fake.capabilities = (b"IMAP4rev1",)
        with patch("ionos_mail_bridge.mail._connect_imap", return_value=fake), \
             patch.object(fake, "uid") as uid_call, \
             patch.object(fake, "select") as select:
            with self.assertRaisesRegex(RuntimeError, "UIDPLUS"):
                delete_saved_draft(CONFIG, "15")
        uid_call.assert_not_called()
        select.assert_not_called()

    def test_delete_rejects_invalid_uid_before_connect(self):
        with patch("ionos_mail_bridge.mail._connect_imap") as connect:
            for uid in ("0", "1:*", "15,16", "", "15\r\n"):
                with self.assertRaises(ValueError):
                    delete_saved_draft(CONFIG, uid)
        connect.assert_not_called()

    def test_delete_missing_uid_does_not_store_or_expunge(self):
        fake = FakeIMAP()
        with patch("ionos_mail_bridge.mail._connect_imap", return_value=fake), \
             patch.object(fake, "uid", return_value=("OK", [None])) as calls:
            with self.assertRaises(ValueError):
                delete_saved_draft(CONFIG, "999")
        self.assertEqual([c.args[0] for c in calls.call_args_list], ["FETCH"])

    def test_delete_store_failure_does_not_expunge(self):
        fake = FakeIMAP()
        original_uid = fake.uid
        def uid(command, *args):
            return ("NO", [b"denied"]) if command == "STORE" else original_uid(command, *args)
        with patch("ionos_mail_bridge.mail._connect_imap", return_value=fake), \
             patch.object(fake, "uid", side_effect=uid) as calls:
            with self.assertRaisesRegex(RuntimeError, "mark draft"):
                delete_saved_draft(CONFIG, "15")
        self.assertNotIn("EXPUNGE", [c.args[0] for c in calls.call_args_list])

    def test_delete_expunge_failure_reports_partial_state(self):
        fake = FakeIMAP()
        original_uid = fake.uid
        def uid(command, *args):
            return ("NO", [b"denied"]) if command == "EXPUNGE" else original_uid(command, *args)
        with patch("ionos_mail_bridge.mail._connect_imap", return_value=fake), \
             patch.object(fake, "uid", side_effect=uid):
            with self.assertRaisesRegex(RuntimeError, "may remain marked Deleted"):
                delete_saved_draft(CONFIG, "15")

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

    def test_send_saved_draft_removes_only_target_uid(self):
        class DraftIMAP(FakeIMAP):
            def uid(self, command, *args):
                if command == "FETCH":
                    return "OK", [(b"1 (UID 15 BODY[] {100}",
                                   b"From: sender@example.com\r\nTo: reader@example.org\r\nBcc: hidden@example.org\r\nSubject: Example\r\n\r\nHello"), b")"]
                self.last_uid_command = command, args
                return "OK", [b"done"]

        imap = DraftIMAP()
        smtp = FakeSMTP()
        with patch("ionos_mail_bridge.mail.imaplib.IMAP4_SSL", return_value=imap), \
             patch("ionos_mail_bridge.mail.smtplib.SMTP_SSL", return_value=smtp):
            result = send_saved_draft(CONFIG, "15")
        self.assertFalse(result["draft_retained"])
        self.assertEqual(imap.last_uid_command, ("EXPUNGE", ("15",)))
        message, _, recipients = smtp.sent
        self.assertNotIn("Bcc", message)
        self.assertEqual(recipients, ["reader@example.org", "hidden@example.org"])


if __name__ == "__main__":
    unittest.main()
