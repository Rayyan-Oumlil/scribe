"""
scribe — hold your hotkey to record, release to transcribe and paste.
"""

# ── Admin elevation (must be first) ──────────────────────────────────────────
import ctypes
import os
import sys


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


if not _is_admin():
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        exe = exe[:-10] + "pythonw.exe"
    script = os.path.abspath(sys.argv[0])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, f'-X utf8 "{script}"', None, 1)
    sys.exit()

# ── Single-instance lock (must be before anything else runs) ──────────────────
_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "Scribe_SingleInstance")
if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    hwnd = ctypes.windll.user32.FindWindowW(None, "Scribe")
    if hwnd:
        SW_RESTORE = 9
        SW_SHOW = 5
        ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
        ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    sys.exit()

# ── stdlib ─────────────────────────────────────────────────────────────────────
import gc  # noqa: E402
import re  # noqa: E402
import site  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "error.log"
LOG_FILE.write_text("")


def log(msg: str) -> None:
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")


log("Starting scribe...")

# ── CUDA DLL paths ────────────────────────────────────────────────────────────
for _s in site.getsitepackages():
    _nv = os.path.join(_s, "nvidia")
    if os.path.isdir(_nv):
        for _pkg in os.listdir(_nv):
            _bin = os.path.join(_nv, _pkg, "bin")
            if os.path.isdir(_bin):
                os.environ["PATH"] = _bin + os.pathsep + os.environ.get("PATH", "")

# ── Third-party imports ───────────────────────────────────────────────────────
try:
    import customtkinter as ctk  # noqa: E402
    import keyboard  # noqa: E402
    import numpy as np  # noqa: E402
    import pyautogui  # noqa: E402
    import pyperclip  # noqa: E402
    import sounddevice as sd  # noqa: E402
    from faster_whisper import WhisperModel  # noqa: E402
    from PIL import Image, ImageDraw  # noqa: E402
    import pystray  # noqa: E402
    import config as cfg_mod  # noqa: E402
    from pages import (  # noqa: E402
        DictionaryPage, HelpPage, HomePage,
        SnippetsPage, ScratchpadPage, SettingsPage, StylePage,
    )
    log("Imports OK")
except Exception as e:
    log(f"Import error: {e}")
    sys.exit(1)

# ── Model lifecycle (lazy load + idle unload) ─────────────────────────────────
# Compute configs tried in order on first load. int8_float16 is ~30% smaller
# than float16 with negligible accuracy loss; falls back if GPU doesn't support it.
COMPUTE_CONFIGS = [
    ("cuda", "int8_float16"),
    ("cuda", "float16"),
    ("cpu",  "int8"),
]
IDLE_TIMEOUT_MINUTES_DEFAULT = 5
IDLE_CHECK_INTERVAL_S        = 30

_model: "WhisperModel | None" = None
_model_lock = threading.Lock()
_last_used  = 0.0  # time.time() of last successful transcription


def _load_model_blocking() -> None:
    """Try each compute config until one loads. Sets _model. Caller holds _model_lock."""
    global _model
    for dev, ct in COMPUTE_CONFIGS:
        try:
            log(f"Loading Whisper on {dev} ({ct})...")
            _model = WhisperModel("large-v3-turbo", device=dev, compute_type=ct)
            log(f"Model ready on {dev} ({ct}).")
            return
        except Exception as e:
            log(f"  load failed on {dev}/{ct}: {e}")
    log("FATAL: model load failed on all configs.")


def _ensure_model_loaded(app: "ScribeApp", show_loading_status: bool = False) -> bool:
    """Block until model is loaded. Returns True on success."""
    global _model
    with _model_lock:
        if _model is not None:
            return True
        if show_loading_status:
            app.after(0, app.set_status, "loading")
        _load_model_blocking()
        return _model is not None


def _trigger_background_load(app: "ScribeApp") -> None:
    """Spawn a daemon thread to load the model in parallel with recording.
    Does NOT change status — recording stays red."""
    if _model is not None:
        return
    threading.Thread(
        target=_ensure_model_loaded, args=(app,), kwargs={"show_loading_status": False}, daemon=True
    ).start()


