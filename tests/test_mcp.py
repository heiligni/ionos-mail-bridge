"""Public MCP contracts: discovery and delegation, without mailbox access."""

import unittest
from unittest.mock import patch

from ionos_mail_bridge import mcp_server
from ionos_mail_bridge.mail import Config


class MCPContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_tools_and_reply_parameters_are_discoverable(self):
        tools = {tool.name: tool for tool in await mcp_server.mcp.list_tools()}
        self.assertEqual(set(tools), {
            "folders", "messages", "search", "read_message", "save_draft",
            "send", "send_draft", "delete_draft",
        })
        for name in ("save_draft", "send"):
            schema = tools[name].input_schema
            self.assertIn("reply_to_uid", schema["properties"])
            self.assertEqual(schema["properties"]["reply_to_folder"]["default"], "INBOX")
            self.assertNotIn("reply_to_uid", schema.get("required", []))
        self.assertEqual(tools["delete_draft"].input_schema["required"], ["uid"])

    async def test_reply_draft_adapter_passes_original_folder_and_uid(self):
        config = Config("sender@example.com", "fake")
        with patch.object(mcp_server.Config, "from_env", return_value=config), \
             patch.object(mcp_server, "create_draft", return_value={"uid": "456"}) as create:
            result = mcp_server.save_draft(
                to=["reader@example.org"], subject="Re: Hello", body="Thanks",
                reply_to_uid="123", reply_to_folder="Archive",
            )
        self.assertEqual(result, {"uid": "456"})
        create.assert_called_once_with(
            config, to=["reader@example.org"], subject="Re: Hello", body="Thanks",
            cc=None, bcc=None, reply_to_uid="123", reply_to_folder="Archive",
        )

    async def test_delete_adapter_uses_draft_uid(self):
        config = Config("sender@example.com", "fake")
        with patch.object(mcp_server.Config, "from_env", return_value=config), \
             patch.object(mcp_server, "delete_saved_draft", return_value={"status": "deleted"}) as delete:
            self.assertEqual(mcp_server.delete_draft("456"), {"status": "deleted"})
        delete.assert_called_once_with(config, "456")
