from doctoskill.llms_txt import fetch_llms_txt, parse_llms_txt


class Response:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class Session:
    def __init__(self, values):
        self.values = values

    def get(self, url, timeout=10, headers=None):
        return Response(self.values.get(url, ""), 200 if url in self.values else 404)


def test_parse_llms_txt_preserves_fenced_code():
    sections = parse_llms_txt(
        "# Framework\n\n## Start\n\n```py\nprint('hi')\n```\n\n## Configure\n\nUse config."
    )
    assert [title for title, _ in sections] == ["Start", "Configure"]
    assert "print('hi')" in sections[0][1]


def test_fetch_llms_prefers_full_then_falls_back():
    root = "https://example.com"
    assert fetch_llms_txt(
        root,
        session=Session(
            {f"{root}/llms-full.txt": "full", f"{root}/llms.txt": "short"}
        ),
    ) == "full"
    assert fetch_llms_txt(
        root, session=Session({f"{root}/llms.txt": "short"})
    ) == "short"
    assert fetch_llms_txt(root, session=Session({})) is None
