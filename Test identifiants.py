from Utilities.JiraEnvironment import JiraEnvironment
from environment_config import get_environment
from Utilities.OrgEnvironment import OrgEnvironment
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
orgId = environment["org_id"]
orgToken = environment["org_token"]
folder = r'./Files'

env = JiraEnvironment(baseUrl,user,token,folder)
org = OrgEnvironment(orgId,orgToken,folder)

groups = org.getGroups()
projects = env.getProjects()