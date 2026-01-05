"""
Simple GUI wrapper (customtkinter) for browsing characters, creating a new one,
quick editing core fields, exporting to PDF, and launching a level-up helper.

Usage:
    C:/Projects/FightingSystem/.venv/Scripts/python.exe gui_app.py

Requirements:
    pip install customtkinter
    pip install playwright jinja2 (for PDF export via SharedSheetPDF)
    python -m playwright install chromium
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import logging
import traceback
import random
import webbrowser
import re
import html as html_mod
import tempfile
import tkinter as tk

try:
    from playwright.sync_api import sync_playwright  # pragma: no cover - optional for PNG rendering
    PLAYWRIGHT_AVAILABLE = True
except Exception:  # pragma: no cover
    PLAYWRIGHT_AVAILABLE = False

try:
    import customtkinter as ctk
except ImportError as e:  # pragma: no cover - GUI dependency
    raise SystemExit("customtkinter is required. Install with `pip install customtkinter`.") from e

try:
    from tkhtmlview import HTMLLabel  # pragma: no cover - optional HTML summary rendering
    HTML_SUMMARY_AVAILABLE = True
except Exception:
    HTML_SUMMARY_AVAILABLE = False

try:
    from tkinterweb import HtmlFrame  # pragma: no cover - richer HTML (WebKit/Chromium-backed)
    HTML_FRAME_AVAILABLE = True
except Exception:
    HTML_FRAME_AVAILABLE = False

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# --------------------------- logging ---------------------------
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / "gui_app.log"

logger = logging.getLogger("FightingSystem.gui_app")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    _fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_fh)
    logger.propagate = False

from character_builder import CharacterBuilder  # noqa: E402
from validation import CharacterValidator  # noqa: E402
from template_model import dump_character_template, load_character_template, Talent as TemplateTalent  # noqa: E402
from tools.pdf_generator import SharedSheetPDF  # noqa: E402
from core.talent import load_all_talents, get_all_talents_flat  # noqa: E402
from levelup_manager import LevelUpManager, TalentChoice as LevelTalentChoice, AdvancementChoice as LevelAdvancementChoice, AP_COSTS  # noqa: E402
from ROW_constants import ALL_LANGUAGES, ALL_ARMOR_PROFICIENCIES, ALL_WEAPON_PROFICIENCIES, ALL_TOOL_PROFICIENCIES  # noqa: E402


CHAR_DIR = ROOT_DIR / "characters"
EXPORTS_DIR = ROOT_DIR / "exports"
CHAR_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

# External HTML sheet assets
SHEET_ROOT = ROOT_DIR / "external" / "rowcharactersheet"
SHEET_TEMPLATE = SHEET_ROOT / "templates" / "characters" / "sheet_embed.html"
SHEET_STATIC = SHEET_ROOT / "static" / "rowcharactersheet"
SHEET_CSS = SHEET_STATIC / "blank_sheet.css"
SHEET_JS = SHEET_STATIC / "js" / "sheet_embed.js"
SHEET_IMG_DIR = SHEET_STATIC / "images"


_SHEET_TALENTS_FLAT_CACHE: dict | None = None


def _get_sheet_talents_flat() -> dict:
    """Lazy-load and cache talent definitions for sheet rendering."""
    global _SHEET_TALENTS_FLAT_CACHE
    if _SHEET_TALENTS_FLAT_CACHE is None:
        cats = load_all_talents(str(ROOT_DIR / "data" / "talents"))
        _SHEET_TALENTS_FLAT_CACHE = get_all_talents_flat(cats)
    return _SHEET_TALENTS_FLAT_CACHE


def _format_talent_ui_details(
    talent_def: Any | None,
    *,
    current_rank: int = 0,
    next_rank: int | None = None,
    mode: str = "next",
) -> str:
    """Return a human-readable block for talent UI rows.

    mode:
      - "next": show description + next-rank effect
      - "current": show description + cumulative current-rank effect
    """
    if not talent_def:
        return ""

    desc = str(getattr(talent_def, "description", "") or "").strip()
    parts: list[str] = []
    if desc:
        parts.append(desc)

    try:
        if mode == "next" and next_rank is not None:
            effect = str(getattr(talent_def, "get_rank_description", lambda _r: "")(int(next_rank)) or "").strip()
            if effect:
                parts.append(f"Next (Rank {int(next_rank)}): {effect}")
        elif mode == "current" and int(current_rank) > 0:
            cumulative = str(getattr(talent_def, "get_cumulative_description", lambda _r: "")(int(current_rank)) or "").strip()
            if cumulative:
                parts.append(f"Current Effects (Rank {int(current_rank)}):\n{cumulative}")
    except Exception:
        # If rank text is missing/malformed, keep the base description.
        pass

    return "\n\n".join([p for p in parts if p])


def _safe_slug(text: str, fallback: str) -> str:
    cleaned = "".join(ch for ch in text if ch.isalnum() or ch in "-_ ").strip().replace(" ", "_")
    return cleaned or fallback


def _build_sheet_preview_html(data: Dict[str, Any]) -> str:
    """Render the rowcharactersheet HTML with inline assets and embedded data."""
    css_text = ""
    js_text = ""
    template_text = ""
    try:
        css_text = SHEET_CSS.read_text(encoding="utf-8")
        # Make image URLs absolute so they load from disk.
        img_base = SHEET_IMG_DIR.as_uri()
        css_text = css_text.replace("url('images/", f"url('{img_base}/")
        css_text = css_text.replace('url("images/', f'url("{img_base}/')
        # Tkinterweb lacks gradient support; fall back to flat backgrounds.
        css_text = re.sub(r"repeating-linear-gradient\([^\)]*\)", "none", css_text)
        # Light fallback overrides to keep layout readable under limited CSS support.
        css_text += "\n" + """
