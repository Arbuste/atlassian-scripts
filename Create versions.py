import json
import csv
import requests
from environment_config import get_environment
from requests.auth import HTTPBasicAuth

# --- CONFIGURATION (Champs à renseigner) ---
CSV_PROJECTS_PATH = r"C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Avril\Projets Animal.csv"

# Configuration Jira Cloud
environment = get_environment("avril")
JIRA_CLOUD_URL = environment["jira_base_url"]
JIRA_EMAIL = environment["username"]
JIRA_API_TOKEN = environment["user_token"]


def load_project_mapping_from_csv(csv_path):
    """
    Lit le fichier CSV et retourne un dictionnaire {dc_project_id: pkey}
    """
    mapping = {}
    try:
        with open(csv_path, mode='r', encoding='utf-8') as file:
            # On essaye DictReader ou reader standard avec le délimiteur ';'
            reader = csv.DictReader(file, delimiter=',')
            for row in reader:
                # Lecture des colonnes id et pkey
                dc_id = row.get("id")
                pkey = row.get("pkey")
                
                if dc_id and pkey:
                    mapping[str(dc_id).strip()] = pkey.strip()
                    
        print(f"✅ CSV Projets chargé : {len(mapping)} projets trouvés.")
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du CSV projets : {e}")
        
    return mapping


def get_cloud_project_id(pkey, cloud_url, auth):
    """
    Appelle GET /rest/api/3/project/{projectIdOrKey} pour récupérer l'ID du projet sur Jira Cloud.
    """
    endpoint = f"{cloud_url.rstrip('/')}/rest/api/3/project/{pkey}"
    headers = {"Accept": "application/json"}
    
    response = requests.get(endpoint, headers=headers, auth=auth)
    
    if response.status_code == 200:
        project_data = response.json()
        cloud_id = project_data.get("id")
        print(f"✅ Projet Cloud trouvé pour la clé '{pkey}' -> ID Cloud : {cloud_id}")
        return cloud_id
    else:
        print(f"❌ Erreur lors de la récupération du projet Cloud '{pkey}' ({response.status_code}): {response.text}")
        return None


def transform_version(dc_version, cloud_project_id):
    """
    Filtre les attributs et associe le projectId du Cloud.
    """
    cloud_version = {
        # Jira Cloud attend l'ID sous forme d'entier ou de chaîne (selon le type retourné)
        "projectId": int(cloud_project_id) if str(cloud_project_id).isdigit() else cloud_project_id
    }
    
    # Attributs spécifiquement demandés
    allowed_fields = ["name", "archived", "released", "releaseDate", "description", "startDate"]
    
    for field in allowed_fields:
        if field in dc_version and dc_version[field] is not None:
            cloud_version[field] = dc_version[field]
            
    return cloud_version


def push_versions_to_jira_cloud(versions, cloud_url, auth):
    """
    Envoie chaque version transformée sur Jira Cloud via POST /rest/api/3/version
    """
    endpoint = f"{cloud_url.rstrip('/')}/rest/api/3/version"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    for ver in versions:
        response = requests.post(endpoint, json=ver, headers=headers, auth=auth)
        if response.status_code == 201:
            print(f"✅ Version '{ver.get('name')}' créée avec succès sur Jira Cloud.")
        else:
            print(f"❌ Erreur lors de la création de la version '{ver.get('name')}': {response.status_code} - {response.text}")


# --- EXECUTION PRINCIPALE ---
if __name__ == "__main__":
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    
    with open(r"C:\Users\SimonLUCCHESINI\OneDrive - CBTW\Documents\Avril\Scripts\versions.json", encoding="utf-8") as f:
        raw_versions = json.load(f)

        if not raw_versions:
            print("⚠️ Aucun élément présent dans la liste JSON.")
            exit()

        # 1. Chargement du CSV de mapping des projets
        project_mapping = load_project_mapping_from_csv(CSV_PROJECTS_PATH)

        # 2. Récupération du projectId Data Center à partir du 1er objet JSON
        dc_project_id = str(raw_versions[0].get("projectId", "")).strip()
        
        if not dc_project_id:
            print("❌ L'attribut 'projectId' est introuvable ou vide dans le premier objet du JSON.")
            exit()

        # 3. Récupération de la pkey correspondante dans le CSV
        pkey = project_mapping.get(dc_project_id)
        if not pkey:
            print(f"❌ Le projectId Data Center '{dc_project_id}' n'a pas été trouvé dans le fichier CSV.")
            exit()

        print(f"📌 ProjectId DC : {dc_project_id} -> Clé du projet (pkey) : {pkey}")

        # 4. Appel unique à l'API Cloud pour récupérer le projectId de destination
        cloud_project_id = get_cloud_project_id(pkey, JIRA_CLOUD_URL, auth)

        if not cloud_project_id:
            print("❌ Impossible de continuer sans le projectId du Cloud.")
            exit()

        # 5. Transformation de toutes les versions

        transformed_versions = [transform_version(c, cloud_project_id) for c in raw_versions]

        print("\nAperçu des versions transformées à envoyer :")
        print(json.dumps(transformed_versions, indent=2))

        # 6. Création des versions sur Jira Cloud (décommenter la ligne ci-dessous)
        push_versions_to_jira_cloud(transformed_versions, JIRA_CLOUD_URL, auth)