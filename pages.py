"""All page implementations for scribe."""
from __future__ import annotations

import threading
from datetime import date, datetime
from itertools import groupby
from typing import TYPE_CHECKING

import customtkinter as ctk
import keyboard
import pyperclip

import config as cfg_mod

if TYPE_CHECKING:
    from app import ScribeApp

# ── Design tokens ─────────────────────────────────────────────────────────────
C_BG      = "#FFFFFF"
C_CARD    = "#F9F9F9"
C_CARD2   = "#F3F4F6"
C_ACCENT  = "#111111"
C_MUTED   = "#9CA3AF"
C_BORDER  = "#E5E7EB"
C_ORANGE  = "#F97316"
C_RED     = "#EF4444"
C_DARK    = "#111827"

F_UI   = "Segoe UI"


# ── Shared helpers ─────────────────────────────────────────────────────────────

def lbl(parent, text, size=13, weight="normal", color=C_ACCENT, **kw):
    return ctk.CTkLabel(
        parent, text=text,
        font=ctk.CTkFont(family=F_UI, size=size, weight=weight),
        text_color=color, **kw,
    )


def btn(parent, text, command, fg=C_ORANGE, hover="#EA6806",
        tc="white", w=100, h=34, **kw):
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color=fg, hover_color=hover, text_color=tc,
        font=ctk.CTkFont(family=F_UI, size=13),
        corner_radius=7, width=w, height=h, **kw,
    )


def section(parent, title: str):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=(18, 8))
    lbl(row, title, size=10, weight="bold", color=C_MUTED).pack(side="left")
    ctk.CTkFrame(row, fg_color=C_BORDER, height=1).pack(
        side="left", fill="x", expand=True, padx=(10, 0), pady=1
    )


def card(parent, radius=10, **kw) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=radius, **kw)


# ── Home ───────────────────────────────────────────────────────────────────────

class HomePage(ctk.CTkFrame):
    def __init__(self, parent, app: "ScribeApp"):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=C_BG, corner_radius=0,
            scrollbar_button_color=C_BORDER,
        )
        self._scroll.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        entries = cfg_mod.load_history()["entries"]
        if not entries:
            lbl(
                self._scroll,
                "No transcriptions yet.\nHold your hotkey and start speaking.",
                size=13, color="#D1D5DB",
            ).pack(pady=60)
            return

        by_day = sorted(entries, key=lambda e: e["timestamp"][:10], reverse=True)
        for day, grp in groupby(by_day, key=lambda e: e["timestamp"][:10]):
            day_label = "TODAY" if day == date.today().isoformat() else day
            lbl(self._scroll, day_label, size=10, weight="bold", color="#D1D5DB").pack(
                anchor="w", pady=(12, 4)
            )
            for entry in grp:
                self._row(entry)

    def _row(self, entry: dict):
        row = card(self._scroll, radius=8)
        row.pack(fill="x", pady=2)
        ts = datetime.fromisoformat(entry["timestamp"]).strftime("%I:%M %p").lstrip("0")
        lbl(row, ts, size=11, color=C_MUTED, width=68, anchor="w").pack(
            side="left", padx=(14, 6), pady=11
        )
        lbl(
            row, entry["text"], size=13,
            wraplength=390, anchor="w", justify="left",
        ).pack(side="left", padx=(0, 14), pady=11, fill="x", expand=True)


# ── Dictionary ─────────────────────────────────────────────────────────────────

