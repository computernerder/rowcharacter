import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from character_builder import CharacterBuilder
from validation import CharacterValidator


@pytest.fixture(scope="module")
def validator():
    return CharacterValidator(data_dir=str(ROOT_DIR / "data"))


def _complete_builder_with_defaults() -> CharacterBuilder:
    builder = CharacterBuilder()
    builder.load_game_data(str(ROOT_DIR / "data"))

    # Ability scores that satisfy Mystic path prereqs (INT primary) and reasonable stats
    builder.set_ability_scores({
        "Might": 10,
        "Agility": 14,
        "Endurance": 13,
        "Intellect": 15,
        "Wisdom": 12,
        "Charisma": 8,
    })

    builder.set_race("elf")
    builder.set_ancestry("sylari")
    builder.set_profession("scholar")
    builder.resolve_choice("skill", ["Arcana", "History"], source="Scholar Profession")
    builder.set_path("mystic")
    builder.set_background("scholar")

    # Resolve any remaining pending choices deterministically (pick the first options)
    while builder.pending_choices:
        choice = builder.pending_choices[0]
        selections = choice.options[: choice.count]
        builder.resolve_choice(choice.choice_type, selections, source=choice.source)

    builder.character.character_name = "Test Hero"
    builder.character.player = "Tester"
    builder.recalculate_all()
    return builder


def test_builder_produces_complete_character(validator: CharacterValidator):
    builder = _complete_builder_with_defaults()
    assert builder.is_complete(), "Builder should report completion after steps resolved"

    char = builder.get_character()
    # Basic sanity checks
    assert char.race.lower() == "elf"
    assert char.ancestry.lower() == "sylari"
    assert char.profession.lower() == "scholar"
    assert char.primary_path.lower() == "mystic"
    assert char.background.lower() == "scholar"
    assert char.defense.base > 0
    assert char.health.max >= 1

    # Validate character dictionary against rules
    result = validator.validate_character(char.to_dict())
    assert result.valid, f"Validation failed: {result.errors}"


def test_validator_flags_missing_fields(validator: CharacterValidator):
    result = validator.validate_character({})
    assert not result.valid
    # Should complain about required fields like race/background
    missing = {"race", "ancestry", "profession", "primary_path", "background"}
    assert missing.issubset({err.split(":")[-1].strip() for err in result.errors})


if __name__ == "__main__":
    pytest.main([__file__])
