from aiogram import types

from . import browse


def register_callbacks(dispatcher, dependencies):
    globals().update(dependencies)

    @dispatcher.callback_query()
    async def action_callback(callback: types.CallbackQuery):
            user_id = callback.from_user.id
            data = callback.data or ""
            if user_id != settings.admin_telegram_id and is_protected_action(data):
                await acknowledge(callback, "This action is restricted to the portfolio owner.", show_alert=True, logger=logger)
                return
            # Public button browsing: everyone can use it, and it never calls the LLM.
            if data.startswith("pub:"):
                await browse.handle_public_callback(callback)
                return
            if data == "admin:cancel":
                pending_mutation.pop(user_id, None)
                await callback.answer("Cancelled")
                if callback.message:
                    await callback.message.edit_text("Cancelled.")
                return
            if data == "upload:cancel":
                pending_upload.pop(user_id, None)
                pending_upload_target.pop(user_id, None)
                await callback.answer("Cancelled")
                if callback.message:
                    await callback.message.edit_text("Upload cancelled.")
                return
            if data == "upload:retry":
                if user_id not in pending_upload:
                    await callback.answer("The upload request has expired", show_alert=True)
                    return
                await callback.answer("Ready for another file")
                if callback.message:
                    await callback.message.answer("Please attach the file again.")
                return
            if data == "admin:confirm":
                mutation = pending_mutation.pop(user_id, None)
                if not mutation or mutation[0] != "admin":
                    await callback.answer("No pending operation", show_alert=True)
                    return
                await acknowledge(callback, "Working…", logger=logger)
                try:
                    result = await run_admin_operation(mutation[2] or {}, update_profile=update_profile, manage_content=manage_content, bulk_manage_links=bulk_manage_links)
                    if callback.message:
                        await callback.message.edit_text(result)
                except httpx.HTTPStatusError as error:
                    pending_mutation[user_id] = mutation
                    if callback.message:
                        await callback.message.edit_text(f"The backend rejected that change: {error.response.text[:500]}")
                except Exception:
                    pending_mutation[user_id] = mutation
                    logger.exception("Inline admin mutation failed")
                    if callback.message:
                        await callback.message.edit_text("The operation failed. The pending change was kept so you can retry.")
                return
            if data in {"cv:generate", "cv:revise"}:
                tailored = pending_cv.get(user_id)
                if not tailored:
                    await callback.answer("This CV proposal has expired", show_alert=True)
                    return
                if data == "cv:revise":
                    await callback.answer("Reply with the changes you want")
                    if callback.message:
                        await callback.message.answer("Tell me what you want changed in the proposed CV.")
                    return
                try:
                    patch, job_description, label, base_revision = tailored
                    await callback.answer("Generating CV")
                    if callback.message:
                        await callback.message.answer("Generating the tailored CV…")
                    result = await render_cv(patch, job_description, base_revision, label)
                    async with httpx.AsyncClient(timeout=30) as client:
                        pdf_response = await client.get(result["pdf_url"])
                        pdf_response.raise_for_status()
                    pending_cv.pop(user_id, None)
                    if callback.message:
                        await callback.message.answer_document(types.BufferedInputFile(pdf_response.content, filename=cv_filename(label)), caption="Tailored CV")
                        last_cv_delivery[user_id] = (result["pdf_url"], label)
                except Exception as error:
                    logger.exception("Inline CV rendering failed")
                    if callback.message:
                        detail = error.response.text[:800] if isinstance(error, httpx.HTTPStatusError) else str(error)[:500]
                        await callback.message.answer(f"The tailored CV could not be generated: {detail}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(text="Retry", callback_data="cv:generate"),
                            InlineKeyboardButton(text="Request changes", callback_data="cv:revise"),
                        ]]))
                return
            if data == "cv:download-again":
                delivery = last_cv_delivery.get(user_id)
                if not delivery:
                    await callback.answer("No generated CV is available", show_alert=True)
                    return
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        response = await client.get(delivery[0])
                        response.raise_for_status()
                    await callback.answer("Sending CV")
                    if callback.message:
                        await callback.message.answer_document(types.BufferedInputFile(response.content, filename=cv_filename(delivery[1])), caption="Tailored CV")
                except Exception:
                    logger.exception("CV redelivery failed")
                    await callback.answer("The CV could not be downloaded", show_alert=True)
                return
            if data.startswith("gallery:"):
                try:
                    index = int(data.split(":", 1)[1])
                    item = admin_result_context.get(user_id, [])[index]
                    url = item.get("asset_url")
                    if not url:
                        raise ValueError("missing media URL")
                    async with httpx.AsyncClient(timeout=20) as media_client:
                        response = await media_client.get(url)
                        response.raise_for_status()
                    await callback.answer("Sending image")
                    if callback.message:
                        await callback.message.answer_photo(types.BufferedInputFile(response.content, filename="gallery-image"), caption=item.get("asset_label") or item.get("alt_text") or "Gallery image")
                except Exception:
                    logger.exception("Gallery image delivery failed")
                    await callback.answer("Image unavailable", show_alert=True)
                return
            if data in {"adminlist:next", "adminlist:prev"}:
                context = admin_result_context.get(user_id)
                if not context:
                    await callback.answer("This list has expired", show_alert=True)
                    return
                page_size = 5
                pages = max(1, (len(context["items"]) + page_size - 1) // page_size)
                context["page"] = max(0, min(pages - 1, context["page"] + (1 if data.endswith("next") else -1)))
                start = context["page"] * page_size
                page_items = context["items"][start:start + page_size]
                response = await present_admin_result(context["request"], context["resource"], page_items, {"is_admin": True})
                buttons = []
                if context["page"] > 0:
                    buttons.append(InlineKeyboardButton(text="Previous", callback_data="adminlist:prev"))
                if context["page"] < pages - 1:
                    buttons.append(InlineKeyboardButton(text="Next", callback_data="adminlist:next"))
                await callback.answer()
                if callback.message:
                    await callback.message.edit_text(telegram_html(response), reply_markup=InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None)
                return
            if data.startswith("mng:"):
                await wizard.handle_wizard_callback(callback)
                return
            await callback.answer("Unknown action", show_alert=True)
        
