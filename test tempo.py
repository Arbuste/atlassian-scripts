from Utilities.JiraEnvironment import JiraEnvironment
from Utilities.OrgEnvironment import OrgEnvironment
from Utilities.Utilities import SafeDict
from Utilities.Utilities import Utilities
from environment_config import get_environment
import json
import math
import csv
import xlsxwriter
from datetime import datetime
import collections


environment = get_environment("open_groupe_sandbox")
tempo_url = "https://api.tempo.io/4/timesheet-approvals/user/" + environment["user_id"] + "/approve"
Utilities.post(tempo_url, headers={"Authorization": "Bearer " + environment["tempo_token"]})
