


from dataclasses import dataclass
from typing import Dict, List, Callable

from main import Player



@dataclass
class Race:
    name: str
    description: str

    base_languages: List[str]
    attribute_modifiers: Dict[str, int]
    speed: int

    special_abilities: List[str]



    def apply(self, player: Player):
        for lang in self.base_languages:
            player.languages.add(lang)

        player.speed = self.speed

        for attr, bonus in self.attribute_modifiers.items():
            player.attributes[attr] += bonus
