import requests
from requests.auth import HTTPBasicAuth
from environment_config import get_environment

# Hardcoded authentication details
environment = get_environment("open_groupe_sandbox")
BASE_URL = environment["confluence_base_url"].rstrip("/")
CONFLUENCE_API_V1 = "/wiki/rest/api"
CONFLUENCE_API_V2 = "/wiki/api/v2"
USERNAME = environment["username"]
PASSWORD = environment["user_token"]
AUTH = HTTPBasicAuth(USERNAME, PASSWORD)

# Hardcoded list of space keys to inspect
SPACE_KEYS = [
    '~682510787','~298606825','~456640136','~41854076','~457278918','~805895941','~39203745','~441407911','~666077527','~505995955','~812546621','~311792811','~720693404','~893913398','~235881159','~579309584','~914288092','~417273260','~742084354','~519356733','~987218788','~101693645','~947765554','~870482231','~369209824','~853916335','~733616737','~65133330','~692036963','~818201833','~889300156','~651038517','~974386381','~49107048','~363227166','~839067560','~23267911','~70624623','~440350562','~646725005','~517485688','~94361553','~774457187','~5319289','~747301486','~872587873','~614401385','~716818677','~658005373','~189757842','~628727771','~486917811','~880455518','~625947966','~355620357','~904154530','~264381301','~608512033','~459213487','~336701058','~755315050','~251297428','~222012824','~181351761','~469110851','~841984141','~907616442','~485370101','~672417912','~746062279','~286238607','~776487129','~872033836','~870328642','~381861335','~927612129','~940745218','~225972951','~854497338','~813244562'
]

# Hardcoded target group ID and permission operation
TARGET_GROUP_ID = "ca705400-fa44-4599-8e4e-4e8fa0c790ab"
TARGET_OPERATION_KEY = "read"


def get_paginated_results(path):
    """Fetch all results from a paginated API endpoint."""
    results = []
    next_url = BASE_URL + path

    while next_url:
        response = requests.get(next_url, auth=AUTH, timeout=30)
        response.raise_for_status()

        payload = response.json()
        results.extend(payload.get("results", []))

        next_path = payload.get("_links", {}).get("next")
        next_url = BASE_URL + next_path if next_path else None

    return results


def get_matching_spaces():
    """Retrieve detailed space data for the hardcoded space keys."""
    spaces = get_paginated_results(CONFLUENCE_API_V2 + "/spaces")
    return [space for space in spaces if space.get("key") in SPACE_KEYS]


def get_target_permissions(space_id):
    """Get matching read permissions for the target group."""
    permissions = get_paginated_results(f"{CONFLUENCE_API_V2}/spaces/{space_id}/permissions")
    matching = []

    for permission in permissions:
        principal = permission.get("principal") or {}
        operation = permission.get("operation") or {}

        if (
            principal.get("type") == "group"
            and principal.get("id") == TARGET_GROUP_ID
            and operation.get("key") == TARGET_OPERATION_KEY
        ):
            matching.append(permission)

    return matching


def delete_permission(space_key, permission_id):
    """Delete a space permission via the REST API."""
    delete_url = BASE_URL + f"{CONFLUENCE_API_V1}/space/{space_key}/permission/{permission_id}"
    response = requests.delete(delete_url, auth=AUTH, timeout=30)
    response.raise_for_status()
    return response.status_code


print("Fetching matching Confluence spaces...")
spaces = get_matching_spaces()

print(f"Found {len(spaces)} matching space(s).")

for space in spaces:
    space_key = space.get("key")
    space_id = space.get("id")

    if not space_key or not space_id:
        continue

    print(f"Processing space: {space_key} ({space_id})")
    permissions = get_target_permissions(space_id)

    print(f"Found {len(permissions)} matching permission(s) to remove.")

    for permission in permissions:
        permission_id = permission.get("id")
        if not permission_id:
            continue

        try:
            delete_permission(space_key, permission_id)
            print(f"Deleted permission {permission_id} from space {space_key}")
        except requests.HTTPError as exc:
            print(f"Failed to delete permission {permission_id} from space {space_key}: {exc}")

print("Done.")
