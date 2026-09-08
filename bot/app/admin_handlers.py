from aiogram import types


def configure(dependencies):
    globals().update(dependencies)


async def handle_llm_admin_operation(message: types.Message, operation: dict) -> bool:
    """Handle an operation returned by the single main LLM orchestration loop."""
    user_id = message.from_user.id
    resource, action = operation.get("resource"), operation.get("action")
    if resource == "uploads" and action == "request":
        upload = operation.get("payload") or {}
        asset_type = upload.get("asset_type")
        if not asset_type:
            await message.answer("The upload request did not specify an asset type.")
            return True
        pending_upload[user_id] = (asset_type, upload.get("label") or asset_type)
        if upload.get("entry_id"):
            pending_upload_target[user_id] = {"entry_id": upload["entry_id"], "role": upload.get("role", "gallery")}
        await message.answer(f"Please attach the {asset_type} file.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel upload", callback_data="upload:cancel")]]))
        return True
    if resource == "cv-tailoring" and action == "request":
        job_description = (operation.get("payload") or {}).get("job_description", "").strip()
        if len(job_description) < 30:
            await message.answer("The job description is too short to tailor the CV.")
        else:
            await prepare_cv_patch(message, job_description)
        return True
    if resource == "role-policies" and action == "propose":
        policies = (operation.get("payload") or {}).get("policies") or []
        for policy in policies:
            await manage_content("role-policies", "create", policy)
        names = ", ".join(policy.get("role_family", "").title() for policy in policies)
        await message.answer(f"Saved {len(policies)} pending role polic{'y' if len(policies) == 1 else 'ies'}: {names}." if policies else "I found no evidence-supported role policies.")
        return True
    if resource == "devto-sync" and action == "request":
        result = operation.get("payload") or {}
        await message.answer(f"Synced {result.get('updated', 0)} Dev.to article(s), including their public bodies.")
        return True
    if not resource or not action:
        return False
    if action == "list":
        items = await manage_content(resource, "list", {})
        response = await present_admin_result(message.text or "", resource, items[:5], {"is_admin": True})
        await message.answer(telegram_html(response))
        return True
    if action == "delete":
        if operation.get("id"):
            records = await manage_content(resource, "list", {})
            operation["target"] = next((item for item in records if str(item.get("id")) == str(operation["id"])), None)
        pending_mutation[user_id] = ("admin", f"{resource}:{action}", operation)
        target = operation.get("target") or {}
        label = target.get("name") or target.get("title") or target.get("label") or operation.get("id")
        await message.answer(f"Delete {label}?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Delete", callback_data="admin:confirm"), InlineKeyboardButton(text="Cancel", callback_data="admin:cancel")]]))
        return True
    await run_admin_operation(operation, update_profile=update_profile, manage_content=manage_content, bulk_manage_links=bulk_manage_links)
    await message.answer(f"{resource.replace('-', ' ').title()} {'updated' if action == 'update' else 'created' }.")
    return True

