#Constants for Relm of Warriors game

from enum import Enum


DEFENSE_BASE = 9


class Attribute(str, Enum):
    MIGHT = "Might"
    AGILITY = "Agility"
    ENDURANCE = "Endurance"
    WISDOM = "Wisdom"
    INTELLECT = "Intellect"
    CHARISMA = "Charisma"

    


class Skill(str, Enum):
    ACROBATICS = "Acrobatics"
    ANIMAL_HANDLING = "Animal Handling"
    APPRAISAL = "Appraisal"
    ARCANA = "Arcana"
    ATHLETICS = "Athletics"
    CRAFTING = "Crafting"
    DECEPTION = "Desception"
    DIPLOMACY = "Diplomacy"
    HISTORY = "History"
    INSIGHT = "Insight"
    INTIMIDATION = "Intimidation"
    INVESTIGATION = "Investigation"
    MEDICINE = "Medicine"
    NATURE = "Nature"
    PERCEPTION = "Perception"
    PERFORMANCE = "Performance"
    PERSUASION = "Persuasion"
    RELIGION = "Religion"
    SLEIGHT_OF_HAND = "Slight of Hand"
    STEALTH = "Stealth"
    STREETWISE = "Streetwise"
    SURVIVAL = "Survival"
    TAMING = "Taming"


    @property
    def attribute(self) -> Attribute:
        return {
            Skill.ACROBATICS: Attribute.AGILITY,
            Skill.SLEIGHT_OF_HAND: Attribute.AGILITY,
            Skill.STEALTH: Attribute.AGILITY,

            Skill.ATHLETICS: Attribute.MIGHT,

            Skill.APPRAISAL: Attribute.INTELLECT,
            Skill.ARCANA: Attribute.INTELLECT,
            Skill.CRAFTING: Attribute.INTELLECT,
            Skill.HISTORY: Attribute.INTELLECT,
            Skill.INSIGHT: Attribute.INTELLECT,
            Skill.INVESTIGATION: Attribute.INTELLECT,
            Skill.MEDICINE: Attribute.INTELLECT,
            Skill.NATURE: Attribute.INTELLECT,
            Skill.RELIGION: Attribute.INTELLECT,
            Skill.STREETWISE: Attribute.INTELLECT,

            Skill.ANIMAL_HANDLING: Attribute.WISDOM,
            Skill.PERCEPTION: Attribute.WISDOM,
            Skill.SURVIVAL: Attribute.WISDOM,
            Skill.TAMING: Attribute.WISDOM,

            Skill.DECEPTION: Attribute.CHARISMA,
            Skill.DIPLOMACY: Attribute.CHARISMA,
            Skill.INTIMIDATION: Attribute.CHARISMA,
            Skill.PERFORMANCE: Attribute.CHARISMA,
            Skill.PERSUASION: Attribute.CHARISMA,

        } [self]
    


class Path(Enum):
    DEFENSE = "Defense"
    DIVINE = "Divine"
    EXPLOITATION = "Exploitation"
    MARTIAL = "Martial"
    MYSTIC = "Mystic"
    POWER = "Power"
    SURVIVAL = "Survival"

    @property
    def attributes(self) -> list[Attribute]:
        return {
            Path.DEFENSE: [Attribute.ENDURANCE, Attribute.WISDOM],
            Path.DIVINE: [Attribute.WISDOM, Attribute.CHARISMA],
            Path.EXPLOITATION: [Attribute.AGILITY, Attribute.INTELLECT],
            Path.MARTIAL: [Attribute.MIGHT, Attribute.WISDOM],
            Path.MYSTIC: [Attribute.INTELLECT, Attribute.WISDOM],
            Path.POWER: [Attribute.MIGHT, Attribute.ENDURANCE],
            Path.SURVIVAL: [Attribute.WISDOM, Attribute.AGILITY],
        }[self]



class Race(str, Enum):
    HUMAN = "human"
    ELF = "elf"
    DWARF = "dwarf"
    HALFFOLK = "halffolk"
    GOBLIN = "goblin"
    SIMARI = "simari"
    VELKARR = "velkarr"
    TAURIN = "taurin"

class Profession(str, Enum):
    WARRIOR = "warrior"
    CRIMINAL = "criminal"
    PRIEST = "priest"
    BLACKSMITH = "blacksmith"
    LEATHERWORKER = "leatherworker"
    ARTISAN = "artisan"
    WARDENOFTHEWILD = "warden of the wild"
    SCHOLAR = "scholar"
    FREEAGENT = "free agent"

