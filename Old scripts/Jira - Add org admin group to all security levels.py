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
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier de logs
logPath = r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Luxembourg\Scripts\output security levels.csv'

#URL de l'instance CloudcloudBaseUrl = cloud_environment["jira_base_url"]

basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

with open(logPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    
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
    
    def putCloud(url,headers={},json=None):
        headers['Content-Type'] = 'application/json'
        req = requests.put(cloudBaseUrl + url, auth=basic, headers=headers, json=json)
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
    
    secLevels = []
    isLast = False
    startAt = 0
    pace = 50
    while isLast == False:
        secLevelsReq = getCloud('/rest/api/2/issuesecurityschemes/level?startAt='+str(startAt)+'&maxResults='+str(pace))
        if secLevelsReq:
            if check(secLevelsReq,'values'):
                secLevels = secLevels + secLevelsReq['values']
                startAt = startAt + pace
            if 'isLast' in secLevelsReq:
                isLast = secLevelsReq['isLast']
            else:
                isLast = True
        else:
            break
    
    writer.writerow(['Liste des security levels',json.dumps(secLevels)])
    writer.writerow([])
    
    for secLevel in secLevels:
        if check(secLevel,'issueSecuritySchemeId'):
            bodyData = {
                'members': [
                    {
                        'parameter': 'org-admins',
                        'type': 'group'
                    }
                ]
            }
            putReq = putCloud('/rest/api/2/issuesecurityschemes/' + secLevel['issueSecuritySchemeId'] + '/level/' + secLevel['id'] + '/member',json=bodyData)
            if putReq['isReqSuccess']:
                writer.writerow(['Ajout de groupe dans le level','Succès','Level ID = ' + secLevel['id']])
            else:
                writer.writerow(['Ajout de groupe dans le level','Erreur',json.dumps(putReq)])
        else:
            writer.writerow(['Problème','Level sans security scheme'])
