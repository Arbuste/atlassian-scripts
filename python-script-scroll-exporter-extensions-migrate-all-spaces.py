#
# === Python 3 Confluence Migration Script (Standard Library Only) ===
#
# Prerequisites:
# 1. Python 3
# 2. NO external libraries are required.
#

import base64
import json
import sys
import time
import urllib.parse
import urllib.request

# --- 1. CONFIGURE YOUR SETTINGS HERE ---

from environment_config import get_environment

environment = get_environment("open_groupe_preprod", environment_type="data_center")
CONFLUENCE_BASE_URL = environment["confluence_base_url"].rstrip("/")
PERSONAL_ACCESS_TOKEN = environment["confluence_pat"]

# The CQL query to find the content to migrate
CQL_QUERY = 'macro IN ("scroll-pdf-only-inline","scroll-chm-tablelayout","scroll-epub-index-term","scroll-office-only-inline","scroll-eclipsehelp-ignore-inline","scroll-html-title","scroll-chm-ignore","scroll-html-ignore","scroll-pdf-ignore","scroll-epub-only","scroll-epub-tablelayout","scroll-docbook-ignore-inline","scroll-docbook-tablelayout","scroll-epub-title","scroll-pdf-ignore-inline","scroll-eclipsehelp-only","scroll-office-ignore-inline","scroll-eclipsehelp-title","scroll-chm-index-term","scroll-office-only","scroll-eclipsehelp-ignore","scroll-html-only-inline","scroll-eclipsehelp-tablelayout","scroll-html-only","scroll-pagetitle","scroll-html-index-term","scroll-eclipsehelp-only-inline","scroll-docbook-only","scroll-eclipsehelp-index-term","scroll-office-title","scroll-epub-only-inline","scroll-pdf-only","scroll-office-index-term","scroll-chm-only","scroll-chm-only-inline","scroll-chm-title","scroll-html-tablelayout","scroll-docbook-index-term","scroll-office-tablelayout","scroll-docbook-title","scroll-html-ignore-inline","scroll-docbook-only-inline","scroll-pdf-index-term","scroll-epub-ignore-inline","scroll-exportbutton","scroll-pdf-tablelayout","scroll-pdf-title","scroll-office-ignore","scroll-docbook-ignore","scroll-epub-ignore","scroll-chm-ignore-inline")'

# How often to check the task status (in seconds)
POLL_INTERVAL_SEC = 5  # 5 seconds

# --- END OF CONFIGURATION ---


# --- Helper Functions ---

# Create the Basic Auth header value

def make_api_request(method, url, headers=None):
    """
    A helper function to make API requests using the standard library.
    """
    if headers is None:
        headers = {}

    headers['Authorization'] = f"Bearer {PERSONAL_ACCESS_TOKEN}"
    headers['Accept'] = 'application/json'

    req = urllib.request.Request(url, method=method, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            response_body = response.read().decode('utf-8')
            return json.loads(response_body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"Request Failed. Status: {e.code}. Body: {error_body}", file=sys.stderr)
        raise Exception(f"HTTPError: {e.code}")
    except urllib.error.URLError as e:
        print(f"Request Failed. Reason: {e.reason}", file=sys.stderr)
        raise Exception(f"URLError: {e.reason}")

# --- Main Script Logic ---

def fetch_distinct_space_keys():
    """
    Step 1: Fetches all content matching the CQL and returns a Set of distinct space keys.
    """
    print(f'1. Fetching content with CQL: "{CQL_QUERY}"')
    space_keys = set()
    start = 0
    limit = 50

    while True:
        try:
            params = {
                'cql': CQL_QUERY,
                'expand': 'space',
                'start': start,
                'limit': limit,
            }
            query_string = urllib.parse.urlencode(params)
            url = f"{CONFLUENCE_BASE_URL}/rest/api/content/search?{query_string}"

            data = make_api_request('GET', url)

            for page in data.get('results', []):
                if page.get('space') and page['space'].get('key'):
                    space_keys.add(page['space']['key'])

            if 'next' not in data.get('_links', {}):
                break
            else:
                start += limit

        except Exception as e:
            print(f"Error fetching search results: {e}", file=sys.stderr)
            raise Exception("Failed during search phase.")

    print(f"   Found {len(space_keys)} distinct space(s): [{', '.join(space_keys)}]")
    return space_keys


def start_migration_tasks(space_keys):
    """
    Step 2: Starts the macro migration task for each space key.
    """
    print("\n2. Starting migration tasks for each space...")
    task_ids = []

    for key in space_keys:
        try:
            url = f"{CONFLUENCE_BASE_URL}/plugins/servlet/scroll-exporter-extensions/api/macro-migration/{key}"

            data = make_api_request('POST', url)

            task_id = data.get('runningTaskId')
            if task_id:
                print(f"   Started task for space [{key}]. Task ID: {task_id}")
                task_ids.append(task_id)
            else:
                print(f"   Warning: No 'runningTaskId' returned for space [{key}]", file=sys.stderr)

        except Exception as e:
            print(f"   Error starting task for space [{key}]: {e}", file=sys.stderr)

    return task_ids


def monitor_tasks(task_ids, timeout_minutes=30):
    """
    Step 3: Polls the long-running task API until all tasks are complete.
    """
    if not task_ids:
        print("\nNo tasks to monitor.")
        return

    print(f"\n3. Monitoring {len(task_ids)} task(s)... (Checking every {POLL_INTERVAL_SEC}s)")

    start_time = time.time()
    completed_count = 0
    finished_tasks = set()

    while True:
        elapsed_min = (time.time() - start_time) / 60
        if elapsed_min > timeout_minutes:
            print(f"\n Timeout reached ({timeout_minutes} minutes). Exiting monitor loop.")
            break

        total_percentage = 0
        completed_count = 0

        for task_id in task_ids:
            try:
                url = f"{CONFLUENCE_BASE_URL}/rest/api/longtask/{task_id}"
                task = make_api_request('GET', url)
                total_percentage += task.get('percentageComplete', 0)

                if task.get('finished', False) or task.get('percentageComplete', 0) >= 100:
                    if task_id not in finished_tasks:
                        print(f"\n   [Task {task_id}] Marked complete.")
                        finished_tasks.add(task_id)
                    completed_count += 1

            except Exception as e:
                print(f"\n   [Task {task_id}] Error fetching status: {e}", file=sys.stderr)

        if len(task_ids) > 0:
            overall_progress = int(total_percentage / len(task_ids))
        else:
            overall_progress = 0

        sys.stdout.write(
            f"   Progress: [{completed_count} / {len(task_ids)}] complete. Overall: {overall_progress}%...   \r"
        )
        sys.stdout.flush()

        if completed_count == len(task_ids):
            print("\n\nAll tasks finished or reached 100%.")
            break

        time.sleep(POLL_INTERVAL_SEC)


def main():
    """
    Main function to run the script
    """
    if not all([CONFLUENCE_BASE_URL, PERSONAL_ACCESS_TOKEN, CQL_QUERY]):
        print("Error: Please fill in all configuration constants at the top of the script.", file=sys.stderr)
        sys.exit(1)

    print("--- Confluence Migration Script Starting ---")

    try:
        space_keys = fetch_distinct_space_keys()
        if not space_keys:
            print("\nNo spaces matched the CQL query. Exiting.")
            return

        task_ids = start_migration_tasks(space_keys)
        monitor_tasks(task_ids)

        print("\n--- Script finished successfully. ---")

    except Exception as e:
        print(f"\n--- Script failed: {e} ---", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

