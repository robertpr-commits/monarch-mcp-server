"""Tests for MONARCH_MCP_READ_ONLY gating of write tools."""

from monarch_mcp_server import app


async def _registered_names():
    return {t.name for t in await app.mcp.list_tools()}


# The 21 mutating tools that read-only mode must hide.
WRITE_TOOLS = {
    "create_transaction",
    "update_transaction",
    "categorize_transaction",
    "update_transaction_notes",
    "mark_transaction_reviewed",
    "bulk_categorize_transactions",
    "delete_transaction",
    "create_transaction_category",
    "update_category",
    "set_transaction_tags",
    "create_transaction_tag",
    "add_transaction_tag",
    "create_transaction_rule",
    "update_transaction_rule",
    "delete_transaction_rule",
    "split_transaction",
    "update_merchant",
    "review_recurring_stream",
    "refresh_accounts",
    "upload_account_balance_history",
    "set_budget_amount",
}


class TestWriteToolGating:
    async def test_write_tool_is_noop_in_read_only(self, monkeypatch):
        monkeypatch.setattr(app, "READ_ONLY_MODE", True)

        async def unique_blocked_tool():
            return "ok"

        decorated = app.write_tool()(unique_blocked_tool)
        # The original function is returned untouched and never registered.
        assert decorated is unique_blocked_tool
        assert "unique_blocked_tool" not in await _registered_names()

    async def test_write_tool_registers_when_not_read_only(self, monkeypatch):
        monkeypatch.setattr(app, "READ_ONLY_MODE", False)

        async def unique_allowed_tool():
            return "ok"

        app.write_tool()(unique_allowed_tool)
        assert "unique_allowed_tool" in await _registered_names()


class TestDefaultRegistration:
    async def test_all_write_tools_registered_by_default(self):
        # Tests run with MONARCH_MCP_READ_ONLY unset, so writers are present.
        assert WRITE_TOOLS <= await _registered_names()

    async def test_core_read_tools_registered(self):
        names = await _registered_names()
        for read_tool in (
            "get_accounts",
            "get_transactions",
            "get_budgets",
            "get_transaction_categories",
            "get_transaction_tags",
        ):
            assert read_tool in names