def _unload_model() -> None:
    """Free model memory. Safe to call at any time; no-op if not loaded."""
    global _model
    with _model_lock:
        if _model is None:
            return
        log("Unloading model (idle).")
        _model = None
    gc.collect()
    log("Model unloaded.")


def _idle_monitor(app: "ScribeApp") -> None:
    """Daemon: unload the model after idle_timeout_minutes of inactivity."""
    while True:
        time.sleep(IDLE_CHECK_INTERVAL_S)
        timeout_min = app.cfg.get("idle_timeout_minutes", IDLE_TIMEOUT_MINUTES_DEFAULT)
        if timeout_min <= 0:
            continue
        if _model is None:
            continue
        if (time.time() - _last_used) > timeout_min * 60:
            _unload_model()

# ── Recording state ───────────────────────────────────────────────────────────
SAMPLE_RATE   = 16000
_recording    = False
_pasting      = False   # suppresses hotkey during ctrl+v paste
_audio_chunks: list = []
_record_start = 0.0
_lock         = threading.Lock()

FILLERS = re.compile(
    r'\b(um+|uh+|hmm+|like|you know|actually|basically|literally)\b[,.]?',
    re.IGNORECASE,
)


def _apply_post(text: str, cfg: dict) -> str:
    style = cfg.get("style", {})
    # Corrections
    for wrong, right in cfg.get("corrections", {}).items():
        text = text.replace(wrong, right)
    # Snippets (whole-word, case-insensitive)
    for shortcut, expansion in cfg.get("snippets", {}).items():
        text = re.sub(r'\b' + re.escape(shortcut) + r'\b', expansion, text, flags=re.IGNORECASE)
    # Filler removal
    if style.get("remove_fillers"):
        text = FILLERS.sub("", text)
        text = re.sub(r' {2,}', " ", text).strip()
    # Capitalize
    if style.get("capitalize") and text:
        text = text[0].upper() + text[1:]
    return text.strip()


def _record_audio() -> None:
    global _audio_chunks
    _audio_chunks = []

    def _cb(indata, frames, t, status):
        with _lock:
            if _recording:
                _audio_chunks.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=_cb):
        while _recording:
            time.sleep(0.05)


def _transcribe_and_paste(app: "ScribeApp") -> None:
    global _record_start, _last_used, _pasting
    with _lock:
        chunks = list(_audio_chunks)
    duration = time.time() - _record_start

    if not chunks:
        app.after(0, app.set_status, "idle")
        return

    audio = np.concatenate(chunks, axis=0).flatten()
    if len(audio) < SAMPLE_RATE * 0.3:
        log("Too short.")
        app.after(0, app.set_status, "idle")
        return

    # Hold the lock for the whole transcribe so the idle monitor can't unload mid-call.
    with _model_lock:
        if _model is None:
            app.after(0, app.set_status, "loading")
            _load_model_blocking()
        if _model is None:
            log("Skipping transcribe — model unavailable.")
            app.after(0, app.set_status, "idle")
            return

        app.after(0, app.set_status, "transcribing")
        try:
            selected_lang = app.cfg.get("language", "auto")
            # "auto" → full Whisper auto-detect.
            # "auto-fr-en" → auto-detect, but snap to fr or en (whichever was more probable).
            # "fr" / "en" / etc → force.
            if selected_lang in ("auto", "auto-fr-en"):
                whisper_lang = None
            else:
                whisper_lang = selected_lang
            segs, info = _model.transcribe(audio, language=whisper_lang, beam_size=1, vad_filter=False)
            if selected_lang == "auto-fr-en" and info.language not in ("fr", "en"):
                probs = dict(getattr(info, "all_language_probs", []) or [])
                snap = "fr" if probs.get("fr", 0) >= probs.get("en", 0) else "en"
                log(f"snap {info.language}->{snap}")
                segs, info = _model.transcribe(audio, language=snap, beam_size=1, vad_filter=False)
            log(f"lang={info.language} p={info.language_probability:.2f}")
            raw  = " ".join(s.text.strip() for s in segs).strip()
            text = _apply_post(raw, app.cfg)
            _last_used = time.time()

            if text:
                log(f"-> {text}")
                cfg_mod.save_entry(text, len(text.split()), duration)
                app.after(0, app.on_new_entry, text)
                _pasting = True
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.1)
                _pasting = False
            else:
                log("Nothing detected.")
        except Exception as e:
            log(f"Transcribe error: {e}")
        finally:
            app.after(0, app.set_status, "idle")


