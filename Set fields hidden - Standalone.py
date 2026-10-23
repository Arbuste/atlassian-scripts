import requests
import math
import json
from requests.auth import HTTPBasicAuth
from environment_config import get_environment
from requests.adapters import HTTPAdapter, Retry
import csv
import os
import time
from datetime import datetime, timezone

class SafeDict(dict):
    def __getitem__(self, key):
        val = super().get(key, False)
        return val if val else False

class Utilities:
    @staticmethod
    def get(url,auth=None,params=None,headers=None):
        resp = {'isReqSuccess': False, 'requestPayload': '','responseStatusCode': '','responseHeaders': {},'responseBody': {}}
        preReq = requests.Request('GET',url,auth=auth,params=params,headers=headers)
        prepared = preReq.prepare()
        resp['requestPayload'] = prepared.method + ' ' + prepared.url + ' | ' + ','.join('{}: {}'.format(k, v) for k, v in prepared.headers.items())
        s = requests.session()
        retries = Retry(total=5,
                backoff_factor=0.1,
                status_forcelist=[ 500, 502, 503, 504 ])
        s.mount('https://', HTTPAdapter(max_retries=retries))
        req = s.send(prepared)
        resp['responseStatusCode'] = req.status_code
        resp['responseHeaders'] = req.headers
        if math.floor(req.status_code/100) == 2:
            resp['isReqSuccess'] = True
        try:
            resp['responseBody'] = req.json()
        except:
            pass

        return resp

    @staticmethod
    def post(url,auth=None,params=None,headers=None,json=None):
        resp = {'isReqSuccess': False, 'requestPayload': '','responseStatusCode': '','responseHeaders': {},'responseBody': {}}
        preReq = requests.Request('POST',url,auth=auth,params=params,headers=headers,json=json)
        prepared = preReq.prepare()
        resp['requestPayload'] = '{} | {}'.format(prepared.method + ' ' + prepared.url + ' | ' + ','.join('{}: {}'.format(k, v) for k, v in prepared.headers.items()), prepared.body)
        s = requests.session()
        retries = Retry(total=5,
                backoff_factor=0.1,
                status_forcelist=[ 500, 502, 503, 504 ])
        s.mount('https://', HTTPAdapter(max_retries=retries))
        req = s.send(prepared)
        resp['responseStatusCode'] = req.status_code
        resp['responseHeaders'] = req.headers
        if math.floor(req.status_code/100) == 2:
            resp['isReqSuccess'] = True
        try:
            resp['responseBody'] = req.json()
        except:
            pass    

        return resp

    @staticmethod
    def put(url,auth=None,params=None,headers=None,json=None):
        resp = {'isReqSuccess': False, 'requestPayload': '','responseStatusCode': '','responseHeaders': {},'responseBody': {}}
        preReq = requests.Request('PUT',url,auth=auth,params=params,headers=headers,json=json)
        prepared = preReq.prepare()
        resp['requestPayload'] = '{} | {}'.format(prepared.method + ' ' + prepared.url + ' | ' + ','.join('{}: {}'.format(k, v) for k, v in prepared.headers.items()), prepared.body)
        s = requests.session()
        retries = Retry(total=5,
                backoff_factor=0.1,
                status_forcelist=[ 500, 502, 503, 504 ])
        s.mount('https://', HTTPAdapter(max_retries=retries))
        req = s.send(prepared)
        resp['responseStatusCode'] = req.status_code
        resp['responseHeaders'] = req.headers
        if math.floor(req.status_code/100) == 2:
            resp['isReqSuccess'] = True
        try:
            resp['responseBody'] = req.json()
        except:
            pass    

        return resp
    
    @staticmethod
    def delete(url,auth=None,params=None,headers=None):
        resp = {'isReqSuccess': False, 'requestPayload': '','responseStatusCode': '','responseHeaders': {},'responseBody': {}}
        preReq = requests.Request('DELETE',url,auth=auth,params=params,headers=headers)
        prepared = preReq.prepare()
        resp['requestPayload'] = prepared.method + ' ' + prepared.url + ' | ' + ','.join('{}: {}'.format(k, v) for k, v in prepared.headers.items())
        s = requests.session()
        retries = Retry(total=5,
                backoff_factor=0.1,
                status_forcelist=[ 500, 502, 503, 504 ])
        s.mount('https://', HTTPAdapter(max_retries=retries))
        req = s.send(prepared)
        resp['responseStatusCode'] = req.status_code
        resp['responseHeaders'] = req.headers
        if math.floor(req.status_code/100) == 2:
            resp['isReqSuccess'] = True
        try:
            resp['responseBody'] = req.json()
        except:
            pass

        return resp

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

