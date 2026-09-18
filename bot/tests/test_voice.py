from bot.app.voice import ASSEMBLYAI_URL, assemblyai_url


def test_assemblyai_url_uses_phase_one_streaming_configuration():
    url = assemblyai_url()
    assert url.startswith(ASSEMBLYAI_URL + "?")
    assert "sample_rate=16000" in url
    assert "format_turns=True" in url
    assert "speech_model=universal-streaming-english" in url


def test_voice_route_is_registered_on_bot_app():
    from bot.app.main import app

    assert any(route.path == "/ws/voice" for route in app.routes)
