import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
dc_environment = get_environment("open_groupe_prod", "data_center")

import requests
import csvbaseUrl = dc_environment["confluence_base_url"]
token = dc_environment["confluence_pat"]
headers = {'Authorization':'Bearer ' + token}

def scroll(query):
    nextPage = query
    result = []
    while True:
        req = requests.get(baseUrl + nextPage,headers=headers)
        if req is not None:
            response = req.json()
            if 'results' in response:
                result.extend(response['results'])
            if '_links' in response:
                if 'next' in response['_links']:
                    nextPage = response['_links']['next']
                else:
                    break
            else:
                break
    return result

with open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Open\Numbered Headings.csv', mode='w', newline='', encoding='utf-8') as outFile:
    writer = csv.writer(outFile, delimiter=',', quotechar='"')
    writer.writerow(['Space Name','Space Key','Type','Status','Title'])
    
    spaces = scroll('/rest/api/space')
    print(str(len(spaces)))
    for space in spaces:
        contents = scroll('/rest/api/space/' + space['key'] + '/content/page?expand=body.storage')
        for content in contents:
            if content['status'] == 'current':
                if 'body' in content:
                    if 'storage' in content['body']:
                        if 'value' in content['body']['storage']:
                            writer.writerow([space['key'],space['name'],content['type'],content['status'],content['title']])