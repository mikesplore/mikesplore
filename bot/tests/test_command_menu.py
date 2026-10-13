import asyncio

from bot.app import main


def test_public_command_menu_discloses_owner_management_commands(monkeypatch):
    calls = []

    class FakeBot:
        async def set_my_short_description(self, description):
            pass

        async def set_my_description(self, description):
            assert "do not create separate user profiles" in description

        async def set_my_commands(self, commands, scope=None):
            calls.append((commands, scope))

    monkeypatch.setattr(main, "bot", FakeBot())
    asyncio.run(main.register_commands())

    public_commands = {command.command: command.description for command in calls[0][0]}
    assert {"start", "menu", "help", "manage", "synccv", "referees", "apply"} <= set(public_commands)
    assert all("owner only" in public_commands[name].lower() for name in ("manage", "synccv", "referees", "apply"))

    admin_commands = {command.command for command in calls[1][0]}
    assert set(public_commands) <= admin_commands
    assert "cancel" in admin_commands
    assert calls[1][1].chat_id == main.settings.admin_telegram_id
