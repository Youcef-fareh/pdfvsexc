"""
Template Manager — CRUD for JSON-based extraction templates.
Templates are stored in the user's TEMPLATES_DIR (AppData/FactureConverter/templates/).
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

from app.utils.config import TEMPLATES_DIR


@dataclass
class TemplateField:
    name: str                  # e.g., "N° Facture", "Date", "Table"
    region: list[int]          # [x, y, width, height] in pixels (at 300 DPI)
    field_type: str = "text"   # "text" | "table" | "number" | "date"
    required: bool = False


@dataclass
class Template:
    name: str
    description: str = ""
    fields: list[TemplateField] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    thumbnail_path: str = ""   # Optional path to a reference screenshot

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fields"] = [asdict(f) for f in self.fields]
        return d

    @staticmethod
    def from_dict(data: dict) -> "Template":
        fields = [TemplateField(**f) for f in data.pop("fields", [])]
        return Template(fields=fields, **data)


# ── CRUD operations ───────────────────────────────────────────────────────────

def list_templates() -> list[str]:
    """Return names of all saved templates (without .json extension)."""
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    return [
        os.path.splitext(f)[0]
        for f in sorted(os.listdir(TEMPLATES_DIR))
        if f.endswith(".json")
    ]


def load_template(name: str) -> Template:
    path = _template_path(name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Template not found: {name}")
    with open(path, "r", encoding="utf-8") as fp:
        return Template.from_dict(json.load(fp))


def save_template(template: Template) -> None:
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    template.updated_at = datetime.now().isoformat()
    with open(_template_path(template.name), "w", encoding="utf-8") as fp:
        json.dump(template.to_dict(), fp, ensure_ascii=False, indent=2)


def delete_template(name: str) -> None:
    path = _template_path(name)
    if os.path.exists(path):
        os.remove(path)


def duplicate_template(name: str, new_name: str) -> Template:
    original = load_template(name)
    copy = Template(
        name=new_name,
        description=original.description,
        fields=[TemplateField(**asdict(f)) for f in original.fields],
    )
    save_template(copy)
    return copy


def import_builtin_examples() -> None:
    """Copy bundled example templates into the user's templates directory."""
    from app.utils.config import get_resource_path
    examples_dir = get_resource_path(os.path.join("vendor", "templates"))
    if not os.path.isdir(examples_dir):
        return
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    for fname in os.listdir(examples_dir):
        src = os.path.join(examples_dir, fname)
        dst = os.path.join(TEMPLATES_DIR, fname)
        if fname.endswith(".json") and not os.path.exists(dst):
            shutil.copy2(src, dst)


# ── Template extraction ───────────────────────────────────────────────────────

def apply_template(template: Template, image) -> dict[str, str]:
    """
    Apply a template to a preprocessed PIL Image.
    Returns a dict: field_name → extracted text.
    """
    from app.pipeline.ocr_engine import ocr_region
    from app.utils.arabic_utils import process_cell_text

    result: dict[str, str] = {}
    for tfield in template.fields:
        if len(tfield.region) != 4:
            continue
        region = tuple(tfield.region)  # (x, y, w, h)
        ocr = ocr_region(image, region)
        text = process_cell_text(ocr.raw_text)
        result[tfield.name] = text

    return result


# ── Helper ────────────────────────────────────────────────────────────────────

def _template_path(name: str) -> str:
    safe = name.replace(" ", "_").replace("/", "-")
    return os.path.join(TEMPLATES_DIR, f"{safe}.json")
