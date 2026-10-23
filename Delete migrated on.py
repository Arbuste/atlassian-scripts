import re
import requests
from requests.auth import HTTPBasicAuth
from environment_config import get_environment
# --- CONFIGURATION ---
environment = get_environment("open_groupe_sandbox")
BASE_URL = environment["jira_base_url"].rstrip("/")
USERNAME = environment["username"]
API_TOKEN = environment["user_token"]
AUTH = HTTPBasicAuth(USERNAME, API_TOKEN)

DRY_RUN = False  # Passer à False pour réellement exécuter le PUT (nécessaire pour voir l'erreur du PUT en DEBUG)
DEBUG_MODE = False
TARGET_FIELD_ID = "customfield_10755"  # Remplacer par l'ID exact du champ à tester

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

PATTERN = re.compile(r"\s*\(Migrated on .*\)$")

def clean_description(desc: str) -> str:
    if not desc:
        return ""
    return PATTERN.sub("", desc)

def has_migrated_pattern(desc: str) -> bool:
    return bool(desc and PATTERN.search(desc))

def chunk_list(data: list, chunk_size: int = 100):
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


# --- ÉTAPE 1 : Nettoyage des champs globaux ---
print(f"--- ÉTAPE 1 : Champs globaux {'[DRY RUN]' if DRY_RUN else ''} {'[DEBUG]' if DEBUG_MODE else ''} ---")
start_at = 0
is_last = False
field_found = False

while not is_last and not field_found:
    url = f"{BASE_URL}/rest/api/3/field/search"
    params = {"query": "Migrated on", "startAt": start_at, "maxResults": 50}
    
    if DEBUG_MODE:
        print(f"\n[DEBUG] GET {url} | Params: {params}")
        
    resp = requests.get(url, headers=HEADERS, auth=AUTH, params=params)
    
    if DEBUG_MODE:
        print(f"[DEBUG] Réponse GET ({resp.status_code}): {resp.text[:500]}... (tronqué)")
        
    resp.raise_for_status()
    data = resp.json()
    
    fields = data.get("values", [])
    total = data.get("total", 0)
    
    for field in fields:
        field_id = field.get("id")
        
        # En mode DEBUG, on ignore tout ce qui n'est pas notre champ cible
        if DEBUG_MODE:
            if field_id != TARGET_FIELD_ID:
                continue
            else:
                field_found = True # On arrête la pagination si on a trouvé et traité notre champ cible
            
        description = field.get("description", "")
        
        if DEBUG_MODE:
            print(f"\n[DEBUG] Champ cible trouvé ! ID: {field_id}")
            print(f"[DEBUG] Description brute retournée par l'API : '{description}'")
            print(f"[DEBUG] La regex matche-t-elle ? : {has_migrated_pattern(description)}")
        
        if has_migrated_pattern(description):
            new_desc = clean_description(description)
            
            print(f"\nModification requise pour l'ID: {field_id}")
            print(f"  Ancienne desc : '{description}'")
            print(f"  Nouvelle desc : '{new_desc}'")
            
            if DRY_RUN:
                print("  [DRY-RUN] Appel PUT ignoré.")
            else:
                put_url = f"{BASE_URL}/rest/api/3/field/{field_id}"
                payload = {"description": new_desc}
                
                if DEBUG_MODE:
                    print(f"\n[DEBUG] PUT {put_url} | Payload: {payload}")
                    
                put_resp = requests.put(put_url, headers=HEADERS, auth=AUTH, json=payload)
                
                if DEBUG_MODE:
                    print(f"[DEBUG] Réponse PUT ({put_resp.status_code}): {put_resp.text}")
                    
                if put_resp.status_code in (200, 204):
                    print(f"  -> Mis à jour avec succès.")
                else:
                    print(f"  -> Échec ({put_resp.status_code}): {put_resp.text}")
        
        # Si on est en DEBUG et qu'on a trouvé notre champ (même sans le pattern), on peut s'arrêter
        if DEBUG_MODE:
            field_found = True 

    start_at += len(fields)
    is_last = data.get("isLast", True) or (start_at >= total) or len(fields) == 0
    print("New Start_at ", str(start_at))
    print("Is Last ", str(is_last))


# --- ÉTAPE 2 : Nettoyage des Field Configurations ---
print(f"\n--- ÉTAPE 2 : Field Configurations {'[DRY RUN]' if DRY_RUN else ''} {'[DEBUG]' if DEBUG_MODE else ''} ---")
start_at_config = 0
is_last_config = False

while not is_last_config:
    config_url = f"{BASE_URL}/rest/api/3/fieldconfiguration"
    params = {"startAt": start_at_config, "maxResults": 50}
    
    resp = requests.get(config_url, headers=HEADERS, auth=AUTH, params=params)
    resp.raise_for_status()
    data = resp.json()
    configs = data.get("values", [])
    total_configs = data.get("total", 0)
    
    for config in configs:
        config_id = config.get("id")
        start_at_items = 0
        is_last_item = False
        matching_items = []
        
        while not is_last_item:
            items_url = f"{BASE_URL}/rest/api/3/fieldconfiguration/{config_id}/fields"
            item_params = {"startAt": start_at_items, "maxResults": 50}
            
            item_resp = requests.get(items_url, headers=HEADERS, auth=AUTH, params=item_params)
            item_resp.raise_for_status()
            item_data = item_resp.json()
            items = item_data.get("values", [])
            total_items = item_data.get("total", 0)
            
            for item in items:
                item_id = item.get("id")
                
                # En mode DEBUG, on ignore tout ce qui n'est pas notre champ cible
                if DEBUG_MODE and item_id != TARGET_FIELD_ID:
                    continue
                    
                desc = item.get("description", "")
                
                if DEBUG_MODE:
                    print(f"\n[DEBUG] Item cible trouvé dans la config {config_id} !")
                    print(f"[DEBUG] Description brute : '{desc}'")
                    print(f"[DEBUG] La regex matche-t-elle ? : {has_migrated_pattern(desc)}")

                if has_migrated_pattern(desc):
                    new_desc = clean_description(desc)
                    print(f"  Configuration ID: {config_id} | Field ID: {item_id}")
                    print(f"    Ancienne desc : '{desc}'")
                    print(f"    Nouvelle desc : '{new_desc}'")
                        
                    matching_items.append({
                        "id": item_id,
                        "description": new_desc
                    })
            
            start_at_items += len(items)
            is_last_item = item_data.get("isLast", True) or (start_at_items >= total_items) or len(items) == 0

        if matching_items:
            if DRY_RUN:
                print("  [DRY-RUN] Appel PUT ignoré pour cette configuration.")
            else:
                for chunk in chunk_list(matching_items, 100):
                    update_url = f"{BASE_URL}/rest/api/3/fieldconfiguration/{config_id}/fields"
                    payload = {"fieldConfigurationItems": chunk}
                    
                    if DEBUG_MODE:
                        print(f"\n[DEBUG] PUT {update_url} | Payload: {payload}")
                        
                    put_resp = requests.put(update_url, headers=HEADERS, auth=AUTH, json=payload)
                    
                    if DEBUG_MODE:
                        print(f"[DEBUG] Réponse PUT ({put_resp.status_code}): {put_resp.text}")
                        
                    if put_resp.status_code in (200, 204):
                        print(f"  -> Lot mis à jour avec succès.")
                    else:
                        print(f"  -> Échec mise à jour du lot ({put_resp.status_code}): {put_resp.text}")

    start_at_config += len(configs)
    is_last_config = data.get("isLast", True) or (start_at_config >= total_configs) or len(configs) == 0

print("\nOpération terminée !")