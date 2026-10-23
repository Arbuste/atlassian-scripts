from Utilities.Utilities import Utilities
from requests.auth import HTTPBasicAuth
import csv
import os
import time
from datetime import datetime, timezone
import http.client as http_client

class OrgEnvironment:
    def __init__(self,orgId,token,folder=os.getcwd()):
        self.baseUrl = 'https://api.atlassian.com'
        self.orgId = orgId
        self.token = token
        self.log = open(folder + r'\JiraLogs.csv', 'w', newline='', encoding='utf-8')
        self.logger = csv.writer(self.log, delimiter=',',quotechar='"')
        self.logger.writerow(['Timestamp','Request Payload','Response Status Code','Response Headers','Response Body'])
        self.retryAfter = 10

    def get(self,uri,headers=None,params=None):
        headers = headers or {}
        headers['Authorization'] = 'Bearer ' + self.token
        resp = Utilities.get(self.baseUrl + uri,params=params,headers=headers)
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

    def post(self,uri,headers=None,params=None,json=None,baseUrl=''):
        headers = headers or {}
        headers['Authorization'] = 'Bearer ' + self.token
        if baseUrl:
            resp = Utilities.post(baseUrl + uri,params=params,headers=headers,json=json)
        else:
            resp = Utilities.post(self.baseUrl + uri,params=params,headers=headers,json=json)
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
    
    def put(self,uri,headers=None,params=None,json=None,baseUrl=''):
        headers = headers or {}
        headers['Authorization'] = 'Bearer ' + self.token
        if baseUrl:
            resp = Utilities.put(baseUrl + uri,params=params,headers=headers,json=json)
        else:
            resp = Utilities.put(self.baseUrl + uri,params=params,headers=headers,json=json)
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
    
    def delete(self,uri,headers=None,params=None):
        headers = headers or {}
        headers['Authorization'] = 'Bearer ' + self.token
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
    
    def getAllPaginated(self,uri,params={}):
        cursor = None
        isLast = False
        res = []
        while not isLast:
            if cursor:
                params['cursor'] = cursor
            req = self.get(uri,params=params)
            if req['isReqSuccess']:
                res = res + req['data']
                isLast = True
                if 'links' in req:
                    if 'next' in req['links']:
                        if req['links']['next']:
                            isLast = False
                            cursor = req['links']['next']
            else:
                break
        return res

    def getGroups(self,groupIds=[]):
        return self.getAllPaginated('/admin/v2/' + self.orgId + '/directories/-/groups')
    
    def activateAccount(self,accountId):
        return self.post(uri='/users/' + accountId + '/manage/lifecycle/enable')
    
    def deactivateAccount(self,accountId):
        return self.post(uri='/users/' + accountId + '/manage/lifecycle/disable',headers={'Content-Type': 'application/json'})

    def deleteAccount(self,accountId):
        return self.post(uri='/users/' + accountId + '/manage/lifecycle/delete')

    def getUser(self,accountId):
        return self.get(uri='/users/' + accountId + '/manage/profile')
                        
    def setEmail(self,accountId,newEmail):
        json = {"email": newEmail}
        return self.put(uri='/users/' + accountId + '/manage/email',json=json)