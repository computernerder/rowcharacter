"""
ROW Core - Character creation data classes and loaders.

Usage:
    from core import Race, Ancestry, Profession, Path, Background
    from core import load_all_races, load_all_ancestries, load_all_professions
    from core import load_all_paths, load_all_backgrounds
"""

from .common import Feature, SkillBonus, ReputationModifier
from .race import Race, load_race, load_all_races
from .ancestry import Ancestry, load_ancestry, load_all_ancestries, get_ancestries_for_race
from .profession import Profession, Duty, load_profession, load_all_professions
from .path import Path, PathPrerequisite, load_path, load_all_paths
from .background import (
    Background, 
    PersonalityEntry, 
    PersonalityTables,
    load_background, 
    load_all_backgrounds
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
    "PersonalityEntry",
    "PersonalityTables",
    "load_background",
    "load_all_backgrounds",
]