def _hook(app: "ScribeApp") -> None:
    key = app.cfg.get("hotkey", "left ctrl")
    keyboard.on_press_key(key,   lambda e: _on_press(e, app))
    keyboard.on_release_key(key, lambda e: _on_release(e, app))


def _hook_watchdog(app: "ScribeApp") -> None:
    """Re-register keyboard hooks if displaced by another app (Discord, Steam, etc.)."""
    while True:
        time.sleep(10)
        try:
            listener = getattr(keyboard, "_listener", None)
            if listener is None or not listener.is_alive():
                log("Hook watchdog: listener dead, re-registering.")
                keyboard.unhook_all()
                _hook(app)
        except Exception as e:
            log(f"Hook watchdog error: {e}")


def _on_press(e, app: "ScribeApp") -> None:
    global _recording, _record_start
    if _pasting or _recording:
        return
    _recording    = True
    _record_start = time.time()
    app.after(0, app.set_status, "recording")
    threading.Thread(target=_record_audio, daemon=True).start()
    # Load the model in parallel with recording so it's ready by release.
    _trigger_background_load(app)


def _on_release(e, app: "ScribeApp") -> None:
    global _recording
    if _recording:
        _recording = False
        # Status will be set to "loading" or "transcribing" by _transcribe_and_paste.
        threading.Thread(target=_transcribe_and_paste, args=(app,), daemon=True).start()


# ── Tray ──────────────────────────────────────────────────────────────────────