class DictionaryPage(ctk.CTkFrame):
    def __init__(self, parent, app: "ScribeApp"):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        scroll = ctk.CTkScrollableFrame(self, fg_color=C_BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)
        self._scroll = scroll
        self._build_form()
        self._list = ctk.CTkFrame(scroll, fg_color="transparent")
        self._list.pack(fill="x")
        self.refresh()

    def _build_form(self):
        section(self._scroll, "WORD CORRECTIONS")
        lbl(
            self._scroll,
            "Fix words Whisper gets wrong. Applied automatically after every transcription.",
            size=12, color=C_MUTED, wraplength=520, justify="left",
        ).pack(anchor="w", pady=(0, 12))

        add = card(self._scroll, radius=10)
        add.pack(fill="x", pady=(0, 14))
        row = ctk.CTkFrame(add, fg_color="transparent")
        row.pack(padx=14, pady=12)

        self._wrong = ctk.StringVar()
        self._right = ctk.StringVar()

        ctk.CTkEntry(
            row, textvariable=self._wrong,
            placeholder_text="Wrong word",
            width=165, height=34,
            font=ctk.CTkFont(family=F_UI, size=13),
        ).pack(side="left", padx=(0, 6))
        lbl(row, "→", size=15, color=C_MUTED).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(
            row, textvariable=self._right,
            placeholder_text="Correct word",
            width=165, height=34,
            font=ctk.CTkFont(family=F_UI, size=13),
        ).pack(side="left", padx=(0, 10))
        btn(row, "+ Add", self._add, w=80).pack(side="left")

        hdr = ctk.CTkFrame(self._scroll, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 4))
        lbl(hdr, "Wrong", size=11, weight="bold", color=C_MUTED, width=165, anchor="w").pack(side="left")
        lbl(hdr, "Correct", size=11, weight="bold", color=C_MUTED).pack(side="left", padx=(44, 0))

    def refresh(self):
        for w in self._list.winfo_children():
            w.destroy()
        corrections = cfg_mod.load_config()["corrections"]
        if not corrections:
            lbl(self._list, "No corrections yet.", size=12, color="#D1D5DB").pack(pady=16)
            return
        for wrong, right in corrections.items():
            self._row(wrong, right)

    def _row(self, wrong: str, right: str):
        row = card(self._list, radius=8)
        row.pack(fill="x", pady=2)
        lbl(row, wrong, size=13, width=165, anchor="w").pack(side="left", padx=(14, 0), pady=10)
        lbl(row, "→", size=13, color=C_MUTED).pack(side="left", padx=10)
        lbl(row, right, size=13, anchor="w").pack(side="left", fill="x", expand=True)

        def _del(w=wrong):
            c = cfg_mod.load_config()
            c["corrections"].pop(w, None)
            cfg_mod.save_config(c)
            self._app.reload_config()
            self.refresh()

        ctk.CTkButton(
            row, text="×", width=28, height=28,
            fg_color="transparent", hover_color="#FEE2E2",
            text_color=C_RED, font=ctk.CTkFont(size=16),
            command=_del,
        ).pack(side="right", padx=10)

    def _add(self):
        wrong = self._wrong.get().strip()
        right = self._right.get().strip()
        if not wrong or not right:
            return
        c = cfg_mod.load_config()
        c["corrections"][wrong] = right
        cfg_mod.save_config(c)
        self._app.reload_config()
        self._wrong.set("")
        self._right.set("")
        self.refresh()


# ── Snippets ───────────────────────────────────────────────────────────────────

