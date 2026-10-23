import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sys as _environment_sys
from pathlib import Path as _environment_path
_environment_sys.path.insert(0, str(_environment_path(__file__).resolve().parents[1]))
from environment_config import get_environment
crea_environment = get_environment("creacdiscount")
peaksys_environment = get_environment("peaksys")

import requests
from requests.auth import HTTPBasicAuth
import csvbaseUrlCrea = crea_environment["jira_base_url"]
baseUrlPeaksys = peaksys_environment["jira_base_url"]

accountIds = ['557058:0cbe3dca-f252-4408-b260-a67195a05d52','557058:6b0ba393-d624-485b-9fb2-b886efa64ebf','557058:7a28eae2-d81b-474f-809f-c25444a42736','557058:e3042368-3abe-43b7-87c9-b01c7723175b','5a17d6f3a3481b031fe61498','5a314a55df1e923751322d38','5a32a062096df46fc90dfa48','5a32a197fb39265bb696fe30','5a32a318a761683f858f0900','5a32a3c77dfcb67b603015c8','5a32a3cbcade456582f1bad1','5a32a4bff6302e6581fcf149','5a32a507096df46fc90dfab4','5a3b6926b48b552ad9b2bb50','5a9430b154c8ff39bc248cab','5a9fd05e7b6a362a6237dede','5ab4c8814373ef2a697c2578','5ad5b39b34f1e62b1ac91dc5','5ae9a15dbfd66b2c4cf7db84','5b27b763835f7165ffe2f1e4','5b3b3c5d3148f52eed8ff183','5b76e2afef7a8d2b0612d801','5ba202c69477482ee0fabfd1','5beaddadb1b62d62a213bc46','5c335b97c5484b691dd2cc5f','5c4f27da1b87891f8a9cb9b2','5c73bf4a84926c623fb1dd8a','5c8a3454ebe39e5c70ec8f6a','5c8f68cf47a4d62d37cdd37f','5ca4b32061c2276e1bd508c3','5cc29bdae386340e2f4781ac','5ce7f9446673c80fe1763a6b','5d52819453184f0da389dc3d','5dadc5bef074330c3b423155','5dcae23637249a0c69300a85','5dcd197b53136d0de3b38157','5e1335e7b783d60db0a035aa','5e297399a09c140c9cc0c656','5e29ba7ba09c140c9cc0df7d','5ecbdca79286180c3042e74d','5ef455d714f60e0ac1be4869','5f0485dae1618b001b910245','5f0eb649591bbc001b9dc656','5f1ae91c70b8a9002503330d','5f483b0e3aa35b003f6ee105','5f4cf3a41ac29c0045502cf9','5f4e4a13d3796e0046a3ab94','5f631d43f7b565006b3c1520','5f6b1f903672f3006a35fe71','5f9ae1a4632c62007153e19c','5fb3ef8ccbead50069dcaedb','5fc1269f3b4f590068c0bbaa','5fc129be0d2f61006f76e412','5fca45680dd553006fea3847','5fd9da1c642089014132a7e4','5fdb784ab66825010ef121ae','5fdb83f5692b79011053f0bf','5fe0c38c692b7901107add38','5ffd6ca4dd5eb501080faa76','5ffd6ca58332a1010e281276','603e01b781a8400068c1cde6','608681ac52a3d40069cfee55','608adbcfccda29006b962565','609bec2075e875006f9d55b3','60b8adcc3c2f6d006eb3f008','60c9fbe58f2cc100692d417b','60ddd1dc0a1f68007040408e','60f67786d4b2160068183aa6','611bd8c4c2f3a50069e1c3a1','6169854e071a720071e6ece8','61766ba1bcb57400686416d7','61ded376125b1200714f11d6','61f90783e688d6007068aec9','6216318f9cd4a70071de7ed5','627cb3dc98eae500689f0728','630897c4f58f7bdcc54597f1','6356a2e0928dc277b9047017','637b5220f6c85b343c081818','6380b2435fce844d6069061e','63a5b356d3aeefa405416202','70121:0a0951f5-191d-4101-8036-c142f49bd3dd','70121:7ead3fb9-d3e7-4dae-b1e9-841869147e33','70121:8437ccfa-29a6-42c7-b058-d0deaddc431b','70121:c23f8d07-8969-46d5-ba94-892777879054','712020:b303b684-0a14-4c50-b66c-9cda75cfe1a1','712020:b996ff92-b916-48cc-8a0c-148088568271','712020:de3b103b-27ac-4d8a-ac4f-8343b803e271','712020:e1ae3f73-1caf-4031-9816-355308fbb3b0','712020:ef8d98a0-52ae-45de-a592-56615228dce0']

with open(r'C:\Users\Simon\OneDrive - Collaboration Betters The World\Documents\Cdiscount\Creacdiscount User Access\Users statuses.csv', mode='w', newline='') as outFile:
    writer = csv.writer(outFile, delimiter=',', quotechar='"')

    writer.writerow(['Account ID','Status Creacdiscount','Status Peaksys'])

    for accountId in accountIds:
        row = [accountId]
        reqCrea = requests.get(baseUrlCrea + '/rest/api/3/user?accountId=' + accountId, auth=HTTPBasicAuth(crea_environment["username"],crea_environment["user_token"]))
        if reqCrea is not None:
            creaUser = reqCrea.json()
            if creaUser is not None:
                if "active" in creaUser:
                    row.append(creaUser["active"])
                else:
                    row.append('User not reachable')
            else:
                row.append('User not reachable')
        else:
            row.append('User not reachable')
        
        reqPeaksys = requests.get(baseUrlPeaksys + '/rest/api/3/user?accountId=' + accountId, auth=HTTPBasicAuth(peaksys_environment["username"],peaksys_environment["user_token"]))
        if reqPeaksys is not None:
            peaksysUser = reqPeaksys.json()
            if peaksysUser is not None:
                if "active" in peaksysUser:
                    row.append(peaksysUser["active"])
                else:
                    row.append('User not reachable')
            else:
                row.append('User not reachable')
        else:
            row.append('User not reachable')
        writer.writerow(row)