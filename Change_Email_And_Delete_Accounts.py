import csv
import requests
import argparse
import time
import os
from Utilities.OrgEnvironment import OrgEnvironment
from environment_config import get_environment
from Utilities.JiraEnvironment import JiraEnvironment

def process(csv_in, csv_out, orgEnv, dry_run=False, sleep_between=0.2):
    with open(csv_out, 'w', newline='', encoding='utf-8') as outf:
        writer = csv.writer(outf)
        writer.writerow(["accountId", "oldEmail", "newEmail","errorStep","errorMessage"])
        with open(csv_in, newline='', encoding='utf-8') as inf:
            reader = csv.reader(inf)
        
            for row in reader:
                if not row:
                    continue
                accountId = row[0].strip()
                if not accountId:
                    continue

                print("Managing user " + accountId)

                user = orgEnv.getUser(accountId)
                if not user['isReqSuccess']:
                    print("Error while getting the user, going to next user")
                    writer.writerow([accountId, '', '', 'get user',str(user)])
                    continue

                if 'account' in user and user['account'] and 'email' in user['account'] and user['account']['email']:
                    oldEmail = user['account']['email']
                else:
                    print("Error while getting the user email, going to next user")
                    writer.writerow([accountId, '', '', 'get email',str(user)])
                    continue

                print("Email obtained (" + oldEmail + ")")

                local, domain = oldEmail.split('@', 1)
                newEmail = f"{local}-old@{domain}"

                if not dry_run:
                    print("Changing email...")
                    try:
                        respEmail = orgEnv.setEmail(accountId, newEmail)
                        if not respEmail['isReqSuccess']:
                            print("Error while changing email, going to next user")
                            writer.writerow([accountId, oldEmail, newEmail, 'change email',str(respEmail)])
                            continue
                    except Exception as e:
                        print("Error while changing email, going to next user")
                        writer.writerow([accountId, oldEmail, newEmail, 'change email','unknown'])
                        continue

                    writer.writerow([accountId,oldEmail,newEmail,"Email changed successfully"])
                else:
                    writer.writerow([accountId, oldEmail, newEmail])

                time.sleep(sleep_between)
            
            inf.close()

        with open(csv_in, newline='', encoding='utf-8') as inf:
            reader = csv.reader(inf)
            for row in reader:
                if not row:
                    continue
                accountId = row[0].strip()
                if not accountId:
                    continue

                print("Deleting user " + accountId)

                # delete
                try:
                    respDelete = orgEnv.deleteAccount(accountId)
                    if not respDelete['isReqSuccess']:
                        print("Error while deleting the user, going to next user")
                        writer.writerow([accountId, '-', '-', 'delete account',str(respDelete)])
                        continue
                except Exception as e:
                    print("Error while deleting the user, going to next user")
                    writer.writerow([accountId, '-', '-', 'delete account','unknown'])
                    continue
                print("User deleted")
                writer.writerow([accountId,'-', '-', "User deleted"])

def main():
    p = argparse.ArgumentParser(description='Change email to -old, verify and delete account using Atlassian Org API')
    p.add_argument('--csv', required=True, help='Input CSV file with one column: accountId')
    p.add_argument('--out', required=False, default='.\\Files\\change_delete_returns.csv', help='Output CSV file')
    p.add_argument('--environment', help='Environment key from environment_config.json')
    p.add_argument('--org-id', help='Atlassian organization id (legacy mode)')
    p.add_argument('--org-token', help='Atlassian org API bearer token (legacy mode)')
    p.add_argument('--dry-run', action='store_true', help='Do not perform changes or deletes')
    args = p.parse_args()

    # Use a named JSON profile when supplied; preserve legacy CLI credentials otherwise.
    if args.environment:
        environment = get_environment(args.environment)
        org_id = environment["org_id"]
        org_token = environment["org_token"]
    else:
        if not args.org_id or not args.org_token:
            p.error("Provide --environment or both --org-id and --org-token.")
        org_id = args.org_id
        org_token = args.org_token

    orgEnv = OrgEnvironment(org_id, org_token, r'./Files')

    process(args.csv, args.out, orgEnv, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
