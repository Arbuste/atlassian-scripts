import requests
from environment_config import get_environment
# --- CONFIGURATION ---
environment = get_environment("avril")
BEARER_TOKEN = environment["org_token"]
ORG_BASE_URL = environment["org_base_url"]
ORG_ID = environment["org_id"]
DIRECTORY_ID = environment["directory_id"]
# Liste des accountIds Atlassian à ajouter au groupe
GROUP_NAMES = ['jira-system-administrators','DSI-Groupe','jira-chefs de projets','societe-sogeval','societe-BNA','site-chateau-gontier','Formulation','GCOM','SAMIE','Portails Eleveurs','societe-radar','DSI-Pilotage','societe-F4F','Codification','Glon-vietnam','projet-nessie','Marketing','DSI-AMOA','DAF','MOA-COMM','MOA-SOURCHES','Sanders Nord','ITECH','RH','BI','Logamix','International','Logistique','Ponte','Volaille Chair','AgroEvolution','Euronutrition','MATRA','MOA-BI','Sanders Centre-Auvergne','MAQ','OPERRA','Veterinaires','societe-feed-alliance','DEM-Cellule Codification','societe-Tapakah','societe-altho','Tresorerie','societe-filiere-oeuf','Codification-Administration','DSI-MOED','INTEGRA','Sanders Grand Est','vitae-ponte','societe-radar-complet','DSI-CODSI','DSI-CODIR','societe-arsoe','jira-utilisateurs-internes','sogeval-prestataire','Sanders Ouest SI','Concerto-intervenants','Symphonie-intervenants','Symphonie-gouvernance','sopral-intervenants','societe-cadexpert','CIBNA-intervenants','SAN.Service Client','Symphonie-prestataires','s3i-intervenants','Concerto-valideurs','kerhis-intervenants','norvolailles-intervenants','intervenants-uneal','societe-mivoc-systemes','Sanders Adour SI','SI-Communication','comite-logistique','sandifeed','DSI-Stage-BI-2012','tma-concerto-participants','tma-concerto-chefprojet','infogroupe-participants','tma-concerto-CPU','san-recla-client-participants','sand-medic-participants','parc-info','parc-auto','gestion-parc-tel','nc-sanders','nc-sanders-adour','nc-sanders-aurore','nc-sanders-auvergne','nc-sanders-bretagne','nc-sanders-est','nc-sanders-nord','nc-sanders-ouest','erp-terrial-participants','societe-terrial','comite-ntic','coord-si-branches','crm-grc-admin','admin-bdd','Codification CG','parc-coproj','rc-coordinateur','nc-sopral','nc-clemont','lapicalcul-web','Symphonie-chefsprojet','ovix-refonte-participants','ano-tempsgo-participants','rc-utilisateur','societe-sunfeed','margesnet-participants','sso-sanders-participants','PCANA-intervenants','repconsrh-intervenants-dsi','repconsrh-intervenants-prestataires','dsi-production','rnc-administrateur','sandra-intervenants-dsi','sandra-intervenants-prestataires','sandra-intervenants-metier','pondimobile-intervenants-metier','pondimobile-intervenants-dsi','pondimobile-intervenants-prestataires','pilotage-elevages-participants-dsi','lapiconnect-intervenants-prestataires','nc-utilisateur','repconsha-intervenants-dsi','jv-euralis-intervenant','spss-intervenants-dsi','spss-intervenants-metier','portailfrancegenes-intervenants-dsi','portailfrancegenes-intervenants-prestataires','support-arc-rh-particip','dsi-developpement','tma-concerto-coordinateurs','tma-sap-concerto-intervenants','tma-sap-concerto-coordinateurs','tma-sap-symphonie-intervenants','tma-sap-symphonie-coordinateurs','tma-applium','tma-sap-concerto-dsi','tma-sap-symphonie-dsi','divalto-new-participants','ordonnancement-production-participants','rc','societe-teatis','tma-sap-symbiose-chefdeprojet','tma-sap-symbiose-participants','fermatel-mobile-prestataires','fermatel-mobile-dsi','fermatel-mobile-metier','intervenants-nutriskel','oceadis-intervenants','Theseo-intervenants','DefaultUsers','CRM projet','s3i','s3i-prestataires','rnc','lapimobile-chefs-projet','lapimobile-intervenants-externes','lapimobile-intervenants-internes','sanders-distributeurs','automation','performance-participants','societe-infologic','xnet-intervenants','nc-aurouze','nc-huttepain bouix','oceane-consulting','jira-system','suivi-radar-industrie','societe-oet','societe-aznetwork','societe-nextdecision','tma-sap-theseo-intervenants','societe-creative-atlantique','edi-f4f-prestataires','tma-sap-theseo-chefsdeprojet','ogaritsolutions','nicelabel','sourches-sponsors','tma-sourches-intervenants','rnc-mixscience','societe-actemium','rc-utilisateurs-mxs','societe-grouplive','societe-adventiel','corossol-Energie Sanders Ouest','DSI-exploitation','rc-utilisateurs-sopral','rnc-mixscience-maq-externes','srh-help-indicateurs','tma-oeufs-dsi','support-arc-rh-chefdp','societe-kerhis','societe-porc-abera','Sanders Aurore','tma-capgemini','support-arc-rh-gestion-paie','support-arc-rh-sirh','support-arc-rh-rh','nc','nc-concessions','nc-aliane','tma-alimaterme-web','tma-sso-sanders','datalab','societe-ibm','DEM - Cellule Codfi attribution médicament','societe-pageup','DSI-CASR-CDP','NA-support-indus','Sanders Adour']

# --- EXECUTION ---
URL = f"{ORG_BASE_URL}/admin/v2/orgs/{ORG_ID}/directories/{DIRECTORY_ID}/groups"

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

for group_name in GROUP_NAMES:
    payload = {"name": group_name}

    response = requests.post(URL, json=payload, headers=HEADERS)

    if response.status_code in (200, 201, 204):
        print(f"[OK] Groupe {group_name} ajouté avec succès.")
    else:
        print(
            f"[ERREUR] Échec pour {group_name} (Code {response.status_code}) : {response.text}"
        )