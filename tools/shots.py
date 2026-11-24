"""
Capture portfolio screenshots of the live sites listed in src/work.json.

    py tools/shots.py               every project
    py tools/shots.py rohtak-property-point yopdfs    only these slugs

For each project it writes, into src/assets/img/work/:
    <slug>.jpg      desktop view, 1280x800
    <slug>-sm.jpg   desktop view, 640x400 (grid cards)
    <slug>-m.jpg    phone view, 360x780

Needs Chrome and internet. Re-run after a client site changes, then `py tools/build.py`.
"""
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = SRC / "assets" / "img" / "work"
TOOLS = ROOT / "tools"
CHROME = next((p for p in [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
] if pathlib.Path(p).exists()), None)
MOBILE_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/131.0.0.0 Mobile Safari/537.36")


def shot(url, png, w, h, scale=1, mobile=False, budget=15000):
    prof = pathlib.Path(tempfile.gettempdir()) / "navera-shots-profile"
    args = [CHROME, "--headless=new", "--hide-scrollbars", "--no-first-run", "--mute-audio",
            "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
            f"--force-device-scale-factor={scale}", f"--user-data-dir={prof}",
            f"--window-size={w},{h}", f"--virtual-time-budget={budget}", f"--screenshot={png}"]
    if mobile:
        args.append(f"--user-agent={MOBILE_UA}")
    args.append(url)
    if png.exists():
        png.unlink()
    subprocess.run(args, check=False, capture_output=True, timeout=180)
    if not png.exists():
        raise SystemExit(f"screenshot failed: {url}")


def to_jpg(src, dst, w, h, q):
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(TOOLS / "resize.ps1"),
                    "-In", str(src), "-Out", str(dst), "-W", str(w), "-H", str(h), "-Format", "jpg", "-Quality", str(q)],
                   check=True)


def main():
    if not CHROME:
        raise SystemExit("Chrome/Edge not found")
    work = json.loads((SRC / "work.json").read_text(encoding="utf-8"))
    only = set(sys.argv[1:])
    cache = TOOLS / ".cache" / "shots"
    cache.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for p in work["projects"]:
        slug = p["slug"]
        if only and slug not in only:
            continue
        url = p.get("shotUrl") or p["url"]
        budget = p.get("shotWait", 15000)
        d = cache / f"{slug}-d.png"
        shot(url, d, 1440, 900, budget=budget)
        to_jpg(d, OUT / f"{slug}.jpg", 1280, 800, 80)
        to_jpg(d, OUT / f"{slug}-sm.jpg", 640, 400, 78)
        # headless Chrome won't lay out a window narrower than ~500px, so the phone view is a
        # 390px iframe pinned to the top-left of the page; the screenshot crops to it exactly.
        frame = cache / f"{slug}-frame.html"
        frame.write_text('<!doctype html><html><body style="margin:0;background:#000">'
                         f'<iframe src="{url}" style="display:block;border:0;width:390px;height:844px"></iframe>'
                         '</body></html>', encoding="utf-8")
        m = cache / f"{slug}-m.png"
        shot(frame.resolve().as_uri(), m, 390, 844, scale=2, mobile=True, budget=budget)
        to_jpg(m, OUT / f"{slug}-m.jpg", 360, 780, 80)
        print("shot:", slug)


if __name__ == "__main__":
    main()
