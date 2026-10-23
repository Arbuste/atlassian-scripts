import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
cloud_environment = get_environment("peaksys")
dc_environment = get_environment("open_groupe_prod", "data_center")

import json
import requests
import csv
import re
import copy
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier converti
outputPath = r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\Automation - Converted.json'
#Chemin vers le fichier source
inputPath = r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\automation-rules-202603181110.json'
#Chemin vers le fichier de logs
logPath = r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\Automation - Logs.csv'

#URL de l'instance DCDCBaseUrl = dc_environment["jira_base_url"]
#Bearer pour interroger l'instance DCbearer_token = dc_environment["jira_pat"]

#URL de l'instance Cloud ciblecloudBaseUrl = cloud_environment["jira_base_url"]
#Identifiants pour interroger l'instance Cloud
basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

with open(logPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    writer.writerow(["Rule","Component","Function","Category","Event","Detail","Additional detail"])
        
    def getDC(url,headers={}):
        headers['Authorization'] = f"Bearer {bearer_token}"
        retour = requests.get(DCBaseUrl + url, headers=headers)
        return retour.json()

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

    #Object types & assets
        
    workspaceId = getCloud('/rest/servicedeskapi/assets/workspace')['values'][0]['workspaceId']
        
    dcObjecttypes = []
    dcObjectSchemas = getDC('/rest/assets/1.0/objectschema/list')['objectschemas']
    for schema in dcObjectSchemas:
        dcObjecttypes = dcObjecttypes + getDC('/rest/assets/1.0/objectschema/' + str(schema['id']) + '/objecttypes/flat')
    
    cloudObjecttypes = []
    cloudObjectSchemas = requests.get(cloud_environment["org_base_url"] + "/jsm/assets/workspace/" + workspaceId + '/v1/objectschema/list',auth=basic).json()['values']
    for schema in cloudObjectSchemas:
        cloudObjecttypes = cloudObjecttypes + requests.get(cloud_environment["org_base_url"] + "/jsm/assets/workspace/" + workspaceId + '/v1/objectschema/' + str(schema['id']) + '/objecttypes/flat',auth=basic).json()
    
    #Assets 
    dcAssets = []
    page = 1
    pace = 10000
    cnt = 0
    limit = pace
    while cnt < limit:
        dcAssetsReq = getDC('/rest/assets/1.0/aql/objects?includeAttributes=false&page=' + str(page) + '&resultPerPage=' + str(pace))
        if dcAssetsReq:
            dcAssets = dcAssets + dcAssetsReq['objectEntries']
            page = page + 1
            cnt = dcAssetsReq['toIndex']
            limit = dcAssetsReq['totalFilterCount']
        else:
            break
            
    cloudAssets = []
    startAt = 1
    pace = 1000
    isLast = False
    while not isLast:
        cloudAssetsReq = requests.post(cloud_environment["org_base_url"] + "/jsm/assets/workspace/" + workspaceId + '/v1/object/aql?includeAttributes=false&startAt=' + str(startAt) + '&maxResults=' + str(pace),json={"qlQuery":""},auth=basic).json()
        if cloudAssetsReq:
            cloudAssets = cloudAssets + cloudAssetsReq['values']
            startAt = startAt + pace
            isLast = cloudAssetsReq['isLast']
        else:
            break
    
    #Asset fields on DC
    dcAssetFieldsReq = getDC('/rest/api/2/customFields?types=com.riadalabs.jira.plugins.insight:rlabs-customfield-default-object&types=com.riadalabs.jira.plugins.insight:rlabs-customfield-object-reference&types=com.riadalabs.jira.plugins.insight:rlabs-customfield-object-reference-multi&types=com.riadalabs.jira.plugins.insight:rlabs-customfield-object-readonly')['values']
    dcAssetFields = []
    dcAssetClauses = []

    for assetField in dcAssetFieldsReq:
        improvedFields = list(filter(lambda field: field['id'] == assetField['id'], dcFields))
        if improvedFields:
            improvedField = improvedFields[0]
            if check(improvedField,'clauseNames'):
                dcAssetClauses = dcAssetClauses + improvedField['clauseNames']
            else:
                dcAssetClauses.append(improvedField['name'])
            dcAssetFields.append(improvedField['id'])
            dcAssetFields.append(improvedField['name'])
        else:
            writer.writerow(['INITIALISATION','INITIALISATION','Asset Fields','Error','Couldn\'t find the field ID in DC',assetField['id']])

    #Boards
    #C'est la partie la plus longue car on ne peut les interroger que 50 à la fois - à commenter si pas nécessaire
    dcBoards = []
    cloudBoards = []
    isLast = False
    startAt = 0
    pace = 50
    while isLast == False:
        dcBoardsReq = getDC('/rest/agile/1.0/board?startAt='+str(startAt)+'&maxResults='+str(pace))
        if dcBoardsReq:
            dcBoards = dcBoards + dcBoardsReq['values']
            startAt = startAt + pace
            isLast = dcBoardsReq['isLast']
        else:
            break
    isLast = False
    startAt = 0
    pace = 50
    while isLast == False:
        cloudBoardsReq = getCloud('/rest/agile/1.0/board?includePrivate=true&startAt='+str(startAt)+'&maxResults='+str(pace))
        if cloudBoardsReq:
            cloudBoards = cloudBoards + cloudBoardsReq['values']
            startAt = startAt + pace
            isLast = cloudBoardsReq['isLast']
        else:
            break

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
    dcUserPickerFieldsReq = getDC('/rest/api/2/customFields?types=com.atlassian.jira.plugin.system.customfieldtypes:userpicker&types=types=com.atlassian.jira.plugin.system.customfieldtypes:multiuserpicker')['values']
    dcUserFields = ['assignee','reporter','creator','Issue creator','Request participants','customfield_10003']
    dcUserClauses = dcUserFields

    for userField in dcUserPickerFieldsReq:
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
            writer.writerow(['INITIALISATION','INITIALISATION','User Fields','Error','Couldn\'t find the field ID in DC',userField['id']])

    currentRule = ''
    currentComponent = ''

    def mapFieldFromId(id):
        if id in ['initiator','parent']:
            return id
        dcFieldsReq = list(filter(lambda field: field['id'] == id, dcFields))
        if dcFieldsReq:
            dcField = dcFieldsReq[0]
            if dcField['id'] in ['components','fixVersions','duedate','description','summary','resolution','status']:
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
                     if len(cloudFieldsReq) > 1:
                         writer.writerow([currentRule,currentComponent,'Map Field From ID','Problem','More than one match in Cloud',str(id)])
                return cloudFieldsReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Field From ID','Info','No direct match in Cloud, checking the clauses...',str(id)])
                for clauseName in dcField['clauseNames']:
                    cloudFieldsReq = list(filter(lambda field: field['name'] == clauseName and field['schema']['type'] == dcField['schema']['type'], cloudFields)) 
                    if cloudFieldsReq:
                        if len(cloudFieldsReq) > 1:
                            writer.writerow([currentRule,currentComponent,'Map Field From ID','Problem','More than one match in Cloud',str(id)])
                        return cloudFieldsReq[0]['id']
                writer.writerow([currentRule,currentComponent,'Map Field From ID','Error','No match in Cloud, even after clauses',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Field From ID','Error','Field not found in DC',str(id)])
            return id

    def mapFieldFromName(name):
        dcFieldsReq = list(filter(lambda field: field['name'] == name, dcFields))
        if dcFieldsReq:
            dcField = dcFieldsReq[0]
            cloudFieldsReq = list(filter(lambda field: field['name'] == dcField['name'], cloudFields))
            if cloudFieldsReq:
                if len(cloudFieldsReq) > 1:
                    cloudFieldsReq = list(filter(lambda field: field['name'] == dcField['name'] and field['schema']['type'] == dcField['schema']['type'], cloudFields))
                    if len(cloudFieldsReq) > 1:
                        writer.writerow([currentRule,currentComponent,'Map Field From Name','Problem','More than one match in Cloud',str(name)])
                return cloudFieldsReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Field From Name','Error','No match in Cloud',str(name)])
                return name
        else:
            writer.writerow([currentRule,currentComponent,'Map Field From Name','Error','Field not found in DC',str(name)])
            return name

    def mapProject(id):
        dcProjectsReq = list(filter(lambda project: project['id'] == id, dcProjects))
        if dcProjectsReq:
            dcProject = dcProjectsReq[0]
            cloudProjectsReq = list(filter(lambda project: project['key'] == dcProject['key'], cloudProjects))
            if cloudProjectsReq:
                if len(cloudProjectsReq) > 1:
                    writer.writerow([currentRule,currentComponent,'Map Project','Problem','More than one match in Cloud',str(id)])
                return cloudProjectsReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Project','Error','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Project','Error','Project not found in DC',str(id)])
            return id

    def mapStatus(id):
        dcStatusesReq = list(filter(lambda status: status['id'] == id, dcStatuses))
        if dcStatusesReq:
            dcStatus = dcStatusesReq[0]
            cloudStatusesReq = list(filter(lambda status: status['name'].lower() == dcStatus['name'].lower() and not 'scope' in status, cloudStatuses))
            if cloudStatusesReq:
                if len(cloudStatusesReq) > 1:
                    cloudStatusesReq = list(filter(lambda status: status['name'].lower() == dcStatus['name'].lower() and not 'scope' in status and status['statusCategory']['name'] == dcStatus['statusCategory']['name'], cloudStatuses))
                    if len(cloudStatusesReq) > 1:
                        writer.writerow([currentRule,currentComponent,'Map Status','Problem','More than one match in Cloud',str(id)])
                return cloudStatusesReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Status','Error','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Status','Error','Status not found in DC',str(id)])
            return id

    def mapPriority(id):
        dcPrioritiesReq = list(filter(lambda priority: priority['id'] == id, dcPriorities))
        if dcPrioritiesReq:
            dcPriority = dcPrioritiesReq[0]
            cloudPrioritiesReq = list(filter(lambda priority: priority['name'].lower() == dcPriority['name'].lower(), cloudPriorities))
            if cloudPrioritiesReq:
                if len(cloudPrioritiesReq) > 1:
                    writer.writerow([currentRule,currentComponent,'Map Priority','Problem','More than one match in Cloud',str(id)])
                return cloudPrioritiesReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Priority','Error','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Priority','Error','Priority not found in DC',str(id)])
            return id

    def mapResolution(id):
        dcResolutionsReq = list(filter(lambda resolution: resolution['id'] == id, dcResolutions))
        if dcResolutionsReq:
            dcResolution = dcResolutionsReq[0]
            cloudResolutionsReq = list(filter(lambda resolution: resolution['name'].lower() == dcResolution['name'].lower(), cloudResolutions))
            if cloudResolutionsReq:
                if len(cloudResolutionsReq) > 1:
                    writer.writerow([currentRule,currentComponent,'Map Resolution','Problem','More than one match in Cloud',str(id)])
                return cloudResolutionsReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Resolution','Error','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Resolution','Error','Resolution not found in DC',str(id)])
            return id

    def mapIssuetype(id):
        dcIssuetypesReq = list(filter(lambda issuetype: issuetype['id'] == id, dcIssuetypes))
        if dcIssuetypesReq:
            dcIssuetype = dcIssuetypesReq[0]
            cloudIssuetypesReq = list(filter(lambda issuetype: issuetype['name'].lower() == dcIssuetype['name'].lower() and not 'scope' in issuetype, cloudIssuetypes))
            if cloudIssuetypesReq:
                if len(cloudIssuetypesReq) > 1:
                    writer.writerow([currentRule,currentComponent,'Map Issue Type','Problem','More than one match in Cloud',str(id)])
                return cloudIssuetypesReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Issue Type','Error','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Issue Type','Error','Issue type not found in DC',str(id)])
            return id

    def mapIssuelink(id):
        dcIssuelinksReq = list(filter(lambda issuelink: issuelink['id'] == id, dcIssuelinks))
        if dcIssuelinksReq:
            dcIssuelink = dcIssuelinksReq[0]
            cloudIssuelinksReq = list(filter(lambda issuelink: issuelink['name'].lower() == dcIssuelink['name'].lower(), cloudIssuelinks))
            if cloudIssuelinksReq:
                if len(cloudIssuelinksReq) > 1:
                    writer.writerow([currentRule,currentComponent,'Map Issue Link','Problem','More than one match in Cloud',str(id)])
                return cloudIssuelinksReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Issue Link','Error','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Issue Link','Error','Issue link not found in DC',str(id)])
            return id

    def mapTeam(id):
        dcTeamsReq = list(filter(lambda team: team['id'] == int(id), dcTeams))
        if dcTeamsReq:
            dcTeam = dcTeamsReq[0]
            cloudTeamsReq = list(filter(lambda team: team['displayName'].lower() == dcTeam['title'].lower(), cloudTeams))
            if cloudTeamsReq:
                if len(cloudTeamsReq) > 1:
                    writer.writerow([currentRule,currentComponent,'Map Team','Problem','More than one match in Cloud',str(id)])
                return cloudTeamsReq[0]['teamId']
            else:
                writer.writerow([currentRule,currentComponent,'Map Team','Error','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Team','Error','Team not found in DC',str(id)])
            return id

    def mapOrganization(id):
        dcOrganizationsReq = list(filter(lambda org: org['id'] == id, dcOrganizations))
        if dcOrganizationsReq:
            dcOrganization = dcOrganizationsReq[0]
            cloudOrganizationsReq = list(filter(lambda org: org['name'] == dcOrganization['name'], cloudOrganizations))
            if cloudOrganizationsReq:
                if len(cloudOrganizationsReq) > 1:
                    writer.writerow([currentRule,currentComponent,'Map Organization','Problem','More than one match in Cloud',str(id)])
                return cloudOrganizationsReq[0]['id']
            else:
                writer.writerow([currentRule,currentComponent,'Map Organization','Error','No match in Cloud',str(id)])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Organization','Error','Organization not found in DC',str(id)])
            return id
        
    def mapObjecttype(id):
        #Attention aux homonymes, il faudrait peut-être vérifier le schéma
        dcObjecttypesReq = list(filter(lambda obj: str(obj['id']) == str(id), dcObjecttypes))
        if dcObjecttypesReq:
            dcObjecttype = dcObjecttypesReq[0]
            cloudObjecttypesReq = list(filter(lambda obj: obj['name'] == dcObjecttype['name'], cloudObjecttypes))
            if cloudObjecttypesReq:
                if len(cloudObjecttypesReq) > 1:
                    writer.writerow([currentRule,currentComponent,'Map Object Type','Problem','More than one match in Cloud',str(id)])
                return str(cloudObjecttypesReq[0]['id'])
            else:
                writer.writerow([currentRule,currentComponent,'Map Object Type','Error','No match in Cloud',str(id)])
                return key
        else:
            writer.writerow([currentRule,currentComponent,'Map Object Type','Error','Object type not found in DC',str(id)])
            return id
        
    def mapAsset(key):
        writer.writerow([currentRule,currentComponent,'Map Asset','Info','Mapping asset'])
        dcAssetsReq = list(filter(lambda obj: obj['objectKey'] == key, dcAssets))
        if dcAssetsReq:
            dcAsset = dcAssetsReq[0]
            cloudAssetsReq = list(filter(lambda obj: obj['name'] == dcAsset['name'] and obj['objectType']['name'] == dcAsset['objectType']['name'], cloudAssets))
            if cloudAssetsReq:
                if len(cloudAssetsReq) > 1:
                    writer.writerow([currentRule,currentComponent,'Map Asset','Problem','More than one match in Cloud',str(key)])
                return cloudAssetsReq[0]['objectKey']
            else:
                writer.writerow([currentRule,currentComponent,'Map Asset','Error','No match in Cloud',str(key)])
                return key
        else:
            writer.writerow([currentRule,currentComponent,'Map Asset','Error','Asset not found in DC',str(key)])
            return key
    
    def mapBoard(id):
        writer.writerow([currentRule,currentComponent,'Map Board','Info'])
        dcBoardsReq = list(filter(lambda board: board['id'] == id, dcBoards))
        if dcBoardsReq:
            dcBoard = dcBoardsReq[0]
            if check(dcBoard,'name'):
                cloudBoardsReq = list(filter(lambda board: 'name' in board and board['name'] == dcBoard['name'], cloudBoards))
                if cloudBoardsReq:
                    if len(cloudBoardsReq) > 1:
                        writer.writerow([currentRule,currentComponent,'Map Board','Problem','More than one match in Cloud',str(id)])
                    return cloudBoardsReq[0]['id']
                else:
                    writer.writerow([currentRule,currentComponent,'Map Board','Error','No match in Cloud',str(id)])
                    return id
            else:
                writer.writerow([currentRule,currentComponent,'Map Board','Error','Name not in DC Board',id])
                return id
        else:
            writer.writerow([currentRule,currentComponent,'Map Board','Error','Board not found in DC',str(id)])
            return id

    def mapUser(userKey,type='key'):
        dcUserReq = list(filter(lambda user: user[type].lower() == userKey.lower(), dcUsers))
        if not dcUserReq:
            writer.writerow([currentRule,currentComponent,'Map User','Error','User not found in DC',userKey])
            return userKey
        else:
            dcUser = dcUserReq[0]
            if not check(dcUser,'emailAddress'):
                writer.writerow([currentRule,currentComponent,'Map User','Error','DC user without email address',userKey])
                return userKey
            else:
                cloudUser = list(filter(lambda user: 'emailAddress' in user and user['emailAddress'].lower() == dcUser['emailAddress'].lower(), cloudUsers))
                if not cloudUser:
                    writer.writerow([currentRule,currentComponent,'Map User','Error','No match in Cloud',userKey])
                    return userKey
                else:
                    if len(cloudUser) > 1:
                        writer.writerow([currentRule,currentComponent,'Map User','Problem','More than one match in Cloud',str(userKey)])
                    return cloudUser[0]['accountId']

    def manageSmartValues(element):
        writer.writerow([currentRule,currentComponent,'Manage Smart Values','Info','Before',str(element)])
        newElement = copy.deepcopy(element)
        results = re.findall('customfield_\d{5}',element,flags=re.I)
        if len(results) > 1:
            writer.writerow([currentRule,currentComponent,'Manage Smart Values','Info','More than one result in smart values',str(element)])
        for field in results:
            newField = mapFieldFromId(field.lower())
            if newField:
                newElement = re.sub(field,newField,newElement)
        newElement = re.sub('lookupAssets','lookupObjects',newElement,flags=re.I)
        newElement = re.sub('webhookResponse','webResponse',newElement,flags=re.I)
        writer.writerow([currentRule,currentComponent,'Manage Smart Values','Info','After',str(newElement)])
        return newElement

    def manageJql(query):
        if 'issuefunction' in query.lower():
            writer.writerow([currentRule,currentComponent,'JQL','Problem','Contains Scriptrunner function',query])

        writer.writerow([currentRule,currentComponent,'JQL','Info','Query: Before',query])
        
        #Special field Customer Request Type
        newQuery = re.sub('''customer request type''','Request type',query,flags=re.I)
        
        #Projects
        projectRegex = '''(?=("?'?project"?'?\s*(?:!?=| (?:not )?in )\s*\(?((?:\s*"?'?\d{5}"?'?\s*,?)+)\)?))'''
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
        teamRegex = '''(?=("?'?(?:team|cf\[11700\])"?'?\s*(?:!?=| (?:not )?in )\s*\(?((?:\s*"?'?\d+"?'?\s*,?)+)\)?))'''
        teamClauses = []
        for d in re.findall(teamRegex,newQuery,flags=re.I):
            l = (d[0],d[1].split(','))
            newClause = d[0]
            i=0
            while i < len(l[1]):
                newClause = newClause.replace(''.join(filter(lambda str: str.isdigit(), l[1][i])),str(mapTeam(''.join(filter(lambda str: str.isdigit(), l[1][i])))))
                i = i+1
            teamClauses.append((d[0],newClause))
        for clause in teamClauses:
            newQuery = newQuery.replace(clause[0],clause[1])
        
        #Users
        #On ne prend pas en compte les clauses BY et CHANGED FROM ou TO username
        userClause = '|'.join([re.escape(d) for d in dcUserClauses])
        userRegex = f'''(?=("?'?(?:{userClause})"?'?\s*(?:!?=| was(?: not)?(?: in)? |(?: not)? in | changed )\s*(\([^\)]+\)|"?'?[^\s]+"?'?)))'''
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
     
        #Assets
        #Clause classique type "Owner Team" in (TEAM-124,TEAM-125), rarement présente
        assetClause = '|'.join([re.escape(d) for d in dcAssetClauses])
        assetClauses = []
        regexs = []
        assetRegexs = []

        #Regex pour le format in (TEAM-123,TEAM-456) ou in (TEAM-123), à faire en premier pour exclure le cas 2 qui va être transformé en cas 1
        assetRegexs.append(f'''(("?'?(?:{assetClause})"?'?)\s*((?: not)? in )\s*\(((?!\s*".*?"\s*,?)[^)]+)\))''')

        #Regex pour le format in ("C-logistics [Peaksys] (CUST-53)", "Prout (Team-123)") ou in ("C-logistics [Peaksys] (CUST-53)") ou in ("TEAM-453")
        assetRegexs.append(f'''(("?'?(?:{assetClause})"?'?)\s*((?: not)? in )\s*\(((?:\s*".*?"\s*,?)+)\))''') #Obligé de faire comme ça pour gérer les parenthèses

        #Regex pour le format = TEAM-123
        assetRegexs.append(f'''(("?'?(?:{assetClause})"?'?)\s*(!?=)\s*((?!".*?(?<!\\\)")[^ ]+))''')
            
        #Regex pour le format = "C-logistics [Peaksys] (CUST-53)"
        assetRegexs.append(f'''(("?'?(?:{assetClause})"?'?)\s*(!?=)\s*(".*?(?<!\\\)"))''')

        for assetRegex in assetRegexs:
            resa = re.findall(assetRegex,newQuery,flags=re.I)
            if resa:
                for res in resa:
                    regexs.append(res)

        for d in regexs:
            #Pour chaque clause, d[0] = totalité de la clause, d[1] = champ, d[2] = opérateur, d[3] = liste des refs
            newClause = d[0]
            l=d[3].split(',')
            i=0
            while i < len(l):
                assetKey = re.search('([a-zA-Z0-9]+-\d+)',l[i])
                if assetKey:
                    newAsset = mapAsset(assetKey.group(1))
                    newClause = newClause.replace(l[i],newAsset)
                i = i+1
            assetClauses.append((d[0],newClause))
            
        for clause in assetClauses:
            newQuery = newQuery.replace(clause[0],clause[1])

        #Regex générale
        assetRegexClass = f'''(("?'?(?:{assetClause})"?'?)\s*(!?=|(?: not)? in )\s*(\((?:[a-zA-Z0-9]+-\d+,?)+\)|[a-zA-Z0-9]+-\d+))'''

        newQuery = re.sub(assetRegexClass,r'\2 in aqlFunction("key\3\4")',newQuery)
        
        fieldClauses = []
        for id in re.findall('''cf\[(\d{5})\]''',newQuery):
            newField = mapFieldFromId('customfield_' + id)
            if newField:
                fieldClauses.append(('cf[' + id + ']',re.sub(r'customfield_(\d{5})',r'cf[\1]',newField)))
        #fieldClauses = [('cf[' + id + ']',re.sub('customfield_(\d{5})','cf[\1]',mapFieldFromId('customfield_' + id))) for id in re.findall('''cf\[(\d{5})\]''',newQuery)]
        for clause in fieldClauses:
            newQuery = newQuery.replace(clause[0],clause[1])   
            
        writer.writerow([currentRule,currentComponent,'JQL','Info','Query: After',newQuery])

        newQuery = manageSmartValues(newQuery)

        return newQuery
        #Cascadefield = id
        #Status = id
        #issuetype ou type = id
        #Versions : les champs sont limités

    def manageAql(query):
        writer.writerow([currentRule,currentComponent,'AQL','Info','Query: Before',query])
        
        newQuery = query
        
        #Key
        keyRegex = f'''key\s*(?:!?=| (?:not )?in | (?:not )?like )\s*\(?((?:\s*"?'?[a-zA-Z0-9]+-\d+"?'?\s*,?)+)\)?'''
        keyClauses = []
        for d in re.findall(keyRegex,newQuery,flags=re.I):
            l = (d[0],d[1].split(','))
            newClause = d[0]
            i=0
            while i < len(l[1]):
                newClause = newClause.replace(''.join(filter(lambda str: re.sub('''["'\s\(\)]''','',str), l[1][i])),str(mapAsset(''.join(filter(lambda str: re.sub('''["'\s\(\)]''','',str), l[1][i])))))
                i = i+1
            keyClauses.append((d[0],newClause))

        for clause in keyClauses:
            newQuery = newQuery.replace(clause[0],clause[1])
            
        #Object Types
        otRegex = '''(?=("?'?objectTypeId"?'?\s*(?:!?=| (?:not )?in )\s*\(?((?:\s*"?'?\d+"?'?\s*,?)+)\)?))'''
        otClauses = []
        for d in re.findall(otRegex,newQuery,flags=re.I):
            l = (d[0],d[1].split(','))
            newClause = d[0]
            i=0
            while i < len(l[1]):
                newClause = newClause.replace(''.join(filter(lambda str: str.isdigit(), l[1][i])),str(mapObjecttype(''.join(filter(lambda str: str.isdigit(), l[1][i])))))
                i = i+1
            otClauses.append((d[0],newClause))
        for clause in otClauses:
            newQuery = newQuery.replace(clause[0],clause[1])
        
        newQuery = manageSmartValues(newQuery)
            
        writer.writerow([currentRule,currentComponent,'AQL','Info','Query: After',newQuery])

        return newQuery
            
    def editFields(componentvalue):
        if componentvalue['operations']:
            for operation in componentvalue['operations']:
                if check(operation,'fieldId'):
                    if operation['fieldId'] == 'customfield_10002':
                        writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Problem','Request Type',str(operation)])
                    if check(operation,'value'):
                        if isinstance(operation['value'],str):
                            operation['value'] = manageSmartValues(operation['value'])
                            #writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Operation with String value',str(operation)])
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
                            elif operation['fieldId'] in dcAssetFields:
                                operation['fieldType'] = 'com.atlassian.jira.plugins.cmdb:cmdb-object-cftype'
                                newValue = ''
                                if isinstance(operation['value'],list):
                                    newValue = 'key in ('
                                    for value in operation['value']:
                                        newValue += mapAsset(value['value']) + ','
                                    newValue = newValue[:-1] + ')'                                    
                                elif isinstance(operation['value'],dict):
                                    newValue = 'key = ' + mapAsset(operation['value']['value'])
                                operation['value'] = newValue
                            elif operation['fieldId'] == 'project':
                                if operation['value']['type'] == 'ID':
                                    operation['value']['value'] = mapProject(operation['value']['value'])
#                                 else:
#                                     #C'est toujours COPY quand ce n'est pas SET, et il n'y a rien à faire
#                                     writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','SET Operation on project not ID',str(operation)])
                            elif operation['fieldId'] == 'issuetype':
                                if operation['value']['type'] == 'ID':
                                    operation['value']['value'] = mapIssuetype(operation['value']['value'])
#                                 else:
#                                     writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','SET Issue type on project not ID',str(operation)])
                            elif operation['fieldId'] == 'priority':
                                if operation['value']['type'] == 'ID':
                                    operation['value']['value'] = mapPriority(operation['value']['value'])
#                                 else:
#                                     writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','SET Priority on project not ID',str(operation)])
                            elif operation['fieldId'] == 'resolution':
                                if operation['value']['type'] == 'ID':
                                    operation['value']['value'] = mapResolution(operation['value']['value'])  
#                                 else:
#                                     writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','SET Resolution on project not ID',str(operation)])                                    
                            elif operation['fieldId'] == 'customfield_10008': #Sprint
                                writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Problem','Set sprint']) 
                            elif operation['fieldId'] == 'issuelinks':
                                match = re.search('\d{5}',operation['value']['linkType'])
                                if match:
                                    linkId = mapIssuelink(match.group(0))
                                    operation['value']['linkType'] = operation['value']['linkType'].replace(match.group(0),linkId)
#                         else:
#                             #Operation ADDREMOVE, seulement sur les labels, rien à faire
#                     else:
                          #C'est des choses qui arrivent, principalement quand on veut vider un champ 
#                         writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Operation without value',str(operation)])
                 
                    if 'customfield_' in operation['fieldId']:
                        operation['fieldId'] = mapFieldFromId(operation['fieldId'])   
                    #reste à faire : request type (10002) - remplacer par une action propre     
                else:
                    writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Problem','Operation without field',str(operation)])
        if check(componentvalue,'advancedFields'):
            writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Info','Advanced Fields: Before',str(componentvalue['advancedFields'])])
            for sm in re.findall('{{.*}}',componentvalue['advancedFields'],flags=re.I):
                newValue = re.sub(r'([^\\])"',r'\1\\"',sm)
                componentvalue['advancedFields'] = componentvalue['advancedFields'].replace(sm,newValue)
            try:
                advancedFields = json.loads(componentvalue['advancedFields'])
                for action in advancedFields.keys(): #update or fields
                    fields = advancedFields[action]
                    for key in fields:
                        if key.lower() in ['Team','team','customfield_11700']:
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
                        if key in dcAssetFields:
                            if action == 'update':
                                for operation in fields[key]:
                                    for operationAction in operation.keys():
                                       fields[key]['key'] = mapAsset(fields[key]['key'])
                            elif action == 'fields':
                                if isinstance(fields[key],list):
                                    for obj in fields[key]:
                                        obj['key'] = mapAsset(obj['key'])
                                elif isinstance(fields[key],dict):
                                    fields[key]['key'] = mapAsset(fields[key]['key'])        
                componentvalue['advancedFields'] = json.dumps(advancedFields)
                componentvalue['advancedFields'] = manageSmartValues(componentvalue['advancedFields'])
                #Resterait à gérer tous les éléments qui peuvent être définis par leur ID : options de champs select / mutli select, statut, etc.
            except ValueError as e:
                writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Error','Advanced Fields: impossible to decode JSON',str(e),str(componentvalue['advancedFields'])])
            writer.writerow([currentRule,currentComponent,'Edit issue (create, edit, clone)','Info','Advanced Fields: After',str(componentvalue['advancedFields'])])
                
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
            component['value']['comment'] = manageSmartValues(component['value']['comment'])
       
        
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
        #Pas Team : pas possible à sélectionner
        #Pas asset non plus
        writer.writerow([currentRule,currentComponent,'Issue field condition','Info','Before',str(component['value'])])
        if check(component['value'],'selectedField'):
            field = component['value']['selectedField']
            if field['type'] == 'ID':
                if check(component['value'],'compareValue'):
                    if check(component['value']['compareValue'],'type'):
                        if component['value']['compareValue']['type'] == 'FIELD':
                            component['value']['compareValue']['value'] = mapFieldFromId(component['value']['compareValue']['value'])
                        elif component['value']['compareValue']['type'] == 'ID':
                            try:
                                value = json.loads(str(component['value']['compareValue']['value']))
                                if field['value'] in dcUserFields:
                                    retour = []
                                    if isinstance(value,list):
                                        for user in value:
                                            retour.append(mapUser(user))
                                        component['value']['compareValue']['value'] = json.dumps(retour)
                                    else:
                                        component['value']['compareValue']['value'] = mapUser(component['value']['compareValue']['value'])
                                elif field['value'] == 'project':
                                    retour = []
                                    if isinstance(value,list):
                                        for project in value:
                                            retour.append(mapProject(project))
                                        component['value']['compareValue']['value'] = json.dumps(retour)
                                    else:
                                        component['value']['compareValue']['value'] = mapProject(component['value']['compareValue']['value'])
                                elif field['value'] == 'priority':
                                    retour = []
                                    if isinstance(value,list):
                                        for priority in value:
                                            retour.append(mapPriority(priority))
                                        component['value']['compareValue']['value'] = json.dumps(retour)
                                    else:
                                        component['value']['compareValue']['value'] = mapPriority(component['value']['compareValue']['value'])
                                elif field['value'] == 'status':
                                    retour = []
                                    if isinstance(value,list):
                                        for status in value:
                                            retour.append(mapStatus(status))
                                        component['value']['compareValue']['value'] = json.dumps(retour)
                                    else:
                                        component['value']['compareValue']['value'] = mapStatus(component['value']['compareValue']['value'])
                                elif field['value'] == 'issuetype':
                                    retour = []
                                    if isinstance(value,list):
                                        for issuetype in value:
                                            retour.append(mapIssuetype(issuetype))
                                        component['value']['compareValue']['value'] = json.dumps(retour)
                                    else:
                                        component['value']['compareValue']['value'] = mapIssuetype(component['value']['compareValue']['value'])
                                elif field['value'] == 'resolution':
                                    retour = []
                                    if isinstance(value,list):
                                        for resolution in value:
                                            retour.append(mapResolution(resolution))
                                        component['value']['compareValue']['value'] = json.dumps(retour)
                                    else:
                                        component['value']['compareValue']['value'] = mapResolution(component['value']['compareValue']['value'])
                                else:
                                    writer.writerow([currentRule,currentComponent,'Issue field condition','Problem','Unmanaged field','Field: ' + field['value'],'Compare value: ' + component['value']['compareValue']['value']])
                            except ValueError as e: #Pas au format json = string
                                if field['value'] in dcUserFields:
                                    component['value']['compareValue']['value'] = mapUser(component['value']['compareValue']['value'])
                                elif field['value'] == 'project':
                                    component['value']['compareValue']['value'] = mapProject(component['value']['compareValue']['value'])
                                elif field['value'] == 'priority':
                                    component['value']['compareValue']['value'] = mapPriority(component['value']['compareValue']['value'])
                                elif field['value'] == 'status':
                                    component['value']['compareValue']['value'] = mapStatus(component['value']['compareValue']['value'])
                                elif field['value'] == 'issuetype':
                                    component['value']['compareValue']['value'] = mapIssuetype(component['value']['compareValue']['value'])
                                elif field['value'] == 'resolution':
                                    component['value']['compareValue']['value'] = mapResolution(component['value']['compareValue']['value'])
                                else:
                                    writer.writerow([currentRule,currentComponent,'Issue field condition','Problem','Unmanaged field','Field: ' + field['value'],'Compare value: ' + component['value']['compareValue']['value']])
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
            print("Issue condition sans select field " + str(component['value']))
        writer.writerow([currentRule,currentComponent,'Issue field condition','Info','After',str(component['value'])])
            
                
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
        component['type'] = 'cmdb.lookup.objects'
        if check(component['value'],'assetKey'):
            aql = 'key = ' + manageSmartValues(mapAsset(component['value']['assetKey']))
        elif check(component['value'],'aql'):
            aql = manageAql(component['value']['aql'])
        else:
            writer.writerow([currentRule,currentComponent,'Lookup Objects','Problem','Lookup Objects without value',str(component['value'])])
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
#                         else: n'exise pas
#                             writer.writerow([currentRule,currentComponent,'Set entity property','User - Type nor ID not SMART',str(value)])
                value['key'] = manageSmartValues(value['key'])
                value['value'] = manageSmartValues(value['value'])

    def jiraissueoutgoingwebhook(component):
        writer.writerow([currentRule,currentComponent,'Send web request','Info','Before',str(component['value'])])
        if not 'http' in component['value']['url']:
            writer.writerow([currentRule,currentComponent,'Send web request','Problem','URL is a secret',str(component['value']['url'])])
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
        writer.writerow([currentRule,currentComponent,'Send web request','Info','After',str(component['value'])])
        
    def jiraissuerelated(component):
        if component['value']['relatedType'] == 'jql':
            component['value']['jql'] = manageJql(component['value']['jql'])

    def jiraissuecreate(component):
        editFields(component['value'])

    def jiraissueeventtriggertransitioned(component):
        if component['value']['eventKey'] != 'jira:issue_updated':
            writer.writerow([currentRule,currentComponent,'Issue Transitioned','Problem','Event key different than issue updated',component['value']['eventKey']])
        if component['value']['issueEvent'] != 'issue_generic':
            writer.writerow([currentRule,currentComponent,'Issue Transitioned','Problem','Issue event different than issue generic',component['value']['eventKey']])
        if component['value']['fromStatus']:
            for fromStatus in component['value']['fromStatus']:
                if fromStatus['type'] != 'ID':
                    writer.writerow([currentRule,currentComponent,'Issue Transitioned','Problem','FromStatus type different than ID',fromStatus['type']])
                else:
                    fromStatus['value'] = mapStatus(fromStatus['value'])
        if component['value']['toStatus']:
            for toStatus in component['value']['toStatus']:
                if toStatus['type'] != 'ID':
                    writer.writerow([currentRule,currentComponent,'Issue Transitioned','Problem','ToStatus type different than ID',toStatus['type']])
                else:
                    toStatus['value'] = mapStatus(toStatus['value'])

    def jiraissueeventtriggercommented(component):
        return

    def jiraissueeventtriggerupdated(component):
        return

    def msteamsnotification(component):
        writer.writerow([currentRule,currentComponent,'Send Teams notification','Info','Before',str(component['value'])])
        if not 'http' in component['value']['webhookUrl']['key']:
            writer.writerow([currentRule,currentComponent,'Send Teams notification','Problem','URL is a secret',str(component['value']['webhookUrl']['key'])])
        
        if check(component['value'],'title'):
            component['value']['title'] = manageSmartValues(component['value']['title'])
        if check(component['value'],'body'):
            component['value']['body'] = manageSmartValues(component['value']['body'])
        component['value']['webhookUrl'] = component['value']['webhookUrl']['key']
        writer.writerow([currentRule,currentComponent,'Send Teams notification','Info','After',str(component['value'])])


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
        writer.writerow([currentRule,currentComponent,'Publish event','Info','Removed component',str(component)])
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
        i = 0
        for event in component['value']['events']:
            if event['event'] in ['issue_resolved','issue_reopened','issue_closed']:
                writer.writerow([currentRule,currentComponent,'Multiple Issue Event','Problem','Unmanaged event',event['event']])
            elif event['event'] in ['issue_commented','issue_comment_edited']:
                rules.insert(len(rules),copy.deepcopy(rule))
                rules[-1]['id'] = generateId(rules[-1]['id'])
                rules[-1]['name'] = 'Copy of ' + rules[-1]['name'] + ' (comment)'
                if event['event'] == 'issue_commented':
                    rules[-1]['trigger'] = {"id":generateId(rules[-1]['trigger']['id']),"component":"TRIGGER","schemaVersion":1,"type":"jira.issue.event.trigger:commented","value":{"synchronous":False,"eventKey":"jira:issue_updated","issueEvent":"issue_commented"},"children":[],"conditions":[],"optimisedIds":[],"newComponent":False}
                elif event['event'] == 'issue_comment_edited':
                    rules[-1]['trigger'] = {"id":generateId(rules[-1]['trigger']['id']),"component":"TRIGGER","schemaVersion":1,"type":"jira.issue.comment.event.trigger:updated","value":{"synchronous":False,"eventKey":"jira:issue_updated","issueEvent":"issue_comment_updated"},"children":[],"conditions":[],"optimisedIds":[],"newComponent":False}
                component['value']['events'].pop(i)
            i = i + 1

    def jiraissuearchive(component):
        global parentComponent
        writer.writerow([currentRule,currentComponent,'Archive issue','Info','Removed component',str(component)])
        i = 0
        for childComponent in parentComponent:
            if childComponent['id'] == component['id']:
                parentComponent.pop(i)
            i = i + 1

    def jiracomparatorcondition(component):
        #A convertir dans la deuxième valeur (pas utile pour CDiscount) :
        #Assets
        #Sprint
        #Teams
        writer.writerow([currentRule,currentComponent,'Advanced compare condition','Info','First element: before',component['value']['first']])
        component['value']['first'] = manageSmartValues(component['value']['first'])
        writer.writerow([currentRule,currentComponent,'Advanced compare condition','Info','First element: after',component['value']['first']])

        writer.writerow([currentRule,currentComponent,'Advanced compare condition','Info','Second element: before',component['value']['second']])
        component['value']['second'] = manageSmartValues(component['value']['second'])
        writer.writerow([currentRule,currentComponent,'Advanced compare condition','Info','Second element: after',component['value']['second']])
        
        #Cas de la règle 4781 - SU - repassage en ouvert d'un ticket mis en attente suite a un commentaire d'une personne et suppression du responsable
        #{{issue.comments.last.author.displayName}} = svc.jira
        
    def jiraissueeventtriggerassigned(component):
        return

    def jirasprinteventtriggerstarted(component):
        component['value']['boardId'] = mapBoard(component['value']['boardId'])

    def jiraworklogadd(component):
        if check(component['value'],'timeSpent'):
            component['value']['timeSpent'] = manageSmartValues(component['value']['timeSpent'])
        if check(component['value'],'dateStarted'):
            if check(component['value']['dateStarted'],'value'):
                component['value']['dateStarted']['value'] = manageSmartValues(component['value']['dateStarted']['value'])

    def comonresolvejiragroovygroovyrunnerexecutescriptissueactionv2(component):
        global parentComponent
        writer.writerow([currentRule,currentComponent,'Scriptrunner Execute Script V2','Info','Removed component',str(component)])
        i = 0
        for childComponent in parentComponent:
            if childComponent['id'] == component['id']:
                parentComponent.pop(i)
            i = i + 1

    def jiraissuecreatesubtasks(component):
        if check(component['value'],'subtasks'):
            for subtask in component['value']['subtasks']:
                subtask['type'] = mapIssuetype(subtask['type'])
                subtask['summary'] = manageSmartValues(subtask['summary'])

    def jiraissuedelete(component):
        return

    def jirasprinteventtriggerclosed(component):
        component['value']['boardId'] = mapBoard(component['value']['boardId'])

    def jiralookupissues(component):
        if check(component['value'],'query'):
            if check(component['value']['query'],'value'):
                component['value']['query']['value'] = manageJql(component['value']['query']['value'])
            else:
                writer.writerow([currentRule,currentComponent,'Lookup issues','Problem','Query without value',str(component['value'])])
        else:
            writer.writerow([currentRule,currentComponent,'Lookup issues','Problem','Component without query',str(component['value'])])

    def jiracreatevariable(component):
        if check(component['value'],'name'):
            if check (component['value']['name'],'value'):
                component['value']['name']['value'] = manageSmartValues(component['value']['name']['value'])
            else:
                writer.writerow([currentRule,currentComponent,'Create variable','Problem','Name without value',str(component['value'])])
        else:
            writer.writerow([currentRule,currentComponent,'Create variable','Problem','Action without name',str(component['value'])])
        if check(component['value'],'query'):
            if check(component['value']['query'],'value'):
                component['value']['query']['value'] = manageSmartValues(component['value']['query']['value'])
            else:
                writer.writerow([currentRule,currentComponent,'Create variable','Problem','Query without value',str(component['value'])])
        else:
            writer.writerow([currentRule,currentComponent,'Create variable','Problem','Action without query',str(component['value'])])

    def jiraslathresholdtrigger(component):
        if check(component['value'],'customFieldId'):
            component['value']['customFieldId'] = mapFieldFromId(component['value']['customFieldId'])
        
    def comonresolvejiragroovygroovyrunnerexecutescriptissueaction(component):
        global parentComponent
        writer.writerow([currentRule,currentComponent,'Scriptrunner Execute Script Legacy','Info','Removed component',str(component)])
        i = 0
        for childComponent in parentComponent:
            if childComponent['id'] == component['id']:
                parentComponent.pop(i)
            i = i + 1
        
    def jiraissueeventtriggerlinkdeleted(component):
        return

    def slacknotification(component):
        writer.writerow([currentRule,currentComponent,'Slack','Info','Before',str(component['value'])])
        if check(component['value'],'channel'):
            component['value']['channel'] = manageSmartValues(component['value']['channel'])
        if check(component['value'],'body'):
            component['value']['body'] = manageSmartValues(component['value']['body'])
        component['value']['webhookUrl'] = component['value']['webhookUrl']['key']
        writer.writerow([currentRule,currentComponent,'Slack','Info','After',str(component['value'])])
        
    def jiraissuehasAttachments(component):
        return

    def jiraissueeventtriggerdeleted(component):
        return

    def jiraissuecommenteventtriggerupdated(component):
        return

    functions = {'jira.jql.scheduled':jirajqlscheduled,'jira.condition.container.block':jiraconditioncontainerblock,'jira.condition.if.block':jiraconditionifblock,'jira.issue.comment':jiraissuecomment,'jira.issue.transition':jiraissuetransition,'jira.issue.edit':jiraissueedit,'jira.issue.field.changed':jiraissuefieldchanged,'jira.issue.condition':jiraissuecondition,'jira.issue.clone':jiraissueclone,'jira.manual.trigger.issue':jiramanualtriggerissue,'jira.issue.assign':jiraissueassign,'jira.issue.refresh.issue':jiraissuerefreshissue,'jira.issue.event.trigger:created':jiraissueeventtriggercreated,'jira.issue.event.trigger:moved':jiraissueeventtriggermoved,'jira.user.condition':jirausercondition,'jira.issue.outgoing.email':jiraissueoutgoingemail,'jira.jql.condition':jirajqlcondition,'codebarrel.action.log':codebarrelactionlog,'com.onresolve.jira.groovy.groovyrunner:lookup-object-beans':comonresolvejiragroovygroovyrunnerlookupobjectbeans,'jira.set.entity.property':jirasetentityproperty,'jira.issue.outgoing.webhook':jiraissueoutgoingwebhook,'jira.issue.related':jiraissuerelated,'jira.issue.create':jiraissuecreate,'jira.issue.event.trigger:transitioned':jiraissueeventtriggertransitioned,'jira.issue.event.trigger:commented':jiraissueeventtriggercommented,'jira.issue.event.trigger:updated':jiraissueeventtriggerupdated,'msteams.notification':msteamsnotification,'automation.trigger.service.limit':automationtriggerservicelimit,'jira.issue.add.watcher':jiraissueaddwatcher,'jira.issues.related.condition':jiraissuesrelatedcondition,'jira.issue.event.trigger:link':jiraissueeventtriggerlink,'jira.sd.add.customer':jirasdaddcustomer,'jira.publish.event':jirapublishevent,'jira.issue.link':jiraissuelink,'jira.multiple.issue.event':jiramultipleissueevent,'jira.issue.archive':jiraissuearchive,'jira.comparator.condition':jiracomparatorcondition,'jira.issue.event.trigger:assigned':jiraissueeventtriggerassigned,'jira.sprint.event.trigger:started':jirasprinteventtriggerstarted,'jira.worklog.add':jiraworklogadd,'com.onresolve.jira.groovy.groovyrunner:execute-script-issue-action-v2':comonresolvejiragroovygroovyrunnerexecutescriptissueactionv2,'jira.issue.create.subtasks':jiraissuecreatesubtasks,'jira.issue.delete':jiraissuedelete,'jira.sprint.event.trigger:closed':jirasprinteventtriggerclosed,'jira.lookup.issues':jiralookupissues,'jira.create.variable':jiracreatevariable,'jira.sla.threshold.trigger':jiraslathresholdtrigger,'com.onresolve.jira.groovy.groovyrunner:execute-script-issue-action':comonresolvejiragroovygroovyrunnerexecutescriptissueaction,'jira.issue.event.trigger:link_deleted':jiraissueeventtriggerlinkdeleted,'slack.notification':slacknotification,'jira.issue.hasAttachments':jiraissuehasAttachments,'jira.issue.event.trigger:deleted':jiraissueeventtriggerdeleted, 'jira.issue.comment.event.trigger:updated':jiraissuecommenteventtriggerupdated}
                        
    def convert(components):
        global currentComponent
        global parentComponent
        for component in components:
            parentComponent = components
            if "type" in component and "component" in component:
                currentComponent = component["component"] + ' ' + component["type"]
                    
                #Champs particuliers
                results = functions[component['type']](component)
            else:
                writer.writerow([currentRule,currentComponent,'Convert','Problem','Component exists but it has no type or subtype'])

            if "children" in component:
                if component["children"]:
                    convert(component["children"])

    with open(inputPath,encoding='utf-8') as f:
        file = json.load(f)
        rules = file['rules']
        rules = [d for d in rules if d['state'] == 'ENABLED']
        
        id = 1
        for rule in rules:
            currentRule = str(rule['id']) + ' - ' + rule['name']
            
            #On fait le trigger en premier parce qu'il peut avoir pour effet de copier la règle existante, et dans ce cas il ne faut pas copier la version convertie du Owner et des projets
            currentComponent = 'TRIGGER - ' + rule['trigger']['type']
            functions[rule['trigger']['type']](rule['trigger'])
            
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
            
            convert(rule['components'])
            id = id + 1
            
            # Si besoin de recréer une règle, le faire ici après toutes les modifs (modifier multipleissueevent)
            # Ou alors avant ? En fonction de quand on fait la copie, en tout cas faut pas faire la copie au milieu
            # Autre possibilité : une fonction de publication à la fin de toutes les modifs
        
        newFile = {"rules":rules,"cloud": False}
        with open(outputPath, 'w', encoding='utf-8') as f2:
            json.dump(newFile, f2)
            


