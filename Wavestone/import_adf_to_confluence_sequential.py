#!/usr/bin/env python3
import base64
import csv
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
from PIL import Image

# ==================================================
# CONFIGURATION
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from environment_config import get_environment
environment = get_environment("wavestone")
# ==================================================
EMAIL = environment["username"]
API_TOKEN = environment["user_token"]
BASE_URL = environment["confluence_base_url"].rstrip("/")

SPACE_KEY = "EXTITKB"
PARENT_ID = "3501621542"   # None ou "" si pas de parent

INPUT_DIR = Path("./adf")
TMP_IMG_DIR = Path("./temp_images")
RESULTS_CSV = Path("./results.csv")

REQUEST_DELAY = 0.3     # sécurité API

MAX_IMAGE_WIDTH = 1600
IMAGE_QUALITY = 85

# ==================================================
# AUTH / HEADERS
# ==================================================
def auth_header():
    token = f"{EMAIL}:{API_TOKEN}".encode()
    return "Basic " + base64.b64encode(token).decode()

HEADERS_JSON = {
    "Authorization": auth_header(),
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# ==================================================
# CSV RESUME
# ==================================================
def load_done_files() -> set:
    if not RESULTS_CSV.exists():
        return set()
    with RESULTS_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["file"] for row in reader if row["status"] == "OK"}

def append_result(file, title, page_id, status, error=""):
    write_header = not RESULTS_CSV.exists()
    with RESULTS_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["file", "title", "page_id", "status", "error"])
        writer.writerow([file, title, page_id, status, error])

# ==================================================
# IMAGE HANDLING
# ==================================================
def optimize_image(path: Path):
    with Image.open(path) as img:
        if img.width > MAX_IMAGE_WIDTH:
            ratio = MAX_IMAGE_WIDTH / img.width
            img = img.resize(
                (MAX_IMAGE_WIDTH, int(img.height * ratio)),
                Image.LANCZOS
            )
        img.save(path, optimize=True, quality=IMAGE_QUALITY)

# ==================================================
# ADF → STORAGE
# ==================================================
@dataclass
class RenderResult:
    html: str
    images: List[Tuple[Path, str]]

def escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )

def extract_base64_image(url: str):
    m = re.match(r"^data:image/([a-zA-Z0-9.+-]+);base64,(.+)$", url)
    if not m:
        return None
    return m.group(1), base64.b64decode(m.group(2))

def adf_to_storage(adf: Dict[str, Any]) -> RenderResult:
    html = []
    images = []
    img_index = 0

    for node in adf.get("content", []):
        t = node.get("type")

        if t == "heading":
            level = node.get("attrs", {}).get("level", 3)
            text = "".join(c.get("text", "") for c in node.get("content", []))
            html.append(f"<h{level}>{escape(text)}</h{level}>")

        elif t == "paragraph":
            text = "".join(c.get("text", "") for c in node.get("content", []))
            html.append(f"<p>{escape(text)}</p>")

        elif t == "bulletList":
            html.append("<ul>")
            for li in node.get("content", []):
                text = "".join(
                    c.get("text", "")
                    for p in li.get("content", [])
                    for c in p.get("content", [])
                )
                html.append(f"<li>{escape(text)}</li>")
            html.append("</ul>")

        elif t == "mediaSingle":
            media = node.get("content", [{}])[0]
            url = media.get("attrs", {}).get("url", "")
            extracted = extract_base64_image(url)

            if extracted:
                ext, blob = extracted
                filename = f"image_{img_index}.{ext}"
                img_index += 1

                img_path = TMP_IMG_DIR / filename
                img_path.write_bytes(blob)
                optimize_image(img_path)

                html.append(
                    f'<ac:image>'
                    f'<ri:attachment ri:filename="{filename}" />'
                    f'</ac:image>'
                )
                images.append((img_path, filename))

    return RenderResult("".join(html), images)

# ==================================================
# CONFLUENCE API
# ==================================================
def create_page(title, storage):
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": SPACE_KEY},
        "body": {"storage": {"value": storage, "representation": "storage"}},
    }
    if PARENT_ID:
        payload["ancestors"] = [{"id": PARENT_ID}]

    r = requests.post(
        f"{BASE_URL}/wiki/rest/api/content",
        headers=HEADERS_JSON,
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["id"]

def get_page_version(page_id):
    r = requests.get(
        f"{BASE_URL}/wiki/rest/api/content/{page_id}?expand=version",
        headers=HEADERS_JSON,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["version"]["number"]

def update_page(page_id, title, storage):
    version = get_page_version(page_id)
    payload = {
        "id": page_id,
        "type": "page",
        "title": title,
        "version": {"number": version + 1},
        "body": {"storage": {"value": storage, "representation": "storage"}},
    }
    r = requests.put(
        f"{BASE_URL}/wiki/rest/api/content/{page_id}",
        headers=HEADERS_JSON,
        json=payload,
        timeout=60,
    )
    r.raise_for_status()

def upload_attachment(page_id, path, filename):
    with path.open("rb") as f:
        r = requests.post(
            f"{BASE_URL}/wiki/rest/api/content/{page_id}/child/attachment",
            headers={
                "Authorization": HEADERS_JSON["Authorization"],
                "X-Atlassian-Token": "nocheck",
            },
            files={"file": (filename, f)},
            timeout=120,
        )
    r.raise_for_status()

# ==================================================
# MAIN
# ==================================================
def main():
    TMP_IMG_DIR.mkdir(exist_ok=True)
    INPUT_DIR.mkdir(exist_ok=True)

    done = load_done_files()
    files = [f for f in INPUT_DIR.glob("*.json") if f.name not in done]

    print(f"Pages à traiter : {len(files)} (déjà faites : {len(done)})")

    for jf in files:
        print(f"\n📄 {jf.name}")
        try:
            adf = json.loads(jf.read_text(encoding="utf-8"))
            title = jf.stem.replace("_", " ").replace(".", " ").strip()

            rr = adf_to_storage(adf)
            page_id = create_page(title, rr.html)

            for img_path, filename in rr.images:
                upload_attachment(page_id, img_path, filename)

            if rr.images:
                update_page(page_id, title, rr.html)

            append_result(jf.name, title, page_id, "OK")
            print(f"✅ {title} ({page_id})")

        except Exception as e:
            append_result(jf.name, "", "", "ERROR", str(e))
            print(f"❌ {jf.name} → {e}")

        time.sleep(REQUEST_DELAY)

    print("\n🎉 Migration terminée (mode séquentiel)")

if __name__ == "__main__":
    main()