/* Fallback for tkinterweb: flatten visuals to simple boxes */
body, .sheet-embed, .page { background: #fff !important; }
.page { box-shadow: none !important; border: 1px solid #999; }
.section { background: #fff !important; border: 1px solid #bbb; box-shadow: none !important; }
.section-title { background: #f2f2f2 !important; color: #000 !important; border-bottom: 1px solid #ccc; }
.value-box, .value-box-lg, .empty-box, .empty-box-lg, .stored-box { background: #fff !important; }
.inner, .grid-table, .stats-table, .talent-table, .feature-table, .skills-table, .weapons-table { border-color: #ccc !important; }
.header, .header-box { background: #fff !important; }
.main-table td { background: #fff !important; }
table { border-collapse: collapse; }
"""
    except Exception:
        css_text = ""

    try:
        js_text = SHEET_JS.read_text(encoding="utf-8")
    except Exception:
        js_text = ""

    try:
        template_text = SHEET_TEMPLATE.read_text(encoding="utf-8")
    except Exception:
        template_text = "<div>sheet_embed.html not found.</div>"

    def _replace_tag_content(html: str, attr_name: str, attr_val: str, content: str) -> str:
        pattern = rf'(<'  # opening
        pattern += r'[^>]*' + re.escape(attr_name) + r'="' + re.escape(attr_val) + r'"'  # attr
        pattern += r'[^>]*>)'  # end of tag
        pattern += r'(.*?)'  # inner
        pattern += r'(</[^>]+>)'
        return re.sub(pattern, lambda m: m.group(1) + content + m.group(3), html, count=1, flags=re.DOTALL)

    # Strip Django template tags and replace static asset references.
    lines = []
    for line in template_text.splitlines():
        if "static 'rowcharactersheet/blank_sheet.css'" in line:
            continue
        if "sheet_embed.js" in line:
            continue
        if "{%" in line:
            continue
        lines.append(line)
    template_text = "\n".join(lines)
    logo_uri = (SHEET_IMG_DIR / "row_small_logo.png").as_uri()
    corner_uri = (SHEET_IMG_DIR / "Corner.png").as_uri()
    template_text = template_text.replace("{% load static %}", "")
    template_text = template_text.replace("{% static 'rowcharactersheet/images/row_small_logo.png' %}", logo_uri)
    template_text = template_text.replace("{% static 'rowcharactersheet/images/Corner.png' %}", corner_uri)
    # Remove any residual Jinja placeholders for skills.
    template_text = template_text.replace("{{ label }}", "").replace("{{ skill.label }}", "").replace("{{ skill.attr }}", "")
    # Replace QR image with a transparent placeholder to avoid file errors.
    transparent_px = "data:image/gif;base64,R0lGODlhAQABAAAAACw="
    template_text = template_text.replace("/characters/{{ character.code }}/qr/", transparent_px)

    # Build simple field map
    field_values = {
        "character_name": data.get("character_name", ""),
        "player": data.get("player", ""),
        "profession": data.get("profession", ""),
        "primary_path": data.get("primary_path", ""),
        "background": data.get("background", ""),
        "race": data.get("race", ""),
        "ancestry": data.get("ancestry", ""),
        "race_block": " / ".join(
            [v.strip() for v in [data.get("race", ""), data.get("ancestry", ""), data.get("background", "")] if v and str(v).strip()]
        ),
        "stored_advance": data.get("stored_advance", ""),
        "speed": data.get("speed", ""),
        "initiative": data.get("initiative", ""),
        "notes": data.get("notes", ""),
        "inventory_total_weight": "",
        "alignment_alignment": (data.get("alignment") or {}).get("alignment", ""),
        "alignment_mod": (data.get("alignment") or {}).get("mod", ""),
        "reputation_reputation": (data.get("reputation") or {}).get("reputation", ""),
        "reputation_mod": (data.get("reputation") or {}).get("mod", ""),
        "level": data.get("level", ""),
        "total_experience": data.get("total_experience", ""),
        "spell_save_dc": (data.get("spellcrafting") or {}).get("save_dc", ""),
        "spell_attack_bonus": (data.get("spellcrafting") or {}).get("attack_bonus", ""),
        "spell_casting": (data.get("spellcrafting") or {}).get("casting", ""),
        "spell_cp_max": ((data.get("spellcrafting") or {}).get("crafting_points") or {}).get("max", ""),
        "spell_cp_current": ((data.get("spellcrafting") or {}).get("crafting_points") or {}).get("current", ""),
        "footer_datecode": (data.get("footer") or {}).get("datecode", ""),
        "footer_config": (data.get("footer") or {}).get("config", ""),
        "footer_id": (data.get("footer") or {}).get("id", ""),
    }
    phys = data.get("physical_traits") or {}
    for key in ["height", "weight", "size", "age", "creature_type", "eyes", "skin", "hair"]:
        field_values[key] = phys.get(key, "")

    defense = data.get("defense") or {}
    for k in ["base", "agility", "shield", "misc", "total"]:
        field_values[f"defense_{k}"] = defense.get(k, "")

    health = data.get("health") or {}
    field_values["health_max"] = health.get("max", "")
    field_values["health_current"] = health.get("current", "")

    armor_hp = data.get("armor_hp") or {}
    field_values["armor_hp_max"] = armor_hp.get("max", "")
    field_values["armor_hp_current"] = armor_hp.get("current", "")

    life = data.get("life_points") or {}
    field_values["life_points_max"] = life.get("max", "")
    field_values["life_points_current"] = life.get("current", "")

    passive = data.get("passive") or {}
    percep = passive.get("perception", {})
    insight = passive.get("insight", {})
    for name, src in [("passive_perception", percep), ("passive_insight", insight)]:
        for part in ["base", "skill", "misc", "total"]:
            field_values[f"{name}_{part}"] = src.get(part, "")

    attack_mods = data.get("attack_mods") or {}
    for name, src in [("attack_melee", attack_mods.get("melee", {})), ("attack_ranged", attack_mods.get("ranged", {}))]:
        for part in ["attr", "misc", "total"]:
            field_values[f"{name}_{part}"] = src.get(part, "")

    personality = data.get("personality") or {}
    for part in ["traits", "ideal", "bond", "flaw"]:
        field_values[f"personality_{part}"] = personality.get(part, "")

    # Apply simple fields
    for field, value in field_values.items():
        safe = html_mod.escape(str(value)) if value not in (None, "") else ""
        template_text = _replace_tag_content(template_text, "data-field", field, safe)

    # Abilities
    abilities = data.get("ability_scores") or {}
    for ability, parts in abilities.items():
        for part_name in ["mod", "saving_throw", "total", "roll", "race", "misc"]:
            if part_name in parts:
                safe = html_mod.escape(str(parts.get(part_name, "")))
                # Replace within the matching row
                row_pattern = rf'(<tr[^>]+data-ability="{re.escape(ability)}"[^>]*>)(.*?)(</tr>)'
                def _row_replacer(match):
                    inner = match.group(2)
                    inner = _replace_tag_content(inner, "data-part", part_name, safe)
                    return match.group(1) + inner + match.group(3)
                template_text = re.sub(row_pattern, _row_replacer, template_text, flags=re.DOTALL)

    # Skills table body (replace tbody content)
    skills = data.get("skills") or {}
    skill_rows = []
    if skills:
        for name, info in skills.items():
            trained = info.get("trained")
            mod = info.get("mod", "")
            rank = info.get("rank", "")
            misc = info.get("misc", "")
            total = info.get("total", "")
            checkbox_class = "checkbox checked" if trained else "checkbox"
            skill_rows.append(
                f"<tr data-skill='{html_mod.escape(str(name))}'>"
                f"<td><span class='{checkbox_class}'></span></td>"
                f"<td class='skill-name'>{html_mod.escape(str(name))}</td>"
                f"<td></td>"
                f"<td>{html_mod.escape(str(mod))}</td>"
                f"<td>{html_mod.escape(str(rank))}</td>"
                f"<td>{html_mod.escape(str(misc))}</td>"
                f"<td>{html_mod.escape(str(total))}</td>"
                "</tr>"
            )
    else:
        for i in range(12):
            skill_rows.append(
                f"<tr data-skill='Skill {i+1}'><td><span class='checkbox'></span></td><td class='skill-name'>Skill {i+1}</td><td></td><td></td><td></td><td></td><td></td></tr>"
            )

    def _replace_tbody(html: str, table_class: str, new_body: str) -> str:
        pattern = rf'(<table[^>]*class="[^"]*{table_class}[^"]*"[^>]*>.*?<tbody>)(.*?)(</tbody>)'
        return re.sub(pattern, lambda m: m.group(1) + new_body + m.group(3), html, count=1, flags=re.DOTALL)

    template_text = _replace_tbody(template_text, "skills-table", "".join(skill_rows))

    # Attacks
    attacks = data.get("attacks") or []
    attack_rows = []
    for atk in attacks[:5]:
        attack_rows.append(
            "<tr>"
            f"<td>{html_mod.escape(str(atk.get('attack_action', '')))}</td>"
            f"<td>{html_mod.escape(str(atk.get('bonus', '')))}</td>"
            f"<td>{html_mod.escape(str(atk.get('damage', '')))}</td>"
            f"<td>{html_mod.escape(str(atk.get('type', '')))}</td>"
            f"<td>{html_mod.escape(str(atk.get('range', '')))}</td>"
            "</tr>"
        )
    while len(attack_rows) < 5:
        attack_rows.append("<tr><td>&nbsp;</td><td></td><td></td><td></td><td></td></tr>")
    template_text = _replace_tbody(template_text, "weapons-table", "".join(attack_rows))

    # Features and talents (visible list only)
    def _fill_simple_list(html: str, list_name: str, items: list[str], rows: int = 5, *, multiline: bool = False) -> str:
        cells = []
        for i in range(rows):
            val = str(items[i]) if i < len(items) else ""
            safe = html_mod.escape(val)
            if multiline:
                safe = safe.replace("\n", "<br>")
            cells.append(f"<tr><td>{safe}</td></tr>")
        pattern = rf'(data-list="{list_name}"[^>]*>\s*<tbody>)(.*?)(</tbody>)'
        return re.sub(pattern, lambda m: m.group(1) + "".join(cells) + m.group(3), html, count=1, flags=re.DOTALL)

    feature_items = [
        (f.get("name") + ": " + f.get("text", "")) if f.get("name") else f.get("text", "")
        for f in (data.get("features") or [])
    ]
    talent_items = [
        (t.get("name") + ": " + t.get("text", "")) if t.get("name") else t.get("text", "")
        for t in (data.get("talents") or [])
    ]
    template_text = _fill_simple_list(template_text, "features", feature_items)
    template_text = _fill_simple_list(template_text, "talents", talent_items)

    # Overflow definitions pages
    template_text = _fill_simple_list(template_text, "features-overflow", feature_items, rows=12, multiline=True)

    talents_flat = {}
    try:
        talents_flat = _get_sheet_talents_flat()
    except Exception:
        talents_flat = {}

    talent_def_items: list[str] = []
    for t in (data.get("talents") or []):
        tid = (t.get("talent_id") or t.get("id") or "")
        rank_raw = t.get("rank", 0)
        try:
            rank = int(rank_raw or 0)
        except Exception:
            rank = 0
        tdef = talents_flat.get(tid)
        name = t.get("name") or (tdef.name if tdef else tid)

        parts: list[str] = []
        header = f"{name}" + (f" (Rank {rank})" if rank else "")
        parts.append(header)

        if tdef:
            base = (getattr(tdef, "description", "") or "").strip()
            if base:
                parts.append(base)
            if rank > 0:
                cumulative = (tdef.get_cumulative_description(rank) or "").strip()
                if cumulative:
                    parts.append(cumulative)
        else:
            fallback = (t.get("text") or "").strip()
            if fallback:
                parts.append(fallback)

        choice_data = t.get("choice_data") if isinstance(t.get("choice_data"), dict) else None
        if choice_data:
            choice_bits = [f"{k}={v}" for k, v in choice_data.items() if str(k).strip()]
            if choice_bits:
                parts.append("Choice: " + ", ".join(choice_bits))

        # Join with newlines to support multiline rendering in the overflow table.
        text = "\n".join([p for p in parts if p])
        if text.strip():
            talent_def_items.append(text)

    template_text = _fill_simple_list(template_text, "talents-overflow", talent_def_items, rows=12, multiline=True)

    # Spells
    spells = ((data.get("spellcrafting") or {}).get("spells") or [])
    spell_rows = []
    for sp in spells[:12]:
        spell_rows.append(
            "<tr style='height:18px'>"
            f"<td>{html_mod.escape(str(sp.get('name', '')))}</td>"
            f"<td>{html_mod.escape(str(sp.get('cp', '')))}</td>"
            f"<td>{html_mod.escape(str(sp.get('details', '')))}</td>"
            "</tr>"
        )
    while len(spell_rows) < 12:
        spell_rows.append("<tr style='height:18px'><td>&nbsp;</td><td></td><td></td></tr>")
    template_text = _replace_tbody(template_text, "spells", "".join(spell_rows))

    return (
        "<!doctype html>\n<html><head><meta charset='utf-8'>"
        f"<style>{css_text}</style>"
        "</head><body>"
        f"{template_text}"
        "</body></html>"
    )


def _write_sheet_preview_file(data: Dict[str, Any]) -> Path:
    html = _build_sheet_preview_html(data)
    name_slug = _safe_slug(data.get("character_name", "character"), "character")
    player_slug = _safe_slug(data.get("player", "player"), "player")
    target = EXPORTS_DIR / f"{name_slug}_{player_slug}_sheet_preview.html"
    target.write_text(html, encoding="utf-8")
    return target


def _render_sheet_png(data: Dict[str, Any]) -> Path | None:
    if not PLAYWRIGHT_AVAILABLE:
        return None
    html = _build_sheet_preview_html(data)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_html:
        tmp_html.write(html.encode("utf-8"))
        html_path = Path(tmp_html.name)
    png_path = html_path.with_suffix(".png")
    try:
        with sync_playwright() as p:  # pragma: no cover - requires Playwright runtime
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 950, "height": 1300})
            page.goto(html_path.as_uri(), wait_until="networkidle")
            page.screenshot(path=str(png_path), full_page=True)
            browser.close()
        return png_path
    except Exception:
        return None


class CharacterListFrame(ctk.CTkFrame):
    def __init__(self, master, on_select):
        super().__init__(master)
        self.on_select = on_select
        self.listbox = ctk.CTkTextbox(self, width=320, height=380, activate_scrollbars=True)
        self.listbox.configure(state="disabled")
        self.listbox.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._items = []
        self.listbox.bind("<ButtonRelease-1>", self._handle_click)

    def set_items(self, items):
        self._items = items
        self.listbox.configure(state="normal")
        self.listbox.delete("1.0", "end")
        for idx, (label, _) in enumerate(items, 1):
            self.listbox.insert("end", f"{idx}. {label}\n")
        self.listbox.configure(state="disabled")

    def _handle_click(self, event):
        try:
            index = int(float(self.listbox.index(f"@{event.x},{event.y}").split(".")[0])) - 1
        except Exception:
            return
        if 0 <= index < len(self._items):
            _, path = self._items[index]
            self.on_select(path)


class NewCharacterWizard(ctk.CTkToplevel):
    def __init__(self, master, builder: CharacterBuilder, on_save):
        super().__init__(master)
        self.base_builder = builder
        self.on_save = on_save
        self.title("New Character Wizard")
        # Fixed vertical size so the bottom nav buttons are always visible.
        # Wider default so the Talents step doesn't clip action buttons.
        self.geometry("980x700")
        self.minsize(950, 700)
        try:
            self.resizable(True, False)
        except Exception:
            pass

        self._created_character_path: Path | None = None

        # Ensure we unregister from CustomTkinter scaling callbacks before destroying widgets.
        try:
            self.protocol("WM_DELETE_WINDOW", self._on_close)
        except Exception:
            pass

        # Identity
        self.var_name = ctk.StringVar(value="New Hero")
        self.var_player = ctk.StringVar(value="Player")

        # Physical traits
        self.var_height = ctk.StringVar(value="5'8\"")
        self.var_weight = ctk.StringVar(value="160 lb")
        self.var_age = ctk.StringVar(value="25")
        self.var_eyes = ctk.StringVar(value="Brown")
        self.var_skin = ctk.StringVar(value="Tan")
        self.var_hair = ctk.StringVar(value="Brown")

        self._physical_user_modified = False
        self._physical_seeded_for_heritage: tuple[str, str] | None = None
        self._seeding_physical = False

        def _mark_physical_modified(*_args):
            if self._seeding_physical:
                return
            self._physical_user_modified = True

        for v in [self.var_height, self.var_weight, self.var_age, self.var_eyes, self.var_skin, self.var_hair]:
            try:
                v.trace_add("write", _mark_physical_modified)
            except Exception:
                # Tkinter < 8.6 fallback (unlikely on modern Python)
                v.trace("w", _mark_physical_modified)

        # Ability scores
        self.abilities = ["Might", "Agility", "Endurance", "Intellect", "Wisdom", "Charisma"]
        # Leave blank on start; point-buy step will seed 8s when that mode is shown.
        self.ability_vars = {name: ctk.StringVar(value="") for name in self.abilities}
        self.ability_entries = {}
        self.mode_var = ctk.StringVar(value="Point Buy")
        self.point_buy_budget = 30
        self.point_buy_label = None
        self.roll_choice_vars = {}
        self.roll_option_menus = {}
        self.standard_choice_vars = {}
        self.standard_option_menus = {}
        self._scores_user_modified = False
        self._scores_seeded_for_heritage: tuple[str, str] | None = None
        self._scores_confirmed = False

        # Core selections
        self.var_race = ctk.StringVar(value=list(builder.races.keys())[0])
        self.var_ancestry = ctk.StringVar(value=list(builder.ancestries.keys())[0])
        self.var_prof = ctk.StringVar(value=list(builder.professions.keys())[0])
        self.var_duty = ctk.StringVar(value="")
        self.var_path = ctk.StringVar(value=list(builder.paths.keys())[0])
        self.var_bg = ctk.StringVar(value=list(builder.backgrounds.keys())[0])

        # Choice handling (e.g., human mode follow-ups)
        self.human_mode_var = ctk.StringVar(value="")
        first_ability = self.abilities[0]
        self.human_plusone_var = ctk.StringVar(value=first_ability)
        self.human_plus2_var = ctk.StringVar(value=first_ability)
        self.human_penalty_var = ctk.StringVar(value=self.abilities[-1])

        self.choice_records = []
        # Talent state (level 1)
        self.talent_categories = load_all_talents(str(ROOT_DIR / "data" / "talents"))
        self.talents_flat = get_all_talents_flat(self.talent_categories)
        self.level1_talent_state: Dict[str, Dict[str, Any]] = {}

        self.step_index = 0
        # Wizard order: start with Heritage, then basics, then build choices.
        self.steps = [
            ("Heritage", self._render_heritage),
            ("Basics", self._render_basics),
            ("Profession", self._render_profession),
            ("Ability Scores", self._render_scores),
            ("Path", self._render_path),
            ("Background", self._render_background),
            ("Choices", self._render_choices),
            ("Talents", self._render_talents),
        ]

        # Ensure ancestry defaults match the current race.
        initial_ancestries = self._ancestries_for_race(self.var_race.get())
        if initial_ancestries:
            self.var_ancestry.set(initial_ancestries[0])

        # Seed sensible point-buy defaults once we have a heritage selection.
        self._maybe_seed_point_buy_from_heritage(force=True)
        # Seed physical trait defaults once we have a heritage selection.
        self._maybe_seed_physical_traits_from_heritage(force=True)

        # Layout: main area + a dedicated bottom nav row (prevents buttons getting pushed off-screen).
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self.main = ctk.CTkFrame(self)
        self.main.grid(row=0, column=0, sticky="nsew", padx=12, pady=(10, 0))
        self.main.grid_rowconfigure(0, weight=1)
        self.main.grid_columnconfigure(1, weight=1)

        self.summary_bar = ctk.CTkFrame(self.main, width=310, height=520)
        self.summary_bar.grid(row=0, column=0, sticky="nw", padx=(0, 12), pady=0)
        self.summary_bar.grid_propagate(False)
        self.summary_labels = {}

        # Simple on-screen table instead of HTML summary
        self.summary_table = ctk.CTkFrame(self.summary_bar)
        self.summary_table.pack(fill="x", expand=False, padx=8, pady=(8, 6))
        headers = ["Ability", "Roll", "Total", "Mod", "Delta"]
        for col, header in enumerate(headers):
            ctk.CTkLabel(self.summary_table, text=header, font=("Segoe UI", 11, "bold")).grid(row=0, column=col, padx=6, pady=2, sticky="w")
        self.summary_table_rows = {}
        for row_idx, ability in enumerate(self.abilities, start=1):
            ctk.CTkLabel(self.summary_table, text=ability).grid(row=row_idx, column=0, padx=6, pady=1, sticky="w")
            roll_lbl = ctk.CTkLabel(self.summary_table, text="--")
            total_lbl = ctk.CTkLabel(self.summary_table, text="--")
            mod_lbl = ctk.CTkLabel(self.summary_table, text="--")
            delta_lbl = ctk.CTkLabel(self.summary_table, text="--")
            roll_lbl.grid(row=row_idx, column=1, padx=6, pady=1, sticky="w")
            total_lbl.grid(row=row_idx, column=2, padx=6, pady=1, sticky="w")
            mod_lbl.grid(row=row_idx, column=3, padx=6, pady=1, sticky="w")
            delta_lbl.grid(row=row_idx, column=4, padx=6, pady=1, sticky="w")
            self.summary_table_rows[ability] = {
                "roll": roll_lbl,
                "total": total_lbl,
                "mod": mod_lbl,
                "delta": delta_lbl,
            }

        # Capture the default label text color so we can restore it after highlighting deltas.
        try:
            any_delta = next(iter(self.summary_table_rows.values()))["delta"]
            self._summary_default_text_color = any_delta.cget("text_color")
        except Exception:
            self._summary_default_text_color = None

        ctk.CTkLabel(self.summary_bar, text="Gains", font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", padx=8, pady=(2, 4))
        self.gains_box = ctk.CTkTextbox(self.summary_bar, width=290, height=360, activate_scrollbars=True)
        self.gains_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.gains_box.configure(state="disabled")

        self.right = ctk.CTkFrame(self.main)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.grid_rowconfigure(0, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        self.body = ctk.CTkFrame(self.right)
        self.body.grid(row=0, column=0, sticky="nsew")

        nav = ctk.CTkFrame(self)
        nav.grid(row=1, column=0, sticky="ew", padx=12, pady=(10, 10))
        self.status = ctk.CTkLabel(nav, text="Fill in each step", anchor="w")
        self.status.grid(row=0, column=0, sticky="w")
        self.btn_back = ctk.CTkButton(nav, text="Back", command=self._prev, state="disabled", width=80)
        self.btn_back.grid(row=0, column=1, padx=6)
        self.btn_next = ctk.CTkButton(nav, text="Next", command=self._next, width=100)
        self.btn_next.grid(row=0, column=2, padx=6)

        self._render_current_step()
        self._update_summary_bar()

    def _cleanup_scaling_tracker(self):
        """Best-effort cleanup to prevent CustomTkinter DPI scaling callbacks firing during destroy."""
        try:
            from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker  # type: ignore

            cb = getattr(self, "_set_scaling", None)
            if cb is not None:
                try:
                    ScalingTracker.remove_window(cb, self)
                except Exception:
                    pass

            # Some CTk versions keep the window in dpi dict; remove defensively.
            try:
                if self in ScalingTracker.window_dpi_scaling_dict:
                    del ScalingTracker.window_dpi_scaling_dict[self]
            except Exception:
                pass
        except Exception:
            pass

    def _on_close(self):
        try:
            logger.info("Wizard close requested")
        except Exception:
            pass
        self._cleanup_scaling_tracker()
        try:
            self.destroy()
        except Exception:
            # If destroy fails, log and swallow to avoid a hard crash.
            try:
                logger.exception("Wizard destroy failed")
            except Exception:
                pass

    # --------------------------- nav helpers ---------------------------
    def _set_status(self, msg: str):
        self.status.configure(text=msg)
        try:
            logger.info("Wizard status: %s", msg)
        except Exception:
            pass

    def _render_current_step(self):
        for child in self.body.winfo_children():
            child.destroy()
        title, renderer = self.steps[self.step_index]
        ctk.CTkLabel(self.body, text=title, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill="x", pady=6)
        renderer()
        self.btn_back.configure(state="normal" if self.step_index > 0 else "disabled")
        self.btn_next.configure(text="Create" if self.step_index == len(self.steps) - 1 else "Next")
        self._set_status(f"Step {self.step_index + 1} of {len(self.steps)}: {title}")
        self._update_summary_bar()

    def _next(self):
        if not self._validate_and_store():
            return
        if self.step_index == len(self.steps) - 1:
            self._finalize()
            return
        self.step_index += 1
        self._render_current_step()

    def _prev(self):
        if self.step_index > 0:
            self.step_index -= 1
            self._render_current_step()

    # --------------------------- step renderers ---------------------------
    def _render_basics(self):
        frame = ctk.CTkFrame(self.body)
        frame.pack(fill="x", padx=8, pady=8)
        basics = [
            ("Name", self.var_name),
            ("Player", self.var_player),
            ("Height", self.var_height),
            ("Weight", self.var_weight),
            ("Age", self.var_age),
            ("Eyes", self.var_eyes),
            ("Skin", self.var_skin),
            ("Hair", self.var_hair),
        ]
        for idx, (label, var) in enumerate(basics):
            ctk.CTkLabel(frame, text=label).grid(row=idx, column=0, padx=8, pady=4, sticky="e")
            ctk.CTkEntry(frame, textvariable=var, width=260).grid(row=idx, column=1, padx=8, pady=4, sticky="w")

    def _render_scores(self):
        frame = ctk.CTkFrame(self.body)
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        mode_row = ctk.CTkFrame(frame)
        mode_row.grid(row=0, column=0, sticky="w", pady=6)
        ctk.CTkLabel(mode_row, text="Method:").pack(side="left", padx=4)
        ctk.CTkOptionMenu(mode_row, variable=self.mode_var, values=["Point Buy", "Standard Array", "Roll"], command=lambda _: self._on_mode_change()).pack(side="left", padx=4)

        # Point buy section
        self.point_buy_frame = ctk.CTkFrame(frame)
        self.point_buy_frame.grid(row=1, column=0, sticky="nw")
        self.point_buy_label = ctk.CTkLabel(self.point_buy_frame, text="Point Buy: 30 points remaining (scores 8-16)", anchor="w")
        self.point_buy_label.grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=4)
        for idx, ability in enumerate(self.abilities, start=1):
            ctk.CTkLabel(self.point_buy_frame, text=ability).grid(row=idx, column=0, padx=8, pady=4, sticky="e")
            minus = ctk.CTkButton(self.point_buy_frame, text="-", width=28, command=lambda n=ability: self._point_buy_adjust(n, -1))
            plus = ctk.CTkButton(self.point_buy_frame, text="+", width=28, command=lambda n=ability: self._point_buy_adjust(n, 1))
            minus.grid(row=idx, column=1, padx=2, pady=4, sticky="e")
            plus.grid(row=idx, column=2, padx=2, pady=4, sticky="w")
            entry = ctk.CTkEntry(self.point_buy_frame, textvariable=self.ability_vars[ability], width=70)
            entry.grid(row=idx, column=3, padx=8, pady=4, sticky="w")
            self.ability_entries[ability] = entry

        # Standard array section
        self.standard_frame = ctk.CTkFrame(frame)
        self.standard_frame.grid(row=2, column=0, sticky="nw", pady=10)
        ctk.CTkLabel(self.standard_frame, text="Standard Array (pick 6 of 7): 15, 14, 13, 12, 11, 10, 8", anchor="w").grid(row=0, column=0, padx=8, pady=4, sticky="w")
        ctk.CTkButton(self.standard_frame, text="Auto-assign in order", width=160, command=self._apply_standard_array).grid(row=0, column=1, padx=8, pady=4, sticky="w")
        self.standard_pool_label = ctk.CTkLabel(self.standard_frame, text="Assign each value once", anchor="w")
        self.standard_pool_label.grid(row=1, column=0, columnspan=2, padx=8, pady=4, sticky="w")
        for idx, ability in enumerate(self.abilities, start=2):
            ctk.CTkLabel(self.standard_frame, text=ability).grid(row=idx, column=0, padx=8, pady=4, sticky="e")
            var = ctk.StringVar(value="")
            menu = ctk.CTkOptionMenu(self.standard_frame, variable=var, values=[""], command=lambda choice, n=ability: self._on_standard_pick(n, choice))
            menu.grid(row=idx, column=1, padx=8, pady=4, sticky="w")
            self.standard_choice_vars[ability] = var
            self.standard_option_menus[ability] = menu

        # Roll section
        self.roll_frame = ctk.CTkFrame(frame)
        self.roll_frame.grid(row=3, column=0, sticky="nw")
        roll_top = ctk.CTkFrame(self.roll_frame)
        roll_top.grid(row=0, column=0, columnspan=3, sticky="w", pady=4)
        ctk.CTkButton(roll_top, text="Roll 6 values (4d6 drop lowest)", width=230, command=self._roll_values).pack(side="left", padx=4)
        self.roll_pool_label = ctk.CTkLabel(roll_top, text="Roll to generate values", anchor="w")
        self.roll_pool_label.pack(side="left", padx=6)

        for idx, ability in enumerate(self.abilities, start=1):
            ctk.CTkLabel(self.roll_frame, text=ability).grid(row=idx, column=0, padx=8, pady=4, sticky="e")
            var = ctk.StringVar(value="")
            menu = ctk.CTkOptionMenu(self.roll_frame, variable=var, values=[""], command=lambda choice, n=ability: self._on_roll_pick(n, choice))
            menu.grid(row=idx, column=1, padx=8, pady=4, sticky="w")
            self.roll_choice_vars[ability] = var
            self.roll_option_menus[ability] = menu

        self._on_mode_change()

    def _render_heritage(self):
        frame = ctk.CTkFrame(self.body)
        frame.pack(fill="both", expand=True, padx=8, pady=8)
        races = list(self.base_builder.races.keys())
        ancestries = self._ancestries_for_race(self.var_race.get())

        ctk.CTkLabel(frame, text="Race").grid(row=0, column=0, padx=8, pady=6, sticky="e")
        ctk.CTkOptionMenu(
            frame,
            variable=self.var_race,
            values=races,
            command=lambda _: (self._refresh_ancestries(), self._maybe_seed_point_buy_from_heritage()),
        ).grid(row=0, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(frame, text="Ancestry").grid(row=1, column=0, padx=8, pady=6, sticky="e")
        self.ancestry_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.var_ancestry,
            values=ancestries,
            command=lambda _: (self._update_heritage_info(), self._maybe_seed_point_buy_from_heritage()),
        )
        self.ancestry_menu.grid(row=1, column=1, padx=8, pady=6, sticky="w")

        info = ctk.CTkTextbox(frame, width=560, height=260, activate_scrollbars=True)
        info.grid(row=2, column=0, columnspan=2, padx=8, pady=8, sticky="nsew")
        info.configure(state="disabled")
        self.heritage_info = info
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        self._update_heritage_info()

        # Keep physical traits in sync with heritage defaults until the user edits them.
        self._maybe_seed_physical_traits_from_heritage()

    def _heritage_ability_modifiers(self) -> Dict[str, int]:
        """Combined ability modifiers from selected race + ancestry."""
        mods: Dict[str, int] = {a: 0 for a in self.abilities}
        race = self.base_builder.races.get(self.var_race.get())
        ancestry = self.base_builder.ancestries.get(self.var_ancestry.get())

        def _apply(source: Dict[str, int] | None):
            if not source:
                return
            for key, value in source.items():
                if key in mods:
                    mods[key] += int(value)

        _apply(getattr(race, "ability_modifiers", None) if race else None)
        _apply(getattr(ancestry, "ability_modifiers", None) if ancestry else None)
        return mods

    def _maybe_seed_point_buy_from_heritage(self, force: bool = False):
        """Seed point-buy starting scores.

        For Point Buy we start at 8 across the board (player allocates points manually).
        This will not overwrite user edits unless forced.
        """
        if not force and self._scores_user_modified:
            return

        race_id = self.var_race.get()
        ancestry_id = self.var_ancestry.get()
        heritage_key = (race_id, ancestry_id)
        if not force and self._scores_seeded_for_heritage == heritage_key:
            return

        # If the user has already entered values (e.g. loaded via step nav), don't overwrite unless forced.
        existing = [self.ability_vars[a].get().strip() for a in self.abilities]
        has_any_value = any(v for v in existing)
        if has_any_value and not force:
            return

        for ability in self.abilities:
            self.ability_vars[ability].set("8")

        self._scores_seeded_for_heritage = heritage_key
        self._scores_confirmed = False
        self._update_point_buy_label(show=(self.mode_var.get() == "Point Buy"))
        self._update_summary_bar()

    def _maybe_seed_physical_traits_from_heritage(self, force: bool = False):
        """Seed basic physical traits from race/ancestry unless the user has edited them."""
        if not force and self._physical_user_modified:
            return

        race_id = self.var_race.get()
        ancestry_id = self.var_ancestry.get()
        heritage_key = (race_id, ancestry_id)
        if not force and self._physical_seeded_for_heritage == heritage_key:
            return

        # If user already filled anything and we're not forcing, avoid clobbering.
        existing = [
            self.var_height.get().strip(),
            self.var_weight.get().strip(),
            self.var_age.get().strip(),
            self.var_eyes.get().strip(),
            self.var_skin.get().strip(),
            self.var_hair.get().strip(),
        ]
        if any(existing) and not force and self._physical_seeded_for_heritage is not None:
            return

        defaults = self._physical_defaults_for_heritage(race_id, ancestry_id)
        self._seeding_physical = True
        try:
            self.var_height.set(defaults["height"])
            self.var_weight.set(defaults["weight"])
            self.var_age.set(defaults["age"])
            self.var_eyes.set(defaults["eyes"])
            self.var_skin.set(defaults["skin"])
            self.var_hair.set(defaults["hair"])
        finally:
            self._seeding_physical = False

        self._physical_seeded_for_heritage = heritage_key

    def _physical_defaults_for_heritage(self, race_id: str, ancestry_id: str) -> Dict[str, str]:
        """Generate race-appropriate default physical traits.

        The UI fields remain free-form, but we seed them with plausible defaults.
        """

        def _height_str(total_inches: int) -> str:
            feet = total_inches // 12
            inches = total_inches % 12
            return f"{feet}'{inches}\""

        def _pick(options: Any, fallback: str) -> str:
            if isinstance(options, list) and options and all(isinstance(x, str) for x in options):
                return random.choice(options)
            return fallback

        race = self.base_builder.races.get(race_id)
        ancestry = self.base_builder.ancestries.get(ancestry_id)
        _ = ancestry  # reserved for future ancestry-specific tweaks

        # Broad defaults by race id. Values are intentionally approximate.
        profiles: Dict[str, Dict[str, Any]] = {
            "elf": {
                "height_in": (66, 78),
                "weight_lb": (120, 190),
                "age": (30, 140),
                "eyes": ["Green", "Blue", "Hazel", "Violet", "Silver"],
                "skin": ["Fair", "Tan", "Copper", "Pale"],
                "hair": ["Black", "Brown", "Blonde", "Silver"],
            },
            "dwarf": {
                "height_in": (48, 58),
                "weight_lb": (140, 220),
                "age": (30, 120),
                "eyes": ["Brown", "Hazel", "Gray", "Green", "Blue"],
                "skin": ["Tan", "Ruddy", "Brown", "Pale"],
                "hair": ["Black", "Brown", "Red", "Gray"],
            },
            "halffolk": {
                "height_in": (36, 46),
                "weight_lb": (40, 85),
                "age": (18, 70),
                "eyes": ["Brown", "Hazel", "Green", "Blue"],
                "skin": ["Fair", "Tan", "Brown"],
                "hair": ["Brown", "Black", "Blonde", "Red"],
            },
            "human": {
                "height_in": (60, 76),
                "weight_lb": (110, 220),
                "age": (18, 60),
                "eyes": ["Brown", "Blue", "Green", "Hazel", "Gray", "Amber"],
                "skin": ["Pale", "Fair", "Tan", "Brown", "Dark"],
                "hair": ["Black", "Brown", "Blonde", "Red", "Gray"],
            },
            "goblin": {
                "height_in": (42, 54),
                "weight_lb": (55, 110),
                "age": (14, 40),
                "eyes": ["Yellow", "Red", "Orange", "Green"],
                "skin": ["Green", "Olive", "Gray"],
                "hair": ["Black", "Brown", "None"],
            },
            "taurin": {
                "height_in": (74, 90),
                "weight_lb": (260, 420),
                "age": (18, 60),
                "eyes": ["Brown", "Amber", "Gold"],
                "skin": ["Brown", "Dark"],
                "hair": ["Black", "Brown", "Dark Brown"],
            },
            "velkarr": {
                "height_in": (66, 80),
                "weight_lb": (130, 240),
                "age": (20, 90),
                "eyes": ["Red", "Purple", "Silver", "Gray"],
                "skin": ["Pale", "Gray", "Ash"],
                "hair": ["Black", "White", "Silver"],
            },
            "simari": {
                "height_in": (60, 76),
                "weight_lb": (110, 220),
                "age": (18, 70),
                "eyes": ["Amber", "Brown", "Blue", "Green"],
                "skin": ["Tan", "Brown", "Olive"],
                "hair": ["Black", "Brown", "Dark Brown"],
            },
        }

        profile = profiles.get(race_id)
        if not profile:
            # Fallback: use size to guess a rough range.
            size = getattr(race, "size", "Medium") if race else "Medium"
            if str(size).lower() == "small":
                profile = {"height_in": (42, 54), "weight_lb": (55, 120), "age": (18, 60)}
            elif str(size).lower() == "large":
                profile = {"height_in": (74, 92), "weight_lb": (240, 420), "age": (18, 60)}
            else:
                profile = {"height_in": (60, 76), "weight_lb": (110, 220), "age": (18, 60)}

        hmin, hmax = profile.get("height_in", (60, 76))
        wmin, wmax = profile.get("weight_lb", (110, 220))
        amin, amax = profile.get("age", (18, 60))

        height = _height_str(random.randint(int(hmin), int(hmax)))
        weight = f"{random.randint(int(wmin), int(wmax))} lb"
        age = str(random.randint(int(amin), int(amax)))

        # Sensible defaults for appearance.
        eyes = _pick(profile.get("eyes", []), "Brown")
        skin = _pick(profile.get("skin", []), "Tan")
        hair = _pick(profile.get("hair", []), "Brown")

        return {
            "height": height,
            "weight": weight,
            "age": age,
            "eyes": eyes,
            "skin": skin,
            "hair": hair,
        }

    def _render_profession(self):
        frame = ctk.CTkFrame(self.body)
        frame.pack(fill="both", expand=True, padx=8, pady=8)
        profs = list(self.base_builder.professions.keys())
        ctk.CTkLabel(frame, text="Profession").grid(row=0, column=0, padx=8, pady=6, sticky="e")
        ctk.CTkOptionMenu(frame, variable=self.var_prof, values=profs, command=lambda _: self._refresh_duties()).grid(row=0, column=1, padx=8, pady=6, sticky="w")

        self.duty_row = ctk.CTkFrame(frame)
        self.duty_row.grid(row=1, column=0, columnspan=2, sticky="w")
        ctk.CTkLabel(self.duty_row, text="Duty (Warrior only)").grid(row=0, column=0, padx=8, pady=6, sticky="e")
        self.duty_menu = ctk.CTkOptionMenu(self.duty_row, variable=self.var_duty, values=self._duties_for_profession(self.var_prof.get()))
        self.duty_menu.grid(row=0, column=1, padx=8, pady=6, sticky="w")
        self._toggle_duty_visibility()

        info = ctk.CTkTextbox(frame, width=560, height=220, activate_scrollbars=True)
        info.grid(row=2, column=0, columnspan=2, padx=8, pady=8, sticky="nsew")
        info.configure(state="disabled")
        self.profession_info = info
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        self._update_profession_info()

    def _render_path(self):
        frame = ctk.CTkFrame(self.body)
        frame.pack(fill="both", expand=True, padx=8, pady=8)
        options = self._path_options()
        ctk.CTkLabel(frame, text="Path (met prereqs marked *)").grid(row=0, column=0, padx=8, pady=6, sticky="e")
        self.path_menu = ctk.CTkOptionMenu(frame, variable=self.var_path, values=options, command=lambda _: self._update_path_info())
        self.path_menu.grid(row=0, column=1, padx=8, pady=6, sticky="w")
        note_box = ctk.CTkTextbox(frame, width=540, height=180, activate_scrollbars=True)
        note_box.configure(state="disabled")
        note_box.grid(row=1, column=0, columnspan=2, padx=8, pady=8, sticky="nsew")
        self.path_info = note_box
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        self._update_path_info()

    def _render_background(self):
        frame = ctk.CTkFrame(self.body)
        frame.pack(fill="x", padx=8, pady=8)
        bgs = list(self.base_builder.backgrounds.keys())
        ctk.CTkLabel(frame, text="Background").grid(row=0, column=0, padx=8, pady=6, sticky="e")
        ctk.CTkOptionMenu(frame, variable=self.var_bg, values=bgs, command=lambda _: self._update_background_info()).grid(row=0, column=1, padx=8, pady=6, sticky="w")
        info = ctk.CTkTextbox(frame, width=560, height=200, activate_scrollbars=True)
        info.grid(row=1, column=0, columnspan=2, padx=8, pady=8, sticky="nsew")
        info.configure(state="disabled")
        self.background_info = info
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        self._update_background_info()

    def _render_choices(self):
        frame = ctk.CTkFrame(self.body)
        frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.choice_records = []
        self.human_mode_var.set("")
        try:
            preview = self._build_preview_builder(check_path=True)
        except Exception as e:
            ctk.CTkLabel(frame, text=f"Cannot build choices: {e}", fg_color="transparent").pack(pady=10)
            return

        pending = preview.get_pending_choices()
        if not pending:
            ctk.CTkLabel(frame, text="No additional choices required.").pack(pady=12)
            return

        scroll = ctk.CTkScrollableFrame(frame, width=640, height=360)
        scroll.pack(fill="both", expand=True)
        ability_list = self.abilities

        for idx, choice in enumerate(pending):
            self._add_choice_row(scroll, idx, choice, ability_list)

        # Human mode follow-up selectors
        self.human_follow_frame = ctk.CTkFrame(scroll)
        self.human_follow_frame.pack(fill="x", pady=4)
        self._render_human_followups(ability_list)

    def _build_preview_with_choices(self):
        """Build a preview builder and apply the currently selected UI choices."""
        preview = self._build_preview_builder(check_path=True)
        # Apply explicit choices captured in UI
        for record in self.choice_records:
            choice = record["choice"]
            selections = record["getter"]()
            preview.resolve_choice(choice.choice_type, selections, source=choice.source)

        # Apply chained human adjustments (if present)
        if self.human_mode_var.get():
            mode = self.human_mode_var.get()
            pending_types = {c.choice_type for c in preview.get_pending_choices()}
            if "human_ability_mode" in pending_types:
                preview.resolve_choice("human_ability_mode", [mode])
            if "+2" in mode:
                if "ability_bonus_plus2" in {c.choice_type for c in preview.get_pending_choices()}:
                    preview.resolve_choice("ability_bonus_plus2", [self.human_plus2_var.get()])
                if "ability_penalty" in {c.choice_type for c in preview.get_pending_choices()}:
                    preview.resolve_choice("ability_penalty", [self.human_penalty_var.get()])
            else:
                if "ability_bonus" in {c.choice_type for c in preview.get_pending_choices()}:
                    preview.resolve_choice("ability_bonus", [self.human_plusone_var.get()])

        preview.recalculate_all()
        return preview

    def _calculate_level1_talent_points(self, preview: CharacterBuilder) -> int:
        """TP = primary path's core ability mod + 5."""
        path_id = self._path_id_from_value(self.var_path.get())
        path = preview.paths.get(path_id)
        if not path:
            return 5
        attr = getattr(path, "talent_points_attribute", "")
        score = preview.character.ability_scores.get(attr)
        mod = getattr(score, "mod", 0) if score else 0
        return int(mod) + 5

    def _talent_points_spent(self) -> tuple[int, int]:
        """Return (total_spent, primary_spent) for current talent state."""
        primary_path_id = self._path_id_from_value(self.var_path.get())
        total = 0
        primary = 0
        for tid, entry in self.level1_talent_state.items():
            rank = int(entry.get("rank", 0) or 0)
            if rank <= 0:
                continue
            tdef = self.talents_flat.get(tid)
            # total spent is sum of purchased ranks because rank N costs N
            spent_for_talent = sum(range(1, rank + 1))
            total += spent_for_talent
            if tdef and tdef.path_id == primary_path_id:
                primary += spent_for_talent
        return total, primary

    def _render_talents(self):
        frame = ctk.CTkFrame(self.body)
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        try:
            preview = self._build_preview_with_choices()
        except Exception as e:
            ctk.CTkLabel(frame, text=f"Cannot compute talents: {e}", fg_color="transparent").pack(pady=10)
            return

        tp_total = self._calculate_level1_talent_points(preview)
        min_primary = min(4, tp_total)
        spent_total, spent_primary = self._talent_points_spent()
        remaining = tp_total - spent_total
        primary_path_id = self._path_id_from_value(self.var_path.get())

        header = ctk.CTkFrame(frame)
        header.pack(fill="x", pady=(0, 8))
        self.talents_status_lbl = ctk.CTkLabel(
            header,
            text=f"Talent Points: {tp_total}  |  Remaining: {remaining}  |  Primary spent: {spent_primary}/{min_primary}",
            anchor="w",
        )
        self.talents_status_lbl.pack(side="left", fill="x", expand=True, padx=8, pady=6)
        ctk.CTkButton(header, text="Reset", width=80, command=self._reset_talents).pack(side="right", padx=8, pady=6)

        scroll = ctk.CTkScrollableFrame(frame)
        scroll.pack(fill="both", expand=True)

        def can_buy(tdef, current_ranks: Dict[str, int], target_rank: int) -> tuple[bool, list[str]]:
            return tdef.can_acquire(
                ability_scores=preview.character.ability_scores,
                level=preview.character.level,
                current_talents=current_ranks,
                target_rank=target_rank,
            )

        # Current ranks (only from this step)
        current_ranks = {tid: int(v.get("rank", 0) or 0) for tid, v in self.level1_talent_state.items()}

        shown_any = False

        # Always render purchased talents so they don't disappear on refresh
        selected_rows: list[dict[str, Any]] = []
        for tid, entry in self.level1_talent_state.items():
            rank = int(entry.get("rank", 0) or 0)
            if rank <= 0:
                continue
            tdef = self.talents_flat.get(tid)
            name = (tdef.name if tdef else (entry.get("name") or tid))
            path_id = (tdef.path_id if tdef and tdef.path_id else "general")
            selected_rows.append(
                {
                    "talent_id": tid,
                    "rank": rank,
                    "name": name,
                    "path_id": path_id,
                    "is_primary_path": path_id == primary_path_id,
                    "is_primary_talent": bool(getattr(tdef, "is_primary", False)) if tdef else False,
                    "requires_choice": bool(getattr(tdef, "requires_choice", False)) if tdef else False,
                    "choice_type": (getattr(tdef, "choice_type", "") if tdef else "") or "choice",
                    "choice_options": list(getattr(tdef, "choice_options", []) or []) if tdef else [],
                }
            )

        if selected_rows:
            shown_any = True
            ctk.CTkLabel(scroll, text="Selected Talents", font=("Segoe UI", 12, "bold"), anchor="w").pack(
                fill="x", padx=8, pady=(10, 4)
            )
            selected_rows.sort(
                key=lambda t: (
                    not t["is_primary_path"],
                    not t["is_primary_talent"],
                    str(t["path_id"]),
                    str(t["name"]).lower(),
                )
            )

            for row_info in selected_rows:
                tid = str(row_info["talent_id"])
                rank = int(row_info["rank"])
                name = str(row_info["name"])
                path_id = str(row_info["path_id"])

                row = ctk.CTkFrame(scroll)
                row.pack(fill="x", padx=6, pady=4)
                row.grid_columnconfigure(0, weight=1)
                row.grid_columnconfigure(1, weight=0)

                title_line = f"{name}  (Rank {rank})"
                title_line += f"  [{path_id}]" if path_id else ""
                ctk.CTkLabel(row, text=title_line, anchor="w", justify="left", wraplength=520).grid(
                    row=0,
                    column=0,
                    sticky="ew",
                    padx=6,
                    pady=4,
                )

                tdef = self.talents_flat.get(tid)
                details = _format_talent_ui_details(tdef, current_rank=rank, mode="current")
                if details:
                    ctk.CTkLabel(row, text=details, anchor="w", justify="left", wraplength=520).grid(
                        row=1,
                        column=0,
                        columnspan=2,
                        sticky="ew",
                        padx=6,
                        pady=(0, 6),
                    )

                btns = ctk.CTkFrame(row)
                btns.grid(row=0, column=1, sticky="e", padx=6)
                ctk.CTkButton(
                    btns,
                    text="Remove",
                    width=80,
                    command=lambda tid=tid: self._remove_talent_rank(tid),
                ).grid(row=0, column=0, padx=4)

                tdef = self.talents_flat.get(tid)
                if tdef and tdef.requires_choice:
                    existing_choice = (self.level1_talent_state.get(tid) or {}).get("choice_data") or {}
                    key = tdef.choice_type or "choice"
                    current_val = ""
                    if isinstance(existing_choice, dict):
                        current_val = str(existing_choice.get(key) or "")
                        if not current_val and existing_choice:
                            try:
                                current_val = str(next(iter(existing_choice.values())))
                            except Exception:
                                current_val = ""

                    choice_row = ctk.CTkFrame(row)
                    choice_row.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 6))
                    ctk.CTkLabel(choice_row, text="Choice:").grid(row=0, column=0, padx=4, sticky="e")
                    options = list(tdef.choice_options or [])
                    default_val = current_val or (options[0] if options else "")
                    var = ctk.StringVar(value=default_val)
                    menu = ctk.CTkOptionMenu(choice_row, variable=var, values=options)
                    menu.grid(row=0, column=1, padx=4, sticky="w")
                    ctk.CTkButton(
                        choice_row,
                        text="Set",
                        width=60,
                        command=lambda tid=tid, v=var: self._set_talent_choice(tid, v.get()),
                    ).grid(row=0, column=2, padx=6)

                    if current_val:
                        ctk.CTkLabel(choice_row, text=f"Current: {current_val}", anchor="w").grid(
                            row=0, column=3, padx=8, sticky="w"
                        )

        # Candidate talents = primary path first, then general
        primary_candidates = []
        general_candidates = []
        for key, target in [(primary_path_id, primary_candidates), ("general", general_candidates)]:
            cat = self.talent_categories.get(key)
            if not cat:
                continue
            for tdef in getattr(cat, "talents", []):
                target.append(tdef)

        def _render_section(title: str, talents: list):
            if not talents:
                return
            ctk.CTkLabel(scroll, text=title, font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", padx=8, pady=(10, 4))

            added = 0

            for tdef in sorted(talents, key=lambda t: (not bool(getattr(t, "is_primary", False)), t.name)):
                cur = int(current_ranks.get(tdef.id, 0))
                if cur >= tdef.max_rank:
                    continue
                nxt = cur + 1
                cost = tdef.get_tp_cost(cur, nxt)
                if cost > remaining:
                    continue
                ok, _reasons = can_buy(tdef, current_ranks, nxt)
                if not ok:
                    continue

                row = ctk.CTkFrame(scroll)
                row.pack(fill="x", padx=6, pady=4)
                row.grid_columnconfigure(0, weight=1)
                row.grid_columnconfigure(1, weight=0)
                title_line = f"{tdef.name}  (Rank {cur} → {nxt}, Cost {cost})"
                if tdef.path_id:
                    title_line += f"  [{tdef.path_id}]"
                else:
                    title_line += "  [general]"
                # Wrap the label so it doesn't push the action buttons off-screen.
                ctk.CTkLabel(row, text=title_line, anchor="w", justify="left", wraplength=520).grid(
                    row=0,
                    column=0,
                    sticky="ew",
                    padx=6,
                    pady=4,
                )

                details = _format_talent_ui_details(tdef, current_rank=cur, next_rank=nxt, mode="next")
                if details:
                    ctk.CTkLabel(row, text=details, anchor="w", justify="left", wraplength=520).grid(
                        row=1,
                        column=0,
                        columnspan=2,
                        sticky="ew",
                        padx=6,
                        pady=(0, 6),
                    )

                btns = ctk.CTkFrame(row)
                btns.grid(row=0, column=1, sticky="e", padx=6)

                ctk.CTkButton(
                    btns,
                    text="Buy",
                    width=70,
                    command=lambda tid=tdef.id: self._buy_talent_rank(tid),
                ).grid(row=0, column=0, padx=4)

                if cur > 0:
                    ctk.CTkButton(
                        btns,
                        text="Remove",
                        width=80,
                        command=lambda tid=tdef.id: self._remove_talent_rank(tid),
                    ).grid(row=0, column=1, padx=4)

                # Choice prompt (if needed and not yet selected)
                if tdef.requires_choice:
                    existing_choice = (self.level1_talent_state.get(tdef.id) or {}).get("choice_data")
                    if not existing_choice:
                        choice_row = ctk.CTkFrame(row)
                        choice_row.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 6))
                        ctk.CTkLabel(choice_row, text="Choice:").grid(row=0, column=0, padx=4, sticky="e")
                        var = ctk.StringVar(value=(tdef.choice_options[0] if tdef.choice_options else ""))
                        menu = ctk.CTkOptionMenu(choice_row, variable=var, values=list(tdef.choice_options or []))
                        menu.grid(row=0, column=1, padx=4, sticky="w")
                        ctk.CTkButton(
                            choice_row,
                            text="Set",
                            width=60,
                            command=lambda tid=tdef.id, v=var: self._set_talent_choice(tid, v.get()),
                        ).grid(row=0, column=2, padx=6)

                added += 1

            nonlocal shown_any
            if added:
                shown_any = True

        _render_section(f"Primary Path Talents ({primary_path_id})", primary_candidates)
        _render_section("General Talents", general_candidates)

        # If nothing is shown, explain why
        if not shown_any:
            ctk.CTkLabel(scroll, text="No talents available to purchase with current prerequisites/TP.").pack(pady=16)

        return

        # Render (legacy path; kept for safety)
        for tdef in []:
            cur = int(current_ranks.get(tdef.id, 0))
            if cur >= tdef.max_rank:
                continue
            nxt = cur + 1
            cost = tdef.get_tp_cost(cur, nxt)
            if cost > remaining:
                continue
            ok, reasons = can_buy(tdef, current_ranks, nxt)
            if not ok:
                continue

            row = ctk.CTkFrame(scroll)
            row.pack(fill="x", padx=6, pady=4)
            title = f"{tdef.name}  (Rank {cur} → {nxt}, Cost {cost})"
            if tdef.path_id:
                title += f"  [{tdef.path_id}]"
            ctk.CTkLabel(row, text=title, anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=4)

            btns = ctk.CTkFrame(row)
            btns.grid(row=0, column=1, sticky="e", padx=6)

            ctk.CTkButton(
                btns,
                text="Buy",
                width=70,
                command=lambda tid=tdef.id: self._buy_talent_rank(tid),
            ).grid(row=0, column=0, padx=4)

            if cur > 0:
                ctk.CTkButton(
                    btns,
                    text="Remove",
                    width=80,
                    command=lambda tid=tdef.id: self._remove_talent_rank(tid),
                ).grid(row=0, column=1, padx=4)

            # Choice prompt (if needed and not yet selected)
            if tdef.requires_choice:
                existing_choice = (self.level1_talent_state.get(tdef.id) or {}).get("choice_data")
                if not existing_choice:
                    choice_row = ctk.CTkFrame(row)
                    choice_row.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 6))
                    ctk.CTkLabel(choice_row, text="Choice:").grid(row=0, column=0, padx=4, sticky="e")
                    var = ctk.StringVar(value=(tdef.choice_options[0] if tdef.choice_options else ""))
                    menu = ctk.CTkOptionMenu(choice_row, variable=var, values=list(tdef.choice_options or []))
                    menu.grid(row=0, column=1, padx=4, sticky="w")
                    ctk.CTkButton(
                        choice_row,
                        text="Set",
                        width=60,
                        command=lambda tid=tdef.id, v=var: self._set_talent_choice(tid, v.get()),
                    ).grid(row=0, column=2, padx=6)

        # If nothing is shown, explain why
        if not scroll.winfo_children():
            ctk.CTkLabel(scroll, text="No talents available to purchase with current prerequisites/TP.").pack(pady=16)

    def _reset_talents(self):
        self.level1_talent_state = {}
        self._render_current_step()

    def _set_talent_choice(self, talent_id: str, value: str):
        tdef = self.talents_flat.get(talent_id)
        if not tdef:
            return
        entry = self.level1_talent_state.setdefault(talent_id, {"rank": 0, "choice_data": {}})
        key = tdef.choice_type or "choice"
        entry["choice_data"] = {key: value}
        self._render_current_step()

    def _buy_talent_rank(self, talent_id: str):
        tdef = self.talents_flat.get(talent_id)
        if not tdef:
            return
        entry = self.level1_talent_state.setdefault(talent_id, {"rank": 0, "choice_data": {}})
        current = int(entry.get("rank", 0) or 0)
        next_rank = current + 1

        try:
            preview = self._build_preview_with_choices()
            tp_total = self._calculate_level1_talent_points(preview)
            spent_total, _spent_primary = self._talent_points_spent()
            remaining = tp_total - spent_total
        except Exception:
            self._set_status("Cannot compute TP right now")
            return

        cost = tdef.get_tp_cost(current, next_rank)
        if cost > remaining:
            self._set_status("Not enough TP for that rank")
            return

        current_ranks = {tid: int(v.get("rank", 0) or 0) for tid, v in self.level1_talent_state.items()}
        can, reasons = tdef.can_acquire(
            ability_scores=preview.character.ability_scores,
            level=preview.character.level,
            current_talents=current_ranks,
            target_rank=next_rank,
        )
        if not can:
            reason = reasons[0] if reasons else "prerequisites not met"
            self._set_status(f"{tdef.name}: {reason}")
            return

        entry["rank"] = next_rank
        self._render_current_step()

    def _remove_talent_rank(self, talent_id: str):
        entry = self.level1_talent_state.get(talent_id)
        if not entry:
            return
        current = int(entry.get("rank", 0) or 0)
        if current <= 0:
            return
        entry["rank"] = current - 1
        if entry["rank"] <= 0:
            self.level1_talent_state.pop(talent_id, None)
        self._render_current_step()

    def _add_choice_row(self, parent, idx: int, choice, ability_list):
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=4, padx=4)
        title = f"{choice.source}: choose {choice.count} {choice.choice_type}"
        ctk.CTkLabel(row, text=title, anchor="w").pack(fill="x", pady=2)

        # For single selection prefer option menu
        if choice.count == 1 and len(choice.options) <= 20:
            var = ctk.StringVar(value=choice.options[0] if choice.options else "")
            menu = ctk.CTkOptionMenu(row, variable=var, values=choice.options, command=lambda _=None: self._on_choice_change(choice.choice_type))
            menu.pack(fill="x", padx=4, pady=2)
            getter = lambda v=var: [v.get()]
            if choice.choice_type == "human_ability_mode":
                self.human_mode_var.set(var.get())
        else:
            vars_list = []
            opts_frame = ctk.CTkFrame(row)
            opts_frame.pack(fill="x", padx=4)
            for opt in choice.options:
                var = ctk.BooleanVar(value=False)
                ctk.CTkCheckBox(opts_frame, text=opt, variable=var, command=lambda ct=choice.choice_type: self._on_choice_change(ct)).pack(anchor="w")
                vars_list.append((opt, var))
            getter = lambda lst=vars_list: [opt for opt, v in lst if v.get()]

        self.choice_records.append({"choice": choice, "getter": getter})

    def _render_human_followups(self, ability_list):
        for child in self.human_follow_frame.winfo_children():
            child.destroy()
        mode = self.human_mode_var.get()
        has_mode = any(rec["choice"].choice_type == "human_ability_mode" for rec in self.choice_records)
        if not has_mode:
            return
        ctk.CTkLabel(self.human_follow_frame, text="Human ability adjustments").pack(anchor="w", padx=4, pady=4)
        mode_box = ctk.CTkFrame(self.human_follow_frame)
        mode_box.pack(fill="x", padx=4, pady=2)
        ctk.CTkLabel(mode_box, text="Mode selected above determines these extra picks.").pack(anchor="w")
        if "+2" in mode:
            line = ctk.CTkFrame(self.human_follow_frame)
            line.pack(fill="x", padx=4, pady=4)
            ctk.CTkLabel(line, text="+2 to ability").grid(row=0, column=0, padx=4, sticky="e")
            ctk.CTkOptionMenu(line, variable=self.human_plus2_var, values=ability_list).grid(row=0, column=1, padx=4, sticky="w")
            line2 = ctk.CTkFrame(self.human_follow_frame)
            line2.pack(fill="x", padx=4, pady=4)
            ctk.CTkLabel(line2, text="-1 to ability").grid(row=0, column=0, padx=4, sticky="e")
            ctk.CTkOptionMenu(line2, variable=self.human_penalty_var, values=ability_list).grid(row=0, column=1, padx=4, sticky="w")
        elif mode:
            line = ctk.CTkFrame(self.human_follow_frame)
            line.pack(fill="x", padx=4, pady=4)
            ctk.CTkLabel(line, text="+1 to ability").grid(row=0, column=0, padx=4, sticky="e")
            ctk.CTkOptionMenu(line, variable=self.human_plusone_var, values=ability_list).grid(row=0, column=1, padx=4, sticky="w")

    def _on_choice_change(self, choice_type: str):
        if choice_type == "human_ability_mode":
            # Update mode var from record
            for record in self.choice_records:
                if record["choice"].choice_type == "human_ability_mode":
                    selection = record["getter"]()
                    if selection:
                        self.human_mode_var.set(selection[0])
                        break
            self._render_human_followups(self.abilities)

    # --------------------------- validation and build helpers ---------------------------
    def _abilities_dict(self, allow_incomplete: bool = False) -> Dict[str, int] | None:
        if self.mode_var.get() == "Roll":
            scores = {}
            for name, var in self.roll_choice_vars.items():
                val = var.get()
                if not val:
                    if allow_incomplete:
                        continue
                    self._set_status("Assign all rolled values")
                    return None
                scores[name] = int(val)
            return scores

        if self.mode_var.get() == "Standard Array":
            scores = {}
            for name, var in self.standard_choice_vars.items():
                val = var.get()
                if not val:
                    if allow_incomplete:
                        continue
                    self._set_status("Assign all standard array values")
                    return None
                scores[name] = int(val)
            return scores

        scores = {}
        for name, var in self.ability_vars.items():
            try:
                val = int(var.get())
            except ValueError:
                if allow_incomplete:
                    continue
                self._set_status(f"Ability {name} must be a number")
                return None
            scores[name] = val
        return scores

    def _on_mode_change(self):
        mode = self.mode_var.get()
        # Show only the active method
        for f in [self.point_buy_frame, self.standard_frame, self.roll_frame]:
            f.grid_remove()
        if mode == "Point Buy":
            self.point_buy_frame.grid()
            # Point Buy should start at 8s (unless the user already tweaked point-buy values).
            if not self._scores_user_modified:
                self._maybe_seed_point_buy_from_heritage(force=True)
            for entry in self.ability_entries.values():
                entry.configure(state="disabled")
            self._update_point_buy_label()
            self._update_summary_bar()
        elif mode == "Standard Array":
            self.standard_frame.grid()
            for var in self.standard_choice_vars.values():
                var.set("")
            self._refresh_standard_options()
            for entry in self.ability_entries.values():
                entry.configure(state="disabled")
            self._update_point_buy_label(show=False)
            self._update_summary_bar()
        elif mode == "Roll":
            self.roll_frame.grid()
            for entry in self.ability_entries.values():
                entry.configure(state="disabled")
            self._update_point_buy_label(show=False)
            self._update_summary_bar()
        else:
            self.point_buy_frame.grid()

    POINT_BUY_COST = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9, 16: 11}

    def _point_buy_remaining(self, scores: Dict[str, int]) -> int:
        spent = 0
        for val in scores.values():
            if val < 8 or val > 16:
                return -1
            cost = self.POINT_BUY_COST.get(val, 0)
            spent += cost
        return self.point_buy_budget - spent

    def _update_point_buy_label(self, show: bool = True):
        if not self.point_buy_label:
            return
        if not show:
            self.point_buy_label.configure(text="Point Buy: (not active)")
            return
        scores = self._abilities_dict(allow_incomplete=True) or {}
        remaining = self._point_buy_remaining(scores) if scores else self.point_buy_budget
        self.point_buy_label.configure(text=f"Point Buy: {remaining} points remaining")

    def _point_buy_adjust(self, ability: str, delta: int):
        if self.mode_var.get() != "Point Buy":
            return
        self._scores_user_modified = True
        self._scores_confirmed = False
        try:
            current = int(self.ability_vars[ability].get())
        except ValueError:
            current = 8
        new = max(8, min(16, current + delta))
        scores = self._abilities_dict(allow_incomplete=True) or {}
        scores[ability] = new
        remaining = self._point_buy_remaining(scores)
        if remaining < 0:
            self._set_status("Point buy over budget")
            return
        self.ability_vars[ability].set(str(new))
        self._update_point_buy_label()
        self._update_summary_bar()

    def _apply_standard_array(self):
        self._scores_user_modified = True
        self._scores_confirmed = False
        array = [15, 14, 13, 12, 11, 10]  # auto-assign top six, leave 8 unused
        for name, val in zip(self.abilities, array):
            self.standard_choice_vars[name].set(str(val))
        self._refresh_standard_options()
        self._update_summary_bar()

    def _roll_values(self):
        self._scores_user_modified = True
        self._scores_confirmed = False
        if self.mode_var.get() != "Roll":
            self.mode_var.set("Roll")
            self._on_mode_change()
        self.rolled_values = []
        for _ in range(6):
            rolls = sorted([random.randint(1, 6) for _ in range(4)])
            self.rolled_values.append(sum(rolls[1:]))
        for var in self.roll_choice_vars.values():
            var.set("")
        self._refresh_roll_options()
        self._update_summary_bar()

    def _remaining_roll_pool(self) -> list[int]:
        remaining = list(self.rolled_values)
        for val in [v.get() for v in self.roll_choice_vars.values() if v.get()]:
            try:
                remaining.remove(int(val))
            except ValueError:
                continue
        return remaining

    def _refresh_roll_options(self):
        if not hasattr(self, "rolled_values"):
            self.rolled_values = []
        remaining = self._remaining_roll_pool()
        pool_text = ", ".join(str(v) for v in remaining) if remaining else "assign all values"
        if not self.rolled_values:
            pool_text = "Roll to generate values"
        self.roll_pool_label.configure(text=f"Rolls remaining: {pool_text}")
        for ability, menu in self.roll_option_menus.items():
            current = self.roll_choice_vars[ability].get()
            options = [str(v) for v in remaining]
            if current and current not in options:
                options.append(current)
            menu.configure(values=options or [""])
            if current and current not in options:
                menu.set(current)

    def _standard_remaining_pool(self) -> list[int]:
        pool = [15, 14, 13, 12, 11, 10, 8]
        remaining = list(pool)
        for val in [v.get() for v in self.standard_choice_vars.values() if v.get()]:
            try:
                remaining.remove(int(val))
            except ValueError:
                continue
        return remaining

    def _refresh_standard_options(self):
        remaining = self._standard_remaining_pool()
        expected_left = 1
        if len(remaining) > expected_left:
            pool_text = ", ".join(str(v) for v in remaining)
        elif len(remaining) == expected_left:
            pool_text = f"{remaining[0]} (unused)"
        else:
            pool_text = "assigned"
        self.standard_pool_label.configure(text=f"Standard pool remaining: {pool_text}")
        for ability, menu in self.standard_option_menus.items():
            current = self.standard_choice_vars[ability].get()
            options = [str(v) for v in remaining]
            if current and current not in options:
                options.append(current)
            menu.configure(values=options or [""])
            if current and current not in options:
                menu.set(current)

    def _on_standard_pick(self, ability: str, choice: str):
        self._scores_user_modified = True
        self._scores_confirmed = False
        if choice:
            self.standard_choice_vars[ability].set(choice)
        self._refresh_standard_options()
        self._update_summary_bar()

    def _on_roll_pick(self, ability: str, choice: str):
        self._scores_user_modified = True
        self._scores_confirmed = False
        if choice:
            self.roll_choice_vars[ability].set(choice)
        self._refresh_roll_options()
        self._update_summary_bar()

    def _ancestries_for_race(self, race_id: str):
        values = [a.id for a in self.base_builder.ancestries.values() if a.race_id == race_id]
        return values or [self.var_ancestry.get()]

    def _refresh_ancestries(self):
        values = self._ancestries_for_race(self.var_race.get())
        self.var_ancestry.set(values[0])
        self.ancestry_menu.configure(values=values)
        self._update_heritage_info()
        self._maybe_seed_point_buy_from_heritage()
        self._maybe_seed_physical_traits_from_heritage()
        self._update_summary_bar()

    def _duties_for_profession(self, prof_id: str):
        prof = self.base_builder.professions.get(prof_id)
        if not prof or not prof.duties:
            return [""]
        return [d.id for d in prof.duties]

    def _refresh_duties(self):
        values = self._duties_for_profession(self.var_prof.get())
        self.var_duty.set(values[0])
        self.duty_menu.configure(values=values)
        self._toggle_duty_visibility()
        self._update_profession_info()
        self._update_summary_bar()

    def _toggle_duty_visibility(self):
        prof = self.base_builder.professions.get(self.var_prof.get())
        if prof and prof.duties:
            self.duty_row.grid()
        else:
            self.var_duty.set("")
            self.duty_row.grid_remove()

    def _path_label(self, path_obj, meets: bool) -> str:
        suffix = " *" if meets else ""
        return f"{path_obj.id}{suffix}"

    def _path_id_from_value(self, value: str) -> str:
        return value.replace(" *", "") if value else value

    def _path_options(self):
        try:
            preview = self._build_preview_builder(stop_after="profession", check_path=False)
        except Exception:
            preview = self.base_builder
        entries = []
        for path, meets in preview.get_available_paths():
            entries.append((meets, path.name, self._path_label(path, meets), path.id))
        # Sort: met first, then name
        entries.sort(key=lambda t: (not t[0], t[1]))
        values = [label for _, _, label, _ in entries]
        current_id = self._path_id_from_value(self.var_path.get())
        match_label = next((label for _, _, label, pid in entries if pid == current_id), None)
        if match_label:
            self.var_path.set(match_label)
        elif values:
            self.var_path.set(values[0])
        return values

    def _profession_info_text(self, prof_id: str, duty_id: str | None) -> str:
        prof = self.base_builder.professions.get(prof_id)
        if not prof:
            return "Select a profession to view details."
        lines = [f"Profession: {prof.name}"]
        if prof.description:
            lines.append(prof.description)
        if prof.skill_proficiencies:
            lines.append(f"Skill Proficiencies: {', '.join(prof.skill_proficiencies)}")
        if prof.skill_choices:
            c = prof.skill_choices
            lines.append(f"Choose {c.get('count',1)} skill(s): {', '.join(c.get('options', []))}")
        if prof.tool_proficiencies:
            lines.append(f"Tool Proficiencies: {', '.join(prof.tool_proficiencies)}")
        if prof.tool_choices:
            c = prof.tool_choices
            lines.append(f"Choose {c.get('count',1)} tool(s): {', '.join(c.get('options', []))}")
        if prof.armor_proficiencies:
            lines.append(f"Armor: {', '.join(prof.armor_proficiencies)}")
        if prof.weapon_proficiencies:
            lines.append(f"Weapons: {', '.join(prof.weapon_proficiencies)}")
        if prof.feature:
            lines.append(f"Feature: {prof.feature.name} - {prof.feature.description}")
        if prof.duties:
            lines.append("Duties:")
            for d in prof.duties:
                marker = " (selected)" if duty_id and d.id == duty_id else ""
                lines.append(f"- {d.name}{marker}: {d.description}")
                if d.skill_choices:
                    c = d.skill_choices
                    lines.append(f"  Choose {c.get('count',1)} skill(s): {', '.join(c.get('options', []))}")
                if d.tool_choices:
                    c = d.tool_choices
                    lines.append(f"  Choose {c.get('count',1)} tool(s): {', '.join(c.get('options', []))}")
        return "\n".join(lines)

    def _update_profession_info(self):
        if not hasattr(self, "profession_info"):
            return
        text = self._profession_info_text(self.var_prof.get(), self.var_duty.get() or None)
        self.profession_info.configure(state="normal")
        self.profession_info.delete("1.0", "end")
        self.profession_info.insert("1.0", text)
        self.profession_info.configure(state="disabled")
        self._update_summary_bar()

    def _heritage_info_text(self, race_id: str, ancestry_id: str) -> str:
        lines = []
        race = self.base_builder.races.get(race_id)
        ancestry = self.base_builder.ancestries.get(ancestry_id)
        if race:
            lines.append(f"Race: {race.name}")
            if race.description:
                lines.append(race.description)
            lines.append(f"Size {race.size}, Speed {race.speed}")
            if race.languages:
                lines.append(f"Languages: {', '.join(race.languages)}")
            if race.ability_modifiers:
                mods = ", ".join([f"{k} {'+' if v>=0 else ''}{v}" for k, v in race.ability_modifiers.items()])
                lines.append(f"Ability Adjustments: {mods}")
            if race.features:
                lines.append("Race Features:")
                for feat in race.features:
                    lines.append(f"- {feat.name}: {feat.description}")
        if ancestry:
            lines.append("")
            lines.append(f"Ancestry: {ancestry.name}")
            if ancestry.description:
                lines.append(ancestry.description)
            if ancestry.region:
                lines.append(f"Region: {ancestry.region}")
            if ancestry.languages:
                lines.append(f"Languages: {', '.join(ancestry.languages)}")
            if ancestry.ability_modifiers:
                mods = ", ".join([f"{k} {'+' if v>=0 else ''}{v}" for k, v in ancestry.ability_modifiers.items()])
                lines.append(f"Ability Adjustments: {mods}")
            if ancestry.skill_proficiencies:
                lines.append(f"Skill Proficiencies: {', '.join(ancestry.skill_proficiencies)}")
            if ancestry.tool_proficiencies:
                lines.append(f"Tool Proficiencies: {', '.join(ancestry.tool_proficiencies)}")
            if ancestry.features:
                lines.append("Ancestry Traits:")
                for feat in ancestry.features:
                    lines.append(f"- {feat.name}: {feat.description}")
        return "\n".join(lines) if lines else "Select a race and ancestry to see details."

    def _update_heritage_info(self):
        if not hasattr(self, "heritage_info"):
            return
        text = self._heritage_info_text(self.var_race.get(), self.var_ancestry.get())
        self.heritage_info.configure(state="normal")
        self.heritage_info.delete("1.0", "end")
        self.heritage_info.insert("1.0", text)
        self.heritage_info.configure(state="disabled")
        self._update_summary_bar()

    def _update_background_info(self):
        if not hasattr(self, "background_info"):
            return
        bg = self.base_builder.backgrounds.get(self.var_bg.get())
        text = "No background selected." if not bg else f"{bg.name}\n\n{bg.description}"
        self.background_info.configure(state="normal")
        self.background_info.delete("1.0", "end")
        self.background_info.insert("1.0", text)
        self.background_info.configure(state="disabled")

    def _path_info_text(self, path_id: str) -> str:
        path = self.base_builder.paths.get(path_id)
        if not path:
            return "Select a path to view details."
        lines = [f"Path: {path.name}"]
        if path.description:
            lines.append(path.description)
        if path.prerequisites:
            p = path.prerequisites
            lines.append(f"Prereq: {p.primary_attribute} {p.primary_minimum}+ and one of {', '.join(p.secondary_attributes)} {p.secondary_minimum}+")
        if path.primary_bonus:
            bonus = ", ".join([f"{k} +{v}" for k, v in path.primary_bonus.items()])
            lines.append(f"Primary Bonus: {bonus}")
        if path.talent_points_attribute:
            lines.append(f"Talent Points = {path.talent_points_attribute} mod + 5")
        if path.attack_bonus_melee or path.attack_bonus_ranged:
            lines.append(f"Attack Bonuses: melee +{path.attack_bonus_melee}, ranged +{path.attack_bonus_ranged}")
        if path.role:
            lines.append(f"Role: {path.role}")
        if path.spellcasting:
            lines.append("Grants spellcasting")
        if path.features:
            lines.append("Features:")
            for feat in path.features:
                lines.append(f"- {feat.name}: {feat.description}")
        return "\n".join(lines)

    def _update_path_info(self):
        if not hasattr(self, "path_info"):
            return
        text = self._path_info_text(self._path_id_from_value(self.var_path.get()))
        self.path_info.configure(state="normal")
        self.path_info.delete("1.0", "end")
        self.path_info.insert("1.0", text)
        self.path_info.configure(state="disabled")
        self._update_summary_bar()

    def _update_summary_bar(self):
        if not hasattr(self, "summary_table_rows"):
            return
        # Build a forgiving preview starting at the Heritage step so racial/ancestry mods show up early.
        heritage_idx = next((i for i, (name, _) in enumerate(self.steps) if name == "Heritage"), None)
        ability_idx = next((i for i, (name, _) in enumerate(self.steps) if name == "Ability Scores"), None)
        allow_preview = heritage_idx is not None and self.step_index >= heritage_idx
        b = None
        if allow_preview:
            try:
                # Until the Ability Scores step is completed, we only preview Heritage deltas.
                if not self._scores_confirmed:
                    b = self._build_preview_builder(stop_after="heritage", check_path=False, allow_incomplete=True)
                else:
                    b = self._build_preview_builder(check_path=False, allow_incomplete=True)
            except Exception:
                b = None

        # Track which abilities the player has assigned. We only treat them as assigned after
        # the Ability Scores step validates successfully.
        assigned_scores = (self._abilities_dict(allow_incomplete=True) or {}) if self._scores_confirmed else {}

        for ability in self.abilities:
            lbl = self.summary_labels.get(ability)
            text = f"{ability}: --"
            color = None

            def _fmt(val: int) -> str:
                return f"{val} (mod {((val - 10) // 2):+})"

            roll_val = None
            total_val = None

            if b:
                score = b.character.ability_scores.get(ability)
                if score:
                    delta = score.total - score.roll
                    text = f"{ability}: {_fmt(score.total)} [roll {score.roll} ({delta:+})]"
                    color = "#cc0000" if delta != 0 else None
                    roll_val = score.roll
                    total_val = score.total
            else:
                # Fall back to user-entered values if preview failed
                if self.mode_var.get() == "Roll":
                    val = self.roll_choice_vars.get(ability, ctk.StringVar(value="")).get()
                elif self.mode_var.get() == "Standard Array":
                    val = self.standard_choice_vars.get(ability, ctk.StringVar(value="")).get()
                else:
                    val = self.ability_vars.get(ability, ctk.StringVar(value="")).get()
                if val:
                    try:
                        ival = int(val)
                        text = f"{ability}: {_fmt(ival)}"
                        roll_val = ival
                        total_val = ival
                    except ValueError:
                        pass
            if lbl:
                if color:
                    lbl.configure(text=text, text_color=color)
                else:
                    lbl.configure(text=text)

            score_obj = b.character.ability_scores.get(ability) if b else None
            has_assigned = self._scores_confirmed and (ability in assigned_scores)

            if has_assigned and score_obj:
                delta = score_obj.total - score_obj.roll
                self._update_summary_table(ability, score_obj.roll, score_obj.total, delta)
            elif score_obj:
                # No assigned base yet; show heritage-only delta.
                delta = score_obj.total - score_obj.roll
                self._update_summary_table(ability, None, None, delta, show_delta_only=True)
            else:
                self._update_summary_table(ability, None, None, None)

        self._update_gains_box()

    def _update_gains_box(self):
        if not hasattr(self, "gains_box"):
            return

        def _set_text(text: str):
            self.gains_box.configure(state="normal")
            self.gains_box.delete("1.0", "end")
            self.gains_box.insert("1.0", text)
            self.gains_box.configure(state="disabled")

        # Build a lightweight preview for gains: always apply heritage + profession + background
        # so the sidebar can show what you have / will pick later.
        try:
            b = CharacterBuilder()
            b.load_game_data(str(ROOT_DIR / "data"))
            # Initialize base ability scores so profession HP logic has sane defaults.
            b.set_ability_scores({a: 10 for a in self.abilities})
            b.set_race(self.var_race.get())
            b.set_ancestry(self.var_ancestry.get())

            duty_id = self.var_duty.get() or ""
            prof = self.base_builder.professions.get(self.var_prof.get())
            if prof and prof.duties and not duty_id:
                opts = self._duties_for_profession(self.var_prof.get())
                duty_id = (opts[0] if opts else "")
            if prof:
                try:
                    b.set_profession(self.var_prof.get(), duty_id=duty_id or None)
                except Exception:
                    # Profession/duty might not be selected yet.
                    pass

            # Background can add languages/choices; include if selected.
            if self.var_bg.get():
                try:
                    b.set_background(self.var_bg.get())
                except Exception:
                    pass

            trained_skills: list[str] = []
            for key, entry in (b.character.skills or {}).items():
                trained = bool(getattr(entry, "trained", False))
                rank = int(getattr(entry, "rank", 0) or 0)
                if trained or rank > 0:
                    name = key.value if hasattr(key, "value") else str(key)
                    trained_skills.append(name)
            trained_skills = sorted(set(trained_skills))

            languages = sorted(set(b.character.languages or []))
            profs = sorted(set(b.character.proficiencies or []))

            pending = []
            try:
                pending = b.get_pending_choices()
            except Exception:
                pending = getattr(b, "pending_choices", []) or []

            pending_lines: list[str] = []
            for choice in pending:
                ctype = getattr(choice, "choice_type", "")
                count = int(getattr(choice, "count", 1) or 1)
                source = getattr(choice, "source", "")
                if ctype in {"skill", "tool", "language"}:
                    label = "skills" if ctype == "skill" else ("tools" if ctype == "tool" else "languages")
                    pending_lines.append(f"Choose {count} {label} ({source})")
                elif ctype.startswith("ability") or ctype.startswith("human_"):
                    pending_lines.append(f"Choose {count} option(s) ({source})")

            lines: list[str] = []
            lines.append("Skills:")
            lines.append(", ".join(trained_skills) if trained_skills else "--")
            lines.append("")
            lines.append("Languages:")
            lines.append(", ".join(languages) if languages else "--")
            lines.append("")
            lines.append("Proficiencies:")
            lines.append(", ".join(profs) if profs else "--")

            if pending_lines:
                lines.append("")
                lines.append("Pick later:")
                lines.extend([f"- {p}" for p in pending_lines])

            _set_text("\n".join(lines))
        except Exception:
            _set_text("--")

    def _update_summary_table(self, ability: str, roll_val: int | None, total_val: int | None, delta: int | None, show_delta_only: bool = False):
        row = self.summary_table_rows.get(ability)
        if not row:
            return
        default_color = getattr(self, "_summary_default_text_color", None)
        if show_delta_only:
            row["roll"].configure(text="--")
            row["total"].configure(text="--")
            row["mod"].configure(text="--")
            if delta:
                row["delta"].configure(text=f"{delta:+}", text_color="#cc0000")
            else:
                if default_color is not None:
                    row["delta"].configure(text="--", text_color=default_color)
                else:
                    row["delta"].configure(text="--")
            return
        if roll_val is None or total_val is None or delta is None:
            row["roll"].configure(text="--")
            row["total"].configure(text="--")
            row["mod"].configure(text="--")
            if default_color is not None:
                row["delta"].configure(text="--", text_color=default_color)
            else:
                row["delta"].configure(text="--")
            return
        row["roll"].configure(text=str(roll_val))
        row["total"].configure(text=str(total_val))
        row["mod"].configure(text=f"{(total_val - 10)//2:+}")
        if delta != 0:
            row["delta"].configure(text=f"{delta:+}", text_color="#cc0000")
        else:
            if default_color is not None:
                row["delta"].configure(text=f"{delta:+}", text_color=default_color)
            else:
                row["delta"].configure(text=f"{delta:+}")

    def _validate_and_store(self) -> bool:
        step = self.steps[self.step_index][0]
        if step == "Basics":
            if not self.var_name.get().strip():
                self._set_status("Name is required")
                return False
            filename = f"{_safe_slug(self.var_name.get(), 'character')}_{_safe_slug(self.var_player.get(), 'player')}.json"
            target = CHAR_DIR / filename
            if target.exists():
                self._set_status("A character with this name and player already exists")
                return False
            return True
        if step == "Ability Scores":
            scores = self._abilities_dict()
            if scores is None:
                return False
            if self.mode_var.get() == "Point Buy":
                remaining = self._point_buy_remaining(scores)
                if remaining < 0:
                    self._set_status("Point buy over budget")
                    return False
            if self.mode_var.get() == "Roll":
                if not getattr(self, "rolled_values", []):
                    self._set_status("Roll first, then assign each value")
                    return False
                if self._remaining_roll_pool():
                    self._set_status("Assign all rolled values")
                    return False
            if self.mode_var.get() == "Standard Array":
                remaining = self._standard_remaining_pool()
                expected_left = 1  # 7-value pool, 6 abilities
                assigned = [v.get() for v in self.standard_choice_vars.values() if v.get()]
                if len(assigned) < len(self.abilities):
                    self._set_status("Assign all six ability values")
                    return False
                if len(remaining) != expected_left:
                    self._set_status("Use six distinct values from the 7-number standard array")
                    return False
            self._scores_confirmed = True
            return True
        if step == "Heritage":
            if not self.var_race.get() or not self.var_ancestry.get():
                self._set_status("Select race and ancestry")
                return False
            return True
        if step == "Profession":
            prof = self.base_builder.professions.get(self.var_prof.get())
            if not prof:
                self._set_status("Select a profession")
                return False
            if prof.duties and not self.var_duty.get():
                self._set_status("Duty is required for this profession")
                return False
            return True
        if step == "Path":
            try:
                preview = self._build_preview_builder(stop_after="profession", check_path=False)
                preview.set_path(self._path_id_from_value(self.var_path.get()))
            except Exception as e:
                self._set_status(f"Path invalid: {e}")
                return False
            return True
        if step == "Background":
            if not self.var_bg.get():
                self._set_status("Select a background")
                return False
            return True
        if step == "Choices":
            for record in self.choice_records:
                choice = record["choice"]
                selections = record["getter"]()
                if len(selections) != choice.count:
                    self._set_status(f"{choice.source} needs {choice.count} selection(s)")
                    return False
            # Prevent duplicates across same choice type (skills, languages, tools)
            buckets = {}
            for record in self.choice_records:
                ctype = record["choice"].choice_type
                for sel in record["getter"]():
                    buckets.setdefault(ctype, set())
                    if sel in buckets[ctype]:
                        self._set_status(f"Duplicate {ctype} selection: {sel}")
                        return False
                    buckets[ctype].add(sel)
            if self.human_mode_var.get():
                if "+2" in self.human_mode_var.get():
                    if not self.human_plus2_var.get() or not self.human_penalty_var.get():
                        self._set_status("Pick both +2 and -1 abilities for human")
                        return False
                else:
                    if not self.human_plusone_var.get():
                        self._set_status("Pick the +1 ability for human")
                        return False
            return True
        if step == "Talents":
            try:
                preview = self._build_preview_with_choices()
            except Exception as e:
                try:
                    logger.exception("Talents preview build failed")
                except Exception:
                    pass
                self._set_status(f"Talents invalid: {e}")
                return False

            tp_total = self._calculate_level1_talent_points(preview)
            min_primary = min(4, tp_total)
            spent_total, spent_primary = self._talent_points_spent()
            try:
                logger.info(
                    "Talent validation: tp_total=%s min_primary=%s spent_total=%s spent_primary=%s selected=%s",
                    tp_total,
                    min_primary,
                    spent_total,
                    spent_primary,
                    {tid: int(v.get('rank', 0) or 0) for tid, v in self.level1_talent_state.items()},
                )
            except Exception:
                pass
            if spent_total > tp_total:
                self._set_status(f"Spent {spent_total} TP but only have {tp_total}")
                return False
            if spent_primary < min_primary:
                self._set_status(f"Spend at least {min_primary} TP in primary path talents")
                return False

            # Validate prerequisites and sequential ranks with the real talent defs
            current_ranks: Dict[str, int] = {}
            for tid, entry in self.level1_talent_state.items():
                final_rank = int(entry.get("rank", 0) or 0)
                if final_rank <= 0:
                    continue
                tdef = self.talents_flat.get(tid)
                if not tdef:
                    try:
                        logger.error("Unknown talent id encountered: %s", tid)
                    except Exception:
                        pass
                    self._set_status(f"Unknown talent id: {tid}")
                    return False
                if tdef.requires_choice and not entry.get("choice_data"):
                    try:
                        logger.info("Talent choice missing: %s (%s)", tdef.name, tid)
                    except Exception:
                        pass
                    self._set_status(f"{tdef.name} requires a choice")
                    return False

                for r in range(1, final_rank + 1):
                    can, reasons = tdef.can_acquire(
                        ability_scores=preview.character.ability_scores,
                        level=preview.character.level,
                        current_talents=current_ranks,
                        target_rank=r,
                    )
                    if not can:
                        reason = reasons[0] if reasons else "prerequisites not met"
                        try:
                            logger.info("Talent prerequisites failed: %s rank=%s reason=%s", tdef.name, r, reason)
                        except Exception:
                            pass
                        self._set_status(f"{tdef.name}: {reason}")
                        return False
                    current_ranks[tid] = r

            return True
        return True

    def _build_preview_builder(self, stop_after: str | None = None, check_path: bool = True, allow_incomplete: bool = False):
        b = CharacterBuilder()
        b.load_game_data(str(ROOT_DIR / "data"))
        b.character.character_name = self.var_name.get().strip()
        b.character.player = self.var_player.get().strip()
        b.character.physical_traits.height = self.var_height.get().strip()
        b.character.physical_traits.weight = self.var_weight.get().strip()
        b.character.physical_traits.age = self.var_age.get().strip()
        b.character.physical_traits.eyes = self.var_eyes.get().strip()
        b.character.physical_traits.skin = self.var_skin.get().strip()
        b.character.physical_traits.hair = self.var_hair.get().strip()

        # Race/Ancestry → Profession → Ability Scores → Path → Background
        b.set_race(self.var_race.get())
        b.set_ancestry(self.var_ancestry.get())
        if stop_after == "heritage":
            return b

        duty_id = self.var_duty.get() or None
        if allow_incomplete and not duty_id:
            duty_options = self._duties_for_profession(self.var_prof.get())
            first_duty = duty_options[0] if duty_options else ""
            duty_id = first_duty or None
        b.set_profession(self.var_prof.get(), duty_id=duty_id)
        scores = self._abilities_dict(allow_incomplete=allow_incomplete)
        if scores is None:
            raise ValueError("Abilities invalid")
        b.set_ability_scores(scores)
        if stop_after == "profession":
            return b

        b.set_path(self._path_id_from_value(self.var_path.get()), ignore_prerequisites=not check_path)
        if stop_after == "path":
            return b
        b.set_background(self.var_bg.get())
        return b

    def _finalize(self):
        try:
            logger.info(
                "Finalize start: race=%s ancestry=%s prof=%s duty=%s path=%s bg=%s mode=%s",
                self.var_race.get(),
                self.var_ancestry.get(),
                self.var_prof.get(),
                self.var_duty.get(),
                self.var_path.get(),
                self.var_bg.get(),
                self.mode_var.get(),
            )
            b = self._build_preview_builder(check_path=True)
            # Resolve explicit choices captured in UI
            for record in self.choice_records:
                choice = record["choice"]
                selections = record["getter"]()
                b.resolve_choice(choice.choice_type, selections, source=choice.source)
            # Handle chained human adjustments
            if self.human_mode_var.get():
                mode = self.human_mode_var.get()
                pending_types = {c.choice_type for c in b.get_pending_choices()}
                if "human_ability_mode" in pending_types:
                    b.resolve_choice("human_ability_mode", [mode])
                if "+2" in mode:
                    if "ability_bonus_plus2" in {c.choice_type for c in b.get_pending_choices()}:
                        b.resolve_choice("ability_bonus_plus2", [self.human_plus2_var.get()])
                    if "ability_penalty" in {c.choice_type for c in b.get_pending_choices()}:
                        b.resolve_choice("ability_penalty", [self.human_penalty_var.get()])
                else:
                    if "ability_bonus" in {c.choice_type for c in b.get_pending_choices()}:
                        b.resolve_choice("ability_bonus", [self.human_plusone_var.get()])
            # Resolve any remaining simple pending choices automatically with first options
            while b.get_pending_choices():
                choice = b.get_pending_choices()[0]
                default_sel = choice.options[: choice.count]
                b.resolve_choice(choice.choice_type, default_sel, source=choice.source)

            # Persist selected level-1 talents (stable id + rank + path_id + choice_data)
            primary_path_id = self._path_id_from_value(self.var_path.get())
            selected: List[Dict[str, Any]] = []
            for tid, entry in self.level1_talent_state.items():
                rank = int(entry.get("rank", 0) or 0)
                if rank <= 0:
                    continue
                tdef = self.talents_flat.get(tid)
                name = tdef.name if tdef else tid
                path_id = (tdef.path_id if tdef and tdef.path_id else "general")
                choice_data = entry.get("choice_data") or {}
                is_primary_path = (path_id == primary_path_id)
                is_primary_talent = bool(getattr(tdef, "is_primary", False)) if tdef else False
                selected.append({
                    "talent_id": tid,
                    "name": name,
                    "rank": rank,
                    "path_id": path_id,
                    "choice_data": choice_data,
                    "is_primary_path": is_primary_path,
                    "is_primary_talent": is_primary_talent,
                })

            # Sort: primary path talents first (and the path's scaling talent first), then others.
            selected.sort(key=lambda t: (
                not t["is_primary_path"],
                not t["is_primary_talent"],
                str(t["path_id"]),
                str(t["name"]).lower(),
            ))

            talents_payload: List[TemplateTalent] = [
                TemplateTalent(
                    talent_id=str(t["talent_id"]),
                    name=str(t["name"]),
                    rank=int(t["rank"]),
                    path_id=str(t["path_id"]),
                    choice_data=dict(t["choice_data"]) if isinstance(t["choice_data"], dict) else {},
                    text=f"{t['name']} (Rank {t['rank']})",
                )
                for t in selected
            ]
            b.character.talents = talents_payload

            b.recalculate_all()
            created_path = None
            if self.on_save:
                created_path = self.on_save(b.character)
            if isinstance(created_path, (str, Path)):
                try:
                    self._created_character_path = Path(created_path)
                except Exception:
                    self._created_character_path = None
            self._show_post_create_screen()
        except Exception as e:
            try:
                logger.exception("Finalize failed")
            except Exception:
                pass
            self._set_status(f"Could not create character: {e} (see logs/gui_app.log)")

    def _show_post_create_screen(self):
        """After Create, show next actions: level up, export PDF, or exit."""
        for child in self.body.winfo_children():
            child.destroy()

        # Lock navigation on this final screen.
        try:
            self.btn_back.configure(state="disabled")
            self.btn_next.configure(state="disabled")
        except Exception:
            pass

        ctk.CTkLabel(self.body, text="Character Created", font=("Segoe UI", 16, "bold"), anchor="w").pack(
            fill="x", pady=(6, 10)
        )
        msg = "Choose what to do next:"
        if self._created_character_path is None:
            msg = "Character saved. Choose what to do next:"
        ctk.CTkLabel(self.body, text=msg, anchor="w").pack(fill="x", padx=8, pady=(0, 10))

        btns = ctk.CTkFrame(self.body)
        btns.pack(fill="x", padx=8, pady=8)

        ctk.CTkButton(btns, text="Level Up", command=self._post_level_up).pack(fill="x", pady=6)
        ctk.CTkButton(btns, text="Export PDF", command=self._post_export_pdf).pack(fill="x", pady=6)
        ctk.CTkButton(btns, text="Exit Wizard", command=self._on_close).pack(fill="x", pady=6)

        self._set_status("Created. You can level up, export PDF, or exit.")

    def _post_level_up(self):
        if not self._created_character_path or not self._created_character_path.exists():
            self._set_status("Cannot level up: saved character file not found")
            return

        def _after_save():
            try:
                refresh = getattr(self.master, "_refresh_list", None)
                if callable(refresh):
                    refresh()
            except Exception:
                pass
            self._set_status("Level up complete")

        LevelUpWizard(self.master, self._created_character_path, on_saved=_after_save)

    def _post_export_pdf(self):
        if not self._created_character_path or not self._created_character_path.exists():
            self._set_status("Cannot export PDF: saved character file not found")
            return
        try:
            data = json.loads(self._created_character_path.read_text(encoding="utf-8"))
            char = load_character_template(data)
        except Exception as e:
            self._set_status(f"Failed to load saved character: {e}")
            return

        pdf_name = f"{_safe_slug(char.character_name, 'character')}_{_safe_slug(char.player, 'player')}.pdf"
        pdf_path = EXPORTS_DIR / pdf_name
        try:
            SharedSheetPDF().generate_to_file(sheet_data=char.to_dict(), output_path=pdf_path)
            self._set_status(f"PDF saved to {pdf_path}")
        except Exception as e:  # pragma: no cover
            self._set_status(f"PDF export failed: {e}")


class EditCharacterDialog(ctk.CTkToplevel):
    def __init__(self, master, data: Dict[str, Any], on_save):
        super().__init__(master)
        self.data = data
        self.on_save = on_save
        self.title("Edit Character")
        self.geometry("460x420")
        self.resizable(False, False)

        fields = [
            ("Name", "character_name"),
            ("Player", "player"),
            ("Race", "race"),
            ("Ancestry", "ancestry"),
            ("Profession", "profession"),
            ("Path", "primary_path"),
            ("Background", "background"),
            ("Notes", "notes"),
        ]
        self.vars = {}
        row = 0
        for label, key in fields:
            ctk.CTkLabel(self, text=label).grid(row=row, column=0, padx=10, pady=6, sticky="e")
            if key == "notes":
                var = ctk.StringVar(value=str(data.get(key, "")))
                txt = ctk.CTkTextbox(self, width=260, height=120)
                txt.insert("1.0", var.get())
                txt.grid(row=row, column=1, padx=10, pady=6, sticky="w")
                self.vars[key] = txt
            else:
                var = ctk.StringVar(value=str(data.get(key, "")))
                self.vars[key] = var
                ctk.CTkEntry(self, textvariable=var, width=260).grid(row=row, column=1, padx=10, pady=6, sticky="w")
            row += 1

        btn_row = ctk.CTkFrame(self)
        btn_row.grid(row=row, column=0, columnspan=2, pady=16)
        ctk.CTkButton(btn_row, text="Save", command=self._save).grid(row=0, column=0, padx=8)
        ctk.CTkButton(btn_row, text="Cancel", command=self.destroy).grid(row=0, column=1, padx=8)

    def _save(self):
        for key, widget in self.vars.items():
            if isinstance(widget, ctk.CTkTextbox):
                self.data[key] = widget.get("1.0", "end").strip()
            else:
                self.data[key] = widget.get().strip()
        if self.on_save:
            self.on_save(self.data)
        self.destroy()


class LevelUpWizard(ctk.CTkToplevel):
    """GUI level-up flow mirroring interactive_levelup.py for one level."""

    def __init__(self, master, character_path: Path, on_saved):
        super().__init__(master)
        self.character_path = character_path
        self.on_saved = on_saved

        self.title("Level Up")
        self.geometry("860x720")
        self.minsize(840, 720)
        try:
            self.resizable(True, False)
        except Exception:
            pass

        self.manager = LevelUpManager(data_dir=str(ROOT_DIR / "data"))
        ok = self.manager.load_character(str(character_path))
        if not ok or not self.manager.character:
            ctk.CTkLabel(self, text=f"Failed to load {character_path}", anchor="w").pack(padx=12, pady=12)
            ctk.CTkButton(self, text="Close", command=self.destroy).pack(pady=8)
            return

        self.options = self.manager.get_level_up_options()

        # State
        self.step_index = 0
        self.steps: List[str] = ["Summary"]
        if self.options.grants_ability_increase:
            self.steps.append("Ability Increase")
        self.steps.extend(["Talents", "Advancements", "HP", "Confirm"])

        self.abilities = list(self.manager.character.ability_scores.keys())
        self.ability_inc_mode = ctk.StringVar(value="")  # "plus2" | "plus1" | ""
        self.ability_plus2 = ctk.StringVar(value=self.abilities[0] if self.abilities else "")
        self.ability_plus1_a = ctk.StringVar(value=self.abilities[0] if self.abilities else "")
        self.ability_plus1_b = ctk.StringVar(value=self.abilities[1] if len(self.abilities) > 1 else (self.abilities[0] if self.abilities else ""))

        # Talent selections: talent_id -> payload
        self.selected_talents: Dict[str, Dict[str, Any]] = {}

        # Advancement selections: list of dicts
        self.advancements: List[Dict[str, Any]] = []

        # Advancements UI state
        self.ap_target_menu = None

        self.hp_method = ctk.StringVar(value="average")  # "average" | "roll"
        self.hp_roll_value: int | None = None
        self.hp_roll_label = None

        # Layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self.body = ctk.CTkFrame(self)
        self.body.grid(row=0, column=0, sticky="nsew", padx=12, pady=(10, 0))
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        nav = ctk.CTkFrame(self)
        nav.grid(row=1, column=0, sticky="ew", padx=12, pady=(10, 10))
        nav.grid_columnconfigure(0, weight=1)

        self.status = ctk.CTkLabel(nav, text="", anchor="w")
        self.status.grid(row=0, column=0, sticky="w")
        self.btn_back = ctk.CTkButton(nav, text="Back", width=80, command=self._prev, state="disabled")
        self.btn_back.grid(row=0, column=1, padx=6)
        self.btn_next = ctk.CTkButton(nav, text="Next", width=110, command=self._next)
        self.btn_next.grid(row=0, column=2, padx=6)

        self._render()

    def _set_status(self, msg: str):
        self.status.configure(text=msg)
        try:
            logger.info("LevelUpWizard status: %s", msg)
        except Exception:
            pass

    def _clear_body(self):
        for child in self.body.winfo_children():
            child.destroy()

    def _prev(self):
        if self.step_index > 0:
            self.step_index -= 1
            self._render()

    def _next(self):
        if not self._validate_step():
            return
        if self.step_index == len(self.steps) - 1:
            self._apply_and_save()
            return
        self.step_index += 1
        self._render()

    def _render(self):
        self._clear_body()
        step = self.steps[self.step_index]
        self.btn_back.configure(state="normal" if self.step_index > 0 else "disabled")
        self.btn_next.configure(text="Apply" if step == "Confirm" else "Next")
        self._set_status(f"Step {self.step_index + 1} of {len(self.steps)}: {step}")

        if step == "Summary":
            self._render_summary()
        elif step == "Ability Increase":
            self._render_ability_increase()
        elif step == "Talents":
            self._render_talents()
        elif step == "Advancements":
            self._render_advancements()
        elif step == "HP":
            self._render_hp()
        elif step == "Confirm":
            self._render_confirm()

    def _render_summary(self):
        frame = ctk.CTkFrame(self.body)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        char = self.manager.character
        if not char:
            ctk.CTkLabel(frame, text="No character loaded", anchor="w").grid(row=0, column=0, sticky="ew", padx=10, pady=10)
            return
        title = f"{char.character_name or '(unnamed)'} ({char.player or ''})"
        ctk.CTkLabel(frame, text=title, font=("Segoe UI", 16, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))

        box = ctk.CTkTextbox(frame, height=520, activate_scrollbars=True)
        box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        summary = self.manager.get_level_summary()
        lines = []
        lines.append(f"File: {self.character_path}")
        lines.append(f"Race: {char.race} / {char.ancestry}")
        lines.append(f"Profession: {char.profession}")
        lines.append(f"Path: {char.primary_path}")
        lines.append(f"Level: {summary.get('level')} → {self.options.new_level}")
        lines.append(f"XP: {summary.get('xp', 0):,} (need {summary.get('xp_needed', 0):,} more for next)")
        lines.append("")
        lines.append(f"Talent Points this level: {self.options.talent_points}")
        lines.append(f"Advancement Points this level: {self.options.advancement_points}")
        if self.options.grants_ability_increase:
            lines.append("Grants Ability Increase: Yes")
        if self.options.grants_extra_attack:
            lines.append("Grants Extra Attack: Yes")
        if self.options.spellcrafting_points:
            lines.append(f"Spellcrafting Points gained: {self.options.spellcrafting_points}")
        lines.append("")
        lines.append("Abilities:")
        for name, score in char.ability_scores.items():
            try:
                lines.append(f"  {name:12} {score.total:2d} (mod {score.mod:+d})")
            except Exception:
                lines.append(f"  {name}")
        box.insert("1.0", "\n".join(lines))
        box.configure(state="disabled")

    def _render_ability_increase(self):
        frame = ctk.CTkFrame(self.body)
        frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(frame, text="This level grants an Ability Score Increase:", font=("Segoe UI", 14, "bold"), anchor="w").grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 6))

        r1 = ctk.CTkRadioButton(frame, text="+2 to one ability", variable=self.ability_inc_mode, value="plus2")
        r1.grid(row=1, column=0, sticky="w", padx=10, pady=6)
        ctk.CTkOptionMenu(frame, variable=self.ability_plus2, values=self.abilities).grid(row=1, column=1, sticky="w", padx=10, pady=6)

        r2 = ctk.CTkRadioButton(frame, text="+1 to two abilities", variable=self.ability_inc_mode, value="plus1")
        r2.grid(row=2, column=0, sticky="w", padx=10, pady=6)
        ctk.CTkOptionMenu(frame, variable=self.ability_plus1_a, values=self.abilities).grid(row=2, column=1, sticky="w", padx=10, pady=6)
        ctk.CTkOptionMenu(frame, variable=self.ability_plus1_b, values=self.abilities).grid(row=2, column=2, sticky="w", padx=10, pady=6)

        ctk.CTkLabel(frame, text="(Leave unselected if you want to skip for now)", anchor="w").grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 10))

    def _render_talents(self):
        frame = ctk.CTkFrame(self.body)
        frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(frame)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        header.grid_columnconfigure(0, weight=1)
        self.tp_label = ctk.CTkLabel(header, text="", anchor="w")
        self.tp_label.grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ctk.CTkButton(header, text="Clear", width=80, command=self._clear_talents).grid(row=0, column=1, padx=6, pady=6)

        scroll = ctk.CTkScrollableFrame(frame)
        scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        available = list(self.options.available_talents or [])
        primary_id = self.manager.get_primary_path_id() or ""
        available.sort(key=lambda t: (t.get("path_id") != primary_id, t.get("path_id", ""), t.get("name", "")))

        if not available:
            ctk.CTkLabel(scroll, text="No talents available at this level.").pack(pady=14)
        else:
            for t in available:
                tid = t.get("talent_id", "")
                name = t.get("name", tid)
                cur = t.get("current_rank", 0)
                nxt = t.get("next_rank", cur + 1)
                cost = t.get("tp_cost", nxt)
                path_id = t.get("path_id", "general")
                requires_choice = bool(t.get("requires_choice"))
                choice_type = t.get("choice_type") or "choice"
                choice_options = list(t.get("choice_options") or [])

                row = ctk.CTkFrame(scroll)
                row.pack(fill="x", padx=6, pady=4)
                row.grid_columnconfigure(0, weight=1)
                label = f"{name}  Rank {cur} → {nxt}  Cost {cost}  ({path_id})"
                ctk.CTkLabel(row, text=label, anchor="w", justify="left", wraplength=520).grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))

                tdef = self.manager.talents_flat.get(tid)
                details = _format_talent_ui_details(tdef, current_rank=cur, next_rank=nxt, mode="next")
                if details:
                    ctk.CTkLabel(row, text=details, anchor="w", justify="left", wraplength=520).grid(
                        row=1,
                        column=0,
                        columnspan=3,
                        sticky="w",
                        padx=6,
                        pady=(0, 6),
                    )

                if requires_choice:
                    choice_var = ctk.StringVar(value="")
                    existing = (self.selected_talents.get(tid) or {}).get("choice_data") or {}
                    if existing and choice_type in existing:
                        choice_var.set(str(existing.get(choice_type, "")))
                    menu = ctk.CTkOptionMenu(row, variable=choice_var, values=[""] + choice_options, width=160)
                    menu.grid(row=0, column=1, padx=6, pady=6)
                else:
                    choice_var = None

                def _toggle_select(_tid=tid, _t=t, _choice_var=choice_var, _choice_type=choice_type):
                    if _tid in self.selected_talents:
                        self.selected_talents.pop(_tid, None)
                    else:
                        choice_data = {}
                        if _choice_var is not None:
                            sel = _choice_var.get().strip()
                            if sel:
                                choice_data = {_choice_type: sel}
                        self.selected_talents[_tid] = {
                            "talent_id": _tid,
                            "name": _t.get("name", _tid),
                            "new_rank": int(_t.get("next_rank", 1)),
                            "points_spent": int(_t.get("tp_cost", _t.get("next_rank", 1))),
                            "path_id": _t.get("path_id", "general"),
                            "requires_choice": bool(_t.get("requires_choice")),
                            "choice_type": _t.get("choice_type") or "choice",
                            "choice_data": choice_data,
                        }
                    self._update_tp_label()
                    self._render_talents()  # refresh button states / choice pickers

                selected = (tid in self.selected_talents)
                btn_text = "Remove" if selected else "Add"
                ctk.CTkButton(row, text=btn_text, width=80, command=_toggle_select).grid(row=0, column=2, padx=6, pady=6)

        self._update_tp_label()

    def _update_tp_label(self):
        spent = sum(int(v.get("points_spent", 0) or 0) for v in self.selected_talents.values())
        total = int(self.options.talent_points)
        remaining = total - spent
        if hasattr(self, "tp_label") and self.tp_label is not None:
            self.tp_label.configure(text=f"Talent Points: {spent}/{total} spent (remaining {remaining})")

    def _clear_talents(self):
        self.selected_talents = {}
        self._render_talents()

    def _render_advancements(self):
        frame = ctk.CTkFrame(self.body)
        frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(frame)
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        top.grid_columnconfigure(0, weight=1)
        self.ap_label = ctk.CTkLabel(top, text="", anchor="w")
        self.ap_label.grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ctk.CTkButton(top, text="Clear", width=80, command=self._clear_advancements).grid(row=0, column=1, padx=6, pady=6)

        legend = ctk.CTkLabel(
            frame,
            text="Costs: Skill rank +1 = 1 AP | Train new skill = 4 AP | Proficiency = 10 AP | Language = 10 AP",
            anchor="w",
        )
        legend.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 6))

        form = ctk.CTkFrame(frame)
        form.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 6))

        self.ap_type_var = ctk.StringVar(value="skill_rank")
        self.ap_target_var = ctk.StringVar(value="")
        ctk.CTkLabel(form, text="Type").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        type_menu = ctk.CTkOptionMenu(
            form,
            variable=self.ap_type_var,
            values=["skill_rank", "train_skill", "proficiency", "language"],
            command=lambda _=None: self._refresh_ap_target_choices(),
        )
        type_menu.grid(row=0, column=1, padx=6, pady=6, sticky="w")
        ctk.CTkLabel(form, text="Target").grid(row=0, column=2, padx=6, pady=6, sticky="e")
        self.ap_target_menu = ctk.CTkOptionMenu(form, variable=self.ap_target_var, values=[""], width=220)
        self.ap_target_menu.grid(row=0, column=3, padx=6, pady=6, sticky="w")

        trained = list(self.options.trained_skills or [])
        if trained:
            ctk.CTkLabel(form, text="Trained skills:").grid(row=1, column=0, padx=6, pady=(0, 6), sticky="e")
            ctk.CTkLabel(form, text=", ".join(trained[:10]) + ("..." if len(trained) > 10 else ""), anchor="w").grid(row=1, column=1, columnspan=3, padx=6, pady=(0, 6), sticky="w")

        ctk.CTkButton(form, text="Add", width=90, command=self._add_advancement).grid(row=0, column=4, padx=6, pady=6)

        # Seed dropdown options based on current type/character.
        self._refresh_ap_target_choices()

        list_box = ctk.CTkScrollableFrame(frame)
        list_box.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))

        if not self.advancements:
            ctk.CTkLabel(list_box, text="No advancement purchases selected.").pack(pady=14)
        else:
            for idx, item in enumerate(self.advancements):
                row = ctk.CTkFrame(list_box)
                row.pack(fill="x", padx=6, pady=4)
                row.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(row, text=f"{item['choice_type']} → {item['target']} (AP {item['points_spent']})", anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=6)
                ctk.CTkButton(row, text="Remove", width=80, command=lambda i=idx: self._remove_advancement(i)).grid(row=0, column=1, padx=6, pady=6)

        self._update_ap_label()

    def _clear_advancements(self):
        self.advancements = []
        self._render_advancements()

    def _remove_advancement(self, index: int):
        if 0 <= index < len(self.advancements):
            self.advancements.pop(index)
        self._render_advancements()

    def _update_ap_label(self):
        spent = sum(int(v.get("points_spent", 0) or 0) for v in self.advancements)
        total = int(self.options.advancement_points)
        remaining = total - spent
        if hasattr(self, "ap_label") and self.ap_label is not None:
            self.ap_label.configure(text=f"Advancement Points: {spent}/{total} spent (remaining {remaining})")

    def _add_advancement(self):
        ctype = self.ap_type_var.get().strip()
        target = self.ap_target_var.get().strip()
        if not target:
            self._set_status("Pick a target")
            return
        cost = int(AP_COSTS.get(ctype, 0) or 0)
        if cost <= 0:
            self._set_status("Invalid advancement type")
            return
        spent = sum(int(v.get("points_spent", 0) or 0) for v in self.advancements)
        if spent + cost > int(self.options.advancement_points):
            self._set_status("Not enough AP remaining")
            return
        self.advancements.append({"choice_type": ctype, "target": target, "points_spent": cost})
        self.ap_target_var.set("")
        self._render_advancements()

    def _advancement_target_options(self, choice_type: str) -> list[str]:
        """Return curated target options for a given advancement choice type."""
        char = self.manager.character
        if not char:
            return []

        ct = (choice_type or "").strip()
        if ct == "train_skill":
            # Only skills not yet trained.
            options = [name for name, entry in char.skills.items() if not getattr(entry, "trained", False)]
            return sorted(options)

        if ct == "skill_rank":
            # Only skills that are trained.
            options = [name for name, entry in char.skills.items() if getattr(entry, "trained", False)]
            return sorted(options)

        if ct == "language":
            known = set()
            try:
                known = {str(x).strip().lower() for x in (char.languages or []) if str(x).strip()}
            except Exception:
                known = set()
            options = [lang for lang in ALL_LANGUAGES if str(lang).strip().lower() not in known]
            return sorted(options)

        if ct == "proficiency":
            all_profs = set(ALL_ARMOR_PROFICIENCIES) | set(ALL_WEAPON_PROFICIENCIES) | set(ALL_TOOL_PROFICIENCIES)
            all_profs.discard("None")
            known = set()
            try:
                known = {str(x).strip().lower() for x in (char.proficiencies or []) if str(x).strip()}
            except Exception:
                known = set()
            options = [p for p in all_profs if str(p).strip().lower() not in known]
            return sorted(options)

        return []

    def _refresh_ap_target_choices(self):
        """Update the Target dropdown based on the selected advancement type."""
        if self.ap_target_menu is None:
            return

        ctype = self.ap_type_var.get().strip()
        options = self._advancement_target_options(ctype)
        values = [""] + options
        try:
            self.ap_target_menu.configure(values=values)
        except Exception:
            # Some CTk versions may not support dynamic values updates; fall back to a re-render.
            self._render_advancements()
            return

        current = self.ap_target_var.get().strip()
        if current and current in options:
            return
        # Default to first available option, else blank.
        self.ap_target_var.set(options[0] if options else "")

    def _render_hp(self):
        frame = ctk.CTkFrame(self.body)
        frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        ctk.CTkLabel(frame, text="Hit Point Increase", font=("Segoe UI", 14, "bold"), anchor="w").grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 6))

        end_mod = 0
        try:
            char = self.manager.character
            if char and "Endurance" in char.ability_scores:
                end_mod = int(char.ability_scores["Endurance"].mod)
        except Exception:
            end_mod = 0
        ctk.CTkLabel(frame, text=f"Endurance modifier: {end_mod:+d}", anchor="w").grid(row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 8))

        ctk.CTkRadioButton(frame, text="Take average (5 + END)", variable=self.hp_method, value="average").grid(row=2, column=0, sticky="w", padx=10, pady=6)
        ctk.CTkRadioButton(frame, text="Roll (d8 + END)", variable=self.hp_method, value="roll").grid(row=3, column=0, sticky="w", padx=10, pady=6)
        ctk.CTkButton(frame, text="Roll d8", width=120, command=self._roll_hp).grid(row=3, column=1, sticky="w", padx=10, pady=6)
        self.hp_roll_label = ctk.CTkLabel(frame, text="", anchor="w")
        self.hp_roll_label.grid(row=3, column=2, sticky="w", padx=10, pady=6)

        self._update_hp_label()

    def _roll_hp(self):
        self.hp_method.set("roll")
        self.hp_roll_value = random.randint(1, 8)
        self._update_hp_label()

    def _update_hp_label(self):
        if self.hp_roll_label is None:
            return
        if self.hp_method.get() != "roll":
            self.hp_roll_label.configure(text="")
            return
        if self.hp_roll_value is None:
            self.hp_roll_label.configure(text="(click Roll d8)")
        else:
            self.hp_roll_label.configure(text=f"Rolled {self.hp_roll_value}")

    def _render_confirm(self):
        frame = ctk.CTkFrame(self.body)
        frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Review & Apply", font=("Segoe UI", 14, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))

        box = ctk.CTkTextbox(frame, height=520, activate_scrollbars=True)
        box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        lines = []
        lines.append(f"Level: {self.options.current_level} → {self.options.new_level}")
        lines.append("")

        # Show what will carry over into stored_advance.
        try:
            spent_tp = sum(int(v.get("points_spent", 0) or 0) for v in self.selected_talents.values())
            spent_ap = sum(int(v.get("points_spent", 0) or 0) for v in self.advancements)
            remaining_tp = max(0, int(self.options.talent_points) - spent_tp)
            remaining_ap = max(0, int(self.options.advancement_points) - spent_ap)
        except Exception:
            remaining_tp = 0
            remaining_ap = 0

        if remaining_tp or remaining_ap:
            lines.append(f"Carryover after apply: TP {remaining_tp}, AP {remaining_ap} (saved to stored_advance)")
            lines.append("")

        ability_inc = self._ability_increase_payload()
        if ability_inc:
            lines.append("Ability Increase:")
            for k, v in ability_inc.items():
                lines.append(f"  {k} +{v}")
            lines.append("")

        if self.selected_talents:
            lines.append("Talents:")
            for t in self.selected_talents.values():
                lines.append(f"  {t['name']} (to Rank {t['new_rank']}) [TP {t['points_spent']}]")
            lines.append("")
        else:
            lines.append("Talents: (none)")
            lines.append("")

        if self.advancements:
            lines.append("Advancements:")
            for a in self.advancements:
                lines.append(f"  {a['choice_type']} → {a['target']} [AP {a['points_spent']}]")
            lines.append("")
        else:
            lines.append("Advancements: (none)")
            lines.append("")

        if self.hp_method.get() == "average":
            lines.append("HP: average")
        else:
            lines.append(f"HP: roll ({self.hp_roll_value if self.hp_roll_value is not None else 'not rolled'})")

        box.insert("1.0", "\n".join(lines))
        box.configure(state="disabled")

    def _ability_increase_payload(self) -> Dict[str, int] | None:
        if not self.options.grants_ability_increase:
            return None
        mode = self.ability_inc_mode.get().strip()
        if mode == "plus2":
            a = self.ability_plus2.get().strip()
            return {a: 2} if a else None
        if mode == "plus1":
            a = self.ability_plus1_a.get().strip()
            b = self.ability_plus1_b.get().strip()
            if not a or not b or a == b:
                return None
            return {a: 1, b: 1}
        return None

    def _validate_step(self) -> bool:
        step = self.steps[self.step_index]
        if step == "Ability Increase" and self.options.grants_ability_increase:
            mode = self.ability_inc_mode.get().strip()
            if mode == "plus2" and not self.ability_plus2.get().strip():
                self._set_status("Pick the +2 ability")
                return False
            if mode == "plus1":
                a = self.ability_plus1_a.get().strip()
                b = self.ability_plus1_b.get().strip()
                if not a or not b:
                    self._set_status("Pick both +1 abilities")
                    return False
                if a == b:
                    self._set_status("Choose two different abilities")
                    return False
            return True

        if step == "Talents":
            spent = sum(int(v.get("points_spent", 0) or 0) for v in self.selected_talents.values())
            if spent > int(self.options.talent_points):
                self._set_status("Spent more TP than available")
                return False
            for v in self.selected_talents.values():
                if v.get("requires_choice") and not (v.get("choice_data") or {}):
                    self._set_status(f"{v.get('name', 'Talent')} requires a choice")
                    return False
            return True

        if step == "Advancements":
            spent = sum(int(v.get("points_spent", 0) or 0) for v in self.advancements)
            if spent > int(self.options.advancement_points):
                self._set_status("Spent more AP than available")
                return False
            # Basic validation for skill_rank against trained list
            trained = set(self.options.trained_skills or [])
            for v in self.advancements:
                if v.get("choice_type") == "skill_rank" and v.get("target") not in trained:
                    self._set_status("Skill rank upgrades must be for a trained skill")
                    return False
            return True

        if step == "HP":
            if self.hp_method.get() == "roll" and self.hp_roll_value is None:
                self._set_status("Click Roll d8 (or choose average)")
                return False
            return True

        return True

    def _apply_and_save(self):
        try:
            ability_inc = self._ability_increase_payload() or {}

            talent_choices: List[LevelTalentChoice] = []
            for t in self.selected_talents.values():
                talent_choices.append(LevelTalentChoice(
                    talent_id=t["talent_id"],
                    talent_name=t["name"],
                    new_rank=int(t["new_rank"]),
                    points_spent=int(t["points_spent"]),
                    path_id=t.get("path_id", "general"),
                    choice_data=t.get("choice_data") or {},
                ))

            advancement_choices: List[LevelAdvancementChoice] = []
            for a in self.advancements:
                advancement_choices.append(LevelAdvancementChoice(
                    choice_type=a["choice_type"],
                    target=a["target"],
                    points_spent=int(a["points_spent"]),
                ))

            hp_roll = 0
            if self.hp_method.get() == "roll":
                hp_roll = int(self.hp_roll_value) if self.hp_roll_value is not None else 0

            hp_roll_opt = hp_roll if self.hp_method.get() == "roll" else None

            ok = self.manager.level_up(
                talent_choices=talent_choices,
                advancement_choices=advancement_choices,
                ability_increase=ability_inc,
                hp_roll=hp_roll_opt,
            )
            if not ok:
                errs = []
                if getattr(self.manager, "last_validation", None) is not None:
                    errs = list(getattr(self.manager.last_validation, "errors", []) or [])
                msg = errs[0] if errs else "Level up validation failed"
                self._set_status(msg)
                try:
                    logger.info("Level up failed: %s", errs)
                except Exception:
                    pass
                return

            if not self.manager.save_character(str(self.character_path)):
                self._set_status("Failed to save character")
                return

            if self.on_saved:
                self.on_saved()
            self.destroy()
        except Exception as e:
            try:
                logger.exception("LevelUpWizard apply failed")
            except Exception:
                pass
            self._set_status(f"Could not level up: {e} (see logs/gui_app.log)")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Realm of Warriors - Characters")
        self.geometry("720x480")
        self.minsize(700, 460)

        self.validator = CharacterValidator(data_dir=str(ROOT_DIR / "data"))
        self.builder = CharacterBuilder()
        self.builder.load_game_data(str(ROOT_DIR / "data"))

        self.selected_path: Path | None = None

        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.list_frame = CharacterListFrame(self, on_select=self._on_select)
        self.list_frame.grid(row=0, column=0, sticky="nsew")

        btns = ctk.CTkFrame(self)
        btns.grid(row=0, column=1, sticky="ns", padx=8, pady=8)

        ctk.CTkButton(btns, text="New Character", command=self._new_character).pack(fill="x", pady=6)
        ctk.CTkButton(btns, text="Edit Selected", command=self._edit_character).pack(fill="x", pady=6)
        ctk.CTkButton(btns, text="Export PDF", command=self._export_pdf).pack(fill="x", pady=6)
        ctk.CTkButton(btns, text="Level Up", command=self._level_up).pack(fill="x", pady=6)
        ctk.CTkButton(btns, text="Refresh", command=self._refresh_list).pack(fill="x", pady=6)
        ctk.CTkButton(btns, text="Quit", command=self.destroy).pack(fill="x", pady=6)

        self.status = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=4)

        self._refresh_list()

    def report_callback_exception(self, *args):  # pragma: no cover - GUI runtime
        """Log Tkinter callback exceptions to logs/gui_app.log.

        Tk may call this with (exc, val, tb) depending on version/typeshed;
        accept varargs to stay compatible.
        """
        try:
            if len(args) == 3:
                exc, val, tb = args
                logger.exception("Tk callback exception", exc_info=(exc, val, tb))
            else:
                logger.exception("Tk callback exception (args=%r)", args)
        except Exception:
            pass
        try:
            return super().report_callback_exception(*args)
        except Exception:
            return None

    def _set_status(self, msg: str):
        self.status.configure(text=msg)
        try:
            logger.info("App status: %s", msg)
        except Exception:
            pass

    def _list_items(self):
        items = []
        for file in sorted(CHAR_DIR.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                name = data.get("character_name", file.stem)
                player = data.get("player", "")
                label = f"{name} ({player})"
            except Exception:
                label = f"{file.stem} (invalid)"
            items.append((label, file))
        return items

    def _refresh_list(self):
        items = self._list_items()
        self.list_frame.set_items(items)
        self.selected_path = items[0][1] if items else None
        self._set_status(f"Loaded {len(items)} characters")

    def _on_select(self, path: Path):
        self.selected_path = path
        self._set_status(f"Selected {path.name}")

    def _new_character(self):
        NewCharacterWizard(self, self.builder, on_save=self._save_new_character)

    def _save_new_character(self, char):
        data = dump_character_template(char)
        filename = f"{_safe_slug(char.character_name, 'character')}_{_safe_slug(char.player, 'player')}.json"
        target = CHAR_DIR / filename
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._set_status(f"Saved {target}")
        self._refresh_list()
        return target

    def _edit_character(self):
        path = self.selected_path
        if not path or not path.exists():
            self._set_status("No character selected")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            self._set_status(f"Failed to load: {e}")
            return

        def _save(updated: Dict[str, Any]):
            path.write_text(json.dumps(updated, indent=2), encoding="utf-8")
            self._set_status(f"Saved {path.name}")
            self._refresh_list()

        # Show an embedded preview: prefer Playwright PNG (pixel-accurate), then tkinterweb, then tkhtmlview.
        def _open_preview_window():
            try:
                html = _build_sheet_preview_html(data)
            except Exception as e:  # pragma: no cover
                self._set_status(f"Preview build failed: {e}")
                return

            win = ctk.CTkToplevel(self)
            win.title(f"Sheet Preview - {data.get('character_name', path.stem)}")
            win.geometry("940x1080")

            if PLAYWRIGHT_AVAILABLE:
                png_path = _render_sheet_png(data)
                if png_path and png_path.exists():
                    try:
                        img = tk.PhotoImage(file=str(png_path))
                        lbl = ctk.CTkLabel(win, image=img, text="")
                        lbl.image = img  # keep reference
                        lbl.pack(fill="both", expand=True)
                        return
                    except Exception as e:  # pragma: no cover
                        self._set_status(f"PNG preview failed: {e}")
                else:
                    self._set_status("Playwright available but rendering failed. Try 'python -m playwright install chromium'.")

            if HTML_FRAME_AVAILABLE:
                try:
                    frame = HtmlFrame(win, horizontal_scrollbar="auto", messages_enabled=False)
                    frame.pack(fill="both", expand=True)
                    frame.load_html(html)
                    return
                except Exception as e:  # pragma: no cover
                    self._set_status(f"tkinterweb preview failed: {e}")

            if HTML_SUMMARY_AVAILABLE:
                try:
                    container = ctk.CTkScrollableFrame(win, width=920, height=1040)
                    container.pack(fill="both", expand=True, padx=8, pady=8)
                    viewer = HTMLLabel(container, html=html)
                    viewer.pack(fill="both", expand=True)
                    return
                except Exception as e:  # pragma: no cover
                    self._set_status(f"tkhtmlview preview failed: {e}")

                    self._set_status("Install tkinterweb (pip install tkinterweb) or tkhtmlview for embedded preview")

        _open_preview_window()
        EditCharacterDialog(self, data, on_save=_save)

    def _export_pdf(self):
        path = self.selected_path
        if not path or not path.exists():
            self._set_status("No character selected")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            char = load_character_template(data)
        except Exception as e:
            self._set_status(f"Failed to load: {e}")
            return

        pdf_name = f"{_safe_slug(char.character_name, 'character')}_{_safe_slug(char.player, 'player')}.pdf"
        pdf_path = EXPORTS_DIR / pdf_name
        try:
            SharedSheetPDF().generate_to_file(sheet_data=char.to_dict(), output_path=pdf_path)
            self._set_status(f"PDF saved to {pdf_path}")
        except Exception as e:  # pragma: no cover
            self._set_status(f"PDF export failed: {e}")

    def _level_up(self):
        path = self.selected_path
        if not path or not path.exists():
            self._set_status("No character selected")
            return

        def _after_save():
            self._set_status(f"Leveled up: {path.name}")
            self._refresh_list()

        LevelUpWizard(self, path, on_saved=_after_save)


def main():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
