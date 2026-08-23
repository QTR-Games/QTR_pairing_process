from pathlib import Path

import skill_schema_check as checker


VALID_FM = """---
name: {name}
description: A useful skill description for QTR testing.
---
"""


def _write_skill(
    skills_dir: Path,
    name: str = "example-skill",
    *,
    frontmatter: str | None = None,
    body: str = "# Instructions\n\nDo the focused task.\n",
) -> Path:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(
        (frontmatter or VALID_FM.format(name=name)) + body,
        encoding="utf-8",
    )
    return skill_path


def test_parse_frontmatter_success():
    frontmatter, body = checker.parse_frontmatter(
        VALID_FM.format(name="example-skill") + "Body text\n"
    )

    assert frontmatter["name"] == "example-skill"
    assert body == "Body text"


def test_parse_frontmatter_strips_matching_quotes():
    frontmatter, _ = checker.parse_frontmatter(
        "---\nname: 'example-skill'\ndescription: \"A useful description.\"\n---\nBody\n"
    )

    assert frontmatter == {
        "name": "example-skill",
        "description": "A useful description.",
    }


def test_parse_frontmatter_rejects_missing_opening_delimiter():
    try:
        checker.parse_frontmatter("name: example-skill\n---\nBody\n")
    except ValueError as error:
        assert "begin" in str(error)
    else:
        raise AssertionError("missing opening delimiter should fail")


def test_parse_frontmatter_rejects_missing_closing_delimiter():
    try:
        checker.parse_frontmatter("---\nname: example-skill\n")
    except ValueError as error:
        assert "closing" in str(error)
    else:
        raise AssertionError("missing closing delimiter should fail")


def test_valid_skill(tmp_path: Path):
    _write_skill(tmp_path)

    messages, valid_count = checker.validate_skills_dir(tmp_path)

    assert messages == []
    assert valid_count == 1


def test_zero_skills_is_valid_with_notice(tmp_path: Path):
    messages, valid_count = checker.validate_skills_dir(tmp_path)

    assert valid_count == 0
    assert [(message.level, message.message) for message in messages] == [
        ("notice", "zero skills found; schema is valid")
    ]


def test_folder_name_mismatch_is_invalid(tmp_path: Path):
    _write_skill(
        tmp_path,
        name="folder-name",
        frontmatter=VALID_FM.format(name="other-name"),
    )

    messages, _ = checker.validate_skills_dir(tmp_path)

    assert any("must match folder name" in message.message for message in messages)


def test_invalid_name_is_rejected(tmp_path: Path):
    _write_skill(
        tmp_path,
        frontmatter=VALID_FM.format(name="Invalid_Name"),
    )

    messages, _ = checker.validate_skills_dir(tmp_path)

    assert any("must match" in message.message for message in messages)


def test_short_description_is_rejected(tmp_path: Path):
    _write_skill(
        tmp_path,
        frontmatter="---\nname: example-skill\ndescription: short\n---\n",
    )

    messages, _ = checker.validate_skills_dir(tmp_path)

    assert any("10 to 300" in message.message for message in messages)


def test_empty_body_is_rejected(tmp_path: Path):
    _write_skill(tmp_path, body=" \n")

    messages, _ = checker.validate_skills_dir(tmp_path)

    assert any("body must be non-empty" in message.message for message in messages)


def test_multiple_valid_skills(tmp_path: Path):
    _write_skill(tmp_path, name="first-skill")
    _write_skill(tmp_path, name="second-skill")

    messages, valid_count = checker.validate_skills_dir(tmp_path)

    assert messages == []
    assert valid_count == 2


def test_run_returns_one_for_invalid_skill(tmp_path: Path):
    _write_skill(tmp_path, body="")

    assert checker.run(tmp_path) == 1
