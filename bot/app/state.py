"""In-memory conversation and workflow state for the Telegram process."""

conversation_history: dict[int, list[dict[str, str]]] = {}
pending: dict[int, dict] = {}
awaiting_entry: set[int] = set()
pending_upload: dict[int, tuple[str, str]] = {}
pending_upload_target: dict[int, dict] = {}
pending_mutation: dict[int, tuple[str, str, dict | None]] = {}
pending_sync: dict[int, tuple[str, list[dict], list[str]]] = {}
awaiting_cv: set[int] = set()
pending_cv: dict[int, tuple[dict, str, str, str]] = {}
last_cv_delivery: dict[int, tuple[str, str]] = {}
list_context: dict[int, tuple[str, int]] = {}
admin_result_context: dict[int, dict] = {}
