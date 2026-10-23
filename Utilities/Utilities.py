import requests
import math
import json
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter, Retry

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