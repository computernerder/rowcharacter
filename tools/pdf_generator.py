"""
Character Sheet PDF Generator for Realm of Warriors

This module provides a portable PDF generator that works in:
- Django web applications (return bytes for HttpResponse)
- CLI applications (write to file)
- Desktop GUI applications (write to file or display)

Dependencies:
    pip install weasyprint jinja2

Usage:
    from character_sheet_pdf import CharacterSheetPDF
    
    generator = CharacterSheetPDF()
    
    # Get PDF as bytes (for web responses)
    pdf_bytes = generator.generate(character_data)
    
    # Or write directly to file
    generator.generate_to_file(character_data, "character.pdf")
"""

from pathlib import Path
from typing import Optional, Union
import sys
import json
import tempfile
from jinja2 import Environment, FileSystemLoader, BaseLoader
from ROW_constants import Skill, Attribute

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

# Make project root importable when running from tools/
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class CharacterSheetPDF:
    """
    Generates PDF character sheets from character data dictionaries.
    
    The generator uses an HTML template with CSS styling, then converts
    to PDF using WeasyPrint. This approach allows:
    - Easy template customization (just edit HTML/CSS)
    - Preview in browser during development
    - Consistent rendering across platforms
    """
    
    # Default template embedded in the class for portability
    # Uses tables for layout (most reliable for PDF generation)
    DEFAULT_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page { size: letter; margin: 0.3in; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 9pt; line-height: 1.2; color: #000; }
        
        .sheet-table { width: 100%; border-collapse: collapse; }
        .sheet-table > tbody > tr > td { vertical-align: top; padding: 4px; }
        .left-col { width: 48%; }
        .right-col { width: 52%; }
        
        .section { border: 1.5px solid #000; padding: 4px 6px; margin-bottom: 6px; }
        .section-title { font-weight: bold; font-size: 8pt; text-transform: uppercase; background: #000; color: #fff; padding: 2px 5px; margin: -4px -6px 4px -6px; }
        .label { font-size: 6pt; text-transform: uppercase; color: #666; }
        .value { font-size: 10pt; font-weight: bold; }
        .value-lg { font-size: 14pt; font-weight: bold; }
        
        .header-table { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
        .header-table td { border: 1px solid #000; padding: 2px 4px; text-align: center; }
        .header-table .label { display: block; }
        .header-table .value { display: block; min-height: 14px; }
        
        .stats-table { width: 100%; border-collapse: collapse; }
        .stats-table th, .stats-table td { border: 1px solid #000; padding: 2px 3px; text-align: center; font-size: 8pt; }
        .stats-table th { background: #eee; font-size: 6pt; text-transform: uppercase; }
        .stats-table .stat-name { font-weight: bold; background: #ddd; width: 35px; }
        .stats-table .mod-cell { background: #f5f5f5; font-weight: bold; font-size: 10pt; }
        
        .combat-table { width: 100%; border-collapse: collapse; }
        .combat-table td { border: 1px solid #000; padding: 3px; text-align: center; vertical-align: top; }
        .combat-table .label { display: block; }
        .combat-table .value-lg { display: block; min-height: 20px; }
        
        .skills-table { width: 100%; border-collapse: collapse; font-size: 7pt; }
        .skills-table th, .skills-table td { border: 1px solid #ccc; padding: 1px 3px; text-align: center; }
        .skills-table th { background: #eee; font-size: 6pt; }
        .skills-table .skill-name { text-align: left; padding-left: 4px; }
        .checkbox { display: inline-block; width: 10px; height: 10px; border: 1px solid #000; text-align: center; line-height: 8px; font-size: 8pt; }
        .checkbox.checked::after { content: "✓"; }
        
        .currency-table { width: 100%; border-collapse: collapse; }
        .currency-table td { border: 1px solid #000; padding: 3px; text-align: center; width: 20%; }
        .currency-table .label { font-weight: bold; font-size: 7pt; color: #000; display: block; }
        
        .weapons-table, .spells-table { width: 100%; border-collapse: collapse; }
        .weapons-table th, .weapons-table td, .spells-table th, .spells-table td { border: 1px solid #000; padding: 2px 4px; font-size: 7pt; }
        .weapons-table th, .spells-table th { background: #eee; font-size: 6pt; text-transform: uppercase; }
        
        .text-area { min-height: 60px; border: 1px solid #000; padding: 4px; font-size: 8pt; white-space: pre-wrap; }
        .text-area.tall { min-height: 100px; }
        .text-area.short { min-height: 40px; }
        
        .traits-table { width: 100%; border-collapse: collapse; }
        .traits-table td { border: 1px solid #000; padding: 2px 4px; text-align: center; width: 25%; }
        
        .personality-table { width: 100%; border-collapse: collapse; }
        .personality-table td { border: 1px solid #000; padding: 3px; vertical-align: top; width: 50%; }
        .personality-table .label { font-weight: bold; color: #000; border-bottom: 1px solid #ccc; margin-bottom: 2px; padding-bottom: 1px; display: block; }
        
        .attack-table { width: 100%; border-collapse: collapse; }
        .attack-table td { border: 1px solid #000; padding: 4px; text-align: center; width: 50%; }
        .attack-formula { font-size: 7pt; color: #666; }
        
        .defense-table { width: 100%; border-collapse: collapse; margin-top: 4px; }
        .defense-table td { border: 1px solid #ccc; padding: 2px; text-align: center; font-size: 7pt; width: 20%; }
        
        .mt-1 { margin-top: 4px; }
        .mb-1 { margin-bottom: 4px; }
    </style>
</head>
<body>
    <!-- HEADER -->
    <table class="header-table">
        <tr>
            <td colspan="3" style="text-align: left; font-size: 18pt; font-weight: bold; letter-spacing: 1px;">Realm of Warriors</td>
            <td><span class="label">Player</span><span class="value">{{ character.player or '' }}</span></td>
            <td><span class="label">Experience</span><span class="value">{{ character.experience or '' }}</span></td>
        </tr>
        <tr>
            <td><span class="label">Character</span><span class="value">{{ character.name or '' }}</span></td>
            <td><span class="label">Profession</span><span class="value">{{ character.profession or '' }}</span></td>
            <td><span class="label">Level</span><span class="value">{{ character.level or '' }}</span></td>
            <td><span class="label">Race</span><span class="value">{{ character.race or '' }}</span></td>
            <td><span class="label">Alignment</span><span class="value">{{ character.alignment or '' }}</span></td>
        </tr>
        <tr>
            <td><span class="label">Primary Path</span><span class="value">{{ character.primary_path or '' }}</span></td>
            <td><span class="label">Background</span><span class="value">{{ character.background or '' }}</span></td>
            <td><span class="label">Ancestry</span><span class="value">{{ character.ancestry or '' }}</span></td>
            <td colspan="2"><span class="label">Reputation</span><span class="value">{{ character.reputation or '' }}</span></td>
        </tr>
    </table>
    
    <!-- MAIN TWO-COLUMN LAYOUT -->
    <table class="sheet-table">
        <tr>
            <!-- LEFT COLUMN -->
            <td class="left-col">
                <!-- ABILITY SCORES -->
                <div class="section">
                    <div class="section-title">Ability Scores</div>
                    <table class="stats-table">
                        <thead>
                            <tr><th></th><th>MOD</th><th>SAVE</th><th>TOTAL</th><th>ROLL</th><th>RACE</th><th>MISC</th></tr>
                        </thead>
                        <tbody>
                            {% for stat in ['mgt', 'agl', 'end', 'int', 'wis', 'cha'] %}
                            {% set s = character.stats.get(stat, {}) %}
                            <tr>
                                <td class="stat-name">{{ stat|upper }}</td>
                                <td class="mod-cell">{{ s.mod if s.mod is not none else '' }}</td>
                                <td>{{ s.save if s.save is not none else '' }}</td>
                                <td>{{ s.total if s.total is not none else '' }}</td>
                                <td>{{ s.roll if s.roll is not none else '' }}</td>
                                <td>{{ s.race if s.race is not none else '' }}</td>
                                <td>{{ s.misc if s.misc is not none else '' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                
                <!-- PASSIVE STATS -->
                <div class="section">
                    <div class="section-title">Passive Stats</div>
                    <table class="combat-table">
                        <tr>
                            <td><span class="label">Perception</span><span class="value-lg">{{ character.passive.perception or '' }}</span></td>
                            <td><span class="label">Wisdom</span><span class="value-lg">{{ character.passive.wisdom or '' }}</span></td>
                            <td><span class="label">Insight</span><span class="value-lg">{{ character.passive.insight or '' }}</span></td>
                            <td><span class="label">Intellect</span><span class="value-lg">{{ character.passive.intellect or '' }}</span></td>
                        </tr>
                    </table>
                </div>
                
                <!-- FEATURES & TRAITS -->
                <div class="section">
                    <div class="section-title">Features & Traits</div>
                    <div class="text-area tall">{{ character.features or '' }}</div>
                </div>
                
                <!-- CURRENCY -->
                <div class="section">
                    <div class="section-title">Currency</div>
                    <table class="currency-table">
                        <tr>
                            <td><span class="label">CP</span><span class="value">{{ character.currency.cp or '' }}</span></td>
                            <td><span class="label">BP</span><span class="value">{{ character.currency.bp or '' }}</span></td>
                            <td><span class="label">SP</span><span class="value">{{ character.currency.sp or '' }}</span></td>
                            <td><span class="label">GP</span><span class="value">{{ character.currency.gp or '' }}</span></td>
                            <td><span class="label">PP</span><span class="value">{{ character.currency.pp or '' }}</span></td>
                        </tr>
                    </table>
                </div>
                
                <!-- ATTACK MODIFIERS -->
                <div class="section">
                    <div class="section-title">Attack Modifiers</div>
                    <table class="attack-table">
                        <tr>
                            <td><span class="label">Melee</span><span class="value-lg">{{ character.attack_mods.melee or '' }}</span><div class="attack-formula">MGT + Misc</div></td>
                            <td><span class="label">Ranged</span><span class="value-lg">{{ character.attack_mods.ranged or '' }}</span><div class="attack-formula">AGL + Misc</div></td>
                        </tr>
                    </table>
                </div>
                
                <!-- PHYSICAL TRAITS -->
                <div class="section">
                    <div class="section-title">Physical Traits</div>
                    <table class="traits-table">
                        <tr>
                            <td><span class="label">Height</span><br><span class="value">{{ character.physical.height or '' }}</span></td>
                            <td><span class="label">Weight</span><br><span class="value">{{ character.physical.weight or '' }}</span></td>
                            <td><span class="label">Size</span><br><span class="value">{{ character.physical.size or '' }}</span></td>
                            <td><span class="label">Age</span><br><span class="value">{{ character.physical.age or '' }}</span></td>
                        </tr>
                        <tr>
                            <td><span class="label">Creature Type</span><br><span class="value">{{ character.physical.creature_type or '' }}</span></td>
                            <td><span class="label">Eyes</span><br><span class="value">{{ character.physical.eyes or '' }}</span></td>
                            <td><span class="label">Skin</span><br><span class="value">{{ character.physical.skin or '' }}</span></td>
                            <td><span class="label">Hair</span><br><span class="value">{{ character.physical.hair or '' }}</span></td>
                        </tr>
                    </table>
                </div>
                
                <!-- TALENTS -->
                <div class="section">
                    <div class="section-title">Talents</div>
                    <div class="text-area short">{% for talent in character.talents %}• {{ talent }}
{% endfor %}</div>
                </div>
            </td>
            
            <!-- RIGHT COLUMN -->
            <td class="right-col">
                <!-- COMBAT STATS -->
                <div class="section">
                    <div class="section-title">Combat Stats</div>
                    <table class="combat-table">
                        <tr>
                            <td><span class="label">Defense</span><span class="value-lg">{{ character.combat.defense or '' }}</span></td>
                            <td><span class="label">Initiative</span><span class="value-lg">{{ character.combat.initiative or '' }}</span></td>
                            <td><span class="label">Walk Speed</span><span class="value-lg">{{ character.combat.walk_speed or '' }}</span></td>
                            <td><span class="label">Stored Adv.</span><span class="value-lg">{{ character.combat.stored_advance or '' }}</span></td>
                        </tr>
                    </table>
                    <table class="combat-table mt-1">
                        <tr>
                            <td colspan="2">
                                <span class="label">Hit Points</span>
                                <table style="width: 100%; border: none;">
                                    <tr>
                                        <td style="border: none; width: 33%;"><span class="label">Armor</span><br><span class="value">{{ character.combat.hp_armor or '' }}</span></td>
                                        <td style="border: none; width: 33%;"><span class="label">Temp</span><br><span class="value">{{ character.combat.hp_temp or '' }}</span></td>
                                        <td style="border: none; width: 33%;"><span class="label">Health</span><br><span class="value">{{ character.combat.hp_health or '' }}</span></td>
                                    </tr>
                                </table>
                            </td>
                            <td colspan="2">
                                <span class="label">Life Points</span>
                                <table style="width: 100%; border: none;">
                                    <tr>
                                        <td style="border: none; width: 50%;"><span class="label">Current</span><br><span class="value-lg">{{ character.combat.lp_current or '' }}</span></td>
                                        <td style="border: none; width: 50%;"><span class="label">Max</span><br><span class="value-lg">{{ character.combat.lp_max or '' }}</span></td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                    <table class="defense-table">
                        <tr>
                            <td><span class="label">Base</span><br>{{ character.combat.defense_base or '9' }}</td>
                            <td><span class="label">AGL</span><br>{{ character.stats.agl.mod if character.stats.get('agl') else '' }}</td>
                            <td><span class="label">Shield</span><br>{{ character.combat.defense_shield or '' }}</td>
                            <td><span class="label">Misc</span><br>{{ character.combat.defense_misc or '' }}</td>
                            <td><span class="label">Align</span><br>{{ character.combat.align_mod or '' }}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- SKILLS -->
                <div class="section">
                    <div class="section-title">Skills</div>
                    <table class="skills-table">
                        <thead>
                            <tr><th style="width: 15px;">T</th><th>Skill Name</th><th>Attr</th><th>Mod</th><th>Rank</th><th>Misc</th><th>Total</th></tr>
                        </thead>
                        <tbody>
                            {% for skill in character.skills %}
                            <tr>
                                <td><span class="checkbox {{ 'checked' if skill.trained else '' }}"></span></td>
                                <td class="skill-name">{{ skill.name }}</td>
                                <td>{{ skill.attr }}</td>
                                <td>{{ skill.mod if skill.mod is not none else '' }}</td>
                                <td>{{ skill.rank if skill.rank is not none else '' }}</td>
                                <td>{{ skill.misc if skill.misc is not none else '' }}</td>
                                <td>{{ skill.total if skill.total is not none else '' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                
                <!-- WEAPONS -->
                <div class="section">
                    <div class="section-title">Weapons & Attacks</div>
                    <table class="weapons-table">
                        <thead><tr><th>Attack Action</th><th>Bonus</th><th>Damage</th><th>Type</th><th>Range</th></tr></thead>
                        <tbody>
                            {% for weapon in character.weapons %}
                            <tr>
                                <td>{{ weapon.name or '' }}</td>
                                <td>{{ weapon.bonus or '' }}</td>
                                <td>{{ weapon.damage or '' }}</td>
                                <td>{{ weapon.type or '' }}</td>
                                <td>{{ weapon.range or '' }}</td>
                            </tr>
                            {% endfor %}
                            {% for i in range(character.weapons|length, 5) %}
                            <tr><td>&nbsp;</td><td></td><td></td><td></td><td></td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                
                <!-- SPELLCRAFTING -->
                <div class="section">
                    <div class="section-title">Spellcrafting</div>
                    <table class="combat-table mb-1">
                        <tr>
                            <td><span class="label">Spell TN Save</span><br><span class="value">{{ character.spellcrafting.tn_save or '' }}</span><div class="attack-formula">8 + INT Mod</div></td>
                            <td><span class="label">Attack Bonus</span><br><span class="value">{{ character.spellcrafting.attack_bonus or '' }}</span><div class="attack-formula">INT Mod</div></td>
                            <td><span class="label">Crafting Pts</span><br><span class="value">{{ character.spellcrafting.crafting_current or '' }} / {{ character.spellcrafting.crafting_max or '' }}</span></td>
                            <td><span class="label">Casting</span><br><span class="value">{{ character.spellcrafting.casting or '' }}</span></td>
                        </tr>
                    </table>
                    <table class="spells-table">
                        <thead><tr><th>Spell Name</th><th>CP</th><th>Details</th></tr></thead>
                        <tbody>
                            {% for spell in character.spells %}
                            <tr><td>{{ spell.name or '' }}</td><td>{{ spell.cp or '' }}</td><td>{{ spell.details or '' }}</td></tr>
                            {% endfor %}
                            {% for i in range(character.spells|length, 6) %}
                            <tr><td>&nbsp;</td><td></td><td></td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                
                <!-- PERSONALITY -->
                <div class="section">
                    <div class="section-title">Personality</div>
                    <table class="personality-table">
                        <tr>
                            <td><span class="label">Traits</span><div>{{ character.personality.traits or '' }}</div></td>
                            <td><span class="label">Ideal</span><div>{{ character.personality.ideal or '' }}</div></td>
                        </tr>
                        <tr>
                            <td><span class="label">Bond</span><div>{{ character.personality.bond or '' }}</div></td>
                            <td><span class="label">Flaw</span><div>{{ character.personality.flaw or '' }}</div></td>
                        </tr>
                    </table>
                </div>
            </td>
        </tr>
    </table>
    
    <!-- NOTES (FULL WIDTH) -->
    <div class="section">
        <div class="section-title">Notes</div>
        <div class="text-area" style="min-height: 60px;">{{ character.notes or '' }}</div>
    </div>
</body>
</html>'''
    
    def __init__(self, template_path: str = None):
        """
        Initialize the PDF generator.
        
        Args:
            template_path: Optional path to a custom HTML template file.
                          If not provided, uses the built-in default template.
        """
        self.template_path = template_path
        self._template = None
    
    @property
    def template(self):
        """Lazy-load the template."""
        if self._template is None:
            if self.template_path:
                template_dir = Path(self.template_path).parent
                template_name = Path(self.template_path).name
                env = Environment(loader=FileSystemLoader(str(template_dir)))
                self._template = env.get_template(template_name)
            else:
                env = Environment(loader=BaseLoader())
                self._template = env.from_string(self.DEFAULT_TEMPLATE)
        return self._template
    
    def _ensure_defaults(self, data: dict) -> dict:
        """Ensure all expected keys exist in the data dictionary."""
        defaults = {
            'name': '', 'player': '', 'profession': '', 'level': '',
            'primary_path': '', 'race': '', 'alignment': '', 'background': '',
            'ancestry': '', 'reputation': '', 'experience': '',
            'stats': {},
            'passive': {'perception': '', 'wisdom': '', 'insight': '', 'intellect': ''},
            'combat': {
                'defense': '', 'defense_base': '9', 'defense_shield': '', 'defense_misc': '',
                'initiative': '', 'walk_speed': '', 'stored_advance': '',
                'hp_armor': '', 'hp_temp': '', 'hp_health': '',
                'lp_current': '', 'lp_max': '', 'align_mod': '', 'rep_mod': ''
            },
            'currency': {'cp': '', 'bp': '', 'sp': '', 'gp': '', 'pp': ''},
            'attack_mods': {'melee': '', 'ranged': ''},
            'physical': {
                'height': '', 'weight': '', 'size': '', 'age': '',
                'creature_type': '', 'eyes': '', 'skin': '', 'hair': ''
            },
            'skills': [], 'weapons': [], 'talents': [], 'spells': [],
            'spellcrafting': {
                'tn_save': '', 'attack_bonus': '',
                'crafting_current': '', 'crafting_max': '', 'casting': ''
            },
            'personality': {'traits': '', 'ideal': '', 'bond': '', 'flaw': ''},
            'features': '', 'notes': ''
        }
        
        def merge_defaults(defaults, data):
            result = defaults.copy()
            for key, value in data.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_defaults(result[key], value)
                else:
                    result[key] = value
            return result
        
        return merge_defaults(defaults, data)
    
    def render_html(self, character_data: dict) -> str:
        """Render the character sheet as HTML."""
        data = self._ensure_defaults(character_data)
        return self.template.render(character=data)
    
    def generate(self, character_data: dict) -> bytes:
        """Generate a PDF from character data. Returns PDF as bytes."""
        from weasyprint import HTML
        html_content = self.render_html(character_data)
        return HTML(string=html_content).write_pdf()
    
    def generate_to_file(self, character_data: dict, output_path: Union[str, Path]) -> None:
        """Generate a PDF and save it to a file."""
        pdf_bytes = self.generate(character_data)
        Path(output_path).write_bytes(pdf_bytes)
    
    def save_html(self, character_data: dict, output_path: Union[str, Path]) -> None:
        """Save the rendered HTML to a file (useful for debugging)."""
        html_content = self.render_html(character_data)
        Path(output_path).write_text(html_content)


# === Shared JS-driven sheet ===
class SharedSheetPDF:
    """Render the shared rowcharactersheet template with Playwright."""

    def __init__(self, sheet_root: Union[str, Path, None] = None):
        self.sheet_root = Path(sheet_root) if sheet_root else ROOT_DIR / "external" / "rowcharactersheet"
        self.template_path = self.sheet_root / "standalone.html"

    def _ensure_playwright(self) -> None:
        if sync_playwright is None:  # pragma: no cover - optional dependency
            raise ImportError(
                "Playwright is required for SharedSheetPDF. Install with `pip install playwright` "
                "and run `playwright install chromium`."
            )

    def _assert_template(self) -> None:
        if not self.template_path.exists():
            raise FileNotFoundError(f"Shared sheet template not found at {self.template_path}")

    def _default_skills(self) -> list[tuple[str, str]]:
        attr_abbr = {
            Attribute.MIGHT: "MGT",
            Attribute.AGILITY: "AGL",
            Attribute.ENDURANCE: "END",
            Attribute.INTELLECT: "INT",
            Attribute.WISDOM: "WIS",
            Attribute.CHARISMA: "CHA",
        }
        skills = []
        for skill in Skill:
            label = skill.value
            slug = label.lower().replace(" ", "_")
            abbr = attr_abbr.get(skill.attribute, "")
            skills.append({"label": label, "slug": slug, "attr": abbr})
        return skills

    def _render_template(self) -> str:
        env = Environment(loader=FileSystemLoader(str(self.sheet_root)))
        env.filters["make_list"] = list
        template = env.get_template("standalone.html")
        return template.render(skills=self._default_skills())

    def _build_init_script(self, sheet_data: dict, fallback_data: Optional[dict]) -> str:
        data_json = json.dumps(sheet_data or {}, ensure_ascii=False)
        script = (
            "(() => {"
            f"const data = {data_json};"
            "Object.defineProperty(window, 'sheetData', { value: data, writable: false, configurable: false });"
        )
        if fallback_data is not None:
            fallback_json = json.dumps(fallback_data or {}, ensure_ascii=False)
            script += f"Object.defineProperty(window, 'sheetFallback', {{ value: {fallback_json}, writable: false, configurable: false }});"
        script += "})();"
        return script

    def generate(
        self,
        sheet_data: dict,
        fallback_data: Optional[dict] = None,
        pdf_path: Union[str, Path, None] = None,
        wait_ms: int = 200,
    ) -> bytes:
        """Generate the shared sheet PDF using Playwright and return PDF bytes."""
        self._ensure_playwright()
        self._assert_template()

        with sync_playwright() as p:  # type: ignore[call-arg]
            browser = p.chromium.launch(args=["--no-sandbox"], headless=True)
            try:
                context = browser.new_context()
                page = context.new_page()
                page.add_init_script(self._build_init_script(sheet_data, fallback_data))
                rendered_html = self._render_template()
                with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, dir=self.sheet_root) as tmp:
                    tmp.write(rendered_html)
                    temp_path = Path(tmp.name)
                page.goto(temp_path.as_uri())
                page.wait_for_load_state("networkidle")
                if wait_ms:
                    page.wait_for_timeout(wait_ms)
                pdf_bytes = page.pdf(format="Letter", print_background=True)
                if pdf_path:
                    Path(pdf_path).write_bytes(pdf_bytes)
                return pdf_bytes
            finally:
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass
                browser.close()

    def generate_to_file(self, sheet_data: dict, output_path: Union[str, Path], fallback_data: Optional[dict] = None) -> None:
        """Generate and write the PDF to disk."""
        self.generate(sheet_data, fallback_data=fallback_data, pdf_path=output_path)


# === EXAMPLE DATA STRUCTURE ===
EXAMPLE_CHARACTER = {
    "name": "Thorin Ironforge",
    "player": "Josh",
    "profession": "Warrior",
    "level": 5,
    "primary_path": "Battle Master",
    "race": "Dwarf",
    "alignment": "Lawful Good",
    "background": "Soldier",
    "ancestry": "Mountain Dwarf",
    "reputation": "Honorable",
    "experience": 6500,
    
    "stats": {
        "mgt": {"mod": 3, "save": 5, "total": 17, "roll": 15, "race": 2, "misc": 0},
        "agl": {"mod": 1, "save": 1, "total": 12, "roll": 12, "race": 0, "misc": 0},
        "end": {"mod": 3, "save": 6, "total": 16, "roll": 14, "race": 2, "misc": 0},
        "int": {"mod": 0, "save": 0, "total": 10, "roll": 10, "race": 0, "misc": 0},
        "wis": {"mod": 1, "save": 1, "total": 13, "roll": 13, "race": 0, "misc": 0},
        "cha": {"mod": -1, "save": -1, "total": 8, "roll": 8, "race": 0, "misc": 0},
    },
    
    "passive": {"perception": 14, "wisdom": 11, "insight": 11, "intellect": 10},
    
    "combat": {
        "defense": 14, "defense_base": 9, "defense_shield": 2, "defense_misc": 0,
        "initiative": 1, "walk_speed": 25, "stored_advance": 0,
        "hp_armor": 18, "hp_temp": 0, "hp_health": 45,
        "lp_current": 45, "lp_max": 45, "align_mod": 1, "rep_mod": 0
    },
    
    "currency": {"cp": 50, "bp": 0, "sp": 125, "gp": 340, "pp": 10},
    "attack_mods": {"melee": "+5", "ranged": "+3"},
    
    "physical": {
        "height": "4'5\"", "weight": "180 lbs", "size": "Medium", "age": "95",
        "creature_type": "Humanoid", "eyes": "Brown", "skin": "Tan", "hair": "Black"
    },
    
    "skills": [
        {"name": "Acrobatics", "attr": "AGL", "trained": False, "mod": 1, "rank": 0, "misc": 0, "total": 1},
        {"name": "Animal Handling", "attr": "WIS", "trained": False, "mod": 1, "rank": 0, "misc": 0, "total": 1},
        {"name": "Appraisal", "attr": "INT", "trained": True, "mod": 0, "rank": 2, "misc": 0, "total": 2},
        {"name": "Arcana", "attr": "INT", "trained": False, "mod": 0, "rank": 0, "misc": 0, "total": 0},
        {"name": "Athletics", "attr": "MGT", "trained": True, "mod": 3, "rank": 3, "misc": 0, "total": 6},
        {"name": "Crafting", "attr": "INT", "trained": True, "mod": 0, "rank": 4, "misc": 2, "total": 6},
        {"name": "Deception", "attr": "CHA", "trained": False, "mod": -1, "rank": 0, "misc": 0, "total": -1},
        {"name": "History", "attr": "INT", "trained": True, "mod": 0, "rank": 2, "misc": 0, "total": 2},
        {"name": "Insight", "attr": "WIS", "trained": False, "mod": 1, "rank": 0, "misc": 0, "total": 1},
        {"name": "Intimidation", "attr": "CHA", "trained": True, "mod": -1, "rank": 3, "misc": 0, "total": 2},
        {"name": "Investigation", "attr": "INT", "trained": False, "mod": 0, "rank": 0, "misc": 0, "total": 0},
        {"name": "Medicine", "attr": "WIS", "trained": False, "mod": 1, "rank": 0, "misc": 0, "total": 1},
        {"name": "Nature", "attr": "INT", "trained": False, "mod": 0, "rank": 0, "misc": 0, "total": 0},
        {"name": "Perception", "attr": "WIS", "trained": True, "mod": 1, "rank": 3, "misc": 0, "total": 4},
        {"name": "Performance", "attr": "CHA", "trained": False, "mod": -1, "rank": 0, "misc": 0, "total": -1},
        {"name": "Persuasion", "attr": "CHA", "trained": False, "mod": -1, "rank": 0, "misc": 0, "total": -1},
        {"name": "Religion", "attr": "INT", "trained": False, "mod": 0, "rank": 0, "misc": 0, "total": 0},
        {"name": "Sleight of Hand", "attr": "AGL", "trained": False, "mod": 1, "rank": 0, "misc": 0, "total": 1},
        {"name": "Stealth", "attr": "AGL", "trained": False, "mod": 1, "rank": 0, "misc": -2, "total": -1},
        {"name": "Survival", "attr": "WIS", "trained": True, "mod": 1, "rank": 2, "misc": 0, "total": 3},
    ],
    
    "weapons": [
        {"name": "Battleaxe", "bonus": "+5", "damage": "1d8+3", "type": "Slashing", "range": "Melee"},
        {"name": "Handaxe", "bonus": "+5", "damage": "1d6+3", "type": "Slashing", "range": "20/60"},
        {"name": "Light Crossbow", "bonus": "+3", "damage": "1d8+1", "type": "Piercing", "range": "80/320"},
    ],
    
    "talents": [
        "Dwarven Resilience", "Stonecunning", "Second Wind", "Action Surge", "Combat Superiority"
    ],
    
    "spells": [],
    
    "spellcrafting": {
        "tn_save": "", "attack_bonus": "",
        "crafting_current": "", "crafting_max": "", "casting": ""
    },
    
    "personality": {
        "traits": "I judge people by their actions, not their words.",
        "ideal": "Greater Good - Our lot is to lay down our lives in defense of others.",
        "bond": "I fight for those who cannot fight for themselves.",
        "flaw": "I have little respect for anyone who is not a proven warrior."
    },
    
    "features": """• Darkvision (60 ft)
• Dwarven Resilience (advantage vs poison)
• Tool Proficiency (Smith's tools)
• Stonecunning (History checks on stonework)
• Fighting Style: Defense (+1 AC in armor)
• Second Wind (1d10+5 HP, 1/short rest)
• Action Surge (1/short rest)
• Superiority Dice: 4d8""",
    
    "notes": "Currently seeking the lost forge of Clan Ironforge in the mountains."
}


if __name__ == "__main__":
    generator = CharacterSheetPDF()
    generator.generate_to_file(EXAMPLE_CHARACTER, "character_sheet.pdf")
    print("Generated: character_sheet.pdf")
    generator.save_html(EXAMPLE_CHARACTER, "character_sheet.html")
    print("Generated: character_sheet.html")