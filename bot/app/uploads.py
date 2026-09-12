from aiogram import types


def register_upload_handler(dispatcher, dependencies):
    globals().update(dependencies)

    @dispatcher.message(lambda message: bool(message.document or message.photo))
    async def document(message: types.Message):
            if not is_admin(message):
                await message.answer("Document ingestion is restricted to the administrator.")
                return
            wizard_session = wizard_sessions.get(message.from_user.id)
            if wizard_session and wizard_session.get("step") == "media":
                # Deterministic /manage wizard media field: arm pending_upload so
                # the flow below uploads through the exact same path as /upload.
                await wizard.prepare_media_upload(message, wizard_session)
            asset_type = "file"
            try:
                if message.from_user.id not in awaiting_cv or pending_upload.get(message.from_user.id):
                    await message.answer("File received. Uploading it now…")
                await show_typing(message)
                asset_request = pending_upload.get(message.from_user.id)
                telegram_file_id = message.document.file_id if message.document else message.photo[-1].file_id
                telegram_file = await bot.get_file(telegram_file_id)
                if telegram_file.file_size and telegram_file.file_size > 5 * 1024 * 1024:
                    await message.answer("That file is too large. Please send a file no bigger than 5 MB.")
                    return
                buffer = __import__('io').BytesIO()
                await bot.download_file(telegram_file.file_path, buffer)
                filename = message.document.file_name if message.document else "upload.jpg"
                mime_type = message.document.mime_type if message.document else "image/jpeg"
                if message.from_user.id in awaiting_cv:
                    pending_upload.pop(message.from_user.id, None)
                    if mime_type.startswith("image/"):
                        await message.answer("Reading the job poster…")
                        job_description = await extract_job_description_from_image(buffer.getvalue(), mime_type)
                    elif mime_type == "application/pdf":
                        from pypdf import PdfReader
                        job_description = "\n".join(page.extract_text() or "" for page in PdfReader(buffer).pages).strip()
                        if len(job_description) < 30:
                            await message.answer("That PDF has no readable text. Please send an image poster or a text-based PDF.")
                            return
                    else:
                        await message.answer("For a job description, send a poster image or PDF.")
                        return
                    awaiting_cv.discard(message.from_user.id)
                    await prepare_cv_patch(message, job_description)
                    return
                if asset_request:
                    asset_type, label = asset_request
                    if asset_type == "cv-json":
                        import json
                        try:
                            data = json.loads(buffer.getvalue().decode("utf-8"))
                            await save_cv_base(data)
                        except Exception:
                            logger.exception("Base CV JSON upload failed")
                            await message.answer("That is not a valid CV JSON file or it failed backend validation.")
                            return
                        pending_upload.pop(message.from_user.id, None)
                        await message.answer("Base CV JSON saved.")
                        return
                    if asset_type == "certificate":
                        # Certificates have their own database collection and public
                        # listing endpoint. Do not store them as generic site assets.
                        result = await upload_certificate(label, filename, buffer.getvalue(), mime_type)
                        pending_upload.pop(message.from_user.id, None)
                        await message.answer(f"Certificate uploaded: {html.escape(result['title'], quote=False)}")
                        return
                    result = await upload_asset(asset_type, label, filename, buffer.getvalue(), mime_type)
                    pending_upload.pop(message.from_user.id, None)
                    await message.answer(f"Asset uploaded: {html.escape(result['label'], quote=False)}")
                    target = pending_upload_target.pop(message.from_user.id, None)
                    if target:
                        await manage_content("entry-assets", "create", {
                            "entry_id": target["entry_id"],
                            "asset_id": result["id"],
                            "role": target.get("role", "gallery"),
                            "alt_text": label,
                            "caption": label,
                            "custom_order": 0,
                        })
                        await message.answer("The uploaded asset was attached to the project.")
                    if asset_type == "profile-image":
                        try:
                            await bot.set_my_profile_photo(
                                photo=types.InputProfilePhotoStatic(
                                    photo=types.BufferedInputFile(buffer.getvalue(), filename=filename)
                                )
                            )
                            await message.answer("My profile image was updated too.")
                        except Exception:
                            logger.exception("Telegram bot profile photo update failed")
                            await message.answer("The portfolio image was updated, but Telegram's bot profile image could not be changed.")
                if wizard_sessions.get(message.from_user.id):
                    await wizard.media_upload_complete(message)
                else:
                    await message.answer("I don't have an upload request for this file yet. Please describe what you want to add.")
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 413:
                    await message.answer("That file is too large. Please send a file no bigger than 5 MB.")
                else:
                    logger.exception("%s upload failed", asset_type)
                    await message.answer(f"I couldn't upload that {asset_type}. Please check R2 configuration and try again.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="Retry upload", callback_data="upload:retry"),
                        InlineKeyboardButton(text="Cancel", callback_data="upload:cancel"),
                    ]]))
            except Exception:
                logger.exception("%s upload failed", asset_type)
                await message.answer(f"I couldn't upload that {asset_type}. Please check R2 configuration and try again.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="Retry upload", callback_data="upload:retry"),
                    InlineKeyboardButton(text="Cancel", callback_data="upload:cancel"),
                ]]))
        

