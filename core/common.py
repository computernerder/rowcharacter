"""
Common dataclasses used across all character creation layers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class Feature:
    """A narrative ability with name and description text."""
    name: str
    description: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Feature":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description}


@dataclass
class SkillBonus:
    """A bonus to a specific skill."""
    skill: str  # Skill name
    bonus: int
    advantage: bool = False  # Some features grant advantage

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillBonus":
        return cls(
            skill=data.get("skill", ""),
            bonus=data.get("bonus", 0),
            advantage=data.get("advantage", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill": self.skill,
            "bonus": self.bonus,
            "advantage": self.advantage,
        }


@dataclass
class ReputationModifier:
    """Regional reputation modifier."""
    region: str
    value: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReputationModifier":
        return cls(
            region=data.get("region", ""),
            value=data.get("value", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"region": self.region, "value": self.value}
