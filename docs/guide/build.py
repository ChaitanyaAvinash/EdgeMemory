"""Builds the EdgeMemory user guide PDF (docs/EdgeMemory-Guide.pdf) from guide.src.html.

Owns: expanding screenshot placeholders into cropped figures, then printing the page to PDF with Microsoft
Edge in headless mode (no extra packages). A placeholder is
    <!--shot file.png Y H | caption-->
and shows the band of the 1440-pixel-wide screenshot from pixel row Y, H pixels tall. Each band is cropped to a
JPEG in docs/guide/img/crops with Windows' built-in System.Drawing, which keeps the PDF small (about 2.6 MB).

Screenshots come from the running app (docs/guide/img, taken with headless Edge at 1440 px wide, light theme,
reduced motion). Usage: python docs/guide/build.py
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
WIDTH = 1440  # screenshot width in pixels
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


CROPS: list[tuple[str, int, int, str]] = []  # (source png, y, h, output jpg) for crop_all()


def figure(m: re.Match) -> str:
    name, y, h, caption = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).strip()
    out = f"crops/{Path(name).stem}-{y}-{h}.jpg"
    CROPS.append((name, y, h, out))
    return (
        f'<figure class="shot"><div class="crop"><img src="img/{out}" alt="{caption}"></div>'
        f"<figcaption>{caption}</figcaption></figure>"
    )


def crop_all() -> None:
    """Crop each band to a JPEG with Windows' built-in System.Drawing (keeps the PDF small; no extra packages)."""
    (HERE / "img" / "crops").mkdir(exist_ok=True)
    lines = [
        "Add-Type -AssemblyName System.Drawing",
        "$enc = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }",
        "$p = New-Object System.Drawing.Imaging.EncoderParameters(1)",
        "$p.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]84)",
    ]
    for name, y, h, out in CROPS:
        src, dst = HERE / "img" / name, HERE / "img" / out
        lines += [
            f"$img = [System.Drawing.Image]::FromFile('{src}')",
            f"$hh = [Math]::Min({h}, $img.Height - {y})",
            "$bmp = New-Object System.Drawing.Bitmap($img.Width, $hh)",
            "$g = [System.Drawing.Graphics]::FromImage($bmp)",
            "$g.InterpolationMode = 'HighQualityBicubic'",
            f"$g.DrawImage($img, (New-Object System.Drawing.Rectangle(0, 0, $img.Width, $hh)), "
            f"(New-Object System.Drawing.Rectangle(0, {y}, $img.Width, $hh)), 'Pixel')",
            f"$bmp.Save('{dst}', $enc, $p)",
            "$g.Dispose(); $bmp.Dispose(); $img.Dispose()",
        ]
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", "\n".join(lines)], check=True, capture_output=True
    )


def main() -> None:
    src = (HERE / "guide.src.html").read_text(encoding="utf-8")
    html = re.sub(r"<!--shot\s+(\S+)\s+(\d+)\s+(\d+)\s*\|(.*?)-->", figure, src, flags=re.S)
    crop_all()
    # The cover uses the whole home screenshot; ship it as a JPEG too.
    CROPS.clear()
    CROPS.append(("home-light.png", 0, 1060, "crops/cover.jpg"))
    crop_all()
    html = html.replace('src="img/home-light.png"', 'src="img/crops/cover.jpg"')
    out_html = HERE / "guide.html"
    out_html.write_text(html, encoding="utf-8")
    pdf = HERE.parent / "EdgeMemory-Guide.pdf"
    subprocess.run(
        [
            EDGE,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--virtual-time-budget=8000",
            f"--print-to-pdf={pdf}",
            out_html.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    print(f"wrote {pdf} ({pdf.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
