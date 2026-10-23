import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
cloud_environment = get_environment("peaksys_sandbox_migration_01")
dc_environment = get_environment("cdiscount", "data_center")

import json
import requests
import csv
import re
from requests.auth import HTTPBasicAuthDCBaseUrl = dc_environment["jira_base_url"]
cloudBaseUrl = cloud_environment["jira_base_url"]
bearer_token = dc_environment["jira_pat"]

headers = {"Authorization": f"Bearer {bearer_token}"}
basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

dcFields = requests.get(DCBaseUrl + '/field', headers=headers).json()
cloudFields = requests.get(cloudBaseUrl + '/field',auth=basic).json()

def mapUser(userKey):
    svcJira = '712020:367293a3-5f77-422a-9b4f-a582251933c0'
    dcUserReq = requests.get(DCBaseUrl + '/user?key=' + userKey,headers=headers)
    if dcUserReq is None:
        return svcJira
    else:
        dcUser = dcUserReq.json()
        cloudUser = requests.get(cloudBaseUrl + '/user/search?query=' + dcUser['emailAddress'],auth=basic)
        if cloudUser is None:
            return svcJira
        else:
            return cloudUser.json()[0]['accountId']
        
def mapFieldFromId(id):
    dcFieldsReq = list(filter(lambda field: field['id'] == id, dcFields))
    if dcFieldsReq:
        dcField = dcFieldsReq[0]
        if dcField['id'] == 'components':
            return 'components'
        elif dcField['id'] == 'fixVersions':
            return 'fixVersions'
        elif dcField['id'] == 'duedate':
            return 'duedate'
        elif dcField['id'] == 'customfield_11200':
            dcField['name'] = 'Story points'
        elif dcField['id'] == 'customfield_14300':
            dcField['name'] = 'Flagged'
        cloudFieldsReq = list(filter(lambda field: field['name'] == dcField['name'] and field['schema']['type'] == dcField['schema']['type'], cloudFields)) 
        if cloudFieldsReq:
            return cloudFieldsReq[0]['id']

def mapFieldFromName(name):
    dcFieldsReq = list(filter(lambda field: field['name'] == name, dcFields))
    if dcFieldsReq:
        dcField = dcFieldsReq[0]
        cloudFieldsReq = list(filter(lambda field: field['name'] == dcField['name'] and field['schema']['type'] == dcField['schema']['type'], cloudFields))
        if cloudFieldsReq:
            return cloudFieldsReq[0]['id']

def convert(components):
    for component in components:
        writer.writerow([component['type']])
        
        if "children" in component:
            if component["children"]:
                convert(component["children"])

currentRule = ''
currentComponent = ''

with open(r'C:\Users\simon.lucchesini\Documents\Analyse Automation\automation-rules-202501281617.json',encoding='utf-8') as f:
    rules = json.load(f)['rules']
    with open(r'C:\Users\simon.lucchesini\Downloads\output.csv', 'w', newline='', encoding='utf-8') as f2:
        writer = csv.writer(f2, delimiter=',',quotechar='"')
        
                    
        for rule in rules:
            writer.writerow([rule['trigger']['type']])
            
            convert(rule['components'])
            
            



