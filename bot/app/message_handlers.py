from aiogram import types

from . import browse


def register_message_handlers(dispatcher, dependencies):
    globals().update(dependencies)

    @dispatcher.message(lambda message: not message.document and not message.photo)
    async def question(message: types.Message):
            if is_admin(message) and message.text:
                if message.text.strip().lower() == "/cancel":
                    pending.pop(message.from_user.id, None)
                    awaiting_entry.discard(message.from_user.id)
                    pending_mutation.pop(message.from_user.id, None)
                    pending_upload_target.pop(message.from_user.id, None)
                    pending_sync.pop(message.from_user.id, None)
                    awaiting_cv.discard(message.from_user.id)
                    pending_cv.pop(message.from_user.id, None)
                    wizard_sessions.pop(message.from_user.id, None)
                    await message.answer("Cancelled.")
                    return
                if message.text.strip().startswith("/"):
                    await message.answer("Only /start, /menu, /help, /manage, and /cancel are available. Use /menu to browse the portfolio with buttons, or describe what you need in ordinary language.")
                    return
                active_wizard = wizard_sessions.get(message.from_user.id)
                if active_wizard:
                    if await handle_wizard_text(message, active_wizard):
                        return
                normalized_admin_text = message.text.strip().lower()
                confirmation_text = normalized_admin_text in {"yes", "confirm", "go ahead", "proceed", "do it"}
                if message.from_user.id in pending_cv and not confirmation_text:
                    try:
                        current_patch, job_description, label, base_revision = pending_cv[message.from_user.id]
                        decision = await tailor_cv(job_description, current_patch, message.text)
                        if decision.get("status") != "rejected" and decision.get("action") != "confirm":
                            decision = {
                                "summary": {key: str(decision.get("summary", {}).get(key, "")) for key in ("old", "new")},
                                "selected_projects": [str(item) for item in decision.get("selected_projects", [])],
                                "selected_skills": {str(category): [str(item) for item in items] for category, items in (decision.get("selected_skills") or {}).items()},
                            }
                        if decision.get("action") == "confirm":
                            confirmation_text = True
                        elif decision.get("status") == "rejected":
                            await message.answer("I won't apply this CV revision: " + html.escape(decision.get("reason", "There is not enough verified evidence.")))
                            return
                        else:
                            pending_cv[message.from_user.id] = (decision, job_description, label, base_revision)
                            await message.answer("Updated proposed CV changes:\n\n" + format_cv_patch(decision) + "\n\nConfirm, or tell me what to change.")
                            return
                    except Exception as error:
                        logger.exception("CV revision handling failed")
                        await message.answer(friendly_error(error, "I couldn't understand that CV change. Please describe what you want changed."))
                        return
                if confirmation_text:
                    sync = pending_sync.pop(message.from_user.id, None)
                    if sync:
                        try:
                            result = await apply_sync(sync[0], sync[1], sync[2])
                            await message.answer(f"{sync[0].title()} sync complete: {result['updated']} entries upserted.")
                        except httpx.HTTPStatusError as error:
                            pending_sync[message.from_user.id] = sync
                            logger.exception("Sync apply failed with backend response")
                            await message.answer(f"The sync was rejected by the backend: {error.response.text[:800]}\n\nThe preview is still pending; fix the issue and try /confirm again.")
                        except Exception:
                            pending_sync[message.from_user.id] = sync
                            logger.exception("Sync apply failed")
                            await message.answer("The sync could not be completed. The preview is still pending; try /confirm again.")
                        return
                    tailored = pending_cv.pop(message.from_user.id, None)
                    if tailored:
                        await message.answer("Confirmed. I’m now rendering the tailored PDF…")
                        try:
                            patch, job_description, label, base_revision = tailored
                            result = await render_cv(patch, job_description, base_revision, label)
                            async with httpx.AsyncClient(timeout=30) as client:
                                pdf_response = await client.get(result["pdf_url"])
                                pdf_response.raise_for_status()
                            last_cv_delivery[message.from_user.id] = (result["pdf_url"], label)
                            await message.answer_document(types.BufferedInputFile(pdf_response.content, filename=cv_filename(label)), caption="Tailored CV", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                InlineKeyboardButton(text="Download again", callback_data="cv:download-again"),
                            ]]))
                        except httpx.HTTPStatusError as error:
                            pending_cv[message.from_user.id] = tailored
                            logger.exception("Tailored CV rejected by backend")
                            await message.answer(f"The backend rejected the tailored CV: {error.response.text[:500]}")
                        except Exception as error:
                            pending_cv[message.from_user.id] = tailored
                            logger.exception("Tailored CV rendering failed")
                            await message.answer(f"The tailored CV could not be rendered: {str(error)[:500]}. The proposal is still pending; please say yes to retry or describe a change.")
                        return
                    mutation = pending_mutation.pop(message.from_user.id, None)
                    if mutation:
                        try:
                            if mutation[0] == "delete": await delete_entry(mutation[1])
                            elif mutation[0] == "asset-delete": await delete_asset(mutation[1])
                            elif mutation[0] == "certificate-delete": await delete_certificate(mutation[1])
                            elif mutation[0] == "profile": await update_profile(mutation[2] or {})
                            elif mutation[0] == "manage":
                                resource, action = mutation[1].split(":", 1)
                                await manage_content(resource, action, mutation[2] or {})
                            elif mutation[0] == "admin":
                                operation = mutation[2] or {}
                                result_message = await run_admin_operation(operation, update_profile=update_profile, manage_content=manage_content, bulk_manage_links=bulk_manage_links)
                            else: await update_entry(mutation[1], mutation[2] or {})
                            if mutation[0] == "profile":
                                result_message = "Profile updated."
                            elif mutation[0] == "manage":
                                result_message = "Content managed."
                            elif mutation[0] == "edit":
                                result_message = "Entry updated."
                            elif mutation[0] == "admin":
                                action = (mutation[2] or {}).get("action")
                                resource = (mutation[2] or {}).get("resource", "content")
                                result_message = {"create": f"{resource.title()} created.", "update": f"{resource.title()} updated.", "delete": f"{resource.title()} deleted."}.get(action, "Change applied.")
                            else:
                                result_message = "Entry deleted."
                            await message.answer(result_message)
                        except httpx.HTTPStatusError as error:
                            logger.exception("Admin mutation rejected")
                            pending_mutation[message.from_user.id] = mutation
                            await message.answer(f"The backend rejected that change: {error.response.text[:500]}")
                        except Exception:
                            logger.exception("Admin mutation failed")
                            pending_mutation[message.from_user.id] = mutation
                            await message.answer("The change could not be completed. The proposal is still pending; please try again or say cancel.")
                        return
                    entry = pending.pop(message.from_user.id, None)
                    if not entry:
                        await message.answer("There is no pending preview. File uploads are saved immediately; /confirm is only for pending edits or content changes.")
                        return
                    try:
                        created = await create_entry(entry)
                        await message.answer(f"Saved entry: {html.escape(created['title'], quote=False)}")
                    except Exception:
                        pending[message.from_user.id] = entry
                        await message.answer("The backend rejected the entry. The preview is still pending.")
                    return
                if message.from_user.id in awaiting_cv:
                    awaiting_cv.discard(message.from_user.id)
                    await prepare_cv_patch(message, message.text)
                    return
                if message.from_user.id in pending_cv:
                    patch, job_description, _label, _revision = pending_cv[message.from_user.id]
                    await prepare_cv_patch(message, job_description, message.text)
                    return
                if message.from_user.id in awaiting_entry:
                    try:
                        await show_typing(message)
                        entry = await extract_entry(message.text)
                        pending[message.from_user.id] = entry
                        awaiting_entry.discard(message.from_user.id)
                        await message.answer("Preview (send /confirm to save, /cancel to discard):\n\n" + format_preview(entry))
                    except Exception as error:
                        logger.exception("Entry extraction failed")
                        await message.answer(friendly_error(error, "I couldn't extract a valid entry. Please provide a clearer instruction."))
                    return
                question_text = message.text or ""
                user_id = message.from_user.id
                normalized = question_text.lower().strip()
                is_next = normalized in {"yes", "y", "next", "next page", "show more", "more"} or "next page" in normalized
                if is_next and user_id in list_context:
                    content_type, current_page = list_context[user_id]
                    question_text = f"Show page {current_page + 1} of {content_type}s from the portfolio."
                    list_context[user_id] = (content_type, current_page + 1)
                elif is_next and conversation_history.get(user_id):
                    # A detail follow-up such as "next" should stay with the previous
                    # subject instead of becoming a fresh search for the literal word.
                    question_text = "Continue with the same subject as my previous request and provide the next useful detail."
                else:
                    content_type = next((value for value in ("project", "article", "hackathon", "event") if value in normalized), None)
                    if content_type and any(word in normalized for word in ("show", "list", "what", "which")):
                        list_context[user_id] = (content_type, 1)
                history = conversation_history.setdefault(user_id, [])
                streamed_message = await message.answer("…")
                last_edit = 0.0
        
                async def update_stream(text: str):
                    nonlocal last_edit
                    now = asyncio.get_running_loop().time()
                    if now - last_edit < 0.7 and len(text) < 3900:
                        return
                    last_edit = now
                    await streamed_message.edit_text(html.escape(text[-4000:]))
        
                try:
                    response = await answer(
                        question_text,
                        history[-6:],
                        on_text=update_stream,
                        user_context={
                            "first_name": message.from_user.first_name if message.from_user else None,
                            "last_name": message.from_user.last_name if message.from_user else None,
                            "is_admin": is_admin(message),
                        },
                    )
                    if response.startswith("__ADMIN_OPERATION__"):
                        operation = json.loads(response.removeprefix("__ADMIN_OPERATION__"))
                        await handle_llm_admin_operation(message, operation)
                        return
                    history.extend([
                        {"role": "user", "content": question_text},
                        {"role": "assistant", "content": response},
                    ])
                    del history[:-6]
                except Exception as error:
                    logger.exception("LLM answer failed")
                    await message.answer(friendly_error(error, "I couldn't complete that request right now. Please try again shortly."))
                    return
            if response.startswith("__BOT_ACTION__"):
                await streamed_message.delete()
                action = __import__('json').loads(response.removeprefix("__BOT_ACTION__"))
                try:
                    if action["action"] == "send_cv":
                        await send_cv(message)
                    elif action["action"] == "send_certificates":
                        await deliver_certificates(message, action.get("query", ""))
                except Exception:
                    logger.exception("Bot action failed")
                    await message.answer("I couldn't complete that request right now. Please try again shortly.")
                return
            # Browse navigation is available from /menu and deterministic browse
            # commands. Ordinary LLM answers stay as plain replies.
            await streamed_message.edit_text(telegram_html(response), reply_markup=None)
        
        