environment = get_environment("open_groupe_sandbox")
baseUrl = environment["jira_base_url"]
user = environment["username"]
token = environment["user_token"]
PATH_TO_FOLDER = r'' #Mets le chemin du dossier où se trouve le fichier "Fields to Hide.csv" au format Windows, par exemple : r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files'
PATH_TO_INPUT_FILE = os.path.join(PATH_TO_FOLDER, 'Fields to Hide.csv') #Le nom du fichier avec les champs à cacher
PATH_TO_LOG_FILE = os.path.join(PATH_TO_FOLDER, 'Hide Fields - Logs 2.csv') #Le nom du fichier de logs pour voir s'il y a eu des erreurs

env = JiraEnvironment(baseUrl,user,token,PATH_TO_FOLDER)

with open(PATH_TO_INPUT_FILE, mode='r', newline='') as inFile, \
    open(PATH_TO_LOG_FILE, mode='w', newline='') as outFile:
    reader = csv.DictReader(inFile, delimiter=',', quotechar='"')
    fieldsToHide = list(reader)
    writer = csv.writer(outFile, delimiter=',', quotechar='"')

    fields = env.getAllFields()
    fieldsDict = {field['name']: field['id'] for field in fields}

    fieldConfigurations = env.getAllFieldConfigurations()
    fieldConfigurationsDict = {config['name']: config['id'] for config in fieldConfigurations}

    from collections import defaultdict

    grouped = defaultdict(list)
    for fieldConf in set(field['name'] for field in fieldsToHide):
        if fieldConf in fieldConfigurationsDict.keys():
            grouped[fieldConf] = {'id': fieldConfigurationsDict[fieldConf],'fields': []}
            for item in [field for field in fieldsToHide if field['name'] == fieldConf]:
                if item['cfname'] != '':
                    if item['cfname'] in fieldsDict.keys():
                        grouped[fieldConf]['fields'].append(fieldsDict[item['cfname']])
                    else:
                        writer.writerow(["Warning","Mapping","Field",str(item['cfname']),"Not found in Jira Cloud - skipping"])
                else:
                    grouped[fieldConf]['fields'].append(item['fieldidentifier'])
        else:
            writer.writerow(["Warning","Mapping","Field Configuration",str(fieldConf),"Not found in Jira Cloud - skipping"])

    # Convert to regular dict if needed
    grouped = dict(grouped)
    
    for fieldConf in grouped:
        confFields = env.getConfigurationFields(grouped[fieldConf]['id'])
        fieldsToAdd = []
        fieldsToHide = []
        for field in grouped[fieldConf]['fields']:
            if field not in set(field['id'] for field in confFields):
                fieldsToAdd.append(field)
                writer.writerow(["Info","Preparing","Field",str(field),"Will be added to Field Configuration " + str(fieldConf)])
            fieldsToHide.append(field)
            writer.writerow(["Info","Preparing","Field",str(field),"Will be hidden in Field Configuration " + str(fieldConf)])
        env.addFieldsToFieldConfiguration(grouped[fieldConf]['id'], fieldsToAdd)
        env.hideFieldsInFieldConfiguration(grouped[fieldConf]['id'], fieldsToHide)