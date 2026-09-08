import html


def configure(dependencies):
    globals().update(dependencies)


async def prepare_cv_patch(message: types.Message, job_description: str, revision: str | None = None):
    status = await message.answer("Analyzing the job description…")
    try:
        await status.edit_text("Searching relevant projects and skills…")
        current = pending_cv.get(message.from_user.id)
        patch = await tailor_cv(job_description, current[0] if current else None, revision)
        if patch.get("status") == "rejected":
            await status.edit_text("I won't create a tailored CV for this job.\n\n" + html.escape(patch.get("reason", "There is not enough verified portfolio evidence for this role.")))
            return
        base = await get_cv_base()
        cv_name = (base.get("data") or {}).get("name") or "Tailored CV"
        pending_cv[message.from_user.id] = (patch, job_description, cv_name, base["revision"])
        await status.edit_text("Preparing proposed CV changes…")
        await status.edit_text("Proposed CV changes:\n\n" + format_cv_patch(patch), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Generate CV", callback_data="cv:generate"), InlineKeyboardButton(text="Request changes", callback_data="cv:revise")]]))
    except Exception:
        logger.exception("CV patch preparation failed")
        await status.edit_text("I couldn't prepare a valid CV patch. Please check the base CV and try again.")