class SnippetsPage(ctk.CTkFrame):
    def __init__(self, parent, app: "ScribeApp"):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        scroll = ctk.CTkScrollableFrame(self, fg_color=C_BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)
        self._scroll = scroll
        self._build_form()
        self._list = ctk.CTkFrame(scroll, fg_color="transparent")
        self._list.pack(fill="x")
        self.refresh()

    def _build_form(self):
        section(self._scroll, "TEXT SNIPPETS")
        lbl(
            self._scroll,
            "Say a shortcut word and it expands to full text when transcribed.",
            size=12, color=C_MUTED, wraplength=520, justify="left",
        ).pack(anchor="w", pady=(0, 12))

        add = card(self._scroll, radius=10)
        add.pack(fill="x", pady=(0, 14))

        top = ctk.CTkFrame(add, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 6))
        self._key = ctk.StringVar()
        ctk.CTkEntry(
            top, textvariable=self._key,
            placeholder_text="Shortcut word (e.g. addr)",
            width=220, height=34,
            font=ctk.CTkFont(family=F_UI, size=13),
        ).pack(side="left", padx=(0, 10))
        btn(top, "+ Add", self._add, w=80).pack(side="left")

        self._val = ctk.CTkTextbox(
            add, height=58,
            font=ctk.CTkFont(family=F_UI, size=13),
            border_width=1, border_color=C_BORDER,
            fg_color="#FFFFFF",
        )
        self._val.pack(fill="x", padx=14, pady=(0, 12))
        self._val.insert("0.0", "Expansion text...")

    def refresh(self):
        for w in self._list.winfo_children():
            w.destroy()
        snippets = cfg_mod.load_config()["snippets"]
        if not snippets:
            lbl(self._list, "No snippets yet. Add one above.", size=12, color="#D1D5DB").pack(pady=16)
            return
        for key, val in snippets.items():
            self._row(key, val)

    def _row(self, key: str, val: str):
        row = card(self._list, radius=8)
        row.pack(fill="x", pady=2)
        tag = ctk.CTkFrame(row, fg_color=C_DARK, corner_radius=5)
        tag.pack(side="left", padx=14, pady=10)
        lbl(tag, key, size=12, weight="bold", color=C_ORANGE).pack(padx=8, pady=4)
        lbl(row, "→", size=13, color=C_MUTED).pack(side="left", padx=8)
        preview = val[:55] + ("…" if len(val) > 55 else "")
        lbl(row, preview, size=12, color="#374151", wraplength=320, justify="left").pack(
            side="left", fill="x", expand=True
        )

        def _del(k=key):
            c = cfg_mod.load_config()
            c["snippets"].pop(k, None)
            cfg_mod.save_config(c)
            self._app.reload_config()
            self.refresh()

        ctk.CTkButton(
            row, text="×", width=28, height=28,
            fg_color="transparent", hover_color="#FEE2E2",
            text_color=C_RED, font=ctk.CTkFont(size=16),
            command=_del,
        ).pack(side="right", padx=10)

    def _add(self):
        key = self._key.get().strip()
        val = self._val.get("0.0", "end").strip()
        if not key or not val or val == "Expansion text...":
            return
        c = cfg_mod.load_config()
        c["snippets"][key] = val
        cfg_mod.save_config(c)
        self._app.reload_config()
        self._key.set("")
        self._val.delete("0.0", "end")
        self._val.insert("0.0", "Expansion text...")
        self.refresh()


# ── Style ──────────────────────────────────────────────────────────────────────

