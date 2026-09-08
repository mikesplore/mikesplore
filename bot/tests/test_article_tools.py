import asyncio

from bot.app import tools


def test_search_articles_filters_projects(monkeypatch):
    async def fake_search(query, page=1):
        return {
            "total": 2,
            "page": page,
            "entries": [
                {"type": "project", "title": "Vela", "slug": "vela"},
                {"type": "article", "title": "Remote agents", "slug": "remote-agents"},
            ],
        }

    monkeypatch.setattr(tools, "search_portfolio", fake_search)
    result = asyncio.run(tools.search_articles("remote"))
    assert result["total"] == 1
    assert [item["title"] for item in result["articles"]] == ["Remote agents"]


def test_list_articles_requests_article_content_type(monkeypatch):
    captured = {}

    async def fake_list(content_type=None, page=1, page_size=5):
        captured.update(content_type=content_type, page=page)
        return {"total": 1, "page": page, "entries": [{"type": "article", "title": "A real article"}]}

    monkeypatch.setattr(tools, "list_entries", fake_list)
    result = asyncio.run(tools.list_articles(2))
    assert captured == {"content_type": "article", "page": 2}
    assert result["articles"][0]["title"] == "A real article"
