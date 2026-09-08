from bot.app.admin_handlers import configure as configure_admin_handlers
from bot.app.callback_handlers import register_callbacks
from bot.app.message_handlers import register_message_handlers
from bot.app.uploads import register_upload_handler


class FakeDispatcher:
    def __init__(self):
        self.handlers = []

    def _register(self, kind):
        def decorator(function):
            self.handlers.append((kind, function))
            return function

        return decorator

    def callback_query(self, *args, **kwargs):
        return self._register("callback")

    def message(self, *args, **kwargs):
        return self._register("message")


def test_extracted_dispatcher_handlers_register_once():
    dispatcher = FakeDispatcher()
    register_callbacks(dispatcher, {})
    register_upload_handler(dispatcher, {})
    register_message_handlers(dispatcher, {"handle_llm_admin_operation": lambda *_: None})

    assert [kind for kind, _ in dispatcher.handlers] == ["callback", "message", "message"]
    assert len({function.__name__ for _, function in dispatcher.handlers}) == 3


def test_admin_dependencies_are_injected():
    import bot.app.admin_handlers as admin_handlers

    marker = object()
    configure_admin_handlers({"manage_content": marker})

    assert admin_handlers.manage_content is marker
