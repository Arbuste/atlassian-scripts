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
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier de logs
logPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Permission Schemes\output migrate.csv'

#URL de l'instance DCDCBaseUrl = dc_environment["jira_base_url"]
#URL de l'instance DCcloudBaseUrl = cloud_environment["jira_base_url"]

#Bearer pour interroger l'instance DCbearer_token = dc_environment["jira_pat"]

basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

with open(logPath, 'w', newline='', encoding='utf-8') as log:
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
    
    def putDC(url,body,headers={}):
        headers['Authorization'] = f"Bearer {bearer_token}"
        headers['Content-type'] = 'application/json'
        return requests.put(DCBaseUrl + url, headers=headers,json=body)
    
    def getCloud(url):
        return requests.get(cloudBaseUrl + url,auth=basic)
    
    def postCloud(url,body,headers={}):
        headers['Content-type'] = 'application/json'
        return requests.post(cloudBaseUrl + url, auth=basic,headers=headers,json=body)
    
    #Users
    dcUsers = []
    cloudUsers = []
    isLast = False
    startAt = 0
    pace = 1000
    while isLast == False:
        dcUsersReq = getDC('/rest/api/2/user/search?username=.&includeInactiveUsers=true&startAt='+str(startAt)+'&maxResults='+str(pace)).json()
        if dcUsersReq:
            dcUsers = dcUsers + dcUsersReq
            startAt = startAt + pace
        else:
            break
    startAt = 0
    pace = 1000
    while isLast == False:
        cloudUsersReq = getCloud('/rest/api/2/users/search?startAt='+str(startAt)+'&maxResults='+str(pace)).json()
        if cloudUsersReq:
            cloudUsers = cloudUsers + cloudUsersReq
            startAt = startAt + pace
        else:
            break
        
    #Roles
    dcRoles = getDC('/rest/api/2/role').json()
    cloudRoles = getCloud('/rest/api/2/role').json()
    
    def mapUser(userKey,type='key'):
        dcUserReq = list(filter(lambda user: user[type].lower() == userKey.lower(), dcUsers))
        if not dcUserReq:
            writer.writerow(['User','Error','User not found in DC',userKey])
            return userKey
        else:
            dcUser = dcUserReq[0]
            if not check(dcUser,'emailAddress'):
                writer.writerow(['User','Error','DC user without email address',userKey])
                return userKey
            else:
                cloudUser = list(filter(lambda user: 'emailAddress' in user and user['emailAddress'].lower() == dcUser['emailAddress'].lower(), cloudUsers))
                if not cloudUser:
                    writer.writerow(['User','Error','No match in Cloud',userKey])
                    return userKey
                else:
                    if len(cloudUser) > 1:
                        writer.writerow(['User','Problem','More than one match in Cloud',str(userKey)])
                    return cloudUser[0]['accountId']
    
    def mapRole(roleId):
        dcRolesReq = list(filter(lambda role: role['id'] == roleId, dcRoles))
        if not dcRolesReq:
            writer.writerow(['Role','Error','Role not found in DC',str(roleId)])
            return roleId
        else:
            dcRole = dcRolesReq[0]
            cloudRole = list(filter(lambda role: role['name'].lower() == dcRole['name'].lower(), cloudRoles))
            if not cloudRole:
                writer.writerow(['Role','Error','No match in Cloud',str(roleId)])
                return roleId
            else:
                return cloudRole[0]['id']
    
    def convert(holder):
        if holder['type'] == 'projectRole':
            holder['parameter'] = mapRole(int(holder['parameter']))
        elif holder['type'] == 'user':
            holder['parameter'] = mapUser(holder['parameter'],'name')
        
    projects = getDC('/rest/api/2/project').json()
    doneSchemes = []
    for project in projects:
        schemeRequest = getDC('/rest/api/2/project/' + str(project['id']) + '/permissionscheme')
        if schemeRequest.status_code == 200:
            scheme = schemeRequest.json()
            schemeId = scheme['id']
            if not schemeId in doneSchemes:
                cloudSchemeRequest = getCloud('/rest/api/3/project/' + project['key'] + '/permissionscheme')
                if cloudSchemeRequest.status_code == 200:
                    cloudScheme = cloudSchemeRequest.json()
                    writer.writerow(['Permission Scheme','Info','Managing Permission Scheme','Scheme Id : ' + str(schemeId),'Project Key : ' + project['key']])
                    permissions = getDC('/rest/api/2/permissionscheme/' + str(schemeId) + '/permission').json()['permissions']
                    writer.writerow(['Permission Scheme','Info','Old Permissions','Scheme Id : ' + str(schemeId),json.dumps(permissions)])
                    oldPermissions = [perm for perm in permissions if perm['permission'] in ['ARCHIVE_ISSUES','RESTORE_ISSUES']]
                    newPermissions = []
                    for perm in oldPermissions:
                        if perm['permission'] == 'RESTORE_ISSUES':
                            newPermission = 'UNARCHIVE_ISSUES'
                        else:
                            newPermission = perm['permission']
                        if check(perm['holder'],'parameter'):
                            convert(perm['holder'])
                            newPermissions.append({'holder': { "type": perm['holder']['type'], "parameter": perm['holder']['parameter'] }, 'permission': newPermission})
                        else:
                            newPermissions.append({'holder': { "type": perm['holder']['type'] }, 'permission': newPermission})
                    writer.writerow(['Permission Scheme','Info','New Permissions','Scheme Id : ' + str(cloudScheme['id']),json.dumps(newPermissions)])
                    
                    for perm in newPermissions:
                        changeRequest = postCloud('/rest/api/3/permissionscheme/' + str(cloudScheme['id']) + '/permission',perm)                
                        if changeRequest.status_code == 201:
                            writer.writerow(['Permission Scheme','Info','Permission Successfully Added','Scheme Id : ' + str(cloudScheme['id']) + ', Permission: ' + json.dumps(perm)])
                        else:
                            writer.writerow(['Permission Scheme','Error Code ' + str(changeRequest.status_code),'Permission Addition Failed','Scheme Id : ' + str(cloudScheme['id']),json.dumps(changeRequest.json())])
                    doneSchemes.append(schemeId)
                else:
                    writer.writerow(['Project','Error','Project not found in Cloud','Project Key : ' + project['key']])
