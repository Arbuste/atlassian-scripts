import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment

cloud_environment = get_environment("open_groupe_sandbox", service_account=True)

import json
import requests
import math
import csv
from datetime import datetime
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier de logs
outputFolder = r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Luxembourg'

#URL de l'instance Cloud
# prod 0fda4548-5ae8-4a5a-96ac-49a448d784b9
# sandbox 162613d3-a4ec-4784-ac5f-46b5354f4d73cloudBaseUrl = cloud_environment["jira_base_url"]
basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

def check(dict, key):
    res = False
    if key in dict:
        if dict[key]:
            res = True
    return res

def getCloud(url,headers={}):
    req = requests.get(cloudBaseUrl + url, auth=basic, headers=headers)
    resp = {"reqStatusCode": req.status_code}
    if math.floor(req.status_code/100) == 2:
        resp['isReqSuccess'] = True
    else:
        resp['isReqSuccess'] = False
    try:
        respBody = req.json()
        if isinstance(respBody,dict):
            resp |= respBody
        elif isinstance(respBody,list):
            resp["values"] = respBody
    except:
        pass      
    return resp

def postCloud(url,body,headers={}):
    req = requests.post(cloudBaseUrl + url, data=body, auth=basic, headers=headers)
    resp = {"reqStatusCode": req.status_code}
    if math.floor(req.status_code/100) == 2:
        resp['isReqSuccess'] = True
    else:
        resp['isReqSuccess'] = False
    try:
        respBody = req.json()
        if isinstance(respBody,dict):
            resp |= respBody
        elif isinstance(respBody,list):
            resp["values"] = respBody
    except:
        pass      
    return resp

#Fields
fieldPath = outputFolder + r'\fields2.csv'
with open(fieldPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    writer.writerow(['Field Name','Field ID','Number of issues','Last created'])
    
    fieldsReq = getCloud('/rest/api/3/field')
    if fieldsReq['isReqSuccess']:
        fields = fieldsReq['values']
        customFields = [it for it in fields if it['custom'] == True and 'clauseNames' in it]
       
        for cf in customFields:
            countReq = postCloud('/rest/api/3/search/approximate-count',json.dumps({ 'jql': '"' + cf['clauseNames'][0] + '" is not null' }),headers={'Content-Type': 'application/json'})
            if countReq['isReqSuccess']:
                if countReq['count'] > 0:
                    issuesReq = getCloud('/rest/api/3/search/jql?jql="' + cf['clauseNames'][0] + '"%20is%20not%20null%20order%20by%20created%20desc&fields=*all')
                    if issuesReq:
                        writer.writerow([cf['name'],cf['id'],countReq['count'],str(datetime.strptime(issuesReq['issues'][0]['fields']['created'], '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%Y-%m-%d'))])
                    else:
                        writer.writerow([cf['name'],cf['id'],countReq['count'],str(issuesReq['errorMessages'])])
                else:
                    writer.writerow([cf['name'],cf['id'],0])
            else:
                writer.writerow([cf['name'],cf['id'],str(countReq['errorMessages'])])

