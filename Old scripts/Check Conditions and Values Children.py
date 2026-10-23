import json

currentRule = ''
currentComponent = ''
retour = []

def check(components,areConditions):
    for component in components:
        currentComponent = component["component"] + ' ' + component["type"]
        if "value" in component:
            if component["value"] is not None:
                if "children" in component["value"]:
                    if not component["value"]["children"]:
                        retour.append(currentRule + ' : ' + currentComponent + ', value has children')
                elif "conditions" in component["value"]:
                    if not component["value"]["conditions"]:
                        retour.append(currentRule + ' : ' + currentComponent + ', value has conditions')
        
        if areConditions == True and "children" in component:
            if not component["children"]:
                #print("componentchildren=" + str(component["children"]))
                retour.append(currentRule + ' : ' + currentComponent + ', condition has children')
                check(component["children"],False)
        elif areConditions == True and "conditions" in component:
            if not component["conditions"]:
                #print("componentchildren=" + str(component["children"]))
                retour.append(currentRule + ' : ' + currentComponent + ', condition has conditions')
                check(component["conditions"],True)
        elif areConditions == False:
            if "conditions" in component:
                if not component["conditions"]:
                    check(component["conditions"],True)
            if "children" in component:
                if not component["children"]:
                    check(component["children"],False)

with open(r'C:\Users\simon.lucchesini\Downloads\automation-rules-202501281617.json',encoding='utf-8') as f:
    d = json.load(f)
    
    for rule in d["rules"]:
        currentRule = rule["name"]
        currentComponent = ''
        check(rule["components"], False)
        
print(retour)
