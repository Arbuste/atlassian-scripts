from Utilities.JiraEnvironment import JiraEnvironment
from environment_config import get_environment
from Utilities.Utilities import SafeDict
import json
import math
import csv
import xlsxwriter
from datetime import datetime

# TME
environment = get_environment("tme")
baseUrl = environment["jira_base_url"]
user = environment["username"]
token = environment["user_token"]
folder = r'.\Files'

env = JiraEnvironment(baseUrl,user,token,folder)
spaces = ['BIICI','CKA','CC','AB','SMP','DA','AMW','HD','DIT','DB','ITOM','IA','PEU','NET','OPSDEVOPS','PROG','SRVCDLVR','SNCSM','SRVCSNWTM','STOR','TBI','TCOE','TOS','TDA','TOLZ','OSBS','CCPPM']
statusDict = {}

workbook = xlsxwriter.Workbook(folder + r'\Project Statuses.xlsx')

worksheet = workbook.add_worksheet('Project Statuses')
worksheet.write(0,0, "Project Key")
worksheet.write(1,0, "Work Type")

i = 0
for spaceKey in spaces:
    statusSet = {}
    issueTypes = env.getStatusesFromProject(spaceKey)
    str(spaceKey + " " + str([issueType["name"] for issueType in issueTypes]))
    for issueType in issueTypes:
        if "statuses" in issueType:
            dumpStatuses = json.dumps(issueType["statuses"], sort_keys=True)
            if dumpStatuses in statusSet:
                statusSet[dumpStatuses]["it"] += ", " + issueType["name"]
                worksheet.write(1,statusSet[dumpStatuses]["col"],statusSet[dumpStatuses]["it"])
            else:
                i += 1
                statusSet[dumpStatuses] = { "it": issueType["name"], "col": i }
                worksheet.write(1,statusSet[dumpStatuses]["col"],statusSet[dumpStatuses]["it"])

                for status in issueType.get("statuses", []):
                    worksheet.write(0,i, spaceKey)
                    if status['id'] not in statusDict:
                        if statusDict == {}:
                            statusDict[status['id']] = 2
                        else:
                            statusDict[status['id']] = max(list(statusDict.values())) + 1
                        worksheet.write(statusDict[status['id']],0,status["name"])
                    worksheet.write(statusDict[status['id']],i,1)

workbook.close()
