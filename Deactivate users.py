import requests
import csv
import time
from Utilities.OrgEnvironment import OrgEnvironment
from environment_config import get_environment
with open(r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\Deactivation.csv', mode='r', newline='') as inFile, \
    open(r'C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Dev\Scripts Atlassian\Files\Deactivation - returns.csv', mode='w', newline='') as outFile:
    reader = csv.reader(inFile, delimiter=',', quotechar='"')
    writer = csv.writer(outFile, delimiter=',', quotechar='"')

    #Header
    header = next(reader)
    header.append('Deactivate Response')
    writer.writerow(header)
    environment = get_environment("open_groupe_sandbox")
    apiKey = environment["org_token"]
    orgId = environment["org_id"]
    orgEnv = OrgEnvironment(orgId,apiKey)
    
    for user in reader:
        print('Dealing with user ' + user[0])
        reqDeactivate = orgEnv.deactivateAccount(user[0])
        print(str(reqDeactivate['isReqSuccess']))
        if reqDeactivate['isReqSuccess']:
            print('DEACTIVATE OK')
            user.append('204')
        else:
            print('DEACTIVATE NOT OK: ' + str(reqDeactivate))
            user.append(str(reqDeactivate))
        
        writer.writerow(user)
        time.sleep(0.2)
