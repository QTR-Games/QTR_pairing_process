"""Validate the lightweight frontmatter schema for repository skills."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class ValidationMessage:
    """A schema validation result that can be printed locally or in Actions."""

    level: str
    message: str
    path: Path | None = None


def _strip_optional_quotes(value: str) -> str:
    """Remove a matching single or double quote pair from a scalar value."""

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse leading simple YAML-style frontmatter without a YAML dependency."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("frontmatter must begin with a leading '---' delimiter")

    frontmatter: dict[str, str] = {}
    for index, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return frontmatter, "\n".join(lines[index:])
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"frontmatter line {index} must use 'key: value' syntax")

        key, value = line.split(":", 1)
        key = key.strip()
        value = _strip_optional_quotes(value.strip())
        if not key:
            raise ValueError(f"frontmatter line {index} has an empty key")
        if key in frontmatter:
            raise ValueError(f"frontmatter contains duplicate key '{key}'")
        frontmatter[key] = value

    raise ValueError("frontmatter closing '---' delimiter is missing")


def validate_skill(path: Path) -> list[ValidationMessage]:
    """Return every validation error for one SKILL.md file."""

    try:
        frontmatter, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [ValidationMessage("error", str(error), path)]

    messages: list[ValidationMessage] = []
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")

    if not name:
        messages.append(ValidationMessage("error", "frontmatter requires 'name'", path))
    elif not NAME_PATTERN.fullmatch(name):
        messages.append(
            ValidationMessage(
                "error",
                "name must match ^[a-z0-9][a-z0-9-]*$",
                path,
            )
        )
    elif name != path.parent.name:
        messages.append(
            ValidationMessage(
                "error",
                f"name '{name}' must match folder name '{path.parent.name}'",
                path,
            )
        )

    if not description:
        messages.append(
            ValidationMessage("error", "frontmatter requires 'description'", path)
        )
    elif description != description.strip() or not 10 <= len(description) <= 300:
        messages.append(
            ValidationMessage(
                "error",
                "description must be trimmed and contain 10 to 300 characters",
                path,
            )
        )

    if not body.strip():
        messages.append(ValidationMessage("error", "SKILL.md body must be non-empty", path))
    return messages


def validate_skills_dir(skills_dir: Path) -> tuple[list[ValidationMessage], int]:
    """Validate every direct skill folder and return messages and valid count."""

    if not skills_dir.exists():
        return [ValidationMessage("error", "skills directory does not exist", skills_dir)], 0
    if not skills_dir.is_dir():
        return [ValidationMessage("error", "skills path must be a directory", skills_dir)], 0

    messages: list[ValidationMessage] = []
    valid_names: set[str] = set()
    skill_count = 0

    for folder in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
        skill_path = folder / "SKILL.md"
        if not skill_path.is_file():
            messages.append(
                ValidationMessage("error", "skill folder requires SKILL.md", folder)
            )
            continue

        skill_count += 1
        skill_messages = validate_skill(skill_path)
        messages.extend(skill_messages)
        if skill_messages:
            continue

        name, _ = parse_frontmatter(skill_path.read_text(encoding="utf-8"))
        skill_name = name["name"]
        if skill_name in valid_names:
            messages.append(
                ValidationMessage("error", f"skill name '{skill_name}' must be unique", skill_path)
            )
        else:
            valid_names.add(skill_name)

    if skill_count == 0:
        messages.append(ValidationMessage("notice", "zero skills found; schema is valid", skills_dir))
    return messages, len(valid_names)


def _format_message(message: ValidationMessage, github: bool) -> str:
    path = str(message.path) if message.path is not None else ""
    if github:
        location = f" file={path}" if path else ""
        return f"::{message.level}{location}::{message.message}"
    return f"{message.level.upper()}: {path}: {message.message}" if path else (
        f"{message.level.upper()}: {message.message}"
    )


def run(skills_dir: Path, github: bool = False) -> int:
    """Print schema results and return a process-compatible status code."""

    messages, valid_count = validate_skills_dir(skills_dir)
    errors = [message for message in messages if message.level == "error"]
    for message in messages:
        print(_format_message(message, github))

    if errors:
        print(f"{len(errors)} schema violation(s) found.")
        return 1

    if valid_count == 0:
        print("0 valid skills; schema check passed.")
    else:
        print(f"{valid_count} valid skill(s); schema check passed.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the schema checker as a dependency-free command-line tool."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=Path(".github/skills"),
        help="directory containing <skill-name>/SKILL.md folders",
    )
    parser.add_argument(
        "--github",
        action="store_true",
        help="emit GitHub Actions workflow annotations",
    )
    arguments = parser.parse_args(argv)
    return run(arguments.skills_dir, github=arguments.github)


if __name__ == "__main__":
    raise SystemExit(main())
