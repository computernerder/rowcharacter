from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any

from ROW_constants import (
    Attribute,
    Skill,
    Path,
    Race,
    Profession,
    Background,
    Alignment as AlignmentEnum,
    Reputation as ReputationEnum,
    Size,
)


def _normalize_key(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


_ATTRIBUTE_LOOKUP = {_normalize_key(attr.value): attr for attr in Attribute}


def _parse_attribute(name: str) -> Attribute | None:
    return _ATTRIBUTE_LOOKUP.get(_normalize_key(name))


def _attribute_key(attr: Attribute | str) -> str:
    return attr.value if isinstance(attr, Attribute) else str(attr)


_SKILL_LOOKUP = {_normalize_key(skill.value): skill for skill in Skill}
_SKILL_ALIASES = {
    "sleightofhand": Skill.SLEIGHT_OF_HAND,
    "slightofhand": Skill.SLEIGHT_OF_HAND,  # handle misspelling
    "deception": Skill.DECEPTION,           # handle spelling vs enum value
}


def _parse_skill(name: str) -> Skill | None:
    norm = _normalize_key(name)
    return _SKILL_ALIASES.get(norm) or _SKILL_LOOKUP.get(norm)


def _skill_key(skill: Skill | str) -> str:
    if isinstance(skill, Skill):
        if skill is Skill.SLEIGHT_OF_HAND:
            return "Sleight of Hand"
        if skill is Skill.DECEPTION:
            return "Deception"
        return skill.value
    return str(skill)


def _parse_enum(value: str, lookup: Dict[str, Any]) -> Any | None:
    return lookup.get(_normalize_key(value)) if isinstance(value, str) else None


_PATH_LOOKUP = {_normalize_key(p.value): p for p in Path}
_RACE_LOOKUP = {_normalize_key(r.value): r for r in Race}
_PROF_LOOKUP = {_normalize_key(p.value): p for p in Profession}
_BACKGROUND_LOOKUP = {_normalize_key(b.value): b for b in Background}
_SIZE_LOOKUP = {_normalize_key(s.value): s for s in Size}
_ALIGN_LOOKUP = {_normalize_key(a.value): a for a in AlignmentEnum}
_REPUTE_LOOKUP = {_normalize_key(r.value): r for r in ReputationEnum}


# --- Leaf models ---

@dataclass
class AbilityScore:
    mod: int = 0
    saving_throw: int = 0
    total: int = 10
    roll: int = 10
    race: int = 0
    misc: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AbilityScore":
        return cls(
            mod=data.get("mod", 0),
            saving_throw=data.get("saving_throw", 0),
            total=data.get("total", 10),
            roll=data.get("roll", 10),
            race=data.get("race", 0),
            misc=data.get("misc", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mod": self.mod,
            "saving_throw": self.saving_throw,
            "total": self.total,
            "roll": self.roll,
            "race": self.race,
            "misc": self.misc,
        }


@dataclass
class Defense:
    base: int = 9
    agility: int = 0
    shield: str | int = ""
    misc: int = 0
    total: str | int = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Defense":
        return cls(
            base=data.get("base", 9),
            agility=data.get("agility", 0),
            shield=data.get("shield", ""),
            misc=data.get("misc", 0),
            total=data.get("total", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base": self.base,
            "agility": self.agility,
            "shield": self.shield,
            "misc": self.misc,
            "total": self.total,
        }


@dataclass
class Resource:
    max: int = 0
    current: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Resource":
        return cls(max=data.get("max", 0), current=data.get("current", 0))

    def to_dict(self) -> Dict[str, Any]:
        return {"max": self.max, "current": self.current}


@dataclass
class Health:
    max: int = 0
    current: int = 0
    wounds: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Health":
        return cls(
            max=data.get("max", 0),
            current=data.get("current", 0),
            wounds=data.get("wounds", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"max": self.max, "current": self.current, "wounds": self.wounds}


@dataclass
class PassiveStat:
    base: int = 10
    skill: int = 0
    misc: int = 0
    total: int = 10

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PassiveStat":
        return cls(
            base=data.get("base", 10),
            skill=data.get("skill", 0),
            misc=data.get("misc", 0),
            total=data.get("total", 10),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base": self.base,
            "skill": self.skill,
            "misc": self.misc,
            "total": self.total,
        }


@dataclass
class AttackMod:
    attr: int = 0
    misc: int = 0
    total: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AttackMod":
        return cls(
            attr=data.get("attr", 0),
            misc=data.get("misc", 0),
            total=data.get("total", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"attr": self.attr, "misc": self.misc, "total": self.total}


@dataclass
class SkillEntry:
    trained: bool = False
    mod: int = 0
    rank: int = 0
    misc: int = 0
    total: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillEntry":
        return cls(
            trained=data.get("trained", False),
            mod=data.get("mod", 0),
            rank=data.get("rank", 0),
            misc=data.get("misc", 0),
            total=data.get("total", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trained": self.trained,
            "mod": self.mod,
            "rank": self.rank,
            "misc": self.misc,
            "total": self.total,
        }


@dataclass
class Attack:
    attack_action: str = ""
    bonus: int = 0
    damage: str = ""
    type: str = ""
    range: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Attack":
        return cls(
            attack_action=data.get("attack_action", ""),
            bonus=data.get("bonus", 0),
            damage=data.get("damage", ""),
            type=data.get("type", ""),
            range=data.get("range", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attack_action": self.attack_action,
            "bonus": self.bonus,
            "damage": self.damage,
            "type": self.type,
            "range": self.range,
        }


@dataclass
class Talent:
    # New format (rulebook-accurate + stable references)
    talent_id: str = ""
    name: str = ""
    rank: int = 1
    path_id: str = ""  # e.g. "general", "defense", "martial"
    choice_data: Dict[str, Any] = field(default_factory=dict)

    # Legacy display text (kept for backwards compatibility)
    text: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Talent":
        # Backwards-compatible loader:
        # - old: {"name": "Rage", "text": "..."}
        # - new: {"talent_id": "rage", "name": "Rage", "rank": 2, "path_id": "martial", "choice_data": {...}}
        talent_id = data.get("talent_id") or data.get("id") or ""
        name = data.get("name", "")
        rank = data.get("rank", 1)
        path_id = data.get("path_id") or data.get("path") or ""
        choice_data = data.get("choice_data") or data.get("choice") or {}
        text = data.get("text", "")

        # If this is a legacy entry that lacks rank, treat as rank 1.
        try:
            rank = int(rank)
        except Exception:
            rank = 1

        return cls(
            talent_id=str(talent_id),
            name=str(name),
            rank=rank,
            path_id=str(path_id),
            choice_data=dict(choice_data) if isinstance(choice_data, dict) else {},
            text=str(text),
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "talent_id": self.talent_id,
            "name": self.name,
            "rank": self.rank,
            "path_id": self.path_id,
            "choice_data": self.choice_data,
        }

        # Keep legacy keys for older consumers
        if self.path_id:
            result["path"] = self.path_id
        if self.text:
            result["text"] = self.text

        return result


@dataclass
class Feature:
    name: str = ""
    text: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Feature":
        return cls(name=data.get("name", ""), text=data.get("text", ""))

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "text": self.text}


@dataclass
class Spell:
    name: str = ""
    cp: int = 0
    details: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Spell":
        return cls(name=data.get("name", ""), cp=data.get("cp", 0), details=data.get("details", ""))

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "cp": self.cp, "details": self.details}


@dataclass
class Spellcrafting:
    save_dc: int = 0
    attack_bonus: int = 0
    crafting_points_max: int = 0
    casting: str = ""
    spells: List[Spell] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Spellcrafting":
        return cls(
            save_dc=data.get("save_dc", 0),
            attack_bonus=data.get("attack_bonus", 0),
            crafting_points_max=data.get("crafting_points", {}).get("max", 0),
            casting=data.get("casting", ""),
            spells=[Spell.from_dict(s) for s in data.get("spells", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "save_dc": self.save_dc,
            "attack_bonus": self.attack_bonus,
            "crafting_points": {"max": self.crafting_points_max},
            "casting": self.casting,
            "spells": [s.to_dict() for s in self.spells],
        }


@dataclass
class Inventory:
    items: List[str] = field(default_factory=list)
    total_weight: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Inventory":
        return cls(items=list(data.get("items", [])), total_weight=data.get("total_weight", ""))

    def to_dict(self) -> Dict[str, Any]:
        return {"items": self.items, "total_weight": self.total_weight}


@dataclass
class PhysicalTraits:
    height: str = ""
    weight: str = ""
    size: Size | str = ""
    age: str = ""
    creature_type: str = ""
    eyes: str = ""
    skin: str = ""
    hair: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhysicalTraits":
        size_raw = data.get("size", "")
        size_enum = _parse_enum(size_raw, _SIZE_LOOKUP) if isinstance(size_raw, str) else None
        return cls(
            height=data.get("height", ""),
            weight=data.get("weight", ""),
            size=size_enum or size_raw,
            age=data.get("age", ""),
            creature_type=data.get("creature_type", ""),
            eyes=data.get("eyes", ""),
            skin=data.get("skin", ""),
            hair=data.get("hair", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        size_val = self.size.value if isinstance(self.size, Size) else self.size
        return {
            "height": self.height,
            "weight": self.weight,
            "size": size_val,
            "age": self.age,
            "creature_type": self.creature_type,
            "eyes": self.eyes,
            "skin": self.skin,
            "hair": self.hair,
        }


@dataclass
class Personality:
    traits: str = ""
    ideal: str = ""
    bond: str = ""
    flaw: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Personality":
        return cls(
            traits=data.get("traits", ""),
            ideal=data.get("ideal", ""),
            bond=data.get("bond", ""),
            flaw=data.get("flaw", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "traits": self.traits,
            "ideal": self.ideal,
            "bond": self.bond,
            "flaw": self.flaw,
        }


@dataclass
class Alignment:
    alignment: AlignmentEnum | str = ""
    mod: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alignment":
        raw = data.get("alignment", "")
        enum_val = _parse_enum(raw, _ALIGN_LOOKUP) if isinstance(raw, str) else None
        return cls(alignment=enum_val or raw, mod=data.get("mod", 0))

    def to_dict(self) -> Dict[str, Any]:
        align_val = self.alignment.value if isinstance(self.alignment, AlignmentEnum) else self.alignment
        return {"alignment": align_val, "mod": self.mod}


@dataclass
class Reputation:
    reputation: ReputationEnum | str = ""
    mod: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Reputation":
        raw = data.get("reputation", "")
        enum_val = _parse_enum(raw, _REPUTE_LOOKUP) if isinstance(raw, str) else None
        return cls(reputation=enum_val or raw, mod=data.get("mod", 0))

    def to_dict(self) -> Dict[str, Any]:
        rep_val = self.reputation.value if isinstance(self.reputation, ReputationEnum) else self.reputation
        return {"reputation": rep_val, "mod": self.mod}


@dataclass
class Footer:
    datecode: str = ""
    config: str = ""
    id: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Footer":
        return cls(
            datecode=data.get("datecode", ""),
            config=data.get("config", ""),
            id=data.get("id", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"datecode": self.datecode, "config": self.config, "id": self.id}


# --- Root model ---

@dataclass
class CharacterTemplate:
    id: str = ""
    character_name: str = ""
    player: str = ""
    profession: Profession | str = ""
    primary_path: Path | str | None = None
    race: Race | str = ""
    ancestry: str = ""
    background: Background | str = ""

    level: int = 1
    total_experience: int = 0
    stored_advance: str = ""

    ability_scores: Dict[Attribute | str, AbilityScore] = field(default_factory=dict)
    defense: Defense = field(default_factory=Defense)
    speed: int = 0
    initiative: int = 0

    health: Health = field(default_factory=Health)
    armor_hp: Resource = field(default_factory=Resource)
    life_points: Resource = field(default_factory=Resource)
    focus: Resource = field(default_factory=Resource)

    passive_perception: PassiveStat = field(default_factory=PassiveStat)
    passive_insight: PassiveStat = field(default_factory=PassiveStat)

    attack_mods_melee: AttackMod = field(default_factory=AttackMod)
    attack_mods_ranged: AttackMod = field(default_factory=AttackMod)

    skills: Dict[Skill | str, SkillEntry] = field(default_factory=dict)

    proficiencies: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)

    attacks: List[Attack] = field(default_factory=list)
    talents: List[Talent] = field(default_factory=list)
    features: List[Feature] = field(default_factory=list)

    spellcrafting: Spellcrafting = field(default_factory=Spellcrafting)
    inventory: Inventory = field(default_factory=Inventory)

    notes: str = ""
    physical_traits: PhysicalTraits = field(default_factory=PhysicalTraits)
    personality: Personality = field(default_factory=Personality)
    alignment: Alignment = field(default_factory=Alignment)
    reputation: Reputation = field(default_factory=Reputation)

    qr_payload: str = ""
    footer: Footer = field(default_factory=Footer)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterTemplate":
        abilities: Dict[Attribute | str, AbilityScore] = {}
        for name, entry in data.get("ability_scores", {}).items():
            key = _parse_attribute(name) or name
            abilities[key] = AbilityScore.from_dict(entry)

        skills: Dict[Skill | str, SkillEntry] = {}
        for name, entry in data.get("skills", {}).items():
            key = _parse_skill(name) or name
            skills[key] = SkillEntry.from_dict(entry)

        attacks = [Attack.from_dict(a) for a in data.get("attacks", [])]
        talents = [Talent.from_dict(t) for t in data.get("talents", [])]
        features = [Feature.from_dict(f) for f in data.get("features", [])]

        passive = data.get("passive", {})
        attack_mods = data.get("attack_mods", {})

        primary_raw = data.get("primary_path")
        primary_enum = _parse_enum(primary_raw, _PATH_LOOKUP) if isinstance(primary_raw, str) else None

        race_raw = data.get("race", "")
        race_enum = _parse_enum(race_raw, _RACE_LOOKUP) if isinstance(race_raw, str) else None

        prof_raw = data.get("profession", "")
        prof_enum = _parse_enum(prof_raw, _PROF_LOOKUP) if isinstance(prof_raw, str) else None

        background_raw = data.get("background", "")
        background_enum = _parse_enum(background_raw, _BACKGROUND_LOOKUP) if isinstance(background_raw, str) else None

        return cls(
            id=data.get("id", ""),
            character_name=data.get("character_name", ""),
            player=data.get("player", ""),
            profession=prof_enum or prof_raw,
            primary_path=primary_enum or primary_raw,
            race=race_enum or race_raw,
            ancestry=data.get("ancestry", ""),
            background=background_enum or background_raw,
            level=data.get("level", 1),
            total_experience=data.get("total_experience", 0),
            stored_advance=data.get("stored_advance", ""),
            ability_scores=abilities,
            defense=Defense.from_dict(data.get("defense", {})),
            speed=data.get("speed", 0),
            initiative=data.get("initiative", 0),
            health=Health.from_dict(data.get("health", {})),
            armor_hp=Resource.from_dict(data.get("armor_hp", {})),
            life_points=Resource.from_dict(data.get("life_points", {})),
            focus=Resource.from_dict(data.get("focus", {})),
            passive_perception=PassiveStat.from_dict(passive.get("perception", {})),
            passive_insight=PassiveStat.from_dict(passive.get("insight", {})),
            attack_mods_melee=AttackMod.from_dict(attack_mods.get("melee", {})),
            attack_mods_ranged=AttackMod.from_dict(attack_mods.get("ranged", {})),
            skills=skills,
            proficiencies=list(data.get("proficiencies", [])),
            languages=list(data.get("languages", [])),
            attacks=attacks,
            talents=talents,
            features=features,
            spellcrafting=Spellcrafting.from_dict(data.get("spellcrafting", {})),
            inventory=Inventory.from_dict(data.get("inventory", {})),
            notes=data.get("notes", ""),
            physical_traits=PhysicalTraits.from_dict(data.get("physical_traits", {})),
            personality=Personality.from_dict(data.get("personality", {})),
            alignment=Alignment.from_dict(data.get("alignment", {})),
            reputation=Reputation.from_dict(data.get("reputation", {})),
            qr_payload=data.get("qr_payload", ""),
            footer=Footer.from_dict(data.get("footer", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "character_name": self.character_name,
            "player": self.player,
            "profession": self.profession.value if isinstance(self.profession, Profession) else self.profession,
            "primary_path": self.primary_path.value if isinstance(self.primary_path, Path) else self.primary_path,
            "race": self.race.value if isinstance(self.race, Race) else self.race,
            "ancestry": self.ancestry,
            "background": self.background.value if isinstance(self.background, Background) else self.background,
            "level": self.level,
            "total_experience": self.total_experience,
            "stored_advance": self.stored_advance,
            "ability_scores": { _attribute_key(k): v.to_dict() for k, v in self.ability_scores.items() },
            "defense": self.defense.to_dict(),
            "speed": self.speed,
            "initiative": self.initiative,
            "health": self.health.to_dict(),
            "armor_hp": self.armor_hp.to_dict(),
            "life_points": self.life_points.to_dict(),
            "focus": self.focus.to_dict(),
            "passive": {
                "perception": self.passive_perception.to_dict(),
                "insight": self.passive_insight.to_dict(),
            },
            "attack_mods": {
                "melee": self.attack_mods_melee.to_dict(),
                "ranged": self.attack_mods_ranged.to_dict(),
            },
            "skills": { _skill_key(k): v.to_dict() for k, v in self.skills.items() },
            "proficiencies": list(self.proficiencies),
            "languages": list(self.languages),
            "attacks": [a if isinstance(a, dict) else a.to_dict() for a in self.attacks],
            "talents": [t if isinstance(t, dict) else t.to_dict() for t in self.talents],
            "features": [f if isinstance(f, dict) else f.to_dict() for f in self.features],
            "spellcrafting": self.spellcrafting.to_dict(),
            "inventory": self.inventory.to_dict(),
            "notes": self.notes,
            "physical_traits": self.physical_traits.to_dict(),
            "personality": self.personality.to_dict(),
            "alignment": self.alignment.to_dict(),
            "reputation": self.reputation.to_dict(),
            "qr_payload": self.qr_payload,
            "footer": self.footer.to_dict(),
        }


# Convenience helpers

def load_character_template(data: Dict[str, Any]) -> CharacterTemplate:
    """Create a CharacterTemplate from a plain dict (already parsed JSON)."""
    return CharacterTemplate.from_dict(data)


def dump_character_template(character: CharacterTemplate) -> Dict[str, Any]:
    """Convert a CharacterTemplate back to a plain dict (ready for JSON serialization)."""
    return character.to_dict()
