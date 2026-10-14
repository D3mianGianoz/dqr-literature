import csv
from functools import cache
from pathlib import Path

import spacy


@cache
def get_nlp() -> spacy.language.Language:
    try:
        return spacy.load("en_core_web_md")
    except OSError as exc:
        raise SystemExit(
            "spaCy model en_core_web_md is missing; install it with "
            "`uv run python -m spacy download en_core_web_md`."
        ) from exc


def load_csv(path: Path, *, missing_ok: bool = False) -> list[dict[str, str]]:
    if not path.exists():
        if missing_ok:
            return []
        raise SystemExit(f"Required CSV file is missing: {path}")
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))
