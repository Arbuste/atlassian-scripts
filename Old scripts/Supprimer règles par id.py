import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment

cloud_environment = get_environment("peaksys")
cloudBaseUrl = cloud_environment["jira_base_url"].rstrip("/")
cloudId = cloud_environment["cloud_id"]

import json
import requests
from requests.auth import HTTPBasicAuth

basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

json = {"offset":0,"limit":200,"filter":"","actionTypes":[],"triggerTypes":[],"orchestrationTypes":[],"systemLabelId":"ALL","sortKey":"NAME","sortOrder":"ASC"}
headers = {"Cookie": ""}
headers['Content-Type'] = 'application/json'


for rule in rules:
    print('Suppression de ' + rule['name'] + '...')
    res2 = requests.delete(cloudBaseUrl + "/gateway/api/automation/internal-api/jira/" + cloudId + "/pro/rest/GLOBAL/rule/" + rule, headers=headers)
    print(str(res2))
