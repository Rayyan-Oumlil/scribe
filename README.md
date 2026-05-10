# scribe

Local, private voice-to-text for Windows — no cloud, no latency, no subscription.

Hold your hotkey → speak → release → transcribed text appears at your cursor, in any app.

Powered by [Whisper Large v3 Turbo](https://github.com/openai/whisper) via [faster-whisper](https://github.com/SYSTRAN/faster-whisper). Runs fully on your GPU.

---

## Features

- **System-wide** — works in any app: VS Code, browser, Discord, Word
- **Auto language detection** — EN/FR by default, configurable
- **Corrections & snippets** — fix names, expand shortcuts
- **Filler removal** — strip um, uh, like, you know
- **Model idle unload** — frees GPU memory after inactivity
- **System tray** — runs in background, always accessible

## Requirements

- Windows 10/11
- Python 3.11
- NVIDIA GPU with CUDA (CPU fallback available, slower)

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Or double-click `run.bat`.

To auto-start at login, run `scripts/add_to_startup.ps1` as Administrator.

## Configuration

Edit `config.json` (auto-created on first run):

| Key | Default | Description |
|-----|---------|-------------|
| `hotkey` | `"left ctrl"` | Key to hold while recording |
| `language` | `"auto-fr-en"` | `"auto"`, `"auto-fr-en"`, `"en"`, `"fr"`, etc. |
| `idle_timeout_minutes` | `5` | Unload model after N idle minutes (`0` = never) |
| `style.capitalize` | `true` | Auto-capitalize first word |
| `style.remove_fillers` | `false` | Strip um / uh / like from output |
| `corrections` | `{}` | Word replacements applied post-transcription |
| `snippets` | `{}` | Short triggers expanded to full phrases |

## Project Structure

```
scribe/
├── app.py              # Entry point — GUI, tray, model, recording, transcription
├── config.py           # Config and history persistence
├── pages.py            # UI pages (Home, Dictionary, Snippets, Style, Scratchpad…)
├── requirements.txt
├── run.bat             # Quick launcher
├── assets/
│   ├── app_icon.ico
│   └── make_icon.py    # Regenerate the icon
└── scripts/
    ├── add_to_startup.ps1    # Register as Windows login task (run as Admin)
    ├── create_shortcut.ps1   # Create desktop shortcut
    ├── transcribe_file.py    # Transcribe an audio file directly
    └── _check_env.ps1        # Diagnose Python / package environment
```

## License

MIT
