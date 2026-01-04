"""
Talent class for Realm of Warriors character progression.

Talents represent specialized abilities gained through Path training
or general life experience.

Types:
- General Talents: Available to all characters
- Path Talents: Tied to specific paths (Defense, Divine, etc.)
- Capstone Talents: Ultimate abilities requiring all other path talents
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import json
from pathlib import Path


@dataclass
class TalentPrerequisites:
    """Prerequisites for acquiring a talent."""
    # Ability score requirements (ability_name -> minimum)
    abilities: Dict[str, int] = field(default_factory=dict)
    
    # Prerequisite type for multiple ability requirements
    prereq_type: str = "and"  # "and" or "or"
    
    # Level requirements by rank
    level_by_rank: Dict[int, int] = field(default_factory=dict)
    
    # Required talents
    required_talents: List[str] = field(default_factory=list)
    
    # Is this a capstone (requires all other path talents)?
    is_capstone: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TalentPrerequisites":
        """Create from dictionary."""
        abilities = {}
        prereq_type = data.get("prereq_type", "and")
        
        # Parse ability requirements
        for key, value in data.items():
            if key in {"Might", "Agility", "Endurance", "Intellect", "Wisdom", "Charisma"}:
                abilities[key] = value
        
        # Parse level requirements
        level_by_rank = {}
        if "level" in data:
            level_by_rank[1] = data["level"]
        if "prerequisites_by_rank" in data:
            for rank_str, req in data["prerequisites_by_rank"].items():
                level_by_rank[int(rank_str)] = req.get("level", 0)
        
        return cls(
            abilities=abilities,
            prereq_type=prereq_type,
            level_by_rank=level_by_rank,
            required_talents=data.get("required_talents", []),
            is_capstone=data.get("all_path_talents", False),
        )
    
    def check(
        self, 
        ability_scores: Dict[str, Any], 
        level: int = 1,
        current_talents: Dict[str, int] = None,
        target_rank: int = 1
    ) -> tuple[bool, List[str]]:
        """
        Check if prerequisites are met.
        
        Returns:
            Tuple of (meets_prereqs, list of failure reasons)
        """
        failures = []
        current_talents = current_talents or {}
        
        # Check ability requirements
        if self.abilities:
            if self.prereq_type == "or":
                # Need to meet at least one
                meets_any = False
                for ability, minimum in self.abilities.items():
                    score = self._get_score(ability_scores, ability)
                    if score >= minimum:
                        meets_any = True
                        break
                if not meets_any:
                    failures.append(
                        f"Need {minimum}+ in one of: {', '.join(self.abilities.keys())}"
                    )
            else:
                # Need to meet all
                for ability, minimum in self.abilities.items():
                    score = self._get_score(ability_scores, ability)
                    if score < minimum:
                        failures.append(f"Need {ability} {minimum}+, have {score}")
        
        # Check level requirement for target rank
        if target_rank in self.level_by_rank:
            required_level = self.level_by_rank[target_rank]
            if level < required_level:
                failures.append(f"Rank {target_rank} requires level {required_level}")
        
        # Check required talents
        for talent_id in self.required_talents:
            if talent_id not in current_talents:
                failures.append(f"Requires talent: {talent_id}")
        
        return (len(failures) == 0, failures)
    
    def _get_score(self, ability_scores: Dict[str, Any], ability: str) -> int:
        """Get ability score total from various formats."""
        if ability not in ability_scores:
            return 0
        
        val = ability_scores[ability]
        if isinstance(val, dict):
            return val.get("total", val.get("roll", 0))
        elif hasattr(val, "total"):
            return val.total
        elif isinstance(val, int):
            return val
        return 0


@dataclass
class Talent:
    """
    Represents a talent that characters can acquire.
    
    Talents have multiple ranks, each providing increasing benefits.
    """
    id: str
    name: str
    description: str
    max_rank: int
    
    # Rank descriptions (rank number -> description)
    ranks: Dict[int, str] = field(default_factory=dict)
    
    # Prerequisites
    prerequisites: Optional[TalentPrerequisites] = None
    
    # Category
    category: str = "general"  # "general" or "path"
    path_id: str = ""          # If path talent, which path
    is_primary: bool = False   # Is this the main scaling talent for a path?
    is_capstone: bool = False  # Is this a capstone talent?
    
    # Special requirements
    requires_choice: bool = False
    choice_type: str = ""       # e.g., "fighting_style", "creature_types"
    choice_options: List[str] = field(default_factory=list)
    
    # Weapon/armor requirements
    weapon_requirement: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], category: str = "general", path_id: str = "") -> "Talent":
        """Create a Talent from a dictionary."""
        # Parse prerequisites
        prereqs = None
        if "prerequisites" in data and data["prerequisites"]:
            prereqs = TalentPrerequisites.from_dict(data["prerequisites"])
        
        # Parse ranks - convert string keys to int
        ranks = {}
        if "ranks" in data:
            for rank_key, desc in data["ranks"].items():
                ranks[int(rank_key)] = desc
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            max_rank=data.get("max_rank", 3),
            ranks=ranks,
            prerequisites=prereqs,
            category=category,
            path_id=path_id,
            is_primary=data.get("is_primary", False),
            is_capstone=data.get("is_capstone", False),
            requires_choice=data.get("requires_choice", False),
            choice_type=data.get("choice_type", ""),
            choice_options=data.get("choice_options", []),
            weapon_requirement=data.get("weapon_requirement", ""),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "max_rank": self.max_rank,
            "ranks": {str(k): v for k, v in self.ranks.items()},
        }
        
        if self.prerequisites:
            result["prerequisites"] = {
                "abilities": self.prerequisites.abilities,
                "prereq_type": self.prerequisites.prereq_type,
            }
        
        if self.is_primary:
            result["is_primary"] = True
        if self.is_capstone:
            result["is_capstone"] = True
        if self.requires_choice:
            result["requires_choice"] = True
            result["choice_type"] = self.choice_type
            result["choice_options"] = self.choice_options
        if self.weapon_requirement:
            result["weapon_requirement"] = self.weapon_requirement
        
        return result
    
    def get_rank_description(self, rank: int) -> str:
        """Get the description for a specific rank."""
        if rank in self.ranks:
            return self.ranks[rank]
        return ""
    
    def get_cumulative_description(self, up_to_rank: int) -> str:
        """Get all rank descriptions up to and including the specified rank."""
        descriptions = []
        for r in range(1, up_to_rank + 1):
            if r in self.ranks:
                descriptions.append(f"Rank {r}: {self.ranks[r]}")
        return "\n".join(descriptions)
    
    def can_acquire(
        self, 
        ability_scores: Dict[str, Any],
        level: int = 1,
        current_talents: Dict[str, int] = None,
        target_rank: int = 1
    ) -> tuple[bool, List[str]]:
        """
        Check if a character can acquire this talent at the specified rank.
        
        Returns:
            Tuple of (can_acquire, list of reasons if not)
        """
        failures = []
        current_talents = current_talents or {}
        
        # Check if already at max rank
        current_rank = current_talents.get(self.id, 0)
        if target_rank > self.max_rank:
            failures.append(f"Max rank is {self.max_rank}")
        
        if target_rank <= current_rank:
            failures.append(f"Already at rank {current_rank}")
        
        # Check prerequisites
        if self.prerequisites:
            meets, prereq_failures = self.prerequisites.check(
                ability_scores, level, current_talents, target_rank
            )
            if not meets:
                failures.extend(prereq_failures)
        
        return (len(failures) == 0, failures)
    
    def get_tp_cost(self, from_rank: int, to_rank: int) -> int:
        """
        Calculate TP cost to advance from one rank to another.
        
        Each rank costs TP equal to that rank number.
        """
        if to_rank <= from_rank:
            return 0
        
        total = 0
        for r in range(from_rank + 1, to_rank + 1):
            total += r
        return total


@dataclass
class TalentCategory:
    """A collection of talents (general or for a specific path)."""
    category: str  # "general" or path name
    path_id: str = ""
    path_name: str = ""
    description: str = ""
    talents: List[Talent] = field(default_factory=list)
    
    def get_talent(self, talent_id: str) -> Optional[Talent]:
        """Get a talent by ID."""
        for t in self.talents:
            if t.id == talent_id:
                return t
        return None
    
    def get_primary_talent(self) -> Optional[Talent]:
        """Get the primary scaling talent (for path categories)."""
        for t in self.talents:
            if t.is_primary:
                return t
        return None
    
    def get_capstone(self) -> Optional[Talent]:
        """Get the capstone talent (for path categories)."""
        for t in self.talents:
            if t.is_capstone:
                return t
        return None


def load_talent_category(filepath: str) -> TalentCategory:
    """Load a talent category from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    category = data.get("category", "general")
    path_id = data.get("path_id", "")
    path_name = data.get("path_name", "")
    description = data.get("description", "")
    
    talents = []
    for talent_data in data.get("talents", []):
        talents.append(Talent.from_dict(talent_data, category, path_id))
    
    return TalentCategory(
        category=category,
        path_id=path_id,
        path_name=path_name,
        description=description,
        talents=talents,
    )


def load_all_talents(directory: str) -> Dict[str, TalentCategory]:
    """
    Load all talent categories from a directory.
    
    Returns dict mapping category name to TalentCategory.
    """
    categories = {}
    dir_path = Path(directory)
    
    if not dir_path.exists():
        return categories
    
    for filepath in dir_path.glob("*.json"):
        try:
            cat = load_talent_category(str(filepath))
            key = cat.path_id if cat.path_id else cat.category
            categories[key] = cat
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    
    return categories


def get_all_talents_flat(categories: Dict[str, TalentCategory]) -> Dict[str, Talent]:
    """Get all talents as a flat dictionary by ID."""
    talents = {}
    for cat in categories.values():
        for t in cat.talents:
            talents[t.id] = t
    return talents
