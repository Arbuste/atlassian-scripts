#!/usr/bin/env python3
import base64
import csv
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
import math
import sys
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
PARENT_ID = ""   # None ou "" si pas de parent

INPUT_DIR = Path("./adf")
TMP_IMG_DIR = Path("./temp_images")
RESULTS_CSV = Path("./results.csv")
IMG_INDEX = 0

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

def convert_image_nodes(nodes, page_id):
    modified = False
    global IMG_INDEX
    for node in nodes:
        if node.get("type", "") == "mediaSingle":
            media = node.get("content", [{}])[0]
            url = media.get("attrs", {}).get("url", "")
            extracted = extract_base64_image(url)

            if extracted:
                ext, blob = extracted
                filename = f"image_{IMG_INDEX}.{ext}"
                IMG_INDEX += 1

                img_path = TMP_IMG_DIR / filename
                img_path.write_bytes(blob)
                optimize_image(img_path)

                image = upload_attachment(page_id, img_path, filename)
                media["attrs"] = {
                    "type": "file",
                    "id": image["fileId"],
                    "collection": image["collectionName"]
                }
                modified = True
        elif "content" in node:
            modified = modified or convert_image_nodes(node.get("content", []), page_id)
        
    return modified

# ==================================================
# CONFLUENCE API
# ==================================================
def get_space_id():
    r = requests.get(
        f"{BASE_URL}/wiki/api/v2/spaces",
        params={"keys": SPACE_KEY},
        headers=HEADERS_JSON,
        timeout=60,
    )
    r.raise_for_status()
    if "results" in r.json():
        if len(r.json()["results"]) > 0:
            if "id" in r.json()["results"][0]:
                return r.json()["results"][0]["id"]
    raise Exception("Response not formatted correctly: " + str(r.json()))

def create_page(title, space_id, adf):
    payload = {
        "title": title,
        "spaceId": space_id,
        "body": {"value": json.dumps(adf), "representation": "atlas_doc_format"},
    }
    if PARENT_ID:
        payload["parentId"] = PARENT_ID

    r = requests.post(
        f"{BASE_URL}/wiki/api/v2/pages",
        headers=HEADERS_JSON,
        json=payload,
        timeout=60,
    )
    if math.floor(r.status_code / 100) != 2:
        raise Exception(str(r.status_code) + " : " + str(r.json()))
    return r.json()["id"]

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
    if math.floor(r.status_code / 100) != 2:
        raise Exception(str(r.status_code) + " : " + str(r.json()))
    file_metadata = r.json()["results"][0].get("extensions",{})
    return {"fileId": file_metadata["fileId"], "collectionName": file_metadata["collectionName"]}

def get_page_version(page_id):
    r = requests.get(
        f"{BASE_URL}/wiki/api/v2/pages/{page_id}/versions",
        params={"sort": "-modified-date"},
        headers=HEADERS_JSON,
        timeout=30,
    )
    if math.floor(r.status_code / 100) != 2:
        raise Exception(str(r.status_code) + " : " + str(r.json()))
    return r.json()["results"][0]["number"]

def update_page(page_id, title, adf):
    version = get_page_version(page_id)
    payload = {
        "id": page_id,
        "status": "current",
        "title": title,
        "version": {"number": version + 1},
        "body": {"value": json.dumps(adf), "representation": "atlas_doc_format"},
    }
    r = requests.put(
        f"{BASE_URL}/wiki/api/v2/pages/{page_id}",
        headers=HEADERS_JSON,
        json=payload,
        timeout=60,
    )
    if math.floor(r.status_code / 100) != 2:
        raise Exception(str(r.status_code) + " : " + str(r.json()))

# ==================================================
# MAIN
# ==================================================
def main():
    TMP_IMG_DIR.mkdir(exist_ok=True)
    INPUT_DIR.mkdir(exist_ok=True)
    space_id = get_space_id()

    done = load_done_files()
    files = [f for f in INPUT_DIR.glob("*.json") if f.name not in done]

    print(f"Pages à traiter : {len(files)} (déjà faites : {len(done)})")

    for jf in files:
        print(f"\n📄 {jf.name}")
        try:
            adf = json.loads(jf.read_text(encoding="utf-8"))
            title = jf.stem.replace("_", " ").replace(".", " ").strip()

            page_id = create_page(title, space_id, adf)
            print("Page ID: " + str(page_id))

            modified = convert_image_nodes(adf["content"], page_id)
            
            if modified:
                update_page(page_id, title, adf)

            append_result(jf.name, title, page_id, "OK")
            print(f"✅ {title} ({page_id})")

        except Exception as e:
            append_result(jf.name, "", "", "ERROR", str(e))
            print(f"❌ {jf.name} → {e}")

        time.sleep(REQUEST_DELAY)

    print("\n🎉 Migration terminée (mode séquentiel)")

if __name__ == "__main__":
    main()

