from doctoskill.enhance import enhance_skill


class Messages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        block = type("Block", (), {"text": self.response})()
        return type("Message", (), {"content": [block]})()


class Client:
    def __init__(self, response):
        self.messages = Messages(response)


def test_enhance_rewrites_only_skill_md(tmp_path):
    skill = tmp_path / "skill"
    (skill / "references").mkdir(parents=True)
    old = "---\nname: skill\ndescription: old\n---\n\nOld\n"
    new = "---\nname: skill\ndescription: improved\n---\n\nImproved\n"
    (skill / "SKILL.md").write_text(old, encoding="utf-8")
    (skill / "references" / "page.md").write_text("Reference", encoding="utf-8")
    client = Client(new)
    enhance_skill(skill, client=client)
    assert (skill / "SKILL.md").read_text(encoding="utf-8") == new
    assert client.messages.kwargs["model"]
