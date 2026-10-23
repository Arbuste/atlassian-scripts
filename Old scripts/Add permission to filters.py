import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
dc_environment = get_environment("cdiscount", "data_center")

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
logPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Filters\output add permissions.csv'
entryPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Filters\Extract Filters.csv'

#URL de l'instance DCDCBaseUrl = dc_environment["jira_base_url"]

#Bearer pour interroger l'instance DCbearer_token = dc_environment["jira_pat"]
with open(entryPath,'r',newline='',encoding='utf-8') as source:
    with open(logPath, 'w', newline='', encoding='utf-8') as log:
        reader = csv.DictReader(source,delimiter=',',quotechar='"')
        writer = csv.writer(log, delimiter=',',quotechar='"')
        writer.writerow(["Result","Filter ID","Filter Name","Detail"])

        def getDC(url,headers={}):
            headers['Authorization'] = f"Bearer {bearer_token}"
            req = requests.get(url, headers=headers)
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
        
        def postDC(url,headers={},json=None):
            headers['Content-Type'] = 'application/json'
            headers['Authorization'] = f"Bearer {bearer_token}"
            req = requests.post(url, headers=headers, json=json)
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
        
        def putDC(url,headers={},json=None):
            headers['Content-Type'] = 'application/json'
            headers['Authorization'] = f"Bearer {bearer_token}"
            req = requests.put(url, headers=headers, json=json)
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

        def check(dict, key):
            res = False
            if key in dict:
                if dict[key]:
                    res = True
            return res

        for jiraFilter in reader:
            filtersReq = postDC(DCBaseUrl + '/rest/api/2/filter/'+jiraFilter['id']+'/permission',json={'type':'group','groupname':'peaksys-system-administrators','view':True,'edit':True})
            if filtersReq['isReqSuccess']:
                writer.writerow(['Success',jiraFilter['id'],jiraFilter['name']])
            else:
                writer.writerow(['Error',jiraFilter['id'],jiraFilter['name'],str(filtersReq)])