class StylePage(ctk.CTkFrame):
    def __init__(self, parent, app: "ScribeApp"):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        scroll = ctk.CTkScrollableFrame(self, fg_color=C_BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)
        self._scroll = scroll
        self._build()

    def _build(self):
        style = cfg_mod.load_config().get("style", {})
        cfg = cfg_mod.load_config()
        section(self._scroll, "POST-PROCESSING")
        lbl(
            self._scroll, "Applied to every transcription automatically.",
            size=12, color=C_MUTED,
        ).pack(anchor="w", pady=(0, 10))

        toggles = [
            ("capitalize",     "Capitalize first letter",  "Ensures output starts with a capital."),
            ("remove_fillers", "Remove filler words",       '"um", "uh", "like", "you know" are stripped.'),
        ]
        self._vars: dict[str, ctk.BooleanVar] = {}

        for key, title, desc in toggles:
            c = card(self._scroll, radius=10)
            c.pack(fill="x", pady=4)
            inner = ctk.CTkFrame(c, fg_color="transparent")
            inner.pack(fill="x", padx=16, pady=14)
            txt = ctk.CTkFrame(inner, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True)
            lbl(txt, title, size=13, weight="bold").pack(anchor="w")
            lbl(txt, desc, size=11, color=C_MUTED).pack(anchor="w")
            var = ctk.BooleanVar(value=style.get(key, False))
            self._vars[key] = var
            ctk.CTkSwitch(
                inner, text="", variable=var, command=self._save,
                progress_color=C_ORANGE, button_color="#FFFFFF",
            ).pack(side="right")

        section(self._scroll, "LANGUAGE")
        c2 = card(self._scroll, radius=10)
        c2.pack(fill="x", pady=4)
        inner2 = ctk.CTkFrame(c2, fg_color="transparent")
        inner2.pack(fill="x", padx=16, pady=14)
        lbl(inner2, "Transcription language", size=13, weight="bold").pack(side="left")
        self._lang_map = {
            "Auto-detect": "auto",
            "English": "en",
            "French": "fr",
            "Spanish": "es",
            "Arabic": "ar",
        }
        current_lang = cfg.get("language", "auto")
        current_label = next((label for label, code in self._lang_map.items() if code == current_lang), "Auto-detect")
        self._lang_menu = ctk.CTkOptionMenu(
            inner2, values=list(self._lang_map.keys()),
            width=140, font=ctk.CTkFont(family=F_UI, size=12),
            fg_color=C_CARD, text_color=C_ACCENT, button_color=C_ORANGE,
            command=self._save_language,
        )
        self._lang_menu.pack(side="right")
        self._lang_menu.set(current_label)

    def _save(self):
        c = cfg_mod.load_config()
        for key, var in self._vars.items():
            c["style"][key] = var.get()
        cfg_mod.save_config(c)
        self._app.reload_config()

    def _save_language(self, label: str):
        c = cfg_mod.load_config()
        c["language"] = self._lang_map.get(label, "auto")
        cfg_mod.save_config(c)
        self._app.reload_config()

    def refresh(self):
        cfg = cfg_mod.load_config()
        current_lang = cfg.get("language", "auto")
        current_label = next((label for label, code in self._lang_map.items() if code == current_lang), "Auto-detect")
        self._lang_menu.set(current_label)


# ── Scratchpad ─────────────────────────────────────────────────────────────────

class ScratchpadPage(ctk.CTkFrame):
    def __init__(self, parent, app: "ScribeApp"):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        self._build()

    def _build(self):
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 4))
        lbl(toolbar, "Scratchpad", size=15, weight="bold").pack(side="left")
        btn(toolbar, "Clear", self._clear, fg=C_CARD2, hover=C_BORDER, tc=C_ACCENT, w=70).pack(side="right", padx=(6, 0))
        btn(toolbar, "Copy all", self._copy, w=90).pack(side="right")

        lbl(self, "Transcriptions auto-append here. Edit freely.", size=12, color=C_MUTED).pack(
            anchor="w", pady=(0, 8)
        )
        self._box = ctk.CTkTextbox(
            self, fg_color=C_CARD, corner_radius=10,
            font=ctk.CTkFont(family=F_UI, size=13),
            border_width=1, border_color=C_BORDER,
        )
        self._box.pack(fill="both", expand=True)

    def append(self, text: str):
        current = self._box.get("0.0", "end").strip()
        sep = "\n\n" if current else ""
        ts  = datetime.now().strftime("%I:%M %p").lstrip("0")
        self._box.insert("end", f"{sep}[{ts}]  {text}")
        self._box.see("end")

    def _clear(self):
        self._box.delete("0.0", "end")

    def _copy(self):
        pyperclip.copy(self._box.get("0.0", "end").strip())

    def refresh(self):
        pass


# ── Settings ───────────────────────────────────────────────────────────────────

