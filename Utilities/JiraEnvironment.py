from Utilities.Utilities import Utilities
from requests.auth import HTTPBasicAuth
import csv
import os
import time
from datetime import datetime, timezone

class JiraEnvironment:
    def __init__(self,baseUrl,user,token,folder=os.getcwd()):
        self.basic = HTTPBasicAuth(user, token)
        self.baseUrl = baseUrl
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log = open(folder + r'\JiraLogs ' + timestamp + '.csv', 'w', newline='', encoding='utf-8')
        self.logger = csv.writer(self.log, delimiter=',',quotechar='"')
        self.logger.writerow(['Timestamp','Request Payload','Response Status Code','Response Headers','Response Body'])
        self.retryAfter = 10

    def get(self,uri,headers=None,params=None):
        resp = Utilities.get(self.baseUrl + uri,auth=self.basic,params=params,headers=headers)
        self.logger.writerow([datetime.now(timezone.utc),resp['requestPayload'],resp['responseStatusCode'],resp['responseHeaders'],resp['responseBody']])
        if resp['responseStatusCode'] == 429:
            if 'Retry-After' in resp['responseHeaders'].keys:
                try:
                    self.retryAfter = int(resp['responseHeaders']['Retry-After'])
                except:
                    self.retryAfter += self.retryAfter
            elif 'X-RateLimit-Reset' in resp['responseHeaders'].keys:
                try:
                    limitDate = datetime.strptime(resp['responseHeaders']['X-RateLimit-Reset'], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    self.retryAfter = (limitDate - now).total_seconds()
                except:
                    self.retryAfter += self.retryAfter
            else:
                self.retryAfter += self.retryAfter
            time.sleep(self.retryAfter)
            res = self.get(self,uri,headers,params)
        else:
            res = {'isReqSuccess': resp['isReqSuccess']}
            if resp['responseBody']:
                if isinstance(resp['responseBody'],dict):
                    res |= resp['responseBody']
                elif isinstance(resp['responseBody'],list):
                    res["values"] = resp['responseBody']
        return res

    def post(self,uri,headers=None,params=None,json=None):
        resp = Utilities.post(self.baseUrl + uri,auth=self.basic,params=params,headers=headers,json=json)
        self.logger.writerow([datetime.now(timezone.utc),resp['requestPayload'],resp['responseStatusCode'],resp['responseHeaders'],resp['responseBody']])
        if resp['responseStatusCode'] == 429:
            if 'Retry-After' in resp['responseHeaders'].keys:
                try:
                    self.retryAfter = int(resp['responseHeaders']['Retry-After'])
                except:
                    self.retryAfter += self.retryAfter
            elif 'X-RateLimit-Reset' in resp['responseHeaders'].keys:
                try:
                    limitDate = datetime.strptime(resp['responseHeaders']['X-RateLimit-Reset'], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    self.retryAfter = (limitDate - now).total_seconds()
                except:
                    self.retryAfter += self.retryAfter
            else:
                self.retryAfter += self.retryAfter
            time.sleep(self.retryAfter)
            res = self.post(self,uri,json,headers,params,json)
        else:
            res = {'isReqSuccess': resp['isReqSuccess']}
            if resp['responseBody']:
                if isinstance(resp['responseBody'],dict):
                    res |= resp['responseBody']
                elif isinstance(resp['responseBody'],list):
                    res['values'] = resp['responseBody']
        return res
    
    def put(self,uri,headers=None,params=None,json=None):
        resp = Utilities.put(self.baseUrl + uri,auth=self.basic,params=params,headers=headers,json=json)
        self.logger.writerow([datetime.now(timezone.utc),resp['requestPayload'],resp['responseStatusCode'],resp['responseHeaders'],resp['responseBody']])
        if resp['responseStatusCode'] == 429:
            if 'Retry-After' in resp['responseHeaders'].keys:
                try:
                    self.retryAfter = int(resp['responseHeaders']['Retry-After'])
                except:
                    self.retryAfter += self.retryAfter
            elif 'X-RateLimit-Reset' in resp['responseHeaders'].keys:
                try:
                    limitDate = datetime.strptime(resp['responseHeaders']['X-RateLimit-Reset'], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    self.retryAfter = (limitDate - now).total_seconds()
                except:
                    self.retryAfter += self.retryAfter
            else:
                self.retryAfter += self.retryAfter
            time.sleep(self.retryAfter)
            res = self.put(self,uri,json,headers,params,json)
        else:
            res = {'isReqSuccess': resp['isReqSuccess']}
            if resp['responseBody']:
                if isinstance(resp['responseBody'],dict):
                    res |= resp['responseBody']
                elif isinstance(resp['responseBody'],list):
                    res['values'] = resp['responseBody']
        return res
    
    def delete(self,uri,headers=None,params=None):
        resp = Utilities.delete(self.baseUrl + uri,auth=self.basic,params=params,headers=headers)
        self.logger.writerow([datetime.now(timezone.utc),resp['requestPayload'],resp['responseStatusCode'],resp['responseHeaders'],resp['responseBody']])
        if resp['responseStatusCode'] == 429:
            if 'Retry-After' in resp['responseHeaders'].keys:
                try:
                    self.retryAfter = int(resp['responseHeaders']['Retry-After'])
                except:
                    self.retryAfter += self.retryAfter
            elif 'X-RateLimit-Reset' in resp['responseHeaders'].keys:
                try:
                    limitDate = datetime.strptime(resp['responseHeaders']['X-RateLimit-Reset'], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    self.retryAfter = (limitDate - now).total_seconds()
                except:
                    self.retryAfter += self.retryAfter
            else:
                self.retryAfter += self.retryAfter
            time.sleep(self.retryAfter)
            res = self.delete(self,uri,headers,params)
        else:
            res = {'isReqSuccess': resp['isReqSuccess']}
            if resp['responseBody']:
                if isinstance(resp['responseBody'],dict):
                    res |= resp['responseBody']
                elif isinstance(resp['responseBody'],list):
                    res["values"] = resp['responseBody']
        return res
    
    def getAllPaginatedClassic(self,uri,params={}):
        startAt = 0
        maxResults = 1000
        isLast = False
        res = []
        while not isLast:
            params['startAt'] = str(startAt)
            params['maxResults'] = str(maxResults)
            req = self.get(uri,params=params)
            if req['isReqSuccess']:
                res = res + req['values']
                isLast = req['isLast']
                startAt = startAt + req['maxResults']
            else:
                break
        return res
    
    def getLastIssue(self,projectKey):
        jql = 'project = ' + projectKey + ' order by created desc'
        params = {'jql': jql, 'maxResults': 1, 'fields': '*all'}
        req = self.get('/rest/api/3/search/jql',params=params)
        if req['isReqSuccess']:
            if len(req['issues']) > 0:
                return req['issues'][0]
        return None
    
    def getProjects(self,status='live'):
        return self.getAllPaginatedClassic('/rest/api/3/project/search',{'status':status})
    
    def getWorkflows(self,isActive=True):
        return self.getAllPaginatedClassic('/rest/api/3/workflows/search', {'isActive': str(isActive)})
    
    def getPermissionSchemes(self,params={}):
        permissionSchemesObject = self.get('/rest/api/3/permissionscheme',params=params)
        if permissionSchemesObject['isReqSuccess'] and 'permissionSchemes' in permissionSchemesObject:
            return permissionSchemesObject['permissionSchemes']
        else:
            return []
    
    def getIssueTypeSchemes(self,params={}):
        return self.getAllPaginatedClassic('/rest/api/3/issuetypescheme',params=params)
    
    def getProjectPermissionScheme(self,projectId,params={}):
        return self.get('/rest/api/3/project/' + projectId + '/permissionscheme',params=params)

    def grantBrowsePermission(self,accountId,schemeId):
        body = {
            'holder': {
                'type': 'user',
                'parameter': accountId
            },
            'permission': 'BROWSE_PROJECTS'
        }
        return self.post('/rest/api/3/permissionscheme/' + str(schemeId) + '/permission',json=body)
    
    def deletePermission(self,schemeId,permissionId):
        return self.delete('/rest/api/3/permissionscheme/' + str(schemeId) + '/permission/' + str(permissionId))
    
    def getProjectsInWorkflow(self,workflowId):
        maxResults = 200
        uri = '/rest/api/3/workflow/' + workflowId + '/projectUsages'
        res = []
        params = {'maxResults':str(maxResults),'nextPageToken':''}
        req = self.get(uri,params=params)
        if req['isReqSuccess']:
            res += req['projects']['values']
            if 'nextPageToken' in req['projects']:
                params['nextPageToken']=req['projects']['nextPageToken']
            while params['nextPageToken']:
                req = self.get(uri,params=params)
                if req['isReqSuccess']:
                    res += req['projects']['values']
                    if 'nextPageToken' in req['projects']:
                        params['nextPageToken']=req['projects']['nextPageToken']
        return res
    
    def getAllStatuses(self):
        return self.get('/rest/api/3/status')['values']

    def getStatusesFromProject(self,projectIdOrKey):
        req = self.get('/rest/api/3/project/' + projectIdOrKey + '/statuses')
        if req['isReqSuccess']:
            return req['values']
        else:
            return []

    def countIssues(self,jql):
        countReq = self.post('/rest/api/3/search/approximate-count',json={'jql': jql})
        if countReq['isReqSuccess']:
            return countReq['count']
        else:
            return 0
    
    def getBoards(self):
        return self.getAllPaginatedClassic('/rest/agile/latest/board/')
    
    def getBoardConfiguration(self,boardId):
        return self.get('/rest/agile/1.0/board/' + str(boardId) + '/configuration')
    
    def getAllProjectRoles(self):
        req = self.get('/rest/api/3/role')
        if req['isReqSuccess']:
            return req['values']
        else:
            return []
    
    def getAllSecuritySchemes(self):
        req = self.get('/rest/api/3/issuesecurityschemes')
        if req['isReqSuccess']:
            return req['issueSecuritySchemes']
        else:
            return []
    
    def getAllSecurityLevels(self):
        return self.getAllPaginatedClassic('/rest/api/3/issuesecurityschemes/level')
    
    def getSecurityMembersByLevels(self,levelIds):
        return self.getAllPaginatedClassic('/rest/api/3/issuesecurityschemes/level/member',params={'levelId': levelIds})
    
    def deleteSecurityLevelMember(self,schemeId,levelId,memberId):
        return self.delete('/rest/api/3/issuesecurityschemes/' + str(schemeId) + '/level/' + str(levelId) + '/member/' + str(memberId))
    
    def getAllFieldConfigurations(self):
        return self.getAllPaginatedClassic('/rest/api/3/fieldconfiguration')
    
    def getAllFields(self):
        req = self.get('/rest/api/3/field')
        if req['isReqSuccess']:
            return req['values']
        else:
            return []
        
    def getConfigurationFields(self,configurationId):
        return self.getAllPaginatedClassic('/rest/api/3/fieldconfiguration/' + str(configurationId) + '/fields' )
    
    def addFieldsToFieldConfiguration(self,configurationId,fieldIds):
        req = {"fieldConfigurationItems": [{"id": fieldId, "isHidden": False} for fieldId in fieldIds]}
        return self.put('/rest/api/3/fieldconfiguration/' + str(configurationId) + '/fields',json=req)
    
    def hideFieldsInFieldConfiguration(self,configurationId,fieldIds):
        req = {"fieldConfigurationItems": [{"id": fieldId, "isHidden": True} for fieldId in fieldIds]}
        return self.put('/rest/api/3/fieldconfiguration/' + str(configurationId) + '/fields',json=req)