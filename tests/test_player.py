from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import Player


def test_attribute_modifier():
    player = Player("TestHero")
    assert player.return_attribute_modifier(1) == -5
    assert player.return_attribute_modifier(10) == 0
    assert player.return_attribute_modifier(11) == 0
    assert player.return_attribute_modifier(12) == 1
    assert player.return_attribute_modifier(13) == 1
    assert player.return_attribute_modifier(14) == 2
    assert player.return_attribute_modifier(15) == 2
    assert player.return_attribute_modifier(20) == 5
    assert player.return_attribute_modifier(21) == 5
    assert player.return_attribute_modifier(22) == 6
    assert player.return_attribute_modifier(23) == 6
    assert player.return_attribute_modifier(25) == 7
    assert player.return_attribute_modifier(30) == 10
    assert player.return_attribute_modifier(31) == 10
    