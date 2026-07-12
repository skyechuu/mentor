from doctoskill.slugify import slugify


def test_slugify_titles_and_empty_values():
    assert slugify("Getting Started") == "getting-started"
    assert slugify("What's new!!") == "what-s-new"
    assert slugify("   ") == "untitled"
    assert slugify("Café") == "cafe"
