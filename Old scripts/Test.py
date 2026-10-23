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
import copy
from requests.auth import HTTPBasicAuth
     
query = 'project = 30900 and (reporter in ( simon.lucchesini  ,"daniel.lecoq") or creator was not in svc.jira )'DCBaseUrl = dc_environment["jira_base_url"]
cloudBaseUrl = cloud_environment["jira_base_url"]
bearer_token = dc_environment["jira_pat"]

headers = {"Authorization": f"Bearer {bearer_token}"}
basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

def getDC(url):
    return requests.get(DCBaseUrl + url, headers=headers).json()

def getCloud(url):
    return requests.get(cloudBaseUrl + url,auth=basic).json()

dcProjects = getDC('/rest/api/2/project?includeArchived=true')
cloudProjects = getCloud('/rest/api/2/project')

def mapProject(id):
    dcProjectsReq = list(filter(lambda project: project['id'] == id, dcProjects))
    if dcProjectsReq:
        dcProject = dcProjectsReq[0]
        cloudProjectsReq = list(filter(lambda project: project['key'] == dcProject['key'], cloudProjects))
        if cloudProjectsReq:
            return cloudProjectsReq[0]['id']

def mapUser(userKey):
    svcJira = '712020:367293a3-5f77-422a-9b4f-a582251933c0' #default
    dcUserReq = list(filter(lambda user: user['key'].lower() == userKey.lower(), dcUsers))
    if not dcUserReq:
        return svcJira
    else:
        dcUser = dcUserReq[0]
        if not 'emailAddress' in dcUser:
            return svcJira
        else:
            cloudUser = list(filter(lambda user: 'emailAddress' in user and user['emailAddress'].lower() == dcUser['emailAddress'].lower(), cloudUsers))
            if not cloudUser:
                return svcJira
            else:
                return cloudUser[0]['accountId']

#Fields
dcFields = getDC('/rest/api/2/field')
cloudFields = getCloud('/rest/api/2/field')

#Users
dcUsers = []
cloudUsers = []
isLast = False
startAt = 0
pace = 1000
while isLast == False:
    dcUsersReq = getDC('/rest/api/2/user/search?username=.&includeInactiveUsers=true&startAt='+str(startAt)+'&maxResults='+str(pace))
    if dcUsersReq:
        dcUsers = dcUsers + dcUsersReq
        startAt = startAt + pace
    else:
        break
startAt = 0
pace = 1000
while isLast == False:
    cloudUsersReq = getCloud('/rest/api/2/users/search?startAt='+str(startAt)+'&maxResults='+str(pace))
    if cloudUsersReq:
        cloudUsers = cloudUsers + cloudUsersReq
        startAt = startAt + pace
    else:
        break

#User fields on DC
dcUserPickerFieldsReq = getDC('/rest/api/2/customFields?types=com.atlassian.jira.plugin.system.customfieldtypes:userpicker')['values']
dcMultipleUserPickerFieldsReq = getDC('/rest/api/2/customFields?types=com.atlassian.jira.plugin.system.customfieldtypes:multiuserpicker')['values']
dcUserFields = ['assignee','reporter','creator','Issue creator']

for userField in dcUserPickerFieldsReq + dcMultipleUserPickerFieldsReq:
    improvedFields = list(filter(lambda field: field['id'] == userField['id'], dcFields))
    if improvedFields:
        improvedField = improvedFields[0]
        if 'clauseNames' in improvedField:
            if improvedField['clauseNames']:
                dcUserFields = dcUserFields + improvedField['clauseNames']
            else:
                dcUserFields = dcUserFields + improvedField['name']
        else:
            dcUserFields = dcUserFields + improvedField['name']

userClause = '|'.join([re.escape(d) for d in ['creator','reporter','assignee','Issue creator']])
userRegex = f'''(?=("?'?(?:{userClause})"?'?\s+(?:!?=|is(?: not)|was(?: not)?(?: in)?|(?:not )?in|changed)\s+(\([^\)]+\)|"?'?[^\s]+"?'?)))'''
userClauses = []
print(str(re.findall(userRegex,query,flags=re.I)))
for d in re.findall(userRegex,query,flags=re.I):
    l = (d[0],d[1].split(','))
    newClause = d[0]
    i=0
    while i < len(l[1]):
        newClause = newClause.replace(''.join(filter(lambda str: re.sub('''["'\s\(\)]''','',str), l[1][i])),str(mapUser(''.join(filter(lambda str: re.sub('''["'\s\(\)]''','',str), l[1][i])))))
        i = i+1
    userClauses.append((d[0],newClause))
print(str(userClauses))

for clause in userClauses:
    query = query.replace(clause[0],clause[1])

newQuery = query

projectRegex = '''(?=("?'?project"?'?\s+(?:!?=|is(?: not)|(?:not )?in)\s+\(?((?:\s*"?'?\d{5}"?'?\s*,?)+)\)?))'''
projectClauses = []
for d in re.findall(projectRegex,newQuery,flags=re.I):
    l = (d[0],d[1].split(','))
    newClause = d[0]
    i=0
    while i < len(l[1]):
        newClause = newClause.replace(''.join(filter(lambda str: str.isdigit(), l[1][i])),str(mapProject(''.join(filter(lambda str: str.isdigit(), l[1][i])))))
        i = i+1
    projectClauses.append((d[0],newClause))

print(str(projectClauses))

for clause in projectClauses:
    newQuery = newQuery.replace(clause[0],clause[1])

print(str(newQuery))
        
#[mapProject(''.join(filter(lambda str: str.isdigit(), p))) for l in [(d[0],d[1].split(',')) for d in re.findall(projectRegex,query,flags=re.I)] for p in l[1]]

#projects = [''.join(filter(lambda str: str.isdigit(), p)) for l in [(d[0],e) for e in d[1].split(',') for d in re.findall(projectRegex,query,flags=re.I)] for p in l]