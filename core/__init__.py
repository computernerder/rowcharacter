"""
ROW Core - Character creation data classes and loaders.

Usage:
    from core import Race, Ancestry, Profession, Path, Background, Talent
    from core import load_all_races, load_all_ancestries, load_all_professions
    from core import load_all_paths, load_all_backgrounds, load_all_talents
"""

from .common import Feature, SkillBonus, ReputationModifier
from .race import Race, load_race, load_all_races
from .ancestry import Ancestry, load_ancestry, load_all_ancestries, get_ancestries_for_race
from .profession import Profession, Duty, load_profession, load_all_professions
from .path import Path, PathPrerequisite, load_path, load_all_paths
from .background import (
    Background, 
    BackgroundFeature,
    PersonalityEntry, 
    PersonalityTables,
    load_background, 
    load_all_backgrounds
)
from .talent import (
    Talent,
    TalentPrerequisites,
    TalentCategory,
    load_talent_category,
    load_all_talents,
    get_all_talents_flat,
)

__all__ = [
    # Common
    "Feature",
    "SkillBonus", 
    "ReputationModifier",
    # Race
    "Race",
    "load_race",
    "load_all_races",
    # Ancestry
    "Ancestry",
    "load_ancestry",
    "load_all_ancestries",
    "get_ancestries_for_race",
    # Profession
    "Profession",
    "Duty",
    "load_profession",
    "load_all_professions",
    # Path
    "Path",
    "PathPrerequisite",
    "load_path",
    "load_all_paths",
    # Background
    "Background",
    "BackgroundFeature",
    "PersonalityEntry",
    "PersonalityTables",
    "load_background",
    "load_all_backgrounds",
    # Talent
    "Talent",
    "TalentPrerequisites",
    "TalentCategory",
    "load_talent_category",
    "load_all_talents",
    "get_all_talents_flat",
]