class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent, app: "ScribeApp"):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app       = app
        self._capturing = False
        scroll = ctk.CTkScrollableFrame(self, fg_color=C_BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)
        self._scroll = scroll
        self._build()

    def _build(self):
        cfg = cfg_mod.load_config()

        # ── Hotkey ──
        section(self._scroll, "RECORDING")
        c = card(self._scroll, radius=10)
        c.pack(fill="x", pady=4)
        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)

        txt = ctk.CTkFrame(inner, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True)
        lbl(txt, "Recording hotkey", size=13, weight="bold").pack(anchor="w")
        lbl(txt, "Hold to record, release to transcribe and paste.", size=11, color=C_MUTED).pack(anchor="w")

        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        self._badge_frame = ctk.CTkFrame(right, fg_color=C_DARK, corner_radius=6)
        self._badge_frame.pack(side="left", padx=(0, 10))
        self._badge_lbl = lbl(
            self._badge_frame,
            cfg.get("hotkey", "left ctrl").title(),
            size=12, weight="bold", color="white",
        )
        self._badge_lbl.pack(padx=12, pady=7)

        self._change_btn = btn(right, "Change", self._start_capture, w=85)
        self._change_btn.pack(side="left")

        # ── Appearance ──
        section(self._scroll, "APPEARANCE")
        c2 = card(self._scroll, radius=10)
        c2.pack(fill="x", pady=4)
        inner2 = ctk.CTkFrame(c2, fg_color="transparent")
        inner2.pack(fill="x", padx=16, pady=14)
        lbl(inner2, "Theme", size=13, weight="bold").pack(side="left")
        ctk.CTkOptionMenu(
            inner2, values=["Light", "Dark", "System"],
            width=120, font=ctk.CTkFont(family=F_UI, size=12),
            fg_color=C_CARD, text_color=C_ACCENT, button_color=C_ORANGE,
            command=lambda v: ctk.set_appearance_mode(v.lower()),
        ).pack(side="right")

        # ── Memory ──
        section(self._scroll, "MEMORY")
        c4 = card(self._scroll, radius=10)
        c4.pack(fill="x", pady=4)
        inner4 = ctk.CTkFrame(c4, fg_color="transparent")
        inner4.pack(fill="x", padx=16, pady=14)
        txt4 = ctk.CTkFrame(inner4, fg_color="transparent")
        txt4.pack(side="left", fill="x", expand=True)
        lbl(txt4, "Unload model when idle", size=13, weight="bold").pack(anchor="w")
        lbl(txt4, "Frees ~1.4 GB of RAM after this many minutes without dictation.",
            size=11, color=C_MUTED).pack(anchor="w")
        self._idle_map = {
            "Off":    0,
            "1 min":  1,
            "5 min":  5,
            "10 min": 10,
            "30 min": 30,
        }
        current_minutes = int(cfg.get("idle_timeout_minutes", 5))
        current_idle_label = next(
            (label for label, mins in self._idle_map.items() if mins == current_minutes),
            "5 min",
        )
        self._idle_menu = ctk.CTkOptionMenu(
            inner4, values=list(self._idle_map.keys()),
            width=120, font=ctk.CTkFont(family=F_UI, size=12),
            fg_color=C_CARD, text_color=C_ACCENT, button_color=C_ORANGE,
            command=self._save_idle_timeout,
        )
        self._idle_menu.pack(side="right")
        self._idle_menu.set(current_idle_label)

        # ── About ──
        section(self._scroll, "ABOUT")
        c3 = card(self._scroll, radius=10)
        c3.pack(fill="x", pady=4)
        lbl(c3, "Scribe  —  Private, offline dictation", size=12, color=C_MUTED).pack(
            anchor="w", padx=16, pady=(12, 4)
        )
        lbl(c3, "Whisper Large v3 Turbo  ·  faster-whisper  ·  CUDA", size=11, color="#D1D5DB").pack(
            anchor="w", padx=16, pady=(0, 12)
        )

    def _start_capture(self):
        if self._capturing:
            return
        self._capturing = True
        self._change_btn.configure(text="Press a key…", state="disabled", fg_color="#9CA3AF")
        self._badge_lbl.configure(text="?")

        keyboard.unhook_all()

        def _listen():
            captured = []

            def _handler(e):
                if e.event_type == keyboard.KEY_DOWN and not captured:
                    captured.append(e.name)
                    keyboard.unhook_all()
                    self._app.after(0, self._finish_capture, e.name)

            keyboard.hook(_handler)

        threading.Thread(target=_listen, daemon=True).start()

    def _finish_capture(self, key: str):
        self._capturing = False
        self._change_btn.configure(text="Change", state="normal", fg_color=C_ORANGE)

        cfg = cfg_mod.load_config()
        if key in ("escape", "esc"):
            # Cancelled — restore old badge text
            self._badge_lbl.configure(text=cfg.get("hotkey", "left ctrl").title())
        else:
            cfg["hotkey"] = key
            cfg_mod.save_config(cfg)
            self._badge_lbl.configure(text=key.title())
            self._app.reload_config()

    def _save_idle_timeout(self, label: str):
        cfg = cfg_mod.load_config()
        cfg["idle_timeout_minutes"] = self._idle_map.get(label, 5)
        cfg_mod.save_config(cfg)
        self._app.reload_config()

    def refresh(self):
        cfg = cfg_mod.load_config()
        self._badge_lbl.configure(text=cfg.get("hotkey", "left ctrl").title())
        current_minutes = int(cfg.get("idle_timeout_minutes", 5))
        current_idle_label = next(
            (label for label, mins in self._idle_map.items() if mins == current_minutes),
            "5 min",
        )
        self._idle_menu.set(current_idle_label)


