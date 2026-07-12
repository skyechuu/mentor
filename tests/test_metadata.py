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
        ConvertedPage(
            "Entities package",
            "# Entities package\n\n## Components and archetypes\n\n"
            "Use `IJobEntity` with `EntityQuery` and `Burst`.",
            [],
        ),
        ConvertedPage(
            "Systems",
            "# Systems\n\n## System implementations\n\n"
            "Choose `SystemBase` or `ISystem`.",
            [],
        ),
        ConvertedPage(
            "Entity workflows",
            "# Workflows\n\n## Baking and subscenes\n\n"
            "Record changes in an `EntityCommandBuffer`.",
            [],
        ),
    ]
    name, description, overview = build_skill_metadata(UNITY_URL, pages)
    assert name == "unity-entities-6.5"
    assert "Unity Entities (ECS/DOTS) 6.5" in description
    for keyword in (
        "IJobEntity",
        "EntityQuery",
        "SystemBase",
        "ISystem",
        "EntityCommandBuffer",
        "Burst",
        "Components and archetypes",
        "Baking and subscenes",
    ):
        assert keyword in description
    assert "Open only relevant reference files" in description
    assert "docs-unity3d-com" not in description
    assert len(description) < 1024
    assert "Unity Entities" in overview


def test_api_identifiers_win_over_large_page_title_list():
    pages = [
        ConvertedPage(f"Guide page {index}", f"# Guide page {index}", [])
        for index in range(30)
    ]
    pages.append(
        ConvertedPage(
            "Advanced APIs",
            "## Queries\nUse `EntityQuery`, `IJobEntity`, and `SystemBase`.",
            [],
        )
    )
    _name, description, _overview = build_skill_metadata(UNITY_URL, pages)
    assert "EntityQuery" in description
    assert "IJobEntity" in description
    assert "SystemBase" in description


def test_requested_dotted_version_name_is_preserved():
    pages = [ConvertedPage("Product Docs", "# Product Docs", [])]
    name, _description, _overview = build_skill_metadata(
        "https://example.com/docs/", pages, requested_name="product-2.4"
    )
    assert name == "product-2.4"
