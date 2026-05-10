"""Config and history persistence for scribe."""
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG_FILE  = BASE_DIR / "config.json"
HISTORY_FILE = BASE_DIR / "history.json"

_CONFIG_DEFAULTS: dict = {
    "hotkey": "left ctrl",
    "language": "auto-fr-en",
    "idle_timeout_minutes": 5,  # 0 = never unload
    "corrections": {
        "Ryan":  "Rayyan",
        "Riyan": "Rayyan",
        "Rayan": "Rayyan",
    },
    "snippets": {},
    "style": {
        "capitalize":      True,
        "remove_fillers":  False,
    },
}

# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text())
            out = {**_CONFIG_DEFAULTS, **saved}
            out["language"]              = saved.get("language", _CONFIG_DEFAULTS["language"])
            out["idle_timeout_minutes"]  = int(saved.get("idle_timeout_minutes", _CONFIG_DEFAULTS["idle_timeout_minutes"]))
            out["style"]                 = {**_CONFIG_DEFAULTS["style"],       **saved.get("style", {})}
            out["corrections"]           = saved.get("corrections", dict(_CONFIG_DEFAULTS["corrections"]))
            out["snippets"]              = saved.get("snippets", {})
            return out
        except Exception:
            pass
    return {k: dict(v) if isinstance(v, dict) else v for k, v in _CONFIG_DEFAULTS.items()}

def save_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

# ── History ───────────────────────────────────────────────────────────────────

def load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass
    return {"entries": []}

def save_entry(text: str, words: int, duration: float) -> None:
    from datetime import datetime
    h = load_history()
    h["entries"].append({
        "timestamp": datetime.now().isoformat(),
        "text":      text,
        "words":     words,
        "duration":  round(duration, 2),
    })
    HISTORY_FILE.write_text(json.dumps(h, indent=2))

def compute_stats() -> tuple[int, int, int]:
    from datetime import date, timedelta
    entries    = load_history()["entries"]
    total_w    = sum(e["words"] for e in entries)
    total_dur  = sum(e.get("duration", 0) for e in entries)
    wpm        = int((total_w / total_dur) * 60) if total_dur > 0 else 0
    if not entries:
        return total_w, wpm, 0
    days   = sorted({e["timestamp"][:10] for e in entries}, reverse=True)
    streak = 0
    for i, d in enumerate(days):
        if date.fromisoformat(d) == date.today() - timedelta(days=i):
            streak += 1
        else:
            break
    return total_w, wpm, streak
