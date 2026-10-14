from pathlib import Path
import unicodedata

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


def norm_text(s: str) -> str:
    """Normalize unicode, strip accents, and casefold."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    ).casefold().strip()


def clean_alphanumeric(s: str) -> str:
    """Normalize and keep only alphanumeric tokens separated by single spaces."""
    normed = norm_text(s)
    return " ".join("".join(c if c.isalnum() else " " for c in normed).split())


def inventory_path(path: str) -> str:
    return path.removeprefix("Literature/")


def corpus_root() -> Path:
    """Return the configured Literature directory."""
    config = REPO / "pyproject.local.toml"
    try:
        with config.open("rb") as fh:
            data = _tomllib.load(fh)
    except FileNotFoundError as exc:
        raise SystemExit(
            f"Missing {config}; set [tool.dqr-literature].lit_root there."
        ) from exc
    except _tomllib.TOMLDecodeError as exc:
        raise SystemExit(f"Invalid TOML in {config}: {exc}") from exc
    tool = data.get("tool", {})
    settings = tool.get("dqr-literature", {}) if isinstance(tool, dict) else None
    value = settings.get("lit_root") if isinstance(settings, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"Set [tool.dqr-literature].lit_root in {config}.")
    root = Path(value).expanduser()
    if not root.is_absolute():
        root = REPO / root
    if not root.is_dir():
        raise SystemExit(f"Literature root is not an available directory: {root}")
    return root