def _make_icon() -> Image.Image:
    img  = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, 63, 63], fill="#111827")
    for x, h in [(10, 14), (19, 26), (28, 34), (37, 26), (46, 14)]:
        draw.rounded_rectangle([x, 32 - h // 2, x + 7, 32 + h // 2], radius=3, fill="white")
    return img


def _start_tray(app: "ScribeApp") -> pystray.Icon:
    icon = pystray.Icon(
        "scribe", _make_icon(), "Scribe",
        menu=pystray.Menu(
            pystray.MenuItem("Show",  lambda *_: app.after(0, app.show_window), default=True),
            pystray.MenuItem("Quit",  lambda *_: app.after(0, app.quit_app)),
        ),
    )
    threading.Thread(target=icon.run, daemon=True).start()
    return icon


# ── GUI ───────────────────────────────────────────────────────────────────────

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

C_BG      = "#FFFFFF"
C_SIDEBAR = "#F5F5F5"
C_MUTED   = "#9CA3AF"
C_ACCENT  = "#111111"
C_BORDER  = "#E5E7EB"
C_ORANGE  = "#F97316"
C_DARK    = "#111827"
F_UI      = "Segoe UI"

_STATUS_COLOR = {
    "idle":         "#22C55E",
    "recording":    "#EF4444",
    "transcribing": "#F59E0B",
    "loading":      "#3B82F6",
}


class ScribeApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.cfg: dict  = cfg_mod.load_config()
        self._tray      = None
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._nav_btns: dict[str, ctk.CTkButton] = {}
        self._current   = "Home"

        self.title("Scribe")
        self.geometry("960x600")
        self.minsize(800, 500)
        self.configure(fg_color=C_BG)
        _ico = BASE_DIR / "assets" / "app_icon.ico"
        if _ico.exists():
            self.iconbitmap(str(_ico))

        self._build_sidebar()
        self._build_stats()
        self._build_main_area()
        self._build_pages()
        self._show("Home")

        self._tray = _start_tray(self)
        _hook(self)
        threading.Thread(target=_idle_monitor,    args=(self,), daemon=True).start()
        threading.Thread(target=_hook_watchdog,   args=(self,), daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        log("Ready (model unloaded; will load on first dictation).")

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        sb = ctk.CTkFrame(self, width=190, fg_color=C_SIDEBAR, corner_radius=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        self._sb = sb

        # Logo
        logo = ctk.CTkFrame(sb, fg_color="transparent")
        logo.pack(padx=16, pady=(22, 18), fill="x")
        ctk.CTkLabel(
            logo, text="Scribe",
            font=ctk.CTkFont(family=F_UI, size=18, weight="bold"),
            text_color=C_ACCENT,
        ).pack(side="left")
        badge = ctk.CTkFrame(logo, fg_color=C_BORDER, corner_radius=4)
        badge.pack(side="left", padx=(7, 0))
        ctk.CTkLabel(
            badge, text="Local",
            font=ctk.CTkFont(family=F_UI, size=10, weight="bold"),
            text_color=C_MUTED,
        ).pack(padx=6, pady=2)

        # Nav
        for label in ["Home", "Dictionary", "Snippets", "Style", "Scratchpad"]:
            b = ctk.CTkButton(
                sb, text=label, anchor="w",
                fg_color="transparent", text_color="#6B7280",
                hover_color="#EBEBEB",
                font=ctk.CTkFont(family=F_UI, size=13),
                height=38, corner_radius=8,
                command=lambda name=label: self._show(name),
            )
            b.pack(fill="x", padx=8, pady=1)
            self._nav_btns[label] = b

        # Bottom nav
        ctk.CTkButton(
            sb, text="⏻  Quit", anchor="w",
            fg_color="transparent", text_color="#EF4444",
            hover_color="#FEE2E2",
            font=ctk.CTkFont(family=F_UI, size=12),
            height=34, corner_radius=8,
            command=self.quit_app,
        ).pack(fill="x", padx=8, pady=(1, 10), side="bottom")

        for label in ["Settings", "Help"]:
            b = ctk.CTkButton(
                sb, text=label, anchor="w",
                fg_color="transparent", text_color="#9CA3AF",
                hover_color="#EBEBEB",
                font=ctk.CTkFont(family=F_UI, size=12),
                height=34, corner_radius=8,
                command=lambda name=label: self._show(name),
            )
            b.pack(fill="x", padx=8, pady=1, side="bottom")
            self._nav_btns[label] = b

    def _build_stats(self) -> None:
        panel = ctk.CTkFrame(self, width=200, fg_color="#F9F9F9", corner_radius=0)
        panel.pack(side="right", fill="y")
        panel.pack_propagate(False)
        self._stats_panel = panel
        self._rebuild_stats()

    def _rebuild_stats(self) -> None:
        for w in self._stats_panel.winfo_children():
            w.destroy()
        total_w, wpm, streak = cfg_mod.compute_stats()
        ctk.CTkLabel(
            self._stats_panel, text="Your stats",
            font=ctk.CTkFont(family=F_UI, size=10, weight="bold"),
            text_color=C_MUTED,
        ).pack(anchor="w", padx=20, pady=(22, 10))
        for val, label in [(f"{total_w:,}", "total words"), (str(wpm), "avg wpm"), (str(streak), "day streak")]:
            f = ctk.CTkFrame(self._stats_panel, fg_color="transparent")
            f.pack(anchor="w", padx=20, pady=(0, 16))
            ctk.CTkLabel(
                f, text=val,
                font=ctk.CTkFont(family=F_UI, size=32, weight="bold"),
                text_color=C_ACCENT,
            ).pack(anchor="w")
            ctk.CTkLabel(
                f, text=label,
                font=ctk.CTkFont(family=F_UI, size=12),
                text_color=C_MUTED,
            ).pack(anchor="w")

    def _build_main_area(self) -> None:
        main = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        main.pack(side="left", fill="both", expand=True)
        self._main = main

        # ── Header ──
        hdr = ctk.CTkFrame(main, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 0))

        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        title_row = ctk.CTkFrame(left, fg_color="transparent")
        title_row.pack(anchor="w")
        ctk.CTkLabel(
            title_row,
            text="Hey Rayyan, get back into the flow with",
            font=ctk.CTkFont(family=F_UI, size=15, weight="bold"),
            text_color=C_ACCENT,
        ).pack(side="left")
        key_badge = ctk.CTkFrame(title_row, fg_color=C_ORANGE, corner_radius=6)
        key_badge.pack(side="left", padx=(8, 0))
        self._hotkey_badge = ctk.CTkLabel(
            key_badge,
            text=self.cfg.get("hotkey", "left ctrl").title(),
            font=ctk.CTkFont(family=F_UI, size=12, weight="bold"),
            text_color="white",
        )
        self._hotkey_badge.pack(padx=10, pady=5)

        ctk.CTkLabel(
            left,
            text="Your voice, transcribed locally — private and fast.",
            font=ctk.CTkFont(family=F_UI, size=12),
            text_color=C_MUTED,
        ).pack(anchor="w", pady=(3, 0))

        self._dot = ctk.CTkLabel(
            hdr, text="●",
            font=ctk.CTkFont(size=18),
            text_color=_STATUS_COLOR["idle"],
        )
        self._dot.pack(side="right", padx=(0, 2))

        # ── Dark promo card ──
        promo = ctk.CTkFrame(main, fg_color=C_DARK, corner_radius=12, height=78)
        promo.pack(fill="x", padx=24, pady=(14, 0))
        promo.pack_propagate(False)
        txt = ctk.CTkFrame(promo, fg_color="transparent")
        txt.place(relx=0.03, rely=0.5, anchor="w")
        ctk.CTkLabel(
            txt, text="Make Scribe sound like you",
            font=ctk.CTkFont(family=F_UI, size=14, weight="bold"),
            text_color="#FFFFFF",
        ).pack(anchor="w")
        ctk.CTkLabel(
            txt, text="Add corrections and snippets in Dictionary and Snippets.",
            font=ctk.CTkFont(family=F_UI, size=11),
            text_color="#6B7280",
        ).pack(anchor="w")
        ctk.CTkButton(
            promo, text="Set up", width=72, height=28,
            fg_color="#1F2937", hover_color="#374151",
            font=ctk.CTkFont(family=F_UI, size=12),
            corner_radius=6, text_color="#F9FAFB",
            command=lambda: self._show("Dictionary"),
        ).place(relx=0.97, rely=0.5, anchor="e")

        # ── Page container ──
        ctk.CTkFrame(main, fg_color=C_BORDER, height=1).pack(fill="x", padx=24, pady=(14, 0))
        self._container = ctk.CTkFrame(main, fg_color=C_BG, corner_radius=0)
        self._container.pack(fill="both", expand=True, padx=24, pady=(8, 12))

    def _build_pages(self) -> None:
        self._pages = {
            "Home":       HomePage(self._container, self),
            "Dictionary": DictionaryPage(self._container, self),
            "Snippets":   SnippetsPage(self._container, self),
            "Style":      StylePage(self._container, self),
            "Scratchpad": ScratchpadPage(self._container, self),
            "Settings":   SettingsPage(self._container, self),
            "Help":       HelpPage(self._container, self),
        }

    # ── Navigation ────────────────────────────────────────────────────────────

    def _show(self, name: str) -> None:
        for page in self._pages.values():
            page.pack_forget()
        self._pages[name].pack(fill="both", expand=True)
        self._pages[name].refresh()
        self._current = name

        # Update sidebar highlight
        for label, btn in self._nav_btns.items():
            is_active = label == name
            btn.configure(
                fg_color="#E9E9E9" if is_active else "transparent",
                text_color=C_ACCENT if is_active else (
                    "#6B7280" if label not in ("Settings", "Help") else "#9CA3AF"
                ),
            )

    # ── Public API (called from recording thread via after()) ─────────────────

    def set_status(self, status: str) -> None:
        self._dot.configure(text_color=_STATUS_COLOR[status])

    def on_new_entry(self, text: str) -> None:
        if self._current == "Home":
            self._pages["Home"].refresh()
        scratchpad: ScratchpadPage = self._pages["Scratchpad"]  # type: ignore[assignment]
        scratchpad.append(text)
        self._rebuild_stats()

    def reload_config(self) -> None:
        """Called whenever config changes (hotkey, corrections, snippets, style)."""
        self.cfg = cfg_mod.load_config()
        self._hotkey_badge.configure(text=self.cfg.get("hotkey", "left ctrl").title())
        # Re-register hooks with the new hotkey (unhook first to avoid doubles)
        keyboard.unhook_all()
        _hook(self)

    # ── Window / tray ─────────────────────────────────────────────────────────

    def show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide_window(self) -> None:
        self.withdraw()

    def quit_app(self) -> None:
        os._exit(0)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = ScribeApp()
    app.mainloop()
