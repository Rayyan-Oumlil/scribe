# Scribe — Improvement Roadmap

> Generated 2026-04-07. Prioritized by impact vs effort.

---

## 🔴 High Priority (biggest daily impact)

### 1. Streaming / Real-time transcription
**What:** Start transcribing while you're still speaking, show words appearing live in a floating overlay instead of waiting for release.  
**How:** `faster-whisper` supports a `LiveTranscription` mode. Chunk audio every ~1s and emit partial results.  
**Why:** Cuts perceived latency from ~1–2s to near-zero. This is the #1 thing that makes Whisper Flow feel instant.

---

### 2. Floating overlay widget
**What:** A small transparent pill (like Wispr Flow's) that appears near your cursor when recording — shows waveform bars animating, then the transcribed text fading in.  
**How:** Second `ctk.CTkToplevel` window, `overrideredirect(True)`, positioned near mouse via `pyautogui.position()`.  
**Why:** Right now there's zero visual feedback outside the app window. You can't tell if it recorded or not without switching back to the app.

---

### 3. Audio level meter while recording
**What:** Animated waveform / volume bar in the status area so you can see if your mic is actually picking up sound.  
**How:** Compute RMS of incoming `sounddevice` buffer chunks and update a `CTkProgressBar` via `after()`.  
**Why:** Debugging dead mic, muted input, or wrong device is currently impossible without the log.

---

### 4. Sound feedback (start/stop beeps)
**What:** A short click on press, a different click on release.  
**How:** `winsound.Beep(freq, ms)` — zero dependencies, built into Windows.  
**Why:** Removes all ambiguity about whether the hotkey registered. Industry standard for PTT tools.

---

### 5. Auto-start on Windows login
**What:** Option in Settings to launch Wispr at login.  
**How:** Write a registry key to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` pointing to the shortcut.  
**Why:** Currently you have to manually open it every session.

---

## 🟠 Medium Priority (quality of life)

### 6. Hotkey combinations (not just single keys)
**What:** Support combos like `Right Ctrl`, `Ctrl+Shift`, `Caps Lock`, `F13`–`F24`.  
**How:** `keyboard` library supports `keyboard.add_hotkey("ctrl+shift", ...)`. Update the capture UI to detect combos.  
**Why:** Single keys like `left ctrl` conflict with normal typing. A dedicated combo (e.g. right ctrl alone) is much safer.

---

### 7. Toggle mode vs Push-to-talk
**What:** Option to switch from hold-to-record to tap-once-to-start / tap-again-to-stop.  
**How:** Config flag `"mode": "ptt"` vs `"toggle"`. Changes `_on_press`/`_on_release` logic.  
**Why:** For long dictations, holding a key is tiring. Toggle mode is better for paragraphs.

---

### 8. History search + delete
**What:** Search bar above the history list, and a delete button on each row.  
**How:** Filter `load_history()["entries"]` by substring on input change. Delete updates `history.json`.  
**Why:** History grows fast. Right now there's no way to find or clean up old entries.

---

### 9. Export history
**What:** Button in Home or Scratchpad to export all transcriptions as `.txt` or `.csv`.  
**How:** Write entries to file via `filedialog.asksaveasfilename()`.  
**Why:** Makes the history actually useful for notes, journaling, or review.

---

### 10. Per-app style profiles
**What:** Different corrections/style per application (e.g. casual in Telegram, formal in VS Code).  
**How:** Detect foreground window with `win32gui.GetForegroundWindow()` + `win32process`, match against saved profiles.  
**Why:** This is Wispr Flow's main differentiator. You already have the Style page — this takes it further.

---

## 🟡 Low Priority (nice to have)

### 11. LLM post-processing (optional)
**What:** Optional toggle to run transcription through Claude/local LLM to fix grammar, remove fillers more intelligently, or reformat.  
**How:** Call `anthropic` SDK after Whisper, only if toggled on. Add latency warning in UI.  
**Why:** Whisper output is often run-on sentences with no punctuation. An LLM pass cleans it up significantly.

---

### 12. Multiple microphone selection
**What:** Dropdown in Settings to pick which input device to use.  
**How:** `sounddevice.query_devices()` lists all inputs. Pass `device=id` to `sd.InputStream`.  
**Why:** If you have a headset + webcam mic, it currently picks the system default.

---

### 13. Confidence filtering
**What:** Discard transcription segments below a confidence threshold (Whisper returns `avg_logprob` per segment).  
**How:** Filter `segs` where `s.avg_logprob < threshold` before joining.  
**Why:** Prevents garbage output when Whisper mishears silence or background noise as words.

---

### 14. Clipboard history integration
**What:** Keep last N transcriptions accessible via a quick-access menu on the tray icon.  
**How:** Store last 10 in memory, add submenu to `pystray.Menu`.  
**Why:** If you accidentally paste somewhere else, you lose the text. This gives you a second chance.

---

### 15. Installer / portable `.exe`
**What:** Single-file `.exe` via PyInstaller — no Python needed, works on any Windows machine.  
**How:** `pyinstaller --onefile --noconsole --icon=app_icon.ico app.py`.  
**Why:** Right now setup requires Python 3.11 + CUDA + 8 pip packages. An exe makes it shareable.

---

## Summary Table

| # | Feature | Impact | Effort | Priority |
|---|---------|--------|--------|----------|
| 1 | Streaming transcription | ⬆⬆⬆ | High | 🔴 |
| 2 | Floating overlay | ⬆⬆⬆ | Medium | 🔴 |
| 3 | Audio level meter | ⬆⬆ | Low | 🔴 |
| 4 | Sound feedback | ⬆⬆ | Very low | 🔴 |
| 5 | Auto-start on login | ⬆⬆ | Low | 🔴 |
| 6 | Hotkey combos | ⬆⬆ | Medium | 🟠 |
| 7 | Toggle mode | ⬆⬆ | Low | 🟠 |
| 8 | History search + delete | ⬆⬆ | Low | 🟠 |
| 9 | Export history | ⬆ | Very low | 🟠 |
| 10 | Per-app style profiles | ⬆⬆⬆ | High | 🟠 |
| 11 | LLM post-processing | ⬆⬆ | Medium | 🟡 |
| 12 | Mic selection | ⬆ | Low | 🟡 |
| 13 | Confidence filtering | ⬆ | Low | 🟡 |
| 14 | Clipboard history | ⬆ | Low | 🟡 |
| 15 | Standalone `.exe` | ⬆⬆ | Medium | 🟡 |
