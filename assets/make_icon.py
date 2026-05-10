"""Generate app_icon.ico and update the desktop shortcut."""
from pathlib import Path
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).parent


def draw_icon(size: int) -> Image.Image:
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad    = int(size * 0.04)
    radius = int(size * 0.22)

    # Background — dark rounded square
    draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, fill="#111827")

    # Waveform bars (5 bars, center-aligned, orange + white)
    n_bars   = 5
    bar_w    = max(2, int(size * 0.09))
    gap      = max(1, int(size * 0.04))
    total_w  = n_bars * bar_w + (n_bars - 1) * gap
    x_start  = (size - total_w) // 2
    cx       = size // 2
    heights  = [0.28, 0.48, 0.62, 0.48, 0.28]   # relative to icon size

    for i, h_ratio in enumerate(heights):
        bh   = int(size * h_ratio)
        x0   = x_start + i * (bar_w + gap)
        y0   = cx - bh // 2
        x1   = x0 + bar_w
        y1   = y0 + bh
        br   = bar_w // 2
        color = "#F97316" if i == 2 else "#FFFFFF"   # centre bar orange
        draw.rounded_rectangle([x0, y0, x1, y1], radius=br, fill=color)

    return img


def build_ico() -> Path:
    sizes  = [16, 24, 32, 48, 64, 128, 256]
    frames = [draw_icon(s) for s in sizes]
    ico    = BASE_DIR / "app_icon.ico"
    frames[0].save(
        ico, format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"Icon saved: {ico}")
    return ico


def update_shortcut(ico_path: Path) -> None:
    import subprocess
    script = rf"""
$ws  = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut([System.Environment]::GetFolderPath('Desktop') + '\Scribe.lnk')
$lnk.TargetPath       = 'pyw.exe'
$lnk.Arguments        = '-3.11 -X utf8 "{BASE_DIR / "app.py"}"'
$lnk.WorkingDirectory = '{BASE_DIR}'
$lnk.IconLocation     = '{ico_path}'
$lnk.Description      = 'Scribe — offline dictation'
$lnk.WindowStyle      = 7   # minimised (hides the brief flash)
$lnk.Save()
Write-Host "Shortcut updated."
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True,
    )
    print(result.stdout.strip() or result.stderr.strip())


if __name__ == "__main__":
    ico = build_ico()
    update_shortcut(ico)
    print("Done. Refresh your desktop (F5) to see the new icon.")
