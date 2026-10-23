import json
import math
import requests
from environment_config import get_environment

# Environment configuration
environment = get_environment("open_groupe_sandbox")
ORG_ID = environment["org_id"]
ORG_TOKEN = environment["org_token"]
ORG_BASE_URL = environment["org_base_url"]
WORKSPACE_ID = "ari:cloud:jira-servicedesk::site/67894255-e191-4f88-8803-21545b04a2a8"

USER_EMAILS = [
    "user1@example.com",
    "user2@example.com",
    # Add remaining email addresses here
]

BATCH_SIZE = 25


def chunk_list(lst, size):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def invite_users():
    url = ORG_BASE_URL.rstrip("/") + f"/admin/v2/orgs/{ORG_ID}/users/invite"

    headers = {
        "Authorization": f"Bearer {ORG_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    email_batches = list(chunk_list(USER_EMAILS, BATCH_SIZE))
    total_batches = len(email_batches)

    print(
        f"Starting invitations for {len(USER_EMAILS)} users across {total_batches} batch(es)..."
    )

    for index, batch in enumerate(email_batches, start=1):
        payload = {
            "emails": batch,
            "permissionRules": [
                {
                    "resource": WORKSPACE_ID,
                    "role": "atlassian/customer",
                }
            ],
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code in (200, 201, 202):
                print(
                    f"[{index}/{total_batches}] Successfully invited batch of {len(batch)} users."
                )
            else:
                print(
                    f"[{index}/{total_batches}] Failed to invite batch. Status Code: {response.status_code}, Response: {response.text}"
                )
        except requests.exceptions.RequestException as e:
            print(f"[{index}/{total_batches}] Error processing batch: {e}")


if __name__ == "__main__":
    invite_users()