import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
dc_environment = get_environment("cdiscount_internal", "data_center")

import json
import requests
import csv
import time
import re
import copy
import math
import sys
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier de logs
logPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Permission Schemes\output give back read only.csv'
entryPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Permission Schemes\entryReadOnly.csv'

#URL de l'instance DCDCBaseUrl = dc_environment["jira_base_url"]

#Bearer pour interroger l'instance DCbearer_token = dc_environment["jira_pat"]
with open(entryPath,'r',newline='',encoding='utf-8') as source:
    with open(logPath, 'w', newline='', encoding='utf-8') as log:
        reader = csv.DictReader(source,delimiter=',',quotechar='"')
        writer = csv.writer(log, delimiter=',',quotechar='"')
        writer.writerow(["Object","Category","Event","Detail","Additional detail"])

        def getDC(url,headers={}):
            headers['Authorization'] = f"Bearer {bearer_token}"
            req = requests.get(url, headers=headers)
            resp = {"reqStatusCode": req.status_code}
            if math.floor(req.status_code/100) == 2:
                resp['isReqSuccess'] = True
            else:
                resp['isReqSuccess'] = False
            if 'Content-Type' in req.headers:
                if 'application/json' in req.headers.get('Content-Type'):
                    if isinstance(req.json(),dict):
                        resp |= req.json()
                    elif isinstance(req.json(),list):
                        resp["values"] = req.json()   
            return resp
        
        def postDC(url,headers={},json=None):
            headers['Content-Type'] = 'application/json'
            headers['Authorization'] = f"Bearer {bearer_token}"
            req = requests.post(url, headers=headers, json=json)
            resp = {"reqStatusCode": req.status_code}
            if math.floor(req.status_code/100) == 2:
                resp['isReqSuccess'] = True
            else:
                resp['isReqSuccess'] = False
            if 'Content-Type' in req.headers:
                if 'application/json' in req.headers.get('Content-Type'):
                    if isinstance(req.json(),dict):
                        resp |= req.json()
                    elif isinstance(req.json(),list):
                        resp["values"] = req.json()   
            return resp
        
        def putDC(url,headers={},json=None):
            headers['Content-Type'] = 'application/json'
            headers['Authorization'] = f"Bearer {bearer_token}"
            req = requests.put(url, headers=headers, json=json)
            resp = {"reqStatusCode": req.status_code}
            if math.floor(req.status_code/100) == 2:
                resp['isReqSuccess'] = True
            else:
                resp['isReqSuccess'] = False
            if 'Content-Type' in req.headers:
                if 'application/json' in req.headers.get('Content-Type'):
                    if isinstance(req.json(),dict):
                        resp |= req.json()
                    elif isinstance(req.json(),list):
                        resp["values"] = req.json()   
            return resp

        def check(dict, key):
            res = False
            if key in dict:
                if dict[key]:
                    res = True
            return res
        
        for project in reader:
            assign = putDC(DCBaseUrl + '/rest/api/2/project/' + project['Project Key'] +'/permissionscheme',json={'id': project['Old Permission Scheme ID']})
            if assign['isReqSuccess']:
                writer.writerow(['Project','Info','Re-assignation of old permission scheme succeeded',project['Project Key'],project['Old Permission Scheme ID']])
            else:
                writer.writerow(['Project','Error','Re-assignation of old permission scheme failed',project['Project Key'],str(assign)])
