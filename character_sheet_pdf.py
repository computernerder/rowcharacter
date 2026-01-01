"""
Character Sheet PDF Generator for Realm of Warriors - Version 2

Dependencies: pip install weasyprint jinja2
"""

from pathlib import Path
from typing import Union
from jinja2 import Environment, BaseLoader


class CharacterSheetPDF:
    def __init__(self, template_path: str = None, images_path: str = None):
        self.template_path = template_path
        self.images_path = images_path or "images"
        self._template = None
    
    @property
    def template(self):
        if self._template is None:
            if self.template_path:
                from jinja2 import FileSystemLoader
                template_dir = Path(self.template_path).parent
                template_name = Path(self.template_path).name
                env = Environment(loader=FileSystemLoader(str(template_dir)))
                self._template = env.get_template(template_name)
            else:
                env = Environment(loader=BaseLoader())
                self._template = env.from_string(DEFAULT_TEMPLATE)
        return self._template
    
    def _get_blank_character(self) -> dict:
        return {
            'name': '', 'player': '', 'profession': '', 'level': '',
            'primary_path': '', 'race': '', 'alignment': '', 'background': '',
            'stored_advance': '', 'align_mod': '', 'rep_mod': '', 'experience': '',
            'stats': {stat: {'mod': '', 'save': '', 'total': '', 'roll': '', 'race': '', 'misc': ''} 
                     for stat in ['mgt', 'agl', 'end', 'int', 'wis', 'cha']},
            'passive': {
                'perception': {'skill': '', 'misc': '', 'total': ''},
                'insight': {'skill': '', 'misc': '', 'total': ''}
            },
            'combat': {'defense': '', 'defense_base': '9', 'defense_misc': '',
                      'initiative': '', 'walk_speed': '',
                      'hp_armor': '', 'hp_health': '', 'lp_max': ''},
            'attack_mods': {'melee': '', 'melee_misc': '', 'ranged': '', 'ranged_misc': ''},
            'physical': {'height': '', 'weight': '', 'size': '', 'age': '',
                        'creature_type': '', 'eyes': '', 'skin': '', 'hair': ''},
            'proficiencies': [], 'languages': [],
            'skills': [
                {"name": "Acrobatics", "attr": "AGL", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Animal Handling", "attr": "WIS", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Appraisal", "attr": "INT", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Arcana", "attr": "INT", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Athletics", "attr": "MGT", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Crafting", "attr": "INT", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Deception", "attr": "CHA", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "History", "attr": "INT", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Insight", "attr": "WIS", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Intimidation", "attr": "CHA", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Investigation", "attr": "INT", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Medicine", "attr": "WIS", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Nature", "attr": "INT", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Perception", "attr": "WIS", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Performance", "attr": "CHA", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Persuasion", "attr": "CHA", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Religion", "attr": "INT", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Sleight of Hand", "attr": "AGL", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Stealth", "attr": "AGL", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
                {"name": "Survival", "attr": "WIS", "trained": False, "mod": '', "rank": '', "misc": '', "total": ''},
            ],
            'weapons': [], 'talents': [], 'spells': [],
            'spellcrafting': {'tn_save': '', 'attack_bonus': '', 'crafting_max': '', 'casting': ''},
            'personality': {'traits': '', 'ideal': '', 'bond': '', 'flaw': ''},
            'features': '', 'backstory': '', 'equipment': '', 'notes': ''
        }
    
    def _ensure_defaults(self, data: dict) -> dict:
        defaults = self._get_blank_character()
        def merge(d, u):
            r = d.copy()
            for k, v in u.items():
                if k in r and isinstance(r[k], dict) and isinstance(v, dict):
                    r[k] = merge(r[k], v)
                else:
                    r[k] = v
            return r
        return merge(defaults, data)
    
    def render_html(self, character_data: dict) -> str:
        data = self._ensure_defaults(character_data)
        return self.template.render(character=data, images_path=self.images_path)
    
    def generate(self, character_data: dict, base_url: str = None) -> bytes:
        from weasyprint import HTML
        html_content = self.render_html(character_data)
        base = base_url or str(Path.cwd())
        return HTML(string=html_content, base_url=base).write_pdf()
    
    def generate_to_file(self, character_data: dict, output_path: Union[str, Path], base_url: str = None) -> None:
        Path(output_path).write_bytes(self.generate(character_data, base_url))
    
    def generate_blank(self, output_path: Union[str, Path], base_url: str = None) -> None:
        self.generate_to_file(self._get_blank_character(), output_path, base_url)
    
    def save_html(self, character_data: dict, output_path: Union[str, Path]) -> None:
        Path(output_path).write_text(self.render_html(character_data), encoding="utf-8")


# Template stored in separate variable for readability
DEFAULT_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@page { size: letter; margin: 0.4in; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 9pt; line-height: 1.2; width: 7.7in; }

.page { width: 7.7in; min-height: 10.2in; padding: 0.1in; position: relative; page-break-after: always; }
.page:last-child { page-break-after: avoid; }

.corner { position: absolute; width: 60px; height: 60px; opacity: 0.7; }
.corner-tl { top: 0; left: 0; }
.corner-tr { top: 0; right: 0; transform: rotate(90deg); }
.corner-bl { bottom: 0; left: 0; transform: rotate(-90deg); }
.corner-br { bottom: 0; right: 0; transform: rotate(180deg); }

.two-column { display: table; width: 100%; table-layout: fixed; }
.two-column > .col { display: table-cell; vertical-align: top; padding: 3px; }
.col-left { width: 48%; }
.col-right { width: 52%; }

.section { border: 1.5px solid #000; padding: 4px 6px; margin-bottom: 5px; }
.section-title { font-weight: bold; font-size: 8pt; text-transform: uppercase; background: #000; color: #fff; padding: 2px 5px; margin: -4px -6px 4px -6px; }
.label { font-size: 6pt; text-transform: uppercase; color: #666; display: block; }
.value { font-size: 10pt; font-weight: bold; }
.value-lg { font-size: 14pt; font-weight: bold; }
.value-box { border: 1px solid #000; min-height: 18px; text-align: center; padding: 1px 2px; }
.value-box-lg { border: 1px solid #000; min-height: 24px; text-align: center; padding: 2px; font-size: 12pt; font-weight: bold; }
.empty-box { border: 1px solid #000; min-height: 18px; background: #fafafa; }

.header { margin-bottom: 8px; }
.logo { height: 45px; margin-bottom: 4px; }
.header-grid { display: table; width: 100%; table-layout: fixed; border-collapse: collapse; }
.header-row { display: table-row; }
.header-cell { display: table-cell; border: 1px solid #000; padding: 2px 4px; text-align: center; vertical-align: top; }
.header-cell.wide { width: 20%; }
.header-cell.narrow { width: 10%; }
.header-cell.medium { width: 15%; }

table.fixed { width: 100%; border-collapse: collapse; table-layout: fixed; }
table.fixed th, table.fixed td { border: 1px solid #000; padding: 2px 3px; text-align: center; font-size: 8pt; overflow: hidden; }
table.fixed th { background: #eee; font-size: 6pt; text-transform: uppercase; }

.stats-table .stat-name { font-weight: bold; background: #ddd; width: 40px; }
.stats-table .mod-cell { background: #f5f5f5; font-weight: bold; font-size: 10pt; width: 35px; }
.stats-table td { width: 35px; }

.combat-grid { display: table; width: 100%; table-layout: fixed; }
.combat-row { display: table-row; }
.combat-cell { display: table-cell; border: 1px solid #000; padding: 3px; text-align: center; vertical-align: top; }
.defense-breakdown { display: table; width: 100%; table-layout: fixed; margin-top: 2px; font-size: 7pt; }
.defense-breakdown > div { display: table-cell; text-align: center; border: 1px solid #ccc; padding: 1px; }

.hp-grid { display: table; width: 100%; table-layout: fixed; }
.hp-cell { display: table-cell; border: 1px solid #000; padding: 3px; text-align: center; vertical-align: top; width: 33.33%; }
.hp-inner { display: table; width: 100%; table-layout: fixed; }
.hp-inner > div { display: table-cell; text-align: center; padding: 2px; }

.skills-table { font-size: 7pt; }
.skills-table th, .skills-table td { border: 1px solid #ccc; padding: 1px 2px; }
.skills-table .skill-name { text-align: left; padding-left: 3px; width: 90px; }
.skills-table .trained-col { width: 15px; }
.skills-table .attr-col { width: 28px; }
.skills-table .num-col { width: 25px; }
.checkbox { display: inline-block; width: 10px; height: 10px; border: 1px solid #000; text-align: center; line-height: 8px; font-size: 8pt; }
.checkbox.checked::after { content: "✓"; }

.passive-grid { display: table; width: 100%; table-layout: fixed; }
.passive-stat { display: table-cell; border: 1px solid #000; padding: 3px; text-align: center; width: 50%; }
.passive-inner { display: table; width: 100%; table-layout: fixed; margin-top: 2px; }
.passive-inner > div { display: table-cell; text-align: center; font-size: 7pt; }
.passive-inner .value-box { font-size: 8pt; min-height: 16px; }

.attack-grid { display: table; width: 100%; table-layout: fixed; }
.attack-cell { display: table-cell; border: 1px solid #000; padding: 4px; text-align: center; width: 50%; }
.attack-breakdown { display: table; width: 100%; table-layout: fixed; margin-top: 3px; }
.attack-breakdown > div { display: table-cell; text-align: center; font-size: 7pt; }

.weapons-table th, .weapons-table td { font-size: 7pt; }
.weapons-table .name-col { width: 30%; }
.weapons-table .bonus-col { width: 12%; }
.weapons-table .damage-col { width: 18%; }
.weapons-table .type-col { width: 20%; }
.weapons-table .range-col { width: 20%; }

.text-area { border: 1px solid #000; padding: 4px; font-size: 8pt; white-space: pre-wrap; min-height: 50px; }
.text-area.tall { min-height: 80px; }
.text-area.short { min-height: 35px; }

.currency-grid { display: table; width: 100%; table-layout: fixed; }
.currency-cell { display: table-cell; border: 1px solid #000; padding: 3px; text-align: center; width: 20%; }
.currency-cell .label { font-weight: bold; color: #000; }

.talent-header { display: table; width: 100%; table-layout: fixed; margin-bottom: 3px; }
.talent-header > div { display: table-cell; vertical-align: middle; }
.talent-points { width: 120px; text-align: right; }
.talent-points-boxes { display: inline-block; }
.talent-points-boxes .empty-box { display: inline-block; width: 18px; height: 18px; margin-left: 2px; }

.prof-grid { display: table; width: 100%; table-layout: fixed; }
.prof-cell { display: table-cell; vertical-align: top; padding-right: 8px; }
.prof-cell:last-child { padding-right: 0; }

.traits-grid { display: table; width: 100%; table-layout: fixed; }
.traits-cell { display: table-cell; border: 1px solid #000; padding: 2px 4px; text-align: center; width: 25%; }

.personality-grid { display: table; width: 100%; table-layout: fixed; }
.personality-cell { display: table-cell; border: 1px solid #000; padding: 3px; vertical-align: top; width: 50%; }
.personality-cell .label { font-weight: bold; color: #000; border-bottom: 1px solid #ccc; margin-bottom: 2px; padding-bottom: 1px; }

.spells-header { display: table; width: 100%; table-layout: fixed; margin-bottom: 3px; }
.spells-header > div { display: table-cell; border: 1px solid #000; padding: 3px; text-align: center; }
.spells-table th, .spells-table td { font-size: 7pt; }

.mt-1 { margin-top: 4px; }
.text-left { text-align: left; }
</style>
</head>
<body>
<!-- PAGE 1 -->
<div class="page">
<img class="corner corner-tl" src="{{ images_path }}/Corner.png" alt="" onerror="this.style.display='none'">
<img class="corner corner-tr" src="{{ images_path }}/Corner.png" alt="" onerror="this.style.display='none'">
<img class="corner corner-bl" src="{{ images_path }}/Corner.png" alt="" onerror="this.style.display='none'">
<img class="corner corner-br" src="{{ images_path }}/Corner.png" alt="" onerror="this.style.display='none'">

<div class="header">
<div style="text-align: center;">
<img class="logo" src="{{ images_path }}/row_small_logo.png" alt="Realm of Warriors" onerror="this.outerHTML='<div style=font-size:18pt;font-weight:bold>Realm of Warriors</div>'">
</div>
<div class="header-grid">
<div class="header-row">
<div class="header-cell wide"><span class="label">Character Name</span><span class="value">{{ character.name }}</span></div>
<div class="header-cell medium"><span class="label">Profession</span><span class="value">{{ character.profession }}</span></div>
<div class="header-cell narrow"><span class="label">Level</span><span class="value">{{ character.level }}</span></div>
<div class="header-cell medium"><span class="label">Experience</span><span class="value">{{ character.experience }}</span></div>
<div class="header-cell narrow"><span class="label">Stored Adv.</span><span class="value">{{ character.stored_advance }}</span></div>
<div class="header-cell medium"><span class="label">Player</span><span class="value">{{ character.player }}</span></div>
</div>
<div class="header-row">
<div class="header-cell"><span class="label">Primary Path</span><span class="value">{{ character.primary_path }}</span></div>
<div class="header-cell"><span class="label">Race</span><span class="value">{{ character.race }}</span></div>
<div class="header-cell"><span class="label">Background</span><span class="value">{{ character.background }}</span></div>
<div class="header-cell"><span class="label">Alignment</span><span class="value">{{ character.alignment }}</span></div>
<div class="header-cell narrow"><span class="label">Align Mod</span><span class="value">{{ character.align_mod }}</span></div>
<div class="header-cell narrow"><span class="label">Rep Mod</span><span class="value">{{ character.rep_mod }}</span></div>
</div>
</div>
</div>

<div class="two-column">
<div class="col col-left">
<!-- ABILITY SCORES -->
<div class="section">
<div class="section-title">Ability Scores</div>
<table class="fixed stats-table">
<thead><tr><th></th><th>MOD</th><th>SAVE</th><th>TOTAL</th><th>ROLL</th><th>RACE</th><th>MISC</th></tr></thead>
<tbody>
{% for stat in ['mgt', 'agl', 'end', 'int', 'wis', 'cha'] %}
{% set s = character.stats.get(stat, {}) %}
<tr>
<td class="stat-name">{{ stat|upper }}</td>
<td class="mod-cell">{{ s.mod }}</td>
<td>{{ s.save }}</td>
<td>{{ s.total }}</td>
<td>{{ s.roll }}</td>
<td>{{ s.race }}</td>
<td>{{ s.misc }}</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>

<!-- PASSIVE STATS -->
<div class="section">
<div class="section-title">Passive Stats</div>
<div class="passive-grid">
<div class="passive-stat">
<span class="label">Perception (WIS)</span>
<span class="value-lg">{{ character.passive.perception.total }}</span>
<div class="passive-inner">
<div><span class="label">Base</span><div class="value-box">10</div></div>
<div><span class="label">Skill</span><div class="value-box">{{ character.passive.perception.skill }}</div></div>
<div><span class="label">Misc</span><div class="value-box">{{ character.passive.perception.misc }}</div></div>
<div><span class="label">Total</span><div class="value-box" style="font-weight:bold">{{ character.passive.perception.total }}</div></div>
</div>
</div>
<div class="passive-stat">
<span class="label">Insight (INT)</span>
<span class="value-lg">{{ character.passive.insight.total }}</span>
<div class="passive-inner">
<div><span class="label">Base</span><div class="value-box">10</div></div>
<div><span class="label">Skill</span><div class="value-box">{{ character.passive.insight.skill }}</div></div>
<div><span class="label">Misc</span><div class="value-box">{{ character.passive.insight.misc }}</div></div>
<div><span class="label">Total</span><div class="value-box" style="font-weight:bold">{{ character.passive.insight.total }}</div></div>
</div>
</div>
</div>
</div>

<!-- PROFICIENCIES & LANGUAGES -->
<div class="section">
<div class="section-title">Proficiencies & Languages</div>
<div class="prof-grid">
<div class="prof-cell" style="width:60%"><span class="label">Proficiencies</span><div class="text-area short">{% for p in character.proficiencies %}• {{ p }}
{% endfor %}</div></div>
<div class="prof-cell" style="width:40%"><span class="label">Languages</span><div class="text-area short">{% for l in character.languages %}• {{ l }}
{% endfor %}</div></div>
</div>
</div>

<!-- FEATURES -->
<div class="section">
<div class="section-title">Features & Traits</div>
<div class="text-area tall">{{ character.features }}</div>
</div>

<!-- TALENTS -->
<div class="section">
<div class="section-title">Talents</div>
<div class="talent-header">
<div class="text-left"><span class="label">Talent List</span></div>
<div class="talent-points"><span class="label" style="display:inline">Stored Points:</span>
<div class="talent-points-boxes">
<div class="empty-box"></div><div class="empty-box"></div><div class="empty-box"></div><div class="empty-box"></div><div class="empty-box"></div>
</div></div>
</div>
<div class="text-area short">{% for t in character.talents %}• {{ t }}
{% endfor %}</div>
</div>

<!-- CURRENCY -->
<div class="section">
<div class="section-title">Currency</div>
<div class="currency-grid">
<div class="currency-cell"><span class="label">CP</span><div class="empty-box" style="min-height:20px"></div></div>
<div class="currency-cell"><span class="label">BP</span><div class="empty-box" style="min-height:20px"></div></div>
<div class="currency-cell"><span class="label">SP</span><div class="empty-box" style="min-height:20px"></div></div>
<div class="currency-cell"><span class="label">GP</span><div class="empty-box" style="min-height:20px"></div></div>
<div class="currency-cell"><span class="label">PP</span><div class="empty-box" style="min-height:20px"></div></div>
</div>
</div>
</div>

<div class="col col-right">
<!-- COMBAT STATS -->
<div class="section">
<div class="section-title">Combat Stats</div>
<div class="combat-grid">
<div class="combat-row">
<div class="combat-cell" style="width:50%">
<span class="label">Defense</span><span class="value-lg">{{ character.combat.defense }}</span>
<div class="defense-breakdown">
<div><span class="label">Base</span><div class="value-box">{{ character.combat.defense_base or '9' }}</div></div>
<div><span class="label">AGL</span><div class="value-box">{{ character.stats.agl.mod }}</div></div>
<div><span class="label">Shield</span><div class="empty-box" style="min-height:16px"></div></div>
<div><span class="label">Misc</span><div class="value-box">{{ character.combat.defense_misc }}</div></div>
</div>
</div>
<div class="combat-cell" style="width:25%"><span class="label">Initiative</span><span class="value-lg">{{ character.combat.initiative }}</span></div>
<div class="combat-cell" style="width:25%"><span class="label">Walk Speed</span><span class="value-lg">{{ character.combat.walk_speed }}</span></div>
</div>
</div>
<div class="hp-grid mt-1">
<div class="hp-cell"><span class="label">Armor HP</span><div class="hp-inner">
<div><span class="label">Cur</span><div class="empty-box" style="min-height:22px"></div></div>
<div><span class="label">Max</span><div class="value-box-lg">{{ character.combat.hp_armor }}</div></div>
</div></div>
<div class="hp-cell"><span class="label">Health HP</span><div class="hp-inner">
<div><span class="label">Cur</span><div class="empty-box" style="min-height:22px"></div></div>
<div><span class="label">Max</span><div class="value-box-lg">{{ character.combat.hp_health }}</div></div>
</div></div>
<div class="hp-cell"><span class="label">Life Points</span><div class="hp-inner">
<div><span class="label">Cur</span><div class="empty-box" style="min-height:22px"></div></div>
<div><span class="label">Max</span><div class="value-box-lg">{{ character.combat.lp_max }}</div></div>
</div></div>
</div>
</div>

<!-- ATTACK MODIFIERS -->
<div class="section">
<div class="section-title">Attack Modifiers</div>
<div class="attack-grid">
<div class="attack-cell"><span class="label">Melee</span><span class="value-lg">{{ character.attack_mods.melee }}</span>
<div class="attack-breakdown">
<div><span class="label">MGT Mod</span><div class="value-box">{{ character.stats.mgt.mod }}</div></div>
<div><span class="label">Misc</span><div class="value-box">{{ character.attack_mods.melee_misc }}</div></div>
</div></div>
<div class="attack-cell"><span class="label">Ranged</span><span class="value-lg">{{ character.attack_mods.ranged }}</span>
<div class="attack-breakdown">
<div><span class="label">AGL Mod</span><div class="value-box">{{ character.stats.agl.mod }}</div></div>
<div><span class="label">Misc</span><div class="value-box">{{ character.attack_mods.ranged_misc }}</div></div>
</div></div>
</div>
</div>

<!-- SKILLS -->
<div class="section">
<div class="section-title">Skills</div>
<table class="fixed skills-table">
<thead><tr><th class="trained-col">T</th><th class="skill-name">Skill Name</th><th class="attr-col">Attr</th><th class="num-col">Mod</th><th class="num-col">Rank</th><th class="num-col">Misc</th><th class="num-col">Total</th></tr></thead>
<tbody>
{% for skill in character.skills %}
<tr>
<td><span class="checkbox {{ 'checked' if skill.trained else '' }}"></span></td>
<td class="skill-name">{{ skill.name }}</td>
<td>{{ skill.attr }}</td>
<td>{{ skill.mod }}</td>
<td>{{ skill.rank }}</td>
<td>{{ skill.misc }}</td>
<td>{{ skill.total }}</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>

<!-- WEAPONS -->
<div class="section">
<div class="section-title">Weapons & Attacks</div>
<table class="fixed weapons-table">
<thead><tr><th class="name-col">Attack Action</th><th class="bonus-col">Bonus</th><th class="damage-col">Damage</th><th class="type-col">Type</th><th class="range-col">Range</th></tr></thead>
<tbody>
{% for w in character.weapons %}<tr><td>{{ w.name }}</td><td>{{ w.bonus }}</td><td>{{ w.damage }}</td><td>{{ w.type }}</td><td>{{ w.range }}</td></tr>{% endfor %}
{% for i in range(character.weapons|length, 5) %}<tr><td>&nbsp;</td><td></td><td></td><td></td><td></td></tr>{% endfor %}
</tbody>
</table>
</div>
</div>
</div>
</div>

<!-- PAGE 2 -->
<div class="page">
<img class="corner corner-tl" src="{{ images_path }}/Corner.png" alt="" onerror="this.style.display='none'">
<img class="corner corner-tr" src="{{ images_path }}/Corner.png" alt="" onerror="this.style.display='none'">
<img class="corner corner-bl" src="{{ images_path }}/Corner.png" alt="" onerror="this.style.display='none'">
<img class="corner corner-br" src="{{ images_path }}/Corner.png" alt="" onerror="this.style.display='none'">

<div style="text-align:center;margin-bottom:8px;border-bottom:2px solid #000;padding-bottom:4px">
<span style="font-size:12pt;font-weight:bold">{{ character.name or 'Character Name' }}</span>
<span style="font-size:9pt;color:#666;margin-left:20px">Page 2</span>
</div>

<div class="two-column">
<div class="col col-left">
<!-- PHYSICAL TRAITS -->
<div class="section">
<div class="section-title">Physical Traits</div>
<div class="traits-grid">
<div class="traits-cell"><span class="label">Height</span><br><span class="value">{{ character.physical.height }}</span></div>
<div class="traits-cell"><span class="label">Weight</span><br><span class="value">{{ character.physical.weight }}</span></div>
<div class="traits-cell"><span class="label">Size</span><br><span class="value">{{ character.physical.size }}</span></div>
<div class="traits-cell"><span class="label">Age</span><br><span class="value">{{ character.physical.age }}</span></div>
</div>
<div class="traits-grid mt-1">
<div class="traits-cell"><span class="label">Creature Type</span><br><span class="value">{{ character.physical.creature_type }}</span></div>
<div class="traits-cell"><span class="label">Eyes</span><br><span class="value">{{ character.physical.eyes }}</span></div>
<div class="traits-cell"><span class="label">Skin</span><br><span class="value">{{ character.physical.skin }}</span></div>
<div class="traits-cell"><span class="label">Hair</span><br><span class="value">{{ character.physical.hair }}</span></div>
</div>
</div>

<!-- PERSONALITY -->
<div class="section">
<div class="section-title">Personality</div>
<div class="personality-grid">
<div class="personality-cell"><span class="label">Traits</span><div style="min-height:40px">{{ character.personality.traits }}</div></div>
<div class="personality-cell"><span class="label">Ideal</span><div style="min-height:40px">{{ character.personality.ideal }}</div></div>
</div>
<div class="personality-grid">
<div class="personality-cell"><span class="label">Bond</span><div style="min-height:40px">{{ character.personality.bond }}</div></div>
<div class="personality-cell"><span class="label">Flaw</span><div style="min-height:40px">{{ character.personality.flaw }}</div></div>
</div>
</div>

<!-- BACKSTORY -->
<div class="section">
<div class="section-title">Backstory</div>
<div class="text-area" style="min-height:200px">{{ character.backstory }}</div>
</div>
</div>

<div class="col col-right">
<!-- SPELLCRAFTING -->
<div class="section">
<div class="section-title">Spellcrafting</div>
<div class="spells-header">
<div style="width:25%"><span class="label">Spell TN Save</span><br><span class="value">{{ character.spellcrafting.tn_save }}</span><div style="font-size:6pt;color:#666">8 + INT Mod</div></div>
<div style="width:25%"><span class="label">Attack Bonus</span><br><span class="value">{{ character.spellcrafting.attack_bonus }}</span><div style="font-size:6pt;color:#666">INT Mod</div></div>
<div style="width:25%"><span class="label">Crafting Pts</span><br><div class="hp-inner">
<div><span class="label">Cur</span><div class="empty-box"></div></div>
<div><span class="label">Max</span><div class="value-box">{{ character.spellcrafting.crafting_max }}</div></div>
</div></div>
<div style="width:25%"><span class="label">Casting</span><br><span class="value">{{ character.spellcrafting.casting }}</span></div>
</div>
<table class="fixed spells-table">
<thead><tr><th style="width:30%">Spell Name</th><th style="width:10%">CP</th><th style="width:60%">Details</th></tr></thead>
<tbody>
{% for s in character.spells %}<tr><td>{{ s.name }}</td><td>{{ s.cp }}</td><td>{{ s.details }}</td></tr>{% endfor %}
{% for i in range(character.spells|length, 10) %}<tr><td>&nbsp;</td><td></td><td></td></tr>{% endfor %}
</tbody>
</table>
</div>

<!-- EQUIPMENT -->
<div class="section">
<div class="section-title">Equipment & Inventory</div>
<div class="text-area" style="min-height:150px">{{ character.equipment }}</div>
</div>

<!-- NOTES -->
<div class="section">
<div class="section-title">Notes</div>
<div class="text-area" style="min-height:150px">{{ character.notes }}</div>
</div>
</div>
</div>
</div>
</body>
</html>'''


# Example usage
if __name__ == "__main__":
    generator = CharacterSheetPDF()
    
    # Generate a blank sheet
    generator.generate_blank("blank_sheet.pdf")
    print("Generated: blank_sheet.pdf")
    
    # Save HTML for preview
    generator.save_html(generator._get_blank_character(), "blank_sheet.html")
    print("Generated: blank_sheet.html")