import requests
from requests.auth import HTTPBasicAuth
from environment_config import get_environment

environment = get_environment("open_groupe_sandbox")
BASE_URL = environment["confluence_base_url"].rstrip("/")
CONFLUENCE_API_V1 = "/wiki/rest/api"
USERNAME = environment["username"]
PASSWORD = environment["user_token"]
AUTH = HTTPBasicAuth(USERNAME, PASSWORD)



def get_space_keys():
    """Retrieve all Confluence space keys using paginated GET /wiki/rest/api/space."""
    space_keys = []
    next_url = BASE_URL + CONFLUENCE_API_V1 + "/space"

    while next_url:
        response = requests.get(next_url, auth=AUTH, timeout=30)
        response.raise_for_status()

        payload = response.json()
        results = payload.get("results", [])

        for space in results:
            key = space.get("key")
            if key:
                space_keys.append(key)

        next_uri = payload.get("_links", {}).get("next")
        if next_uri:
            next_url = BASE_URL + next_uri
        else:
            next_url = None

    return space_keys


def delete_space(key):
    """Delete one Confluence space using DELETE /rest/api/space/{key}."""
    delete_url = BASE_URL + f"{CONFLUENCE_API_V1}/space/{key}"
    response = requests.delete(delete_url, auth=AUTH, timeout=30)
    response.raise_for_status()
    return response.status_code


if __name__ == "__main__":
    print("Fetching Confluence spaces...")
    keys = get_space_keys()

    print(f"Found {len(keys)} space(s) to delete.")

    for key in keys:
        try:
            delete_space(key)
            print(f"Deleted space: {key}")
        except requests.HTTPError as exc:
            print(f"Failed to delete space {key}: {exc}")

    print("Done.")