import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
cloud_environment = get_environment("peaksys_sandbox_migration_01")

import json
import requests
import csv
import re
import copy
from requests.auth import HTTPBasicAuth

#Chemin vers le fichier de logs
logPath = r'C:\Users\simon.lucchesini\OneDrive - CBTW\Documents\Confluence\output.csv'

#URL de l'instance de destinationbaseUrl = cloud_environment["confluence_base_url"]

#Identifiants du user Cloud qui va faire les requêtes
basic = HTTPBasicAuth(cloud_environment["username"], cloud_environment["user_token"])

with open(logPath, 'w', newline='', encoding='utf-8') as log:
    writer = csv.writer(log, delimiter=',',quotechar='"')
    writer.writerow(["Object","Category","Event","Detail","Additional detail"])
      
    def getCloud(url):
        return requests.get(baseUrl + url,auth=basic).json()
    
    def check(dict, key):
        res = False
        if key in dict:
            if dict[key]:
                res = True
        return res
    
    nbPages = 0
    pages = []
    nextPage = '/wiki/api/v2/pages?limit=250&body-format=storage'
    while nextPage != '':
        print('Nb pages: ' + str(nbPages))
        reqPages = getCloud(nextPage)
        if reqPages:
            print(str(reqPages))
            if check(reqPages,'results'):
                nbPages += len(reqPages['results'])
                pages += reqPages['results']
                if check(reqPages,'_links'):
                    if check(reqPages['_links'],'next'):
                        nextPage = reqPages['_links']['next']
                    else:
                        break
                else:
                    break
            else:
                break
        else:
            break
    if pages:
        for page in pages:
            if check(page,'body'):
                if check(page['body'],'storage'):
                    if check(page['body']['storage'],'value'):
                        body = page['body']['storage']['value']
                        if 'jira.cdiscount.com' in body:
                            requests.post(baseUrl + '/wiki/rest/api/content/'+page['id']+'/label',auth=basic,json={"prefix":"global","name":"jira-legacy"}) 