# ── Help ───────────────────────────────────────────────────────────────────────

class HelpPage(ctk.CTkFrame):
    def __init__(self, parent, app: "ScribeApp"):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self._app = app
        scroll = ctk.CTkScrollableFrame(self, fg_color=C_BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)
        self._build(scroll)

    def _build(self, scroll):
        section(scroll, "HOW TO USE")
        for num, title, desc in [
            ("1", "Hold your hotkey",    "Press and hold the key set in Settings → Recording hotkey."),
            ("2", "Speak clearly",        "Whisper Large v3 Turbo transcribes everything you say."),
            ("3", "Release to paste",     "Let go — text is pasted into your active window instantly."),
            ("4", "Run in background",    "Close the window. Scribe stays active in the system tray."),
        ]:
            c = card(scroll, radius=10)
            c.pack(fill="x", pady=4)
            inner = ctk.CTkFrame(c, fg_color="transparent")
            inner.pack(fill="x", padx=16, pady=12)
            badge = ctk.CTkFrame(inner, fg_color=C_ORANGE, corner_radius=20, width=30, height=30)
            badge.pack(side="left", padx=(0, 14))
            badge.pack_propagate(False)
            lbl(badge, num, size=12, weight="bold", color="white").place(relx=0.5, rely=0.5, anchor="center")
            txt = ctk.CTkFrame(inner, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True)
            lbl(txt, title, size=13, weight="bold").pack(anchor="w")
            lbl(txt, desc, size=11, color=C_MUTED, wraplength=420, justify="left").pack(anchor="w")

        section(scroll, "TIPS")
        for tip in [
            "Use Dictionary to fix recurring word errors (e.g. Ryan → Rayyan).",
            "Use Snippets to expand shorthand — say 'addr' and get your full address.",
            "Enable filler word removal in Style to clean up 'um', 'uh', 'like'.",
            "Right-click the taskbar tray icon to quit the app completely.",
        ]:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=3)
            lbl(row, "·", size=16, color=C_ORANGE, width=18).pack(side="left")
            lbl(row, tip, size=12, color="#374151", wraplength=490, justify="left").pack(side="left")

        section(scroll, "SHORTCUTS")
        for key, action in [
            ("Hold hotkey",    "Start recording"),
            ("Release hotkey", "Transcribe and paste"),
            ("Tray → Show",    "Bring window back"),
            ("Tray → Quit",    "Exit completely"),
        ]:
            row = card(scroll, radius=8)
            row.pack(fill="x", pady=2)
            kb = ctk.CTkFrame(row, fg_color=C_DARK, corner_radius=5)
            kb.pack(side="left", padx=14, pady=10)
            lbl(kb, key, size=11, weight="bold", color="white").pack(padx=8, pady=4)
            lbl(row, action, size=12, color="#374151").pack(side="left", padx=12)

    def refresh(self):
        pass
