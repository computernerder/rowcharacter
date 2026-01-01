


from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Callable, TYPE_CHECKING





@dataclass
class Race:
    name: str
    description: str

    base_languages: List[str]
    attribute_modifiers: Dict[str, int]
    speed: int

    special_abilities: List[str]

    if TYPE_CHECKING:
        from main import Player

    def apply(self, player: Player):
        for lang in self.base_languages:
            player.languages.add(lang)

        player.speed = self.speed

        for attr, bonus in self.attribute_modifiers.items():
            player.attributes[attr] += bonus
