import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
cloud_environment = get_environment("peaksys")
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

dcFields = requests.get(DCBaseUrl + '/field').json()
cloudFields = requests.get(cloudBaseUrl + '/field').json()

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
    dcFields = list(filter(field: field['id'] == id, dcFields))
    if dcFields:
        dcField = dcFields[0]
        cloudFields = list(filter(field: field['name'] == dcField['name'] and field['schema']['type'] == dcField['schema']['type']))
        if cloudFields:
            return cloudFields[0]['id']

def mapTriggerFieldChanged(trigger):
    

def manageTrigger(trigger):

def check(components):
    for component in components:
        if "type" in component and "component" in component:
            currentComponent = component["component"] + ' ' + component["type"]
        else:
            currentComponent = 'condition in value'
        if "value" in component:
            if component["value"]:
                if re.search('{{[^}]+}}',str(component['value'])):
                    smartValues = re.findall('{{[^}]+}}',str(component['value']))
                    for sm in smartValues:
                        writer.writerow([currentRule, currentComponent, str(component["value"]), sm])
        
        if "conditions" in component:
            if component["conditions"]:
                if re.search('{{[^}]+}}',str(component['conditions'])):
                    smartValues = re.findall('{{[^}]+}}',str(component['conditions']))
                    for sm in smartValues:
                        writer.writerow([currentRule, currentComponent, str(component["conditions"]), sm])
        
        if "children" in component:
            if component["children"]:
                check(component["children"])

currentRule = ''
currentComponent = ''

with open(r'C:\Users\simon.lucchesini\Downloads\automation-rules-202501281617.json',encoding='utf-8') as f:
    d = json.load(f)
    
    rule['authorAccountId'] = mapUser(rule['authorAccountId'])
            
    with open(r'C:\Users\simon.lucchesini\Downloads\output.json', 'w', encoding='utf8') as f:
        json.dump(d, f, ensure_ascii=False)
