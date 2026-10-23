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
import csvDCBaseUrl = dc_environment["jira_base_url"]
cloudBaseUrl = cloud_environment["jira_base_url"]
bearer_token = dc_environment["jira_pat"]

headers = {"Authorization": f"Bearer {bearer_token}"}

currentRule = ''
currentComponent = ''
retour = []

def check(components,areConditions):
    for component in components:
        if "type" in component and "component" in component:
            currentComponent = component["component"] + ' ' + component["type"]
        else:
            currentComponent = 'condition in value'
        if "value" in component:
            if component["value"]:
                if "children" in component["value"]:
                    if component["value"]["children"]:
                        retour.append(currentRule + ' : ' + currentComponent + ', value has children')
                elif "conditions" in component["value"]:
                    if component["value"]["conditions"]:
                        retour.append(currentRule + ' : ' + currentComponent + ', value has conditions')
                        check(component["value"]["conditions"],True)
        
        if areConditions == True and "children" in component:
            if component["children"]:
                #print("componentchildren=" + str(component["children"]))
                retour.append(currentRule + ' : ' + currentComponent + ', condition has children')
                check(component["children"],False)
        elif areConditions == True and "conditions" in component:
            if component["conditions"]:
                #print("componentchildren=" + str(component["children"]))
                retour.append(currentRule + ' : ' + currentComponent + ', condition has conditions')
                check(component["conditions"],True)
        elif areConditions == False:
            if "conditions" in component:
                if component["conditions"]:
                    check(component["conditions"],True)
            if "children" in component:
                if component["children"]:
                    check(component["children"],False)

with open(r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\automation-rules-202603181110.json',encoding='utf-8') as f:
    d = json.load(f)
    
    for rule in d["rules"]:
        currentRule = rule["name"]
        currentComponent = ''
        check(rule["components"], False)
        
print(retour)
