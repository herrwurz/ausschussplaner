"""Exportiert die OpenAPI-Spezifikation als JSON (für Frontend-Codegen)."""
from __future__ import annotations

import json
from pathlib import Path

from app.main import app


def main() -> None:
    spec = app.openapi()
    out = Path("docs/openapi.json")
    out.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ OpenAPI-Spec geschrieben: {out} ({len(spec['paths'])} Pfade)")


if __name__ == "__main__":
    main()
