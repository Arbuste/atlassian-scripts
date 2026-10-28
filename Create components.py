import json
import csv
import requests
from requests.auth import HTTPBasicAuth
from environment_config import get_environment

# --- CONFIGURATION (Champs à renseigner) ---
CSV_FILE_PATH = r"C:\Users\cbtwt\OneDrive - CBTW\Documents\Avril\Liste users.csv"

environment = get_environment("avril")

ORG_ID = environment["org_id"]
ORG_BEARER_TOKEN = environment["org_token"]
ORG_BASE_URL = environment["org_base_url"]
JIRA_CLOUD_URL = environment["jira_base_url"]
JIRA_EMAIL = environment["username"]
JIRA_API_TOKEN = environment["user_token"]
JIRA_PROJECT = "MEP"

def chunked_list(lst, size=100):
    """Découpe une liste en sous-listes de taille maximale `size`."""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def load_csv_user_email_mapping(csv_path):
    """
    Lit le fichier CSV et retourne un dictionnaire {lower_user_name: lower_email_address}
    """
    username_to_email = {}
    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file, delimiter=',') # Adapter le délimiteur si nécessaire (ex: ',')
            for row in reader:
                user_name = row.get("lower_user_name")
                email = row.get("lower_email_address")
                
                if user_name and email:
                    username_to_email[user_name.strip().lower()] = email.strip().lower()
                    
        print(f"✅ CSV chargé : {len(username_to_email)} utilisateurs trouvés.")
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du CSV : {e}")
        
    return username_to_email


def fetch_account_ids_by_emails(emails, org_id, bearer_token):
    """
    Interroge l'API Org Atlassian par paquets de 100 e-mails max
    et retourne un dictionnaire {email: accountId}.
    """
    email_to_account_id = {}
    endpoint = f"{ORG_BASE_URL.rstrip('/')}/admin/v2/orgs/{org_id}/directories/-/users/search"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Nettoyage et dédoublonnage des e-mails
    unique_emails = list(set(email for email in emails if email))
    print(f"⏳ Récupération des accountIds pour {len(unique_emails)} e-mails uniques...")

    for batch in chunked_list(unique_emails, 100):
        payload = {"emails": batch}
        response = requests.post(endpoint, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            # L'API Org Atlassian renvoie généralement la liste sous la clé "data"
            users = data.get("data", data) if isinstance(data, dict) else data
            
            for user in users:
                # Récupération de l'accountId et de l'e-mail (selon la structure renvoyée)
                acc_id = user.get("account_id") or user.get("accountId")
                user_email = user.get("email")
                
                if user_email and acc_id:
                    email_to_account_id[user_email.lower()] = acc_id
        else:
            print(f"❌ Erreur API Org sur un lot d'e-mails ({response.status_code}): {response.text}")

    print(f"✅ {len(email_to_account_id)} accountIds récupérés auprès de l'API Organisation.")
    return email_to_account_id


def build_username_to_account_id_mapping(csv_path, org_id, bearer_token):
    """
    Construit le mapping final direct {lower_user_name: accountId}.
    """
    # 1. Chargement CSV
    username_to_email = load_csv_user_email_mapping(csv_path)
    if not username_to_email:
        return {}

    # 2. Récupération groupée des accountIds via l'API Org
    all_emails = list(username_to_email.values())
    email_to_account_id = fetch_account_ids_by_emails(all_emails, org_id, bearer_token)

    # 3. Association finale username -> accountId
    final_mapping = {}
    for username, email in username_to_email.items():
        # Si l'accountId est trouvé, on l'assigne, sinon chaîne vide
        final_mapping[username] = email_to_account_id.get(email, "")

    return final_mapping


def transform_component(dc_component, user_mapping):
    """
    Transforme un composant Data Center pour le format Jira Cloud.
    """
    cloud_component = {}
    
    # Conservation des attributs standards
    for field in ["name", "assigneeType", "description", "project"]:
        if field in dc_component:
            cloud_component[field] = dc_component[field]
        elif field == "project":
            cloud_component["project"] = JIRA_PROJECT
            
    # Traitement du lead
    if "lead" in dc_component and isinstance(dc_component["lead"], dict):
        lead_key = dc_component["lead"].get("key", "").strip().lower()
        # On récupère directement l'accountId mappé, sinon chaîne vide
        cloud_component["leadAccountId"] = user_mapping.get(lead_key, "")
        
    return cloud_component


def push_to_jira_cloud(components, cloud_url, auth):
    """
    Envoie la liste des composants transformés vers Jira Cloud.
    """
    endpoint = f"{cloud_url.rstrip('/')}/rest/api/3/component"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    for comp in components:
        response = requests.post(endpoint, json=comp, headers=headers, auth=auth)
        if response.status_code == 201:
            print(f"✅ Composant '{comp.get('name')}' créé avec succès.")
        else:
            print(f"❌ Erreur lors de la création de '{comp.get('name')}': {response.status_code} - {response.text}")


# --- EXECUTION PRINCIPALE ---
if __name__ == "__main__":
    jira_auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)

    # 1. Construction complète du mapping user_name -> accountId au démarrage
    user_mapping = build_username_to_account_id_mapping(CSV_FILE_PATH, ORG_ID, ORG_BEARER_TOKEN)

    # 2. Transformation locale des composants (instantanée)
    # utiliser GET /rest/api/2/project/{projectIdOrKey}/components
    with open(r"C:\Users\cbtwt\OneDrive - CBTW\Documents\Avril\Scripts\components.json", encoding="utf-8") as f:
        raw_components = json.load(f)
        transformed_components = [transform_component(c, user_mapping) for c in raw_components]

        print("\nAperçu des composants transformés :")
        print(json.dumps(transformed_components, indent=2))

    # 3. Publication sur Jira Cloud (décommenter pour exécuter)
        push_to_jira_cloud(transformed_components, JIRA_CLOUD_URL, jira_auth)