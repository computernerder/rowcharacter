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

from character_builder import CharacterBuilder  # noqa: E402
from validation import CharacterValidator  # noqa: E402
from template_model import dump_character_template, load_character_template, Talent as TemplateTalent  # noqa: E402
from tools.pdf_generator import SharedSheetPDF  # noqa: E402
from core.talent import load_all_talents, get_all_talents_flat  # noqa: E402


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
        "inventory_total_weight": (data.get("inventory") or {}).get("total_weight", ""),
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
    def _fill_simple_list(html: str, list_name: str, items: list[str], rows: int = 5) -> str:
        cells = []
        for i in range(rows):
            val = html_mod.escape(str(items[i])) if i < len(items) else ""
            cells.append(f"<tr><td>{val}</td></tr>")
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
        self.geometry("720x640")
        self.minsize(700, 600)

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
        # Follow rulebook order: Race/Ancestry → Profession → Ability Scores → Path → Background
        self.steps = [
            ("Basics", self._render_basics),
            ("Heritage", self._render_heritage),
            ("Profession", self._render_profession),
            ("Ability Scores", self._render_scores),
            ("Path", self._render_path),
            ("Background", self._render_background),
            ("Choices", self._render_choices),
            ("Talents", self._render_talents),
        ]

        self.summary_bar = ctk.CTkFrame(self)
        self.summary_bar.pack(fill="x", padx=12, pady=6)
        self.summary_labels = {}

        # Simple on-screen table instead of HTML summary
        self.summary_table = ctk.CTkFrame(self.summary_bar)
        self.summary_table.grid(row=0, column=0, columnspan=len(self.abilities), sticky="w", pady=(4, 0))
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

        self.body = ctk.CTkFrame(self)
        self.body.pack(fill="both", expand=True, padx=12, pady=8)

        nav = ctk.CTkFrame(self)
        nav.pack(fill="x", padx=12, pady=8)
        self.status = ctk.CTkLabel(nav, text="Fill in each step", anchor="w")
        self.status.grid(row=0, column=0, sticky="w")
        self.btn_back = ctk.CTkButton(nav, text="Back", command=self._prev, state="disabled", width=80)
        self.btn_back.grid(row=0, column=1, padx=6)
        self.btn_next = ctk.CTkButton(nav, text="Next", command=self._next, width=100)
        self.btn_next.grid(row=0, column=2, padx=6)

        self._render_current_step()
        self._update_summary_bar()

    # --------------------------- nav helpers ---------------------------
    def _set_status(self, msg: str):
        self.status.configure(text=msg)

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
        ctk.CTkOptionMenu(frame, variable=self.var_race, values=races, command=lambda _: (self._refresh_ancestries(), self._update_summary_bar())).grid(row=0, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(frame, text="Ancestry").grid(row=1, column=0, padx=8, pady=6, sticky="e")
        self.ancestry_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.var_ancestry,
            values=ancestries,
            command=lambda _: (self._update_heritage_info(), self._update_summary_bar()),
        )
        self.ancestry_menu.grid(row=1, column=1, padx=8, pady=6, sticky="w")

        info = ctk.CTkTextbox(frame, width=560, height=260, activate_scrollbars=True)
        info.grid(row=2, column=0, columnspan=2, padx=8, pady=8, sticky="nsew")
        info.configure(state="disabled")
        self.heritage_info = info
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        self._update_heritage_info()

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

        scroll = ctk.CTkScrollableFrame(frame, width=640, height=360)
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

        # Candidate talents = general + primary path
        category_keys = ["general", primary_path_id]
        candidates = []
        for key in category_keys:
            cat = self.talent_categories.get(key)
            if not cat:
                continue
            for tdef in getattr(cat, "talents", []):
                candidates.append(tdef)

        # Render
        for tdef in sorted(candidates, key=lambda t: (t.path_id or "", t.name)):
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
            for name in self.abilities:
                self.ability_vars[name].set("8")
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
        array = [15, 14, 13, 12, 11, 10]  # auto-assign top six, leave 8 unused
        for name, val in zip(self.abilities, array):
            self.standard_choice_vars[name].set(str(val))
        self._refresh_standard_options()
        self._update_summary_bar()

    def _roll_values(self):
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
        if choice:
            self.standard_choice_vars[ability].set(choice)
        self._refresh_standard_options()
        self._update_summary_bar()

    def _on_roll_pick(self, ability: str, choice: str):
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
        allow_preview = heritage_idx is not None and self.step_index >= heritage_idx
        b = None
        if allow_preview:
            try:
                b = self._build_preview_builder(check_path=False, allow_incomplete=True)
            except Exception:
                b = None

        # Track which abilities the player has assigned (partial ok).
        assigned_scores = self._abilities_dict(allow_incomplete=True) or {}

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
            has_assigned = ability in assigned_scores

            if has_assigned and score_obj:
                delta = score_obj.total - score_obj.roll
                self._update_summary_table(ability, score_obj.roll, score_obj.total, delta)
            elif score_obj:
                # No assigned base yet; show heritage-only delta relative to base 10.
                base = 10
                delta = score_obj.total - base
                self._update_summary_table(ability, None, None, delta, show_delta_only=True)
            else:
                self._update_summary_table(ability, None, None, None)

    def _update_summary_table(self, ability: str, roll_val: int | None, total_val: int | None, delta: int | None, show_delta_only: bool = False):
        row = self.summary_table_rows.get(ability)
        if not row:
            return
        if show_delta_only:
            row["roll"].configure(text="--")
            row["total"].configure(text="--")
            row["mod"].configure(text="--")
            if delta:
                row["delta"].configure(text=f"{delta:+}", text_color="#cc0000")
            else:
                row["delta"].configure(text="--")
            return
        if roll_val is None or total_val is None or delta is None:
            row["roll"].configure(text="--")
            row["total"].configure(text="--")
            row["mod"].configure(text="--")
            row["delta"].configure(text="--")
            return
        row["roll"].configure(text=str(roll_val))
        row["total"].configure(text=str(total_val))
        row["mod"].configure(text=f"{(total_val - 10)//2:+}")
        if delta != 0:
            row["delta"].configure(text=f"{delta:+}", text_color="#cc0000")
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
                self._set_status(f"Talents invalid: {e}")
                return False

            tp_total = self._calculate_level1_talent_points(preview)
            min_primary = min(4, tp_total)
            spent_total, spent_primary = self._talent_points_spent()
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
                    self._set_status(f"Unknown talent id: {tid}")
                    return False
                if tdef.requires_choice and not entry.get("choice_data"):
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
            talents_payload: List[TemplateTalent] = []
            for tid, entry in self.level1_talent_state.items():
                rank = int(entry.get("rank", 0) or 0)
                if rank <= 0:
                    continue
                tdef = self.talents_flat.get(tid)
                name = tdef.name if tdef else tid
                path_id = (tdef.path_id if tdef and tdef.path_id else "general")
                talents_payload.append(TemplateTalent(
                    talent_id=tid,
                    name=name,
                    rank=rank,
                    path_id=path_id,
                    choice_data=entry.get("choice_data") or {},
                    text=f"{name} (Rank {rank})",
                ))
            b.character.talents = talents_payload

            b.recalculate_all()
            if self.on_save:
                self.on_save(b.character)
            self.destroy()
        except Exception as e:
            self._set_status(f"Could not create character: {e}")


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
        ctk.CTkButton(btns, text="Level Up (CLI)", command=self._level_up).pack(fill="x", pady=6)
        ctk.CTkButton(btns, text="Refresh", command=self._refresh_list).pack(fill="x", pady=6)
        ctk.CTkButton(btns, text="Quit", command=self.destroy).pack(fill="x", pady=6)

        self.status = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=4)

        self._refresh_list()

    def _set_status(self, msg: str):
        self.status.configure(text=msg)

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
        # Minimal helper: inform user to run CLI; hook can be expanded later.
        popup = ctk.CTkToplevel(self)
        popup.title("Level Up")
        popup.geometry("360x160")
        ctk.CTkLabel(
            popup,
            text=(
                "Level up uses the CLI for now.\n"
                "Run: python interactive_levelup.py <path to character JSON>"
            ),
            justify="left",
        ).pack(padx=12, pady=12)
        ctk.CTkButton(popup, text="OK", command=popup.destroy).pack(pady=8)


def main():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
