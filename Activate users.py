import requests
import csv
import time
from Utilities.OrgEnvironment import OrgEnvironment
from environment_config import get_environment

with open(r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\Activation.csv', mode='r', newline='') as inFile, \
    open(r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\Activation - returns.csv', mode='w', newline='') as outFile:
    reader = csv.reader(inFile, delimiter=',', quotechar='"')
    writer = csv.writer(outFile, delimiter=',', quotechar='"')

    #Header
    header = next(reader)
    header.append('Activate Response')
    writer.writerow(header)

    environment = get_environment("open_groupe_sandbox")
    apiKey = environment["org_token"]
    orgId = environment["org_id"]
    orgEnv = OrgEnvironment(orgId,apiKey)
    
    for user in reader:
        print('Dealing with user ' + user[0])
        reqActivate = orgEnv.activateAccount(user[0])
        print(str(reqActivate['isReqSuccess']))
        if reqActivate['isReqSuccess']:
            print('ACTIVATE OK')
            user.append('204')
        else:
            print('ACTIVATE NOT OK: ' + str(reqActivate))
            user.append(str(reqActivate))
        
        writer.writerow(user)
        time.sleep(0.2)
