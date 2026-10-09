from pathlib import Path

try:
    import tomllib as _tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as _tomllib

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
INVENTORY = DATA / "inventory.csv"
SOA = DATA / "soa_citations.csv"
READING_LOG = DATA / "reading_log.csv"
CORRECTIONS = DATA / "inventory_corrections.json"
NOTES = REPO / "notes" / "papers"


def inventory_path(path: str) -> str:
    return path.removeprefix("Literature/")


def _pyproject_lit_root(config: Path | None = None) -> Path | None:
    if config is None:
        config = REPO / "pyproject.toml"
    try:
        with config.open("rb") as fh:
            data = _tomllib.load(fh)
    except (FileNotFoundError, _tomllib.TOMLDecodeError):
        return None
    value = (data.get("tool", {}).get("dqr-literature", {}) or {}).get("lit_root")
    if not value:
        return None
    return Path(value).expanduser()


def corpus_root(root: Path | None = None, *, config: Path | None = None) -> Path:
    if root is not None:
        return root
    if value := _pyproject_lit_root(config):
        return value
    raise SystemExit(
        "Set [tool.dqr-literature].lit_root in pyproject.toml."
    )
