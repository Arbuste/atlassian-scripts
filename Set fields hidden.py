import csv
from Utilities.JiraEnvironment import JiraEnvironment
from environment_config import get_environment

environment = get_environment("open_groupe_sandbox")
baseUrl = environment["jira_base_url"]
user = environment["username"]
token = environment["user_token"]
env = JiraEnvironment(baseUrl,user,token)

with open(r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\Fields to Hide.csv', mode='r', newline='') as inFile, \
    open(r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\Hide Fields - Logs.csv', mode='w', newline='') as outFile:
    reader = csv.DictReader(inFile, delimiter=',', quotechar='"')
    fieldsToHide = list(reader)
    writer = csv.writer(outFile, delimiter=',', quotechar='"')

    env = JiraEnvironment(baseUrl,user,token)

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