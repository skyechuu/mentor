from doctoskill.metadata import build_skill_metadata, derive_skill_name
from doctoskill.types import ConvertedPage

UNITY_URL = (
    "https://docs.unity3d.com/Packages/"
    "com.unity.entities@6.5/manual/index.html"
)


def test_unity_package_name_keeps_product_and_dotted_version():
    assert derive_skill_name(UNITY_URL) == "unity-entities-6.5"


def test_description_uses_product_aliases_and_heading_topics():
    pages = [
        ConvertedPage("Entities package", "# Entities package\n\n## Components", []),
        ConvertedPage("Systems", "# Systems\n\n## SystemBase and ISystem", []),
        ConvertedPage("Entity queries", "# EntityQuery\n\n## IJobEntity", []),
        ConvertedPage("Baking and subscenes", "# Baking\n\n## Subscenes", []),
    ]
    name, description, overview = build_skill_metadata(UNITY_URL, pages)
    assert name == "unity-entities-6.5"
    assert "Unity Entities (ECS/DOTS) 6.5" in description
    assert "Systems" in description
    assert "Entity queries" in description
    assert "Open only relevant reference files" in description
    assert "docs-unity3d-com" not in description
    assert "Unity Entities" in overview


def test_requested_dotted_version_name_is_preserved():
    pages = [ConvertedPage("Product Docs", "# Product Docs", [])]
    name, _description, _overview = build_skill_metadata(
        "https://example.com/docs/", pages, requested_name="product-2.4"
    )
    assert name == "product-2.4"
