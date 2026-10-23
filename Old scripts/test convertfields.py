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

with open(r'C:\Users\simon.lucchesini\Documents\Analyse Automation\output.csv', 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')DCBaseUrl = dc_environment["jira_base_url"]
cloudBaseUrl = cloud_environment["jira_base_url"]
bearer_token = dc_environment["jira_pat"]

    basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

    def getDC(url,headers={}):
        headers['Authorization'] = f"Bearer {bearer_token}"
        return requests.get(DCBaseUrl + url, headers=headers).json()

    def getCloud(url):
        return requests.get(cloudBaseUrl + url,auth=basic).json()

    def check(dict, key):
        res = False
        if key in dict:
            if dict[key]:
                res = True
        return res

    def generateId(id):
        return str(id) + '1'
    
    #Chargement des éléments
    #Fields
    dcFields = getDC('/rest/api/2/field')
    cloudFields = getCloud('/rest/api/2/field')

    #Projects
    dcProjects = getDC('/rest/api/2/project?includeArchived=true')
    cloudProjects = getCloud('/rest/api/2/project')

    #Statuses
    dcStatuses = getDC('/rest/api/2/status')
    cloudStatuses = getCloud('/rest/api/2/status')

    #Priorities
    dcPriorities = getDC('/rest/api/2/priority')
    cloudPriorities = getCloud('/rest/api/2/priority')

    #Resolution
    dcResolutions = getDC('/rest/api/2/resolution')
    cloudResolutions = getCloud('/rest/api/2/resolution')
    
    #Issue types
    dcIssuetypes = getDC('/rest/api/2/issuetype')
    cloudIssuetypes = getCloud('/rest/api/2/issuetype')

    #Issue links
    dcIssuelinks = getDC('/rest/api/2/issueLinkType')['issueLinkTypes']
    cloudIssuelinks = getCloud('/rest/api/2/issueLinkType')['issueLinkTypes']
    
    #Teams
    dcTeams = []
    cloudTeams = []
    startAt = 1
    pace = 100
    size = pace
    while size == pace:
        dcTeamsReq = getDC('/rest/teams-api/1.0/team?page=' + str(startAt) + '&size=' + str(pace))
        if dcTeamsReq:
            dcTeams = dcTeams + dcTeamsReq
            startAt = startAt + 1
            size = len(dcTeamsReq)
        else:
            break
    cursor = 'X'
    pace = 300
    while cursor:
        if cursor != 'X':
            cloudTeamsReq = getCloud('/gateway/api/public/teams/v1/org/a631b804-8d8b-1233-68c2-c604c1264165/teams?cursor=' + str(cursor) + '&size=' + str(pace))
        else:
            cloudTeamsReq = getCloud('/gateway/api/public/teams/v1/org/a631b804-8d8b-1233-68c2-c604c1264165/teams?size=' + str(pace))
        if cloudTeamsReq:
            cloudTeams = cloudTeams + cloudTeamsReq['entities']
            cursor = cloudTeamsReq['cursor']
        else:
            break
    
    #Organizations
    dcOrganizations = []
    cloudOrganizations = []
    isLast = False
    startAt = 0
    pace = 50
    while isLast == False:
        dcOrganizationsReq = getDC('/rest/servicedeskapi/organization?start=' + str(startAt) + '&limit='+str(pace),{"X-ExperimentalApi": "true"})
        if dcOrganizationsReq:
            dcOrganizations = dcOrganizations + dcOrganizationsReq['values']
            startAt = startAt + pace
            isLast = dcOrganizationsReq['isLastPage']
        else:
            break
    isLast = False
    startAt = 0
    pace = 50
    while isLast == False:
        cloudOrganizationsReq = getCloud('/rest/servicedeskapi/organization?start=' + str(startAt) + '&limit='+str(pace))
        if cloudOrganizationsReq:
            cloudOrganizations = cloudOrganizations + cloudOrganizationsReq['values']
            startAt = startAt + pace
            isLast = cloudOrganizationsReq['isLastPage']
        else:
            break

    #Assets 
#     dcAssets = []
#     page = 1
#     pace = 10000
#     size = pace
#     while size == pace:
#         dcAssetsReq = getDC('/rest/assets/1.0/aql/objects?includeAttributes=false&page=' + str(page) + '&resultPerPage=' + str(pace))
#         if dcAssetsReq:
#             dcAssets = dcAssets + dcAssetsReq['objectEntries']
#             page = page + 1
#             size = pageObjectSize
#         else:
#             break
#         
#     workspaceId = getCloud('/rest/servicedeskapi/assets/workspace')['values'][0]['workspaceId']
#     cloudAssets = []
#     page = 1
#     pace = 10000
#     size = pace
#     while size == pace:
#         cloudAssetsReq = requests.get(cloud_environment["org_base_url"] + "/jsm/assets/workspace/" + workspaceId + '/v1/aql/objects?includeAttributes=false&page=' + str(page) + '&resultPerPage=' + str(pace),auth=basic).json()
#         if cloudAssetsReq:
#             cloudAssets = cloudAssets + cloudAssetsReq['objectEntries']
#             page = page + 1
#             size = pageObjectSize
#         else:
#             break

    #Boards
#     dcBoards = []
#     cloudBoards = []
#     isLast = False
#     startAt = 0
#     pace = 50
#     while isLast == False:
#         dcBoardsReq = getDC('/rest/agile/1.0/board?startAt='+str(startAt)+'&maxResults='+str(pace))
#         if dcBoardsReq:
#             dcBoards = dcBoards + dcBoardsReq['values']
#             startAt = startAt + pace
#             isLast = dcBoardsReq['isLast']
#         else:
#             break
#     isLast = False
#     startAt = 0
#     pace = 50
#     while isLast == False:
#         cloudBoardsReq = getCloud('/rest/agile/1.0/board?includePrivate=true&startAt='+str(startAt)+'&maxResults='+str(pace))
#         if cloudBoardsReq:
#             cloudBoards = cloudBoards + cloudBoardsReq['values']
#             startAt = startAt + pace
#             isLast = cloudBoardsReq['isLast']
#         else:
#             break

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
    dcUserFields = ['assignee','reporter','creator','Issue creator','Request participants','customfield_10003']
    dcUserClauses = dcUserFields

    for userField in dcUserPickerFieldsReq + dcMultipleUserPickerFieldsReq:
        improvedFields = list(filter(lambda field: field['id'] == userField['id'], dcFields))
        if improvedFields:
            improvedField = improvedFields[0]
            if check(improvedField,'clauseNames'):
                dcUserClauses = dcUserClauses + improvedField['clauseNames']
            else:
                dcUserClauses.append(improvedField['name'])
            dcUserFields.append(improvedField['id'])
            dcUserFields.append(improvedField['name'])
        else:
            writer.writerow(['INITIALISATION','User Fields','Couldn\'t find the field ID in DC',userField['id']])

    currentRule = ''
    currentComponent = ''

    def mapFieldFromId(id):
        if id in ['initiator','parent']:
            return id
        dcFieldsReq = list(filter(lambda field: field['id'] == id, dcFields))
        if dcFieldsReq:
            dcField = dcFieldsReq[0]
            if dcField['id'] in ['components','fixVersions','duedate']:
                return dcField['id']
            elif dcField['id'] == 'customfield_10002':
                dcField['name'] = 'Request Type'
            elif dcField['id'] == 'customfield_11200':
                dcField['name'] = 'Story points'
            elif dcField['id'] == 'customfield_14300':
                dcField['name'] = 'Flagged'
            cloudFieldsReq = list(filter(lambda field: field['name'] == dcField['name'], cloudFields))
            if cloudFieldsReq:
                if len(cloudFieldsReq) > 1:
                     cloudFieldsReq = list(filter(lambda field: field['name'] == dcField['name'] and field['schema']['type'] == dcField['schema']['type'], cloudFields))
                return cloudFieldsReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Field From ID','No direct match in Cloud, checking the clauses...',str(id)])
                for clauseName in dcField['clauseNames']:
                    cloudFieldsReq = list(filter(lambda field: field['name'] == clauseName and field['schema']['type'] == dcField['schema']['type'], cloudFields)) 
                    if cloudFieldsReq:
                        return cloudFieldsReq[0]['id']
                writer.writerow([currentRule,currentComponent,'Map Field From ID','No match in Cloud, even after clauses',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Field From ID','Field not found in DC',str(id)])
            return id

    def mapFieldFromName(name):
        dcFieldsReq = list(filter(lambda field: field['name'] == name, dcFields))
        if dcFieldsReq:
            dcField = dcFieldsReq[0]
            cloudFieldsReq = list(filter(lambda field: field['name'] == dcField['name'] and field['schema']['type'] == dcField['schema']['type'], cloudFields))
            if cloudFieldsReq:
                return cloudFieldsReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Field From Name','No match in Cloud',str(name)])
                return name
        else:
            writer.writerow([currentRule,currentComponent,'Map Field From Name','Field not found in DC',str(name)])
            return name

    def mapProject(id):
        dcProjectsReq = list(filter(lambda project: project['id'] == id, dcProjects))
        if dcProjectsReq:
            dcProject = dcProjectsReq[0]
            cloudProjectsReq = list(filter(lambda project: project['key'] == dcProject['key'], cloudProjects))
            if cloudProjectsReq:
                return cloudProjectsReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Project','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Project','Project not found in DC',str(id)])
            return id

    def mapStatus(id):
        dcStatusesReq = list(filter(lambda status: status['id'] == id, dcStatuses))
        if dcStatusesReq:
            dcStatus = dcStatusesReq[0]
            cloudStatusesReq = list(filter(lambda status: status['name'].lower() == dcStatus['name'].lower(), cloudStatuses))
            if cloudStatusesReq:
                return cloudStatusesReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Status','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Status','Status not found in DC',str(id)])
            return id

    def mapPriority(id):
        dcPrioritiesReq = list(filter(lambda priority: priority['id'] == id, dcPriorities))
        if dcPrioritiesReq:
            dcPriority = dcPrioritiesReq[0]
            cloudPrioritiesReq = list(filter(lambda priority: priority['name'].lower() == dcPriority['name'].lower(), cloudPriorities))
            if cloudPrioritiesReq:
                return cloudPrioritiesReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Priority','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Priority','Priority not found in DC',str(id)])
            return id

    def mapResolution(id):
        dcResolutionsReq = list(filter(lambda resolution: resolution['id'] == id, dcResolutions))
        if dcResolutionsReq:
            dcResolution = dcResolutionsReq[0]
            cloudResolutionsReq = list(filter(lambda resolution: resolution['name'].lower() == dcResolution['name'].lower(), cloudResolutions))
            if cloudResolutionsReq:
                return cloudResolutionsReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Resolution','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Resolution','Resolution not found in DC',str(id)])
            return id

    def mapIssuetype(id):
        dcIssuetypesReq = list(filter(lambda issuetype: issuetype['id'] == id, dcIssuetypes))
        if dcIssuetypesReq:
            dcIssuetype = dcIssuetypesReq[0]
            cloudIssuetypesReq = list(filter(lambda issuetype: issuetype['name'].lower() == dcIssuetype['name'].lower(), cloudIssuetypes))
            if cloudIssuetypesReq:
                return cloudIssuetypesReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Issue Types','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Issue Types','Issue type not found in DC',str(id)])
            return id

    def mapIssuelink(id):
        dcIssuelinksReq = list(filter(lambda issuelink: issuelink['id'] == id, dcIssuelinks))
        if dcIssuelinksReq:
            dcIssuelink = dcIssuelinksReq[0]
            cloudIssuelinksReq = list(filter(lambda issuelink: issuelink['name'].lower() == dcIssuelink['name'].lower(), cloudIssuelinks))
            if cloudIssuelinksReq:
                return cloudIssuelinksReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Issue Links','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Issue Links','Issue link not found in DC',str(id)])
            return id

    def mapTeam(id):
        dcTeamsReq = list(filter(lambda team: team['id'] == int(id), dcTeams))
        if dcTeamsReq:
            dcTeam = dcTeamsReq[0]
            cloudTeamsReq = list(filter(lambda team: team['displayName'].lower() == dcTeam['title'].lower(), cloudTeams))
            if cloudTeamsReq:
                return cloudTeamsReq[0]['teamId']
            else:
                writer.writerow([currentRule,currentComponent,'Map Team','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Team','Team not found in DC',str(id)])
            return id

    def mapOrganization(id):
        dcOrganizationsReq = list(filter(lambda org: org['id'] == id, dcOrganizations))
        if dcOrganizationsReq:
            dcOrganization = dcOrganizationsReq[0]
            cloudOrganizationsReq = list(filter(lambda org: org['name'] == dcOrganization['name'], cloudOrganizations))
            if cloudOrganizationsReq:
                return cloudOrganizationsReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Organization','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Organization','Organization not found in DC',str(id)])
            return id
    
    def mapAsset(id):
        dcAssetsReq = list(filter(lambda obj: obj['id'] == id, dcAssets))
        if dcAssetsReq:
            dcAsset = dcAssetsReq[0]
            cloudAssetsReq = list(filter(lambda obj: obj['name'] == dcAsset['name'], cloudAssets))
            if cloudAssetsReq:
                return cloudAssetsReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Assets','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Asset','Asset not found in DC',str(id)])
            return id
    
    def mapBoard(id):
        dcBoardsReq = list(filter(lambda board: board['id'] == id, dcBoards))
        if dcBoardsReq:
            dcBoard = dcBoardsReq[0]
            if check(dcBoard,'name'):
                cloudBoardsReq = list(filter(lambda board: 'name' in board and board['name'] == dcBoard['name'], cloudBoards))
                if cloudBoardsReq:
                    if len(cloudBoardsReq) > 1:
                        writer.writerow([currentRule,currentComponent,'Map Boards','More than one board matches',str(id)])
                    return cloudBoardsReq[0]['id']
                else:
                    writer.writerow([currentRule,currentComponent,'Map Boards','No match in Cloud',str(id)])
                    return id
            else:
                writer.writerow([currentRule,currentComponent,'Map Boards','Name not in DC Board',id])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Boards','Board not found in DC',str(id)])
            return id

    def mapUser(userKey,type='key'):
        dcUserReq = list(filter(lambda user: user[type].lower() == userKey.lower(), dcUsers))
        if not dcUserReq:
            writer.writerow([currentRule,currentComponent,'Map User','Not finding DC user',userKey])
            return userKey
        else:
            dcUser = dcUserReq[0]
            if not check(dcUser,'emailAddress'):
                writer.writerow([currentRule,currentComponent,'Map User','DC user without email address',userKey])
                return userKey
            else:
                cloudUser = list(filter(lambda user: 'emailAddress' in user and user['emailAddress'].lower() == dcUser['emailAddress'].lower(), cloudUsers))
                if not cloudUser:
                    writer.writerow([currentRule,currentComponent,'Map User','No Cloud match for user',userKey])
                    return userKey
                else:
                    return cloudUser[0]['accountId']

    def manageSmartValues(element):
        writer.writerow([currentRule,currentComponent,'Manage Smart Values','Before',str(element)])
        newElement = element
        for field in re.findall('customfield_\d{5}',element,flags=re.I):
            newField = mapFieldFromId(field)
            if newField:
                newElement = re.sub(field,newField,element)
        newElement = re.sub('lookupAssets','lookupObjects',newElement,flags=re.I)
        newElement = re.sub('webhookResponse','webResponse',newElement,flags=re.I)
        writer.writerow([currentRule,currentComponent,'Manage Smart Values','After',str(newElement)])
        return newElement
        

    def manageJql(query):
        writer.writerow([currentRule,currentComponent,'JQL','Origin Query',query])
        
        #Special field Customer Request Type
        newQuery = re.sub('''customer request type''','Request type',query,flags=re.I)
        
        #Projects
        projectRegex = '''(?=("?'?project"?'?\s+(?:!?=|(?:not )?in)\s+\(?((?:\s*"?'?\d{5}"?'?\s*,?)+)\)?))'''
        projectClauses = []
        for d in re.findall(projectRegex,newQuery,flags=re.I):
            l = (d[0],d[1].split(','))
            newClause = d[0]
            i=0
            while i < len(l[1]):
                newClause = newClause.replace(''.join(filter(lambda str: str.isdigit(), l[1][i])),str(mapProject(''.join(filter(lambda str: str.isdigit(), l[1][i])))))
                i = i+1
            projectClauses.append((d[0],newClause))

        for clause in projectClauses:
            newQuery = newQuery.replace(clause[0],clause[1])
        
        #Teams
        teamRegex = '''(?=("?'?(?:team|cf\[11700\])"?'?\s+(?:!?=|(?:not )?in)\s+\(?((?:\s*"?'?\d+"?'?\s*,?)+)\)?))'''
        teamClauses = []
        for d in re.findall(teamRegex,newQuery,flags=re.I):
            l = (d[0],d[1].split(','))
            newClause = d[0]
            i=0
            while i < len(l[1]):
                #newClause = newClause.replace(''.join(filter(lambda str: str.isdigit(), l[1][i])),str(mapTeam(''.join(filter(lambda str: str.isdigit(), l[1][i])))))
                i = i+1
            teamClauses.append((d[0],newClause))
        for clause in teamClauses:
            newQuery = newQuery.replace(clause[0],clause[1])
        
        #Users
        #On ne prend pas en compte les clauses BY et CHANGED FROM ou TO username
        userClause = '|'.join([re.escape(d) for d in dcUserClauses])
        userRegex = f'''(?=("?'?(?:{userClause})"?'?\s+(?:!?=|was(?: not)?(?: in)?|(?:not )?in|changed)\s+(\([^\)]+\)|"?'?[^\s]+"?'?)))'''
        userClauses = []
        for d in re.findall(userRegex,newQuery,flags=re.I):
            l = (d[0],d[1].split(','))
            newClause = d[0]
            i=0
            while i < len(l[1]):
                newClause = newClause.replace(''.join(filter(lambda str: re.sub('''["'\s\(\)]''','',str), l[1][i])),str(mapUser(''.join(filter(lambda str: re.sub('''["'\s\(\)]''','',str), l[1][i])),'name')))
                i = i+1
            userClauses.append((d[0],newClause))

        for clause in userClauses:
            newQuery = newQuery.replace(clause[0],clause[1])
        
        fieldClauses = []
        for id in re.findall('''cf\[(\d{5})\]''',newQuery):
            newField = mapFieldFromId('customfield_' + id)
            if newField:
                fieldClauses.append(('cf[' + id + ']',re.sub(r'customfield_(\d{5})',r'cf[\1]',newField)))
        #fieldClauses = [('cf[' + id + ']',re.sub('customfield_(\d{5})','cf[\1]',mapFieldFromId('customfield_' + id))) for id in re.findall('''cf\[(\d{5})\]''',newQuery)]
        for clause in fieldClauses:
            newQuery = newQuery.replace(clause[0],clause[1])
        if (newQuery != query):
            writer.writerow([currentRule,currentComponent,'JQL','Transformed Query',newQuery])

        newQuery = manageSmartValues(newQuery)

        return newQuery
        #Cascadefield = id
        #Champ Team = id -> changer juste l'identifiant (attention clause peut être cf[11700]
        #Status = id
        #issuetype ou type = id
        #Versions : les champs sont limités
        #User picker
        #Customer Request Type en Request type
        

    def editFields(componentvalue):
        if componentvalue['operations']:
            for operation in componentvalue['operations']:
                if check(operation,'fieldId'):
                    if check(operation,'value'):
                        if isinstance(operation['value'],str):
                            operation['value'] = manageSmartValues(operation['value'])
                            writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Operation with String value',str(operation)])
                        if operation['type'] == 'COPY':
                            if check(operation['value'],'additional'):
                                operation['value']['additional'] = mapFieldFromId(operation['value']['additional'])
                        elif operation['type'] == 'SET':
                            if operation['fieldId'] in dcUserFields:
                                if isinstance(operation['value'],list):
                                    for value in operation['value']:
                                        if value['type'] == 'ID':
                                            value['value'] = mapUser(value['value'])
                                elif isinstance(operation['value'],dict):
                                    value = operation['value']
                                    if value['type'] == 'ID':
                                        value['value'] = mapUser(value['value'])
                            if operation['fieldId'] == 'project':
                                if operation['value']['type'] == 'ID':
                                    operation['value']['value'] = mapProject(operation['value']['value'])
                                else:
                                    #C'est toujours COPY quand ce n'est pas SET, et il n'y a rien à faire
                                    writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','SET Operation on project not ID',str(operation)])
                            elif operation['fieldId'] == 'issuetype':
                                if operation['value']['type'] == 'ID':
                                    operation['value']['value'] = mapIssuetype(operation['value']['value'])
                                else:
                                    writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','SET Issue type on project not ID',str(operation)])
                            elif operation['fieldId'] == 'priority':
                                if operation['value']['type'] == 'ID':
                                    operation['value']['value'] = mapPriority(operation['value']['value'])
                                else:
                                    writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','SET Priority on project not ID',str(operation)])
                            elif operation['fieldId'] == 'resolution':
                                if operation['value']['type'] == 'ID':
                                    operation['value']['value'] = mapResolution(operation['value']['value'])  
                                else:
                                    writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','SET Resolution on project not ID',str(operation)])                                    
                            elif operation['fieldId'] == 'customfield_10008': #Sprint
                                writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Set sprint']) 
                            elif operation['fieldId'] == 'issuelinks':
                                match = re.search('\d{5}',operation['value']['linkType'])
                                if match:
                                    linkId = mapIssuelink(match.group(0))
                                    operation['value']['linkType'] = operation['value']['linkType'].replace(match.group(0),linkId)
                        else:
                            writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Operation nor SET nor COPY',str(operation)])
                            #Operation ADDREMOVE, seulement sur les labels
                    if 'customfield_' in operation['fieldId']:
                        operation['fieldId'] = mapFieldFromId(operation['fieldId'])
                    else:
                        writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Operation without value',str(operation)])
                        
                    #reste à faire : request type (10002) - remplacer par une action propre     
                else:
                    writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Operation without field',str(operation)])
        if check(componentvalue,'advancedFields'):
            try:
                advancedFields = json.loads(componentvalue['advancedFields'])
                writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Advanced Fields: Before',str(advancedFields)])
                for action in advancedFields.keys(): #update or fields
                    fields = advancedFields[action]
                    for key in fields:
                        if key in ['Team','team','customfield_11700']:
                            if action == 'update':
                                for operation in fields[key]:
                                    for operationAction in operation.keys():
                                        operation[operationAction] = mapTeam(operation[operationAction])
                            elif action == 'fields':
                                fields[key] = mapTeam(fields[key])
                        if key in dcUserFields:
                            if action == 'update':
                                for operation in fields[key]:
                                    for operationAction in operation.keys():
                                        operation[operationAction]['name'] = mapUser(operation[operationAction]['name'])
                                        operation[operationAction]['accountId'] = operation[operationAction].pop('name')
                            elif action == 'fields':
                                if isinstance(fields[key],list):
                                    for user in fields[key]:
                                        if check(user,'name'):
                                            user['name'] = mapUser(user['name'])
                                            user['accountId'] = user.pop('name')
                                elif isinstance(fields[key],dict):
                                    if check(fields[key],'name'):
                                        fields[key]['name'] = mapUser(fields[key]['name'])
                                        fields[key]['accountId'] = fields[key].pop('name')
                componentvalue['advancedFields'] = str(advancedFields)
                componentvalue['advancedFields'] = manageSmartValues(componentvalue['advancedFields'])
                #Resterait à gérer tous les éléments qui peuvent être définis par leur ID : options de champs select / mutli select, statut, etc.
            except ValueError as e:
                writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Advanced Fields: impossible to decode JSON',str(e),str(componentvalue['advancedFields'])])

    def jirajqlscheduled(component):
        component['value']['jql'] = manageJql(component['value']['jql'])

    def jiraconditioncontainerblock(component):
        return

    def jiraconditionifblock(component):
        convert(component['conditions'])
#         for condition in component['conditions']:
#             if "value" in condition:
#                 searchSmartValues(condition['value'])
#             functions[condition['type']](condition)

    def jiraissuecomment(component):
        if check(component['value'],'comment'):
            writer.writerow([currentRule,currentComponent,'Comment on issue','Comment Before',str(component['value']['comment'])])
            component['value']['comment'] = manageSmartValues(component['value']['comment'])
            writer.writerow([currentRule,currentComponent,'Comment on issue','Comment After',str(component['value']['comment'])])
        
        
    def jiraissuetransition(component):
        if check(component['value'],'destinationStatus'):
            if component['value']['destinationStatus']['type'] == 'ID':
                component['value']['destinationStatus']['value'] = mapStatus(component['value']['destinationStatus']['value'])
        editFields(component['value'])

    def jiraissueedit(component):
        editFields(component['value'])

    def jiraissuefieldchanged(component):
        for field in component['value']['fields']:
            if field['type'] == 'field':
                field['value'] = mapFieldFromId(field['value'])
            elif field['type'] == 'match':
                field['value'] = mapFieldFromName(field['value'])

    def jiraissuecondition(component):
        #RAF : Ajouter les comparaisons par valeur pour tous types de champs (similaire à edit fields)
        if check(component['value'],'selectedField'):
            field = component['value']['selectedField']
            if field['type'] == 'ID':
                if check(component['value'],'compareValue'):
                    if check(component['value']['compareValue'],'type'):
                        if component['value']['compareValue']['type'] == 'FIELD':
                            component['value']['compareValue']['value'] = mapFieldFromId(component['value']['compareValue']['value'])
                        elif component['value']['compareValue']['type'] == 'ID':
                            try:
                                print(currentRule + " " + type(component['value']['compareValue']['value']).__name__)
                                compareValue = json.loads(str(component['value']['compareValue']['value']))
                                if field['value'] in dcUserFields:
                                    retour = []
                                    if isinstance(compareValue,list):
                                        for user in compareValue:
                                            retour.append(mapUser(user))
                                        component['value']['compareValue']['value'] = str(retour)
                                    elif isinstance(compareValue,str) or isinstance(compareValue,int):
                                        component['value']['compareValue']['value'] = mapUser(compareValue)
                                    else:
                                        print('User field ni string ni list : ' + str(compareValue))
#                                 elif field['value'] == 'project':
#                                     retour = []
#                                     if isinstance(compareValue,list):
#                                         for project in compareValue:
#                                             print("it works")
#                                             retour.append(mapProject(project))
#                                         component['value']['compareValue']['value'] = str(retour)
#                                     elif isinstance(compareValue,str) or isinstance(compareValue,int):
#                                         component['value']['compareValue']['value'] = mapProject(compareValue)
#                                     else:
#                                         print('Project field ni string ni list : ' + str(compareValue))
#                                 elif field['value'] == 'priority':
#                                     retour = []
#                                     if isinstance(compareValue,list):
#                                         for priority in compareValue:
#                                             retour.append(mapPriority(priority))
#                                         component['value']['compareValue']['value'] = str(retour)
#                                     elif isinstance(compareValue,str) or isinstance(compareValue,int):
#                                         component['value']['compareValue']['value'] = mapPriority(compareValue)
#                                     else:
#                                         print('Priority field ni string ni list : ' + str(compareValue))
                                elif field['value'] == 'status':
                                    retour = []
                                    if isinstance(compareValue,list):
                                        for status in compareValue:
                                            retour.append(mapStatus(status))
                                        component['value']['compareValue']['value'] = str(retour)
                                    elif isinstance(compareValue,str) or isinstance(compareValue,int):
                                        component['value']['compareValue']['value'] = mapStatus(compareValue)
                                    else:
                                        print('Status field ni string ni list : ' + str(compareValue))
#                                 elif field['value'] == 'issuetype':
#                                     retour = []
#                                     if isinstance(compareValue,list):
#                                         for issuetype in compareValue:
#                                             retour.append(mapIssuetype(issuetype))
#                                         component['value']['compareValue']['value'] = str(retour)
#                                     elif isinstance(compareValue,str) or isinstance(compareValue,int):
#                                         component['value']['compareValue']['value'] = mapIssuetype(compareValue)
#                                     else:
#                                         print('Issue type field ni string ni list : ' + str(compareValue))
#                                 elif field['value'] == 'resolution':
#                                     retour = []
#                                     if isinstance(compareValue,list):
#                                         for resolution in compareValue:
#                                             retour.append(mapResolution(resolution))
#                                         component['value']['compareValue']['value'] = str(retour)
#                                     elif isinstance(compareValue,str) or isinstance(compareValue,int):
#                                         component['value']['compareValue']['value'] = mapResolution(compareValue)
#                                     else:
#                                         print('Resolution field ni string ni list : ' + str(compareValue))
                                else:
                                    writer.writerow([currentRule,currentComponent,'Issue field condition','Champ pas pris en compte dans le mapping','Champ: ' + field['value'],'Valeur de comparaison: ' + component['value']['compareValue']['value']])
                                #Customer Request Type
                                #Pas Team : pas possible à sélectionner
                                #Pas asset non plus
                            except ValueError as e:
                                print(str(e))
                                print(currentRule + " " + str(component['value']['compareValue']['value']))
#                                 print(str(component['value']['compareValue']))
#                                 print(str(component['value']['compareValue']['value']))
                        elif not component['value']['compareValue']['type'] in ['VALUE','NAME']:
                            print("Type ni FIELD ni ID ni VALUE ni NAME : " + component['value']['compareValue']['type'])
                    else:
                        print("compareValue sans type " + str(component['value']))
                elif not component['value']['comparison'] in ['EMPTY','NOT_EMPTY']:
                    print("Issue condition sans compareValue et pas EMPTY ou NOT EMPTY " + str(component['value']))
                field['value'] = mapFieldFromId(field['value'])
            else:
                print("Field type pas ID " + str(component['value']))
        else:
            print("Issue condition sans selecte field " + str(component['value']))
            
                
    def jiraissueclone(component):
        editFields(component['value'])

    def jiramanualtriggerissue(component):
        return

    def jiraissueassign(component):
        if check(component['value'],'jql'):
            component['value']['jql'] = manageJql(component['value']['jql'])
        
        if check(component['value'],'userList'):
            for user in component['value']['userList']:
                user['value'] = mapUser(user['value'])
        
        if check(component['value'],'excludeUsers'):
            for user in component['value']['excludeUsers']:
                user['value'] = mapUser(user['value'])
        
        if check(component['value'],'assignee'):
            if component['value']['assignee']['type'] == 'SMART':
                component['value']['assignee']['value'] = manageSmartValues(component['value']['assignee']['value'])
            elif component['value']['assignee']['type'] == 'ID':
                component['value']['assignee']['value'] = mapUser(component['value']['assignee']['value'])
                
        if check(component['value'],'smartValue'):
            component['value']['smartValue'] = manageSmartValues(component['value']['smartValue'])

    def jiraissuerefreshissue(component):
        return

    def jiraissueeventtriggercreated(component):
        return

    def jiraissueeventtriggermoved(component):
        if component['value']['sourceProject'] != '-1999':
            component['value']['sourceProject'] = mapProject(component['value']['sourceProject'])
        if component['value']['targetProject'] != '-1999':
            component['value']['targetProject'] = mapProject(component['value']['targetProject'])

    def jirausercondition(component):
        for condition in component['value']['conditions']:
            if check(condition,'field'):
                condition['field'] = mapFieldFromId(condition['field'])
            if check(condition,'check'):
                match condition['check']:
                    case 'USER_IS':
                        for criteria in condition['criteria']:
                            if criteria['type'] == 'ID':
                                criteria['value'] = mapUser(criteria['value'])
                            if criteria['type'] == 'SMART':
                                criteria['value'] = manageSmartValues(criteria['value'])
                    case 'IN_ORGANISATION':
                        for criteria in condition['criteria']:
                            if criteria['type'] == 'ID':
                                criteria['value'] = mapOrganization(criteria['value'])
                

    def jiraissueoutgoingemail(component):
        if check(component['value'],'to'):
            for field in component['value']['to']:
                if field['type'] == 'COPY':
                    field['value'] = mapFieldFromId(field['value'])
                elif field['type'] == 'SMART':
                    field['value'] = manageSmartValues(field['value'])
        if component['value']['cc']:
            for field in component['value']['cc']:
                if field['type'] == 'COPY':
                    field['value'] = mapFieldFromId(field['value'])
                elif field['type'] == 'SMART':
                    field['value'] = manageSmartValues(field['value'])
        if component['value']['bcc']:
            for field in component['value']['bcc']:
                if field['type'] == 'COPY':
                    field['value'] = mapFieldFromId(field['value'])
                elif field['type'] == 'SMART':
                    field['value'] = manageSmartValues(field['value'])
        if check(component['value'],'subject'):
            component['value']['subject'] = manageSmartValues(component['value']['subject'])
        if check(component['value'],'body'):
            component['value']['body'] = manageSmartValues(component['value']['body'])
         
    def jirajqlcondition(component):
        component['value'] = manageJql(component['value'])

    def codebarrelactionlog(component):
        component['value'] = manageSmartValues(component['value'])

    def comonresolvejiragroovygroovyrunnerlookupobjectbeans(component):
        #RAF : ajouter valeurs de champs (objectType = ID)
        component['type'] = 'cmdb.lookup.objects'
        if check(component['value'],'assetKey'):
            aql = 'key = ' + manageSmartValues(component['value']['assetKey'])
        elif check(component['value'],'aql'):
            aql = manageSmartValues(component['value']['aql'])
        else:
            writer.writerow([currentRule,currentComponent,'Lookup Objects without value',str(component['value'])])
            return
        component['value'] = {
            "workspaceId": "971e0c97-6aa1-4b33-95c2-04ef61df728d",
            "schemaId": "1",
            "customSmartValue": {
              "id": "_customsmartvalue_id_1741682612690",
              "name": {
                "type": "FREE",
                "value": "lookupObjects"
              },
              "type": "IQL",
              "query": {
                "type": "SMART",
                "value": aql
              },
              "lazy": False
            }
        }

    def jirasetentityproperty(component):
        if check(component,'value'):
            value = component['value']
            if check(value,'entityType'):
                if value['entityType'] in ['USER','USERLEGACY']:
                    if check(value,'entity'):
                        if value['entity']['type'] == 'ID':
                            value['entity']['value'] = mapUser(value['entity']['value'])
                        elif value['entity']['type'] == 'SMART':
                            value['entity']['value'] = manageSmartValues(value['entity']['value'])
                        else:
                            writer.writerow([currentRule,currentComponent,'Set entity property','User - Type nor ID not SMART',str(value)])
                value['key'] = manageSmartValues(value['key'])
                value['value'] = manageSmartValues(value['value'])

    def jiraissueoutgoingwebhook(component):
        writer.writerow([currentRule,currentComponent,'Send web request',str(component['value'])])
        headers = []
        if check(component['value'],'headers'):
            for header in component['value']['headers']:
                header['value'] = manageSmartValues(header['value']['keyOrValue'])
                header['secure'] = False
        if check(component['value'],'contentType'):
            if component['value']['contentType'] == 'issue':
                component['value']['contentType'] = 'issueJiraFormat'
        if check(component['value'],'customBody'):
            component['value']['customBody'] = manageSmartValues(component['value']['customBody'])
        component['value']['continueOnErrorEnabled'] = False
        
    def jiraissuerelated(component):
        if component['value']['relatedType'] == 'jql':
            component['value']['jql'] = manageJql(component['value']['jql'])

    def jiraissuecreate(component):
        editFields(component['value'])

    def jiraissueeventtriggertransitioned(component):
        if component['value']['eventKey'] != 'jira:issue_updated':
            writer.writerow([currentRule,currentComponent,'Trigger','Event key different than issue updated',component['value']['eventKey']])
        if component['value']['issueEvent'] != 'issue_generic':
            writer.writerow([currentRule,currentComponent,'Trigger','Issue event different than issue generic',component['value']['eventKey']])
        if component['value']['fromStatus']:
            for fromStatus in component['value']['fromStatus']:
                if fromStatus['type'] != 'ID':
                    writer.writerow([currentRule,currentComponent,'Trigger','FromStatus type different than ID',fromStatus['type']])
                else:
                    fromStatus['value'] = mapStatus(fromStatus['value'])
        if component['value']['toStatus']:
            for toStatus in component['value']['toStatus']:
                if toStatus['type'] != 'ID':
                    writer.writerow([currentRule,currentComponent,'Trigger','ToStatus type different than ID',toStatus['type']])
                else:
                    toStatus['value'] = mapStatus(toStatus['value'])

    def jiraissueeventtriggercommented(component):
        return

    def jiraissueeventtriggerupdated(component):
        return

    def msteamsnotification(component):
        if check(component['value'],'title'):
            component['value']['title'] = manageSmartValues(component['value']['title'])
        if check(component['value'],'body'):
            component['value']['body'] = manageSmartValues(component['value']['body'])
        component['value']['webhookUrl'] = component['value']['webhookUrl']['key']

    def automationtriggerservicelimit(component):
        return

    def jiraissueaddwatcher(component):
        if check(component['value'],'watchers'):
            for watcher in component['value']['watchers']:
                if watcher['type'] == 'SMART':
                    watcher['value'] = manageSmartValues(watcher['value'])
                else:
                    watcher['value'] = mapUser(watcher['value'])
        if check(component['value'],'removeWatchers'):
            for watcher in component['value']['removeWatchers']:
                if watcher['type'] == 'SMART':
                    watcher['value'] = manageSmartValues(watcher['value'])
                else:
                    watcher['value'] = mapUser(watcher['value'])

    def jiraissuesrelatedcondition(component):
        if check(component['value'],'relatedJql'):
            component['value']['relatedJql'] = manageJql(component['value']['relatedJql'])
        if check(component['value'],'compareJql'):
            component['value']['compareJql'] = manageJql(component['value']['compareJql'])
        if check(component['value'],'jql'):
            component['value']['jql'] = manageJql(component['value']['jql'])
            
    def jiraissueeventtriggerlink(component):
        return

    def jirasdaddcustomer(component):
        if check(component['value'],'email'):
            component['value']['email'] = manageSmartValues(component['value']['email'])
        if check(component['value'],'displayName'):
            component['value']['displayName'] = manageSmartValues(component['value']['displayName'])
        if check(component['value'],'organization'):
            if component['value']['organization']['type'] == 'ID':
                component['value']['organization']['value'] = mapOrganization(component['value']['organization']['value'])  

    def jirapublishevent(component):
        global parentComponent
        writer.writerow([currentRule,currentComponent,'Publish event','Removed component',str(component)])
        i = 0
        for childComponent in parentComponent:
            if childComponent['id'] == component['id']:
                parentComponent.pop(i)
            i = i + 1

    def jiraissuelink(component):
        if check(component['value'],'linkType'):
            match = re.search('\d{5}',component['value']['linkType'])
            if match:
                linkId = mapIssuelink(match.group(0))
                component['value']['linkType'] = component['value']['linkType'].replace(match.group(0),linkId)

    def jiramultipleissueevent(component):
        global rules
        for event in component['value']['events']:
            if event['event'] in ['issue_resolved','issue_reopened','issue_closed']:
                writer.writerow([currentRule,currentComponent,'Multiple Issue Event','Evenement non géré',event['event']])
            elif event['event'] in ['issue_commented','issue_comment_edited']:
                rules.insert(0,copy.deepcopy(rule))
                rules[-1]['id'] = generateId(rules[-1]['id'])
                rules[-1]['name'] = 'Copy of ' + rules[-1]['name'] + ' (comment)'
                if event['event'] == 'issue_commented':
                    rules[-1]['trigger'] = {"id":generateId(rules[-1]['trigger']['id']),"component":"TRIGGER","schemaVersion":1,"type":"jira.issue.event.trigger:commented","value":{"synchronous":False,"eventKey":"jira:issue_updated","issueEvent":"issue_commented"},"children":[],"conditions":[],"optimisedIds":[],"newComponent":False}
                elif event['event'] == 'issue_comment_edited':
                    rules[-1]['trigger'] = {"id":generateId(rules[-1]['trigger']['id']),"component":"TRIGGER","schemaVersion":1,"type":"jira.issue.comment.event.trigger:updated","value":{"synchronous":False,"eventKey":"jira:issue_updated","issueEvent":"issue_comment_updated"},"children":[],"conditions":[],"optimisedIds":[],"newComponent":False}
        component['value']['events'] = [d for d in component['value']['events'] if d['event'] not in ['issue_commented','issue_comment_edited']]

    def jiraissuearchive(component):
        global parentComponent
        writer.writerow([currentRule,currentComponent,'Archive issue','Removed component',str(component)])
        i = 0
        for childComponent in parentComponent:
            if childComponent['id'] == component['id']:
                parentComponent.pop(i)
            i = i + 1

    def jiracomparatorcondition(component):
        writer.writerow([currentRule,currentComponent,'Advanced compare condition','Premier élément origine',component['value']['first']])
        component['value']['first'] = manageSmartValues(component['value']['first'])
        writer.writerow([currentRule,currentComponent,'Advanced compare condition','Premier élément remplacement',component['value']['first']])

        writer.writerow([currentRule,currentComponent,'Advanced compare condition','Deuxième élément origine',component['value']['second']])
        component['value']['second'] = manageSmartValues(component['value']['second'])
        writer.writerow([currentRule,currentComponent,'Advanced compare condition','Deuxième élément remplacement',component['value']['second']])
        
        #reste à faire : {{issue.comments.last.author.displayName}} = svc.jira
        
    def jiraissueeventtriggerassigned(component):
        return

    def jirasprinteventtriggerstarted(component):
        return
        #component['value']['boardId'] = mapBoard(component['value']['boardId'])

    def jiraworklogadd(component):
        if check(component['value'],'timeSpent'):
            component['value']['timeSpent'] = manageSmartValues(component['value']['timeSpent'])
        if check(component['value'],'dateStarted'):
            if check(component['value']['dateStarted'],'value'):
                component['value']['dateStarted']['value'] = manageSmartValues(component['value']['dateStarted']['value'])

    def comonresolvejiragroovygroovyrunnerexecutescriptissueactionv2(component):
        global parentComponent
        writer.writerow([currentRule,currentComponent,'Scriptrunner Execute Script V2','Removed component',str(component)])
        i = 0
        for childComponent in parentComponent:
            if childComponent['id'] == component['id']:
                parentComponent.pop(i)
            i = i + 1

    def jiraissuecreatesubtasks(component):
        if check(component['value']['subtasks']):
            for subtask in component['value']['subtasks']:
                subtask['type'] = mapIssuetype(subtask['type'])

    def jiraissuedelete(component):
        return

    def jirasprinteventtriggerclosed(component):
        return
        #component['value']['boardId'] = mapBoard(component['value']['boardId'])

    def jiralookupissues(component):
        if check(component['value'],'query'):
            if check(component['value']['query'],'value'):
                component['value']['query']['value'] = manageJql(component['value']['query']['value'])
            else:
                writer.writerow([currentRule,currentComponent,'Lookup issues','Query without value',str(component['value'])])
        else:
            writer.writerow([currentRule,currentComponent,'Lookup issues','Component without query',str(component['value'])])

    def jiracreatevariable(component):
        if check(component['value'],'name'):
            if check (component['value']['name'],'value'):
                component['value']['name']['value'] = manageSmartValues(component['value']['name']['value'])
            else:
                writer.writerow([currentRule,currentComponent,'Create variable','Name without value',str(component['value'])])
        else:
            writer.writerow([currentRule,currentComponent,'Create variable','Action without name',str(component['value'])])
        if check(component['value'],'query'):
            if check(component['value']['query'],'value'):
                component['value']['query']['value'] = manageSmartValues(component['value']['query']['value'])
            else:
                writer.writerow([currentRule,currentComponent,'Create variable','Query without value',str(component['value'])])
        else:
            writer.writerow([currentRule,currentComponent,'Create variable','Action without query',str(component['value'])])

    def jiraslathresholdtrigger(component):
        if check(component['value'],'customFieldId'):
            component['value']['customFieldId'] = mapFieldFromId(component['value']['customFieldId'])
        
    def comonresolvejiragroovygroovyrunnerexecutescriptissueaction(component):
        global parentComponent
        writer.writerow([currentRule,currentComponent,'Scriptrunner Execute Script Legacy','Removed component',str(component)])
        i = 0
        for childComponent in parentComponent:
            if childComponent['id'] == component['id']:
                parentComponent.pop(i)
            i = i + 1
        
    def jiraissueeventtriggerlinkdeleted(component):
        return

    def slacknotification(component):
        if check(component['value'],'channel'):
            component['value']['channel'] = manageSmartValues(component['value']['channel'])
        if check(component['value'],'body'):
            component['value']['body'] = manageSmartValues(component['value']['body'])
        component['value']['webhookUrl'] = component['value']['webhookUrl']['key']
        
    def jiraissuehasAttachments(component):
        return

    def jiraissueeventtriggerdeleted(component):
        return

    def jiraissuecommenteventtriggerupdated(component):
        return

    functions = {'jira.jql.scheduled':jirajqlscheduled,'jira.condition.container.block':jiraconditioncontainerblock,'jira.condition.if.block':jiraconditionifblock,'jira.issue.comment':jiraissuecomment,'jira.issue.transition':jiraissuetransition,'jira.issue.edit':jiraissueedit,'jira.issue.field.changed':jiraissuefieldchanged,'jira.issue.condition':jiraissuecondition,'jira.issue.clone':jiraissueclone,'jira.manual.trigger.issue':jiramanualtriggerissue,'jira.issue.assign':jiraissueassign,'jira.issue.refresh.issue':jiraissuerefreshissue,'jira.issue.event.trigger:created':jiraissueeventtriggercreated,'jira.issue.event.trigger:moved':jiraissueeventtriggermoved,'jira.user.condition':jirausercondition,'jira.issue.outgoing.email':jiraissueoutgoingemail,'jira.jql.condition':jirajqlcondition,'codebarrel.action.log':codebarrelactionlog,'com.onresolve.jira.groovy.groovyrunner:lookup-object-beans':comonresolvejiragroovygroovyrunnerlookupobjectbeans,'jira.set.entity.property':jirasetentityproperty,'jira.issue.outgoing.webhook':jiraissueoutgoingwebhook,'jira.issue.related':jiraissuerelated,'jira.issue.create':jiraissuecreate,'jira.issue.event.trigger:transitioned':jiraissueeventtriggertransitioned,'jira.issue.event.trigger:commented':jiraissueeventtriggercommented,'jira.issue.event.trigger:updated':jiraissueeventtriggerupdated,'msteams.notification':msteamsnotification,'automation.trigger.service.limit':automationtriggerservicelimit,'jira.issue.add.watcher':jiraissueaddwatcher,'jira.issues.related.condition':jiraissuesrelatedcondition,'jira.issue.event.trigger:link':jiraissueeventtriggerlink,'jira.sd.add.customer':jirasdaddcustomer,'jira.publish.event':jirapublishevent,'jira.issue.link':jiraissuelink,'jira.multiple.issue.event':jiramultipleissueevent,'jira.issue.archive':jiraissuearchive,'jira.comparator.condition':jiracomparatorcondition,'jira.issue.event.trigger:assigned':jiraissueeventtriggerassigned,'jira.sprint.event.trigger:started':jirasprinteventtriggerstarted,'jira.worklog.add':jiraworklogadd,'com.onresolve.jira.groovy.groovyrunner:execute-script-issue-action-v2':comonresolvejiragroovygroovyrunnerexecutescriptissueactionv2,'jira.issue.create.subtasks':jiraissuecreatesubtasks,'jira.issue.delete':jiraissuedelete,'jira.sprint.event.trigger:closed':jirasprinteventtriggerclosed,'jira.lookup.issues':jiralookupissues,'jira.create.variable':jiracreatevariable,'jira.sla.threshold.trigger':jiraslathresholdtrigger,'com.onresolve.jira.groovy.groovyrunner:execute-script-issue-action':comonresolvejiragroovygroovyrunnerexecutescriptissueaction,'jira.issue.event.trigger:link_deleted':jiraissueeventtriggerlinkdeleted,'slack.notification':slacknotification,'jira.issue.hasAttachments':jiraissuehasAttachments,'jira.issue.event.trigger:deleted':jiraissueeventtriggerdeleted, 'jira.issue.comment.event.trigger:updated':jiraissuecommenteventtriggerupdated}

    def searchSmartValues(component):
        if component:
            if re.search('{{.+?}}',str(component)):
                sms = re.findall('{{.+?}}',str(component))
                for sm in sms:
                    writer.writerow([currentRule,currentComponent,'Smart Value',str(component),sm])
                #smartValues = re.findall('{{[^}]+}}',str(component))
                #for sm in smartValues:
                #    for customField in filter(lambda field: field.startswith('customfield_'),sm.split('.')):
                #        return
                        
    def convert(components):
        global currentComponent
        global parentComponent
        for component in components:
            parentComponent = components
            if "type" in component and "component" in component:
                currentComponent = component["component"] + ' ' + component["type"]
                
                #Smart values
                if "value" in component:
                    searchSmartValues(component['value'])
                    
                #Champs particuliers
                if component["type"] == 'jira.issue.condition':
                    results = functions[component['type']](component)
            else:
                writer.writerow([currentRule,currentComponent,'Convert','Component exists but it has no type or subtype'])

            if check(component,'conditions'):
                convert(component['conditions'])

            if "children" in component:
                if component["children"]:
                    convert(component["children"])

    with open(r'C:\Users\simon.lucchesini\Documents\Analyse Automation\automation-rules-202502071516.json',encoding='utf-8') as f:
        file = json.load(f)
        rules = file['rules']
        rules = [d for d in rules if d['state'] == 'ENABLED']
        
        id = 1
        for rule in rules:
            currentRule = str(rule['id']) + ' - ' + rule['name']
            currentComponent = 'GENERAL'
            parentComponent = None
            
            mappedUser = mapUser(rule['authorAccountId'])
            if mappedUser != rule['authorAccountId']:
                rule['authorAccountId'] = mappedUser
            else:
                rule['authorAccountId'] = '712020:367293a3-5f77-422a-9b4f-a582251933c0' #svcjira
                
            #Inutile : impossible d'importer un acteur
            #rule['actor'] = {
            #    'type': 'ACCOUNT_ID',
            #    'value': mapUser(rule['actorAccountId'])
            #}
            #del rule['actorAccountId']
            for project in rule['projects']:
                project['projectId'] = mapProject(project['projectId'])
            
            currentComponent = 'TRIGGER - ' + rule['trigger']['type']
            functions[rule['trigger']['type']](rule['trigger'])
            convert(rule['components'])
            id = id + 1
            
            # Si besoin de recréer une règle, le faire ici après toutes les modifs (modifier multipleissueevent)
            # Ou alors avant ? En fonction de quand on fait la copie, en tout cas faut pas faire la copie au milieu
            # Autre possibilité : une fonction de publication à la fin de toutes les modifs
        
        newFile = {"rules":rules,"cloud": False}
        with open(r'C:\Users\simon.lucchesini\Documents\Analyse Automation\import.json', 'w', encoding='utf-8') as f2:
            json.dump(newFile, f2)
            



