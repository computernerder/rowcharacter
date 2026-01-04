"""
Generate a PDF of the blank shared standalone character sheet.

Usage:
    python tools/generate_blank_shared_sheet.py

Requirements:
    pip install playwright
    playwright install chromium
"""
from pathlib import Path
import sys

# Allow importing pdf_generator when running from the tools directory
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.pdf_generator import SharedSheetPDF  # noqa: E402


def main() -> None:
    exports_dir = ROOT_DIR / "exports"
    exports_dir.mkdir(exist_ok=True)
    output_path = exports_dir / "blank_standalone.pdf"
    second_dir = ROOT_DIR / "external"  / "rowcharactersheet" /  "output"
    second_dir.mkdir(exist_ok=True)
    second_path = second_dir / "Realm_of_Warriors_Blank_Standalone.pdf"



    generator = SharedSheetPDF()
    generator.generate_to_file(sheet_data={}, fallback_data={}, output_path=output_path)
    generator.generate_to_file(sheet_data={}, fallback_data={}, output_path=second_path)
    
    print(f"Generated blank standalone sheet at {output_path}")


if __name__ == "__main__":
    main()
