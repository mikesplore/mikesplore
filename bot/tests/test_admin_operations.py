import asyncio

from bot.app.admin_operations import execute_admin_operation


def test_profile_update_ignores_null_fields_to_preserve_existing_values():
    updates = []

    async def update_profile(payload):
        updates.append(payload)

    asyncio.run(
        execute_admin_operation(
            {"resource": "profile", "action": "update", "payload": {"name": "Mike", "tagline": None, "about": "<p>About</p>"}},
            update_profile=update_profile,
            manage_content=None,
            bulk_manage_links=None,
        )
    )

    assert updates == [{"name": "Mike", "about": "<p>About</p>"}]
