import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment

cloud_environment = get_environment("avril")

import csv
from collections import defaultdict
import requests

# ConfigurationBEARER_TOKEN = cloud_environment["org_token"]
ORG_ID = cloud_environment["org_id"]
DIRECTORY_ID = cloud_environment["directory_id"]
CSV_PATH = r"C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Avril\Membership Users Récents.csv"

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# 1. Lecture du CSV et regroupement des groupes par adresse email
email_to_groups = defaultdict(set)
distinct_groups = set()

with open(CSV_PATH, mode="r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        email = row["lower_email_address"].strip()
        group = row["group_name"].strip()
        if email and group:
            email_to_groups[email].add(group)
            distinct_groups.add(group)

# 2. Récupération ou création des ID pour chaque groupe unique
group_name_to_id = {}

for group_name in distinct_groups:
    search_url = f"{ORG_BASE_URL}/admin/v2/orgs/{ORG_ID}/directories/{DIRECTORY_ID}/groups/search"
    search_payload = {"searchTerm": group_name}

    search_res = requests.post(search_url, headers=HEADERS, json=search_payload)
    search_res.raise_for_status()
    data = search_res.json().get("data", [])

    # Vérification d'une correspondance exacte sur l'attribut "name"
    matching_group = next((g for g in data if g.get("name") == group_name), None)

    if matching_group:
        group_id = matching_group["id"]
    else:
        create_url = f"{ORG_BASE_URL}/admin/v2/orgs/{ORG_ID}/directories/{DIRECTORY_ID}/groups"
        create_payload = {"name": group_name}
        
        create_res = requests.post(create_url, headers=HEADERS, json=create_payload)
        create_res.raise_for_status()
        group_id = create_res.json()["id"]

    group_name_to_id[group_name] = group_id

# 3. Envoi des invitations par adresse email avec leurs groupes associés
invite_url = f"{ORG_BASE_URL}/admin/v2/orgs/{ORG_ID}/users/invite"

for email, groups in email_to_groups.items():
    group_ids = [group_name_to_id[g] for g in groups]
    invite_payload = {
        "emails": [email],
        "additionalGroups": group_ids
    }

    invite_res = requests.post(invite_url, headers=HEADERS, json=invite_payload)
    invite_res.raise_for_status()
    print(f"Invitation envoyée pour {email} ({len(group_ids)} groupe(s)).")