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
import math
import time
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier de logs
logPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Permission Schemes\output give back.csv'
entryPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Permission Schemes\entryGiveBack.csv'

#URL des instancescloudBaseUrl = cloud_environment["jira_base_url"]
DCBaseUrl = dc_environment["jira_base_url"]

#Bearer pour interroger l'instance DCbearer_token = dc_environment["jira_pat"]
basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

with open(entryPath,'r',newline='',encoding='utf-8') as source:
    with open(logPath, 'w', newline='', encoding='utf-8') as log:
        reader = csv.DictReader(source,delimiter=',',quotechar='"')
        writer = csv.writer(log, delimiter=',',quotechar='"')
        writer.writerow(["Object","Category","Event","Detail","Additional detail"])
        
        def check(dict, key):
            res = False
            if key in dict:
                if dict[key]:
                    res = True
            return res

        def getDC(url,headers={}):
            headers['Authorization'] = f"Bearer {bearer_token}"
            return requests.get(DCBaseUrl + url, headers=headers)
        
        def getCloud(url):
            return requests.get(cloudBaseUrl + url,auth=basic)
        
        def postCloud(url,body,headers={}):
            headers['Content-type'] = 'application/json'
            return requests.post(cloudBaseUrl + url, auth=basic,headers=headers,json=body)
        
        dcRoles = getDC('/rest/api/2/role').json()
        cloudRoles = getCloud('/rest/api/2/role').json()
        
        def mapRole(roleId):
            dcRolesReq = [role for role in dcRoles if role['id'] == int(roleId)]
            if dcRolesReq:
                dcRole = dcRolesReq[0]
                cloudRolesReq = [role for role in cloudRoles if role['name'] == dcRole['name']]
                if cloudRolesReq:
                    if len(cloudRolesReq) > 1:
                        writer.writerow(['Role','Problem','Map Role','More than one match in Cloud',str(roleId)])
                    return cloudRolesReq[0]['id']
                else:
                    writer.writerow(['Role','Error','Map Role','Error','No match in Cloud',str(roleId)])
                    return roleId
            else:
                writer.writerow(['Role','Error','Map Role','Role not found in DC',str(roleId)])
                return roleId
        
        projectPermissions = {}
        for row in reader:
            schemeId = ''
            if not row['Project Key'] in projectPermissions:
                schemeRequest = getCloud('/rest/api/2/project/' + row['Project Key'] + '/permissionscheme')
                if math.floor(schemeRequest.status_code/100) == 2:
                    scheme = schemeRequest.json()
                    schemeId = str(scheme['id'])
                    projectPermissions[row['Project Key']] = str(schemeId)
                else:
                    details = ''
                    if schemeRequest.json():
                        details = json.dumps(schemeRequest.json())
                    writer.writerow(["Project","Error","Project could not be found","Project Key: " + row['Project Key'] + ", Error: " + str(schemeRequest.status_code) + ", Details: " + details])
                    continue
            else:
                schemeId = projectPermissions[row['Project Key']]
                
            perm = json.loads(row['Removed permissions'])
            if check(perm,'holder'):
                if check(perm['holder'],'type'):
                    if perm['holder']['type'] == 'projectRole' and check(perm['holder'],'parameter'):
                        perm['holder']['parameter'] = mapRole(perm['holder']['parameter'])            
            changeRequest = postCloud('/rest/api/2/permissionscheme/' + schemeId + '/permission', perm)
            
            if math.floor(changeRequest.status_code/100) == 2:
                writer.writerow(["Permission Scheme","Info","Permission added", "Scheme ID: " + schemeId + ", Permission: " + json.dumps(perm)])
            else:
                details = ''
                if schemeRequest.json():
                    details = json.dumps(changeRequest.json())
                writer.writerow(["Permission Scheme","Error","Impossible to add permission", "Scheme ID: " + schemeId + ", Permission: " + json.dumps(perm) + ", Error: " + str(changeRequest.status_code) + ", Details: " + details])
