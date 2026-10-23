import csv
from Utilities.JiraEnvironment import JiraEnvironment
from environment_config import get_environment

with open(r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\Added Security Levels.csv', mode='r', newline='') as inFile, \
    open(r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\Remove Security Levels - Logs.csv', mode='w', newline='') as outFile:
    reader = csv.DictReader(inFile, delimiter=',', quotechar='"')
    addedLevels = list(reader)
    writer = csv.writer(outFile, delimiter=',', quotechar='"')

environment = get_environment("open_groupe_sandbox")
baseUrl = environment["jira_base_url"]
user = environment["username"]
token = environment["user_token"]
    env = JiraEnvironment(baseUrl,user,token)

    securityLevels = env.getAllSecurityLevels()
    securitySchemes = env.getAllSecuritySchemes()

    print(str(securitySchemes))
    schemes_dict = {scheme['id']: scheme for scheme in securitySchemes}

    levels = [
        {**level, 'scheme': schemes_dict[level['issueSecuritySchemeId']]}
        for level in securityLevels
        if level['issueSecuritySchemeId'] in schemes_dict
            and {'Scheme Name': schemes_dict[level['issueSecuritySchemeId']]['name'],
                'Level Name': level['name']} in [{'Scheme Name': addedLevel['Scheme Name'], 'Level Name': addedLevel['Level Name']} for addedLevel in addedLevels]
    ]

    print(str(len(securityLevels)))

    allMembers = env.getSecurityMembersByLevels([ level['id'] for level in levels])
    membersToRemove = [member for member in allMembers if member['holder']['type'] == 'applicationRole']

    for member in membersToRemove:
        env.deleteSecurityLevelMember(member['issueSecuritySchemeId'],member['issueSecurityLevelId'],member['id'])