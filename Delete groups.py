import requests
from environment_config import get_environment
# --- CONFIGURATION (À adapter) ---
environment = get_environment("avril")
BEARER_TOKEN = environment["org_token"]
ORG_ID = environment["org_id"]
DIRECTORY_ID = environment["directory_id"]
ORG_BASE_URL = environment["org_base_url"]

# Liste des accountIds Atlassian à ajouter au groupe
GROUP_NAMES = ['admin-bdd','agroevolution','ano-tempsgo-participants','automation','bi','cibna-intervenants','codification','codification cg','codification-administration','comite-logistique','comite-ntic','concerto-intervenants','concerto-valideurs','coord-si-branches','corossol-energie sanders ouest','crm projet','crm-grc-admin','daf','datalab','defaultusers','dem - cellule codfi attribution médicament','dem-cellule codification','divalto-new-participants','dsi-amoa','dsi-casr-cdp','dsi-codir','dsi-codsi','dsi-developpement','dsi-exploitation','dsi-groupe','dsi-moed','dsi-pilotage','dsi-production','dsi-stage-bi-2012','edi-f4f-prestataires','erp-terrial-participants','euronutrition','fermatel-mobile-dsi','fermatel-mobile-metier','fermatel-mobile-prestataires','formulation','gcom','gestion-parc-tel','glon-vietnam','infogroupe-participants','integra','international','intervenants-nutriskel','intervenants-uneal','itech','jira-administrators','jira-chefs de projets','jira-system','jira-system-administrators','jira-utilisateurs','jira-utilisateurs-internes','jv-euralis-intervenant','kerhis-intervenants','lapicalcul-web','lapiconnect-intervenants-prestataires','lapimobile-chefs-projet','lapimobile-intervenants-externes','lapimobile-intervenants-internes','logamix','logistique','maq','margesnet-participants','marketing','matra','moa-bi','moa-comm','moa-sourches','na-support-indus','nc','nc-aliane','nc-aurouze','nc-clemont','nc-concessions','nc-huttepain bouix','nc-sanders','nc-sanders-adour','nc-sanders-aurore','nc-sanders-auvergne','nc-sanders-bretagne','nc-sanders-est','nc-sanders-nord','nc-sanders-ouest','nc-sopral','nc-utilisateur','nicelabel','norvolailles-intervenants','oceadis-intervenants','oceane-consulting','ogaritsolutions','operra','ordonnancement-production-participants','ovix-refonte-participants','parc-auto','parc-coproj','parc-info','pcana-intervenants','performance-participants','pilotage-elevages-participants-dsi','pondimobile-intervenants-dsi','pondimobile-intervenants-metier','pondimobile-intervenants-prestataires','ponte','portailfrancegenes-intervenants-dsi','portailfrancegenes-intervenants-prestataires','portails eleveurs','projet-nessie','rc','rc-coordinateur','rc-utilisateur','rc-utilisateurs-mxs','rc-utilisateurs-sopral','repconsha-intervenants-dsi','repconsrh-intervenants-dsi','repconsrh-intervenants-prestataires','rh','rnc','rnc-administrateur','rnc-mixscience','rnc-mixscience-maq-externes','s3i','s3i-intervenants','s3i-prestataires','samie','san-recla-client-participants','san.service client','sand-medic-participants','sanders adour','sanders adour si','sanders aurore','sanders centre-auvergne','sanders grand est','sanders nord','sanders ouest si','sanders-distributeurs','sandifeed','sandra-intervenants-dsi','sandra-intervenants-metier','sandra-intervenants-prestataires','si-communication','site-chateau-gontier','societe-actemium','societe-adventiel','societe-altho','societe-arsoe','societe-aznetwork','societe-bna','societe-cadexpert','societe-creative-atlantique','societe-f4f','societe-feed-alliance','societe-filiere-oeuf','societe-grouplive','societe-ibm','societe-infologic','societe-kerhis','societe-mivoc-systemes','societe-nextdecision','societe-oet','societe-pageup','societe-porc-abera','societe-radar','societe-radar-complet','societe-sogeval','societe-sunfeed','societe-tapakah','societe-teatis','societe-terrial','sogeval-prestataire','sopral-intervenants','sourches-sponsors','spss-intervenants-dsi','spss-intervenants-metier','srh-help-indicateurs','sso-sanders-participants','suivi-radar-industrie','support-arc-rh-chefdp','support-arc-rh-gestion-paie','support-arc-rh-particip','support-arc-rh-rh','support-arc-rh-sirh','symphonie-chefsprojet','symphonie-gouvernance','symphonie-intervenants','symphonie-prestataires','theseo-intervenants','tma-alimaterme-web','tma-applium','tma-capgemini','tma-concerto-chefprojet','tma-concerto-coordinateurs','tma-concerto-cpu','tma-concerto-participants','tma-oeufs-dsi','tma-sap-concerto-coordinateurs','tma-sap-concerto-dsi','tma-sap-concerto-intervenants','tma-sap-symbiose-chefdeprojet','tma-sap-symbiose-participants','tma-sap-symphonie-coordinateurs','tma-sap-symphonie-dsi','tma-sap-symphonie-intervenants','tma-sap-theseo-chefsdeprojet','tma-sap-theseo-intervenants','tma-sourches-intervenants','tma-sso-sanders','tresorerie','veterinaires','vitae-ponte','volaille chair','xnet-intervenants']

# --- EXECUTION ---
BASE_URL = f"{ORG_BASE_URL.rstrip('/')}/admin/v2/orgs/{ORG_ID}/directories/{DIRECTORY_ID}/groups"

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

for group_name in GROUP_NAMES:
    payload = {"searchTerm": group_name}
    response_get = requests.post(f"{BASE_URL}/search?expand=counts.users", json=payload, headers=HEADERS)

    if response_get.status_code in (200, 201, 204):
        print(response_get.json()['data'])
        if (len(response_get.json()['data']) > 0):
            print(f"[OK] Groupe {group_name} récupéré avec succès.")
            group = response_get.json()['data'][0]
            if ('counts' in group and 'users' in group['counts'] and group['counts']['users'] == 0):
                print(f"[OK] Groupe {group_name} vide - Suppression.")
                group_id = group['id']
                response_delete = requests.delete(f"{BASE_URL}/{group_id}", json=payload, headers=HEADERS)
                if (response_delete.status_code in (200, 201, 204)):
                    print(f"[OK] Groupe {group_name} supprimé.")
                else:
                    print(f"[ERREUR] Erreur de suppression du groupe {group_name} (Code {response_delete.status_code}) : {response_delete.text}")
            else:
                print(f"[OK] Groupe {group_name} non vide.")
        else:
            print(
                f"[ERREUR] Échec de récupération pour {group_name} - pas de données (Code {response_get.status_code}) : {response_get.text}"
            )
    else:
        print(
            f"[ERREUR] Échec de récupération pour {group_name} (Code {response_get.status_code}) : {response_get.text}"
        )