class Role(str, Enum):
    STRIKER = "striker"
    DEFENDER = "defender"
    HEALER = "healer"
    SPECIALIST = "specialist"
    INFLUENCER = "influencer"

class Alignment(str, Enum):
    ENLIGHTENED = "enlightened"
    RIGHTEOUS = "righteous"
    GOOD = "good"
    NEUTRAL_GOOD = "neutral good"
    TRUE_NEUTRAL = "true neutral"
    NEUTRAL_BAD = "neutral bad"
    BAD = "bad"
    EVIL = "evil"
    VILE = "vile" 

    @property
    def threshold(self) -> int:
        return {
            Alignment.ENLIGHTENED: 12,
            Alignment.RIGHTEOUS: 9,
            Alignment.GOOD: 6,
            Alignment.NEUTRAL_GOOD: 3,
            Alignment.TRUE_NEUTRAL: -2,
            Alignment.NEUTRAL_BAD: -5,
            Alignment.BAD: -8,
            Alignment.EVIL: -11,
            Alignment.VILE: None,
        }[self]


class Reputation(str, Enum):
    FAMOUS = "famous"
    RENOWNED = "renowned"
    RESPECTED = "respected"
    UNKNOWN = "unknown"
    NOTORIOUS = "notorious"
    INFAMOUS = "infamous"
    REVEALED = "revealed"

    @property
    def threshold(self) -> int:
        return {
            Reputation.FAMOUS: 9,
            Reputation.RENOWNED: 6,
            Reputation.RESPECTED: 3,
            Reputation.UNKNOWN: -2,
            Reputation.NOTORIOUS: -5,
            Reputation.INFAMOUS: -8,
            Reputation.REVEALED: None,
        }[self]

class Talent(str, Enum):
    ALERTNESS = "Alertness"
    ARCHERYFOCUS = "Archery Focus"
    ARMORTRAINING = "Armor Training"
    ATHLETE = "Athlete"
    BOOKSMART = "Booksmart"
    COMMONSENSE = "Commonsense"
    DEFENSIVETRAINING = "Defensive Training"
    DUALWIELDING = "Dual Wielding"
    EXPERIENCED = "Experienced"
    FIGHTINGSTYLE = "Fighting Style"
    LUCKY = "Lucky"
    MOBILE = "Mobile"
    NATURALLEADER = "Natural Leader"
    OBSERVANT = "Observant"
    PERSUASIVE = "Persuasive"
    QUICKLEARNER = "Quick Learner"
    QUICKNESS = "Quickness"
    RESILIENT = "Resilient"
    RESOURCEFUL = "Resourceful"
    SKILLFOCUS = "Skill Focus"
    TINKERER = "Tinkerer"
    TOUGHNESS = "Toughness"
    WEAPONMASTERY = "Weapon Mastery"


class RollType(str, Enum):
    ROLL = "roll"
    POINT_BUY = "point_buy"
    STANDARD_ARRAY = "standard_array"

class Size(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class WeaponCategory(str, Enum):
    SIMPLE = "simple"
    MARTIAL = "martial"
    LIGHT = "light"
    FINESSE = "finesse"
    RANGED = "ranged"
    TWO_HANDED = "two-handed"
    MELEE = "melee"

class Background(str, Enum):
    DEVOTEE = "devotee"
    OUTCAST = "outcast"
    VILLAGE_CHAMPION = "village champion"
    SCHOLAR = "scholar"
    ARTISAN = "artisan"
    WANDERER = "wanderer"
    NOBLE_HEIR = "noble heir"
    MERCENARY = "mercenary"
    SEAFARER = "seafarer"
    SHADOW = "shadow"
    NOMAD = "nomad"
    SOLDIER = "soldier"


XP_THRESHOLDS = {
    1: 0,
    2: 300,
    3: 900,
    4: 3000,
    5: 7000,
    6: 13000,
    7: 22000,
    8: 34000,
    9: 49000,
    10: 67000,
    11: 88000,
    12: 112000,
    13: 139000,
    14: 169000,
    15: 202000,
    16: 238000,
    17: 277000,
    18: 317000,
    19: 358000,
    20: 400000,  # +43000 per level after 20
}


class ArmorProficiency(Enum):
    """Armor proficiency types."""
    NONE = "None"
    LIGHT = "Light"
    MEDIUM = "Medium"
    HEAVY = "Heavy"


class WeaponProficiency(Enum):
    """Weapon proficiency types."""
    SIMPLE = "Simple"
    MARTIAL = "Martial"
    LIGHT = "Light"
    FINESSE = "Finesse"
    RANGED = "Ranged"
    TWO_HANDED = "Two-Handed"
    MELEE = "Melee"


class ToolProficiency(Enum):
    """Tool proficiency types from professions, ancestries, and backgrounds."""
    # Artisan Tools (general category)
    ARTISAN_TOOL = "Artisan Tool"
    
    # Specific Artisan Tools
    SMITHING_TOOLS = "Smithing Tools"
    BLACKSMITH_TOOLS = "Blacksmith Tools"
    LEATHERWORKING_TOOLS = "Leatherworking Tools"
    LEATHERWORKER_TOOLS = "Leatherworker Tools"
    CARPENTERS_TOOLS = "Carpenter's Tools"
    JEWELERS_TOOLS = "Jeweler's Tools"
    PAINTERS_TOOLS = "Painter's Tools"
    MASONS_TOOLS = "Mason's Tools"
    ARMORERS_TOOLS = "Armorer's Tools"
    
    # Thievery/Stealth Tools
    THIEVES_TOOLS = "Thieves' Tools"
    DISGUISE_KIT = "Disguise Kit"
    
    # Survival/Nature Tools
    HERBALISM_KIT = "Herbalism Kit"
    HERBAL_KIT = "Herbal Kit"
    HUNTING_TOOLS = "Hunting Tools"
    SNARE_KIT = "Snare Kit"
    HERBAL_POUCH = "Herbal Pouch"
    
    # Navigation/Travel
    NAVIGATORS_TOOLS = "Navigator's Tools"
    
    # Gaming/Entertainment
    GAMING_SET = "Gaming Set"
    MUSICAL_INSTRUMENT = "Musical Instrument"
    
    # Military/Combat
    WHETSTONE_KIT = "Whetstone Kit"
    DRILL_SERGEANT_WHISTLE = "Drill-Sergeant Whistle"
    
    # Vehicles
    WATER_VEHICLES = "Water Vehicles"


class Language(Enum):
    """Languages available in the game."""
    # Common Languages
    COMMON = "Common"
    ELVISH = "Elvish"
    DWARVISH = "Dwarvish"
    ORCISH = "Orcish"
    GOBLIN = "Goblin"
    HALFFOLK = "Halffolk"
    
    # Exotic Languages
    DRACONIC = "Draconic"
    CELESTIAL = "Celestial"
    INFERNAL = "Infernal"
    SYLVAN = "Sylvan"
    AQUAN = "Aquan"
    
    # Racial Languages
    TAURIC = "Tauric"
    SIMARRU = "Simarru"
    VELKARRAN = "Velkarran"
    
    # Ancient/Rare Languages
    ANCIENT_DWARVISH = "Ancient Dwarvish"


class CreatureType(Enum):
    """Creature types for races."""
    HUMANOID = "Humanoid"
    HUMANOID_ELF = "Humanoid (Elf)"
    HUMANOID_DWARF = "Humanoid (Dwarf)"
    HUMANOID_HALFFOLK = "Humanoid (Halffolk)"
    HUMANOID_GOBLIN = "Humanoid (Goblin)"


class Size(Enum):
    """Size categories."""
    TINY = "Tiny"
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"
    HUGE = "Huge"
    GARGANTUAN = "Gargantuan"


class PathRole(Enum):
    """Combat/narrative roles for paths."""
    DEFENDER = "Defender"
    STRIKER = "Striker"
    SUPPORT = "Support"
    SPECIALIST = "Specialist"


# Quick reference dictionaries for validation
ALL_ARMOR_PROFICIENCIES = {e.value for e in ArmorProficiency}
ALL_WEAPON_PROFICIENCIES = {e.value for e in WeaponProficiency}
ALL_TOOL_PROFICIENCIES = {e.value for e in ToolProficiency}
ALL_LANGUAGES = {e.value for e in Language}


# Advancement Point Costs
# Advancement points given  on advancement equal to their Intellect Mod
AP_COSTS = {
    "skill_rank": 1,
    "train_skill": 4, 
    "inherit_50_gold": 5, 
    "ability_boost": 7,
    "new_proficiency": 10,
    "new_language": 10,

}

def attribute_modifier(value: int) -> int:
    '''
    Returns the attribute modifier for a given attribute value.
    Args:
        value (int): The attribute value (1-30).
    Returns:
        int: The attribute modifier.

    calculation is done as follows:
    Value minus 10, divided by 2, rounded down.
    '''
    return (value - 10) // 2