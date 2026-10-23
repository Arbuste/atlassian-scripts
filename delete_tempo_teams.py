"""Delete Tempo teams by iterating paginated team IDs.

This script:
- sets the tempoToken variable
- calls the Tempo teams list API until metadata.next is empty
- collects all team IDs
- deletes each team by ID using the Tempo delete team API
"""

import json
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from environment_config import get_environment
# Tempo bearer token is loaded from the selected environment.

environment = get_environment("open_groupe_sandbox")
tempoToken = environment["tempo_token"]


def get_request(url):
    req = Request(url)
    req.add_header("Authorization", f"Bearer {tempoToken}")
    req.add_header("Accept", "application/json")
    try:
        with urlopen(req) as response:
            content = response.read().decode("utf-8")
            return json.loads(content)
    except HTTPError as exc:
        print(f"HTTPError {exc.code} for GET {url}: {exc.reason}")
        try:
            body = exc.read().decode("utf-8")
            print("Response body:", body)
        except Exception:
            pass
        return None
    except URLError as exc:
        print(f"URLError for GET {url}: {exc.reason}")
        return None


def delete_request(url):
    req = Request(url, method="DELETE")
    req.add_header("Authorization", f"Bearer {tempoToken}")
    req.add_header("Accept", "application/json")
    try:
        with urlopen(req) as response:
            status = response.status
            body = response.read().decode("utf-8")
            return status, body
    except HTTPError as exc:
        body = None
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            pass
        return exc.code, body
    except URLError as exc:
        print(f"URLError for DELETE {url}: {exc.reason}")
        return None, None


def list_tempo_team_ids():
    base_url = "https://api.tempo.io/4/teams"
    team_ids = []
    next_url = base_url

    while next_url:
        print(f"Requesting teams page: {next_url}")
        data = get_request(next_url)
        if data is None:
            print("Failed to retrieve teams page. Stopping pagination.")
            break

        results = data.get("results", [])
        page_ids = [team.get("id") for team in results if team.get("id") is not None]
        print(f"Found {len(page_ids)} IDs on this page.")
        team_ids.extend(page_ids)

        metadata = data.get("metadata", {})
        next_url = metadata.get("next")
        if not next_url:
            print("No next page, finished listing teams.")

    return team_ids


def delete_tempo_teams(team_ids):
    if not team_ids:
        print("No team IDs to delete.")
        return

    for team_id in team_ids:
        if not team_id:
            continue
        delete_url = f"https://api.tempo.io/4/teams/{team_id}"
        print(f"Deleting team ID: {team_id}")
        status, body = delete_request(delete_url)
        if status is None:
            print(f"  Failed to delete team {team_id}: no response.")
            continue

        if 200 <= status < 300:
            print(f"  Deleted team {team_id} successfully (HTTP {status}).")
        else:
            print(f"  Failed to delete team {team_id} (HTTP {status}).")
            if body:
                print(f"  Response body: {body}")


if __name__ == "__main__":
    import os

    print("Starting Tempo team deletion run...")
    ids = list_tempo_team_ids()
    print(f"Total team IDs collected: {len(ids)}")
    print(ids)
    delete_tempo_teams(ids)
    print("Done.")
