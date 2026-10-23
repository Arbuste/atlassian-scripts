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
logPath = r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Luxembourg\Scripts\output tickets 15091820.csv'

#URL de l'instance Cloud
# prod 0fda4548-5ae8-4a5a-96ac-49a448d784b9
# sandbox 162613d3-a4ec-4784-ac5f-46b5354f4d73cloudBaseUrl = cloud_environment["jira_base_url"]

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
   
    issues = []
    nextPageToken = ''
    nbIssues = 0
    pace = 100
    isLast = False
    while not isLast:
        issuesReq = getCloud('/rest/api/3/search/jql?jql=type%20in%20(Project)&fields=*all&maxResults='+str(pace) + '&nextPageToken=' + nextPageToken)
        if issuesReq:
            if check(issuesReq,'issues'):
                issues = issues + issuesReq['issues']
                nbIssues += len(issuesReq['issues'])
                print("Number of issues: " + str(nbIssues))
            if check(issuesReq,'isLast'):
                isLast = issuesReq['isLast']
            if check(issuesReq,'nextPageToken'):
                nextPageToken = issuesReq['nextPageToken']
            else:
                break
        else:
            break
    
    writer.writerow(['Issue Key','Issue Type','Parent'])
    for issue in issues:
        if check(issue['fields'],'parent'):
            writer.writerow([issue['key'],issue['fields']['issuetype']['name'],issue['fields']['parent']['key']])

