import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
INVENTORY = DATA / "inventory.csv"
SOA = DATA / "soa_citations.csv"
READING_LOG = DATA / "reading_log.csv"


def inventory_path(path: str) -> str:
    return path.removeprefix("Literature/")


def corpus_root(root: Path | None = None) -> Path:
    if root is not None:
        return root
    if value := os.environ.get("LIT"):
        return Path(value)
    raise SystemExit("Set LIT to the Literature directory or pass --root.")
