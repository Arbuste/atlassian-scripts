#Requires -Version 5.1

if ([System.Threading.Thread]::CurrentThread.ApartmentState -ne "STA") {
    $psExe = Join-Path $PSHOME "powershell.exe"
    Start-Process -FilePath $psExe -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-STA","-File","`"$PSCommandPath`"")
    exit
}

Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Data

# ============================================================
# METADONNEES APPLICATION
# ============================================================
$script:AppName = "Comala Migration"
$script:AppVersion = "1.0.0"
$script:AppBuild = "2026-04-29"
$script:AppOwner = "Groupe OPEN"

# Correction affichage WPF : évite les bandes noires / zones non repeintes en RDP, VM ou carte graphique capricieuse
try { [System.Windows.Media.RenderOptions]::ProcessRenderMode = [System.Windows.Interop.RenderMode]::SoftwareOnly } catch {}

$script:DefaultConfluenceUrl = "https://preprodconfluence.open-groupe.com"
$script:ConfluenceUrl = $script:DefaultConfluenceUrl
$script:Username = ""
$script:Password = ""
$script:DryRun = $true
$script:ConfigReady = $false
$script:WorkflowDataTable = $null
$script:RestrictionTable = $null
$script:ProcedureTable = $null
$script:ExtractResults = @()
$script:RestrictionJsonData = @()
$script:LastRestoreError = ""
$script:StopRequested = $false
$script:BaseDir = Join-Path -Path ([System.AppDomain]::CurrentDomain.BaseDirectory) -ChildPath "Files Comala App"
if (-not (Test-Path -Path $script:BaseDir)) {
    try {
        # -Force permet de créer les dossiers parents si nécessaire
        New-Item -Path $script:BaseDir -ItemType Directory -Force | Out-Null
    } catch {}
}

if ([string]::IsNullOrWhiteSpace($script:BaseDir) -or -not (Test-Path -Path $script:BaseDir)) { $script:BaseDir = [Environment]::GetFolderPath("MyDocuments") }
$script:ConfigFile = Join-Path $script:BaseDir "config.txt"
$script:LogFile = Join-Path $script:BaseDir "comala_migration.log"
$script:RestrictionsJsonFile = Join-Path $script:BaseDir "restrictions_export.json"
$script:SessionFile = Join-Path $script:BaseDir "comala_migration_session.json"

function ConvertTo-CleanPageId {
    param([AllowNull()][AllowEmptyString()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return "" }
    $clean = [string]$Value
    $clean = $clean.Trim()
    $clean = $clean -replace '^\xEF\xBB\xBF',''
    $clean = $clean -replace '[\u200B-\u200D\uFEFF]',''
    $clean = $clean.Trim('"').Trim("'").Trim()
    if ($clean -notmatch '^\d+$') { return "" }
    return $clean
}

function Get-PageIdsFromCsvCell {
    param([AllowNull()][AllowEmptyString()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return @() }
    $raw = [string]$Value
    $raw = $raw -replace '^\xEF\xBB\xBF',''
    $raw = $raw -replace '[\u200B-\u200D\uFEFF]',''
    $raw = $raw.Trim('"').Trim("'").Trim()
    $ids = @()
    foreach ($m in [regex]::Matches($raw,'\d+')) {
        $id = ConvertTo-CleanPageId $m.Value
        if (-not [string]::IsNullOrWhiteSpace($id)) { $ids += $id }
    }
    return @($ids | Select-Object -Unique)
}

function ConvertTo-CleanCsvValue {
    param([AllowNull()][AllowEmptyString()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return "" }
    $clean = [string]$Value
    $clean = $clean.Trim()
    $clean = $clean -replace '^ï»¿',''
    $clean = $clean -replace '[​-‍]',''
    $clean = $clean.Trim('"').Trim("'").Trim()
    return $clean
}

function Repair-Mojibake {
    param([AllowNull()][AllowEmptyString()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $Text }
    $value = [string]$Text
    if ($value -notmatch 'Ã|Â|â€™|â€œ|â€|ðŸ| ') { return $value }
    try {
        $bytes = [System.Text.Encoding]::GetEncoding(1252).GetBytes($value)
        $fixed = [System.Text.Encoding]::UTF8.GetString($bytes)
        if (-not [string]::IsNullOrWhiteSpace($fixed)) { return $fixed }
    } catch {}
    return $value
}

function Normalize-DisplayText {
    param([AllowNull()][AllowEmptyString()][string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $Text }
    return (Repair-Mojibake (ConvertTo-CleanCsvValue $Text))
}

function Test-StopRequested {
    if ($script:StopRequested) { throw "Processus arrêté par l'utilisateur." }
}

function Reset-StopRequest {
    $script:StopRequested = $false
    Write-AppLog "Demande STOP réinitialisée" "INFO"
}

function Stop-CurrentProcess {
    $script:StopRequested = $true
    Write-AppLog "STOP demandé par l'utilisateur" "WARN"
    Show-MsgBox "Arrêt demandé. Le processus s'arrêtera à la prochaine étape contrôlée." "STOP" "Warning"
}

function Write-AppLog {
    param([Parameter(Mandatory=$true)][string]$Message,[ValidateSet("INFO","OK","WARN","ERROR")][string]$Level="INFO")
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $Level | $Message"
    try { Add-Content -Path $script:LogFile -Value $line -Encoding UTF8 } catch {}
    if ($null -ne $script:TxtLog) {
        try {
            $script:TxtLog.Dispatcher.Invoke([action]{
                $script:TxtLog.Text += $line + "`r`n"
                if ($null -ne $script:ScrollLog) { $script:ScrollLog.ScrollToBottom() }
            })
        } catch {}
    }
    if ($null -ne $script:TxtGlobalStatus) { try { $script:TxtGlobalStatus.Text = $line } catch {} }
}

function Show-MsgBox {
    param([string]$Msg,[string]$Title="Information",[string]$Icon="Information")

    $btn = [System.Windows.MessageBoxButton]::OK
    $ico = try { [System.Windows.MessageBoxImage]$Icon } catch { [System.Windows.MessageBoxImage]::Information }

    try {
        if ($null -ne $window) {
            $window.Topmost = $true
            $window.Activate() | Out-Null
            [System.Windows.MessageBox]::Show($window,$Msg,$Title,$btn,$ico) | Out-Null
            $window.Topmost = $false
            return
        }
    } catch {}

    [System.Windows.MessageBox]::Show($Msg,$Title,$btn,$ico) | Out-Null
}

function Show-ConfirmBox {
    param([string]$Msg,[string]$Title="Confirmation",[string]$Icon="Question")

    $btn = [System.Windows.MessageBoxButton]::YesNo
    $ico = try { [System.Windows.MessageBoxImage]$Icon } catch { [System.Windows.MessageBoxImage]::Question }

    try {
        if ($null -ne $window) {
            $window.Topmost = $true
            $window.Activate() | Out-Null
            $result = [System.Windows.MessageBox]::Show($window,$Msg,$Title,$btn,$ico)
            $window.Topmost = $false
            return $result
        }
    } catch {}

    return [System.Windows.MessageBox]::Show($Msg,$Title,$btn,$ico)
}

function Optimize-WindowForScreen {
    try {
        $window.MaxWidth = [double]::PositiveInfinity
        $window.MaxHeight = [double]::PositiveInfinity
        $window.Width = [System.Windows.SystemParameters]::WorkArea.Width
        $window.Height = [System.Windows.SystemParameters]::WorkArea.Height
        $window.Left = [System.Windows.SystemParameters]::WorkArea.Left
        $window.Top = [System.Windows.SystemParameters]::WorkArea.Top
        $window.WindowState = [System.Windows.WindowState]::Maximized
        $window.Background = New-Object System.Windows.Media.SolidColorBrush ([System.Windows.Media.ColorConverter]::ConvertFromString("#F3F4F6"))
        $window.SnapsToDevicePixels = $true
        $window.UseLayoutRounding = $true
        $window.InvalidateMeasure()
        $window.InvalidateArrange()
        $window.InvalidateVisual()
        $window.UpdateLayout()
    } catch {}
}
function Read-ConnectionFromUi {
    $script:ConfluenceUrl = $script:TxtCfgUrl.Text.Trim().TrimEnd("/")
    $script:Username = $script:TxtCfgUser.Text.Trim()
    if ($script:PwdCfgPassword.Visibility -eq [System.Windows.Visibility]::Visible) { $script:Password = $script:PwdCfgPassword.Password } else { $script:Password = $script:TxtCfgPassword.Text }
    $script:DryRun = [bool]$script:ChkCfgDryRun.IsChecked
    # DryRun est piloté uniquement depuis la page Configuration
    if ([string]::IsNullOrWhiteSpace($script:ConfluenceUrl)) { throw "URL Confluence obligatoire." }
    if ([string]::IsNullOrWhiteSpace($script:Username)) { throw "Compte obligatoire." }
    if ([string]::IsNullOrWhiteSpace($script:Password)) { throw "Token / mot de passe obligatoire." }
}

function Ensure-ConfigFile {
    if (-not (Test-Path $script:ConfigFile)) {
        @("CONFLUENCE_URL=$($script:DefaultConfluenceUrl)","USERNAME=","PASSWORD=","DRY_RUN=true") -join "`r`n" | Set-Content -Path $script:ConfigFile -Encoding UTF8
        Write-AppLog "config.txt créé : $script:ConfigFile" "OK"
    }
}

function Load-ConfigFile {
    Ensure-ConfigFile
    try {
        $cfg = @{}
        Get-Content $script:ConfigFile -Encoding UTF8 | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith("#")) {
                $parts = $line -split "=",2
                if ($parts.Count -eq 2) { $cfg[$parts[0].Trim()] = $parts[1].Trim() }
            }
        }
        $script:ConfluenceUrl = if ($cfg.ContainsKey("CONFLUENCE_URL")) { $cfg["CONFLUENCE_URL"].TrimEnd("/") } else { $script:DefaultConfluenceUrl }
        if ([string]::IsNullOrWhiteSpace($script:ConfluenceUrl) -or $script:ConfluenceUrl -eq "http://localhost:8090") {
            $script:ConfluenceUrl = $script:DefaultConfluenceUrl
        }
        $script:Username = if ($cfg.ContainsKey("USERNAME")) { $cfg["USERNAME"] } else { "" }
        $script:Password = if ($cfg.ContainsKey("PASSWORD")) { $cfg["PASSWORD"] } else { "" }
        $script:DryRun = if ($cfg.ContainsKey("DRY_RUN")) { ($cfg["DRY_RUN"].ToLowerInvariant() -eq "true") } else { $true }
        if ($null -ne $script:TxtCfgUrl) { $script:TxtCfgUrl.Text = $script:ConfluenceUrl }
        if ($null -ne $script:TxtCfgUser) { $script:TxtCfgUser.Text = $script:Username }
        if ($null -ne $script:PwdCfgPassword) { $script:PwdCfgPassword.Password = $script:Password }
        if ($null -ne $script:TxtCfgPassword) { $script:TxtCfgPassword.Text = $script:Password }
        if ($null -ne $script:ChkCfgDryRun) { $script:ChkCfgDryRun.IsChecked = $script:DryRun }
        Update-DryRunStatus
        return $true
    } catch {
        Write-AppLog "Erreur chargement config.txt : $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Save-ConfigFile {
    try {
        Read-ConnectionFromUi
        $dryRunValue = ([string]$script:DryRun).ToLowerInvariant()
        @("CONFLUENCE_URL=$($script:ConfluenceUrl)","USERNAME=$($script:Username)","PASSWORD=$($script:Password)","DRY_RUN=$dryRunValue") -join "`r`n" | Set-Content -Path $script:ConfigFile -Encoding UTF8
        Write-AppLog "Configuration enregistrée" "OK"
        return $true
    } catch {
        Write-AppLog "Erreur configuration : $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function ConvertTo-SafeLabelPart {
    param([AllowNull()][AllowEmptyString()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return "non-defini" }
    $normalized = ([string]$Value).ToLowerInvariant()
    $normalized = $normalized -replace "[àáâãäå]","a"
    $normalized = $normalized -replace "[ç]","c"
    $normalized = $normalized -replace "[èéêë]","e"
    $normalized = $normalized -replace "[ìíîï]","i"
    $normalized = $normalized -replace "[ñ]","n"
    $normalized = $normalized -replace "[òóôõö]","o"
    $normalized = $normalized -replace "[ùúûü]","u"
    $normalized = $normalized -replace "[ýÿ]","y"
    $normalized = $normalized -replace "[^a-z0-9]+","-"
    $normalized = $normalized.Trim("-")
    while ($normalized.Contains("--")) { $normalized = $normalized.Replace("--","-") }
    if ([string]::IsNullOrWhiteSpace($normalized)) { return "non-defini" }
    return $normalized
}

function New-ComalaMigrationLabel {
    param([string]$SpaceKey,[string]$WorkflowName)
    return "migration-comala-$(ConvertTo-SafeLabelPart $SpaceKey)-$(ConvertTo-SafeLabelPart $WorkflowName)"
}

function ConvertTo-AppfireConsolidationLabel {
    param([AllowEmptyString()][string]$WorkflowName,[int]$Counter)
    $baseLabel = [regex]::Replace($WorkflowName,'[^A-Za-z0-9]','')
    if ([string]::IsNullOrWhiteSpace($baseLabel)) { $baseLabel = "Workflow" }
    return "$baseLabel$Counter"
}

function Initialize-WorkflowDataTable {
    $dt = New-Object System.Data.DataTable
    foreach ($col in @("pageId","spaceKey","pageTitle","workflowName","workflowMarkup","labelToAdd","consolidationAction","consolidationStatus","consolidationComment","businessValidation","businessComment","pageUrl","apiStatus","apiMessage","restrictionState")) { [void]$dt.Columns.Add($col,[string]) }
    $script:WorkflowDataTable = $dt
}

function Initialize-RestrictionDataTable {
    $dt = New-Object System.Data.DataTable
    foreach ($col in @("pageId","pageUrl","spaceKey","pageTitle","workflowName","hasRestrictions","actionRequired","actionReelle","raisonAction","principalSummary","dateAction","resultatHttp","readUsers","readGroups","updateUsers","updateGroups","saved","removed","restored","message")) { [void]$dt.Columns.Add($col,[string]) }
    $script:RestrictionTable = $dt
}

function Set-RestrictionRealAction {
    param(
        [Parameter(Mandatory=$true)]$Row,
        [Parameter(Mandatory=$true)][string]$Action,
        [AllowEmptyString()][string]$Reason = "",
        [AllowEmptyString()][string]$Result = ""
    )
    try { $Row["actionReelle"] = $Action } catch {}
    try { $Row["raisonAction"] = $Reason } catch {}
    try { $Row["dateAction"] = (Get-Date -Format "yyyy-MM-dd HH:mm:ss") } catch {}
    try { $Row["resultatHttp"] = $Result } catch {}
}

function Get-RestrictionPrincipalSummary {
    param(
        [AllowNull()]$ReadUsers,
        [AllowNull()]$ReadGroups,
        [AllowNull()]$UpdateUsers,
        [AllowNull()]$UpdateGroups
    )
    $parts = New-Object System.Collections.ArrayList
    $ru = @(ConvertTo-RestrictionNameList $ReadUsers)
    $rg = @(ConvertTo-RestrictionNameList $ReadGroups)
    $uu = @(ConvertTo-RestrictionNameList $UpdateUsers)
    $ug = @(ConvertTo-RestrictionNameList $UpdateGroups)
    if ($ru.Count -gt 0) { [void]$parts.Add("readUsers=" + ($ru -join ", ")) }
    if ($rg.Count -gt 0) { [void]$parts.Add("readGroups=" + ($rg -join ", ")) }
    if ($uu.Count -gt 0) { [void]$parts.Add("updateUsers=" + ($uu -join ", ")) }
    if ($ug.Count -gt 0) { [void]$parts.Add("updateGroups=" + ($ug -join ", ")) }
    return (@($parts) -join " | ")
}

function Initialize-ProcedureDataTable {
    $dt = New-Object System.Data.DataTable
    foreach ($col in @("ordre","done","statut","categorie","etape","section","cible","action","outil","controle","preuve")) { [void]$dt.Columns.Add($col,[string]) }
    $script:ProcedureTable = $dt
}

function Add-ProcedureStep {
    param([int]$Ordre,[string]$Categorie,[string]$Etape,[string]$Action,[string]$Outil,[string]$Controle,[string]$Cible)
    $row = $script:ProcedureTable.NewRow()
    $row["ordre"] = [string]$Ordre
    $row["done"] = ""
    $row["statut"] = "À faire"
    $row["categorie"] = $Categorie
    $row["etape"] = $Etape
    $row["section"] = if ($Ordre -eq 0) { "Configuration" } elseif ($Ordre -ge 1 -and $Ordre -le 8) { "Workflow" } elseif ($Ordre -in 9,10,11,15) { "Restrictions" } elseif ($Ordre -eq 16) { "Logs" } else { "Procédure" }
    $row["cible"] = $Cible
    $row["action"] = $Action
    $row["outil"] = $Outil
    $row["controle"] = $Controle
    $row["preuve"] = ""
    $script:ProcedureTable.Rows.Add($row)
}

function Initialize-Procedure {
    Initialize-ProcedureDataTable
    Add-ProcedureStep 0 "Pré requis" "Configurer l'accès Confluence" "Renseigner URL, compte, mot de passe / token, puis tester la connexion." "IHM + API" "Connexion OK" "Configuration"
    Add-ProcedureStep 1 "Extraction" "Extraire / importer les workflows" "Importer le CSV Appfire ou lancer l'extraction API." "IHM" "Pages chargées" "Workflow"
    Add-ProcedureStep 2 "Analyse" "Charger l'inventaire" "Alimenter la grille Workflow." "IHM" "Lignes visibles" "Workflow"
    Add-ProcedureStep 3 "Analyse" "Contrôler les workflows" "Relire pages, espaces, workflows et labels." "IHM" "Cohérence vérifiée" "Workflow"
    Add-ProcedureStep 4 "Comala" "Consolider les page workflows" "Lancer la consolidation Appfire." "IHM + API" "Consolidation réalisée" "Workflow"
    Add-ProcedureStep 5 "Comala" "Créer les space workflows filtrés" "Créer les space workflows par label." "Comala" "Space workflows créés" "Workflow"
    Add-ProcedureStep 6 "Validation" "Valider les lignes métier" "Marquer OK / KO / À arbitrer." "IHM" "Lignes qualifiées" "Workflow"
    Add-ProcedureStep 7 "Labels" "Contrôler les labels" "Vérifier les labels après consolidation." "Confluence" "Labels présents" "Workflow"
    Add-ProcedureStep 8 "Contrôle DC" "Vérifier le ciblage" "Contrôler les pages ciblées." "Confluence / Comala" "Échantillon validé" "Workflow"
    Add-ProcedureStep 9 "Restrictions" "Analyser les restrictions" "Importer ou lire les restrictions." "IHM + API / CSV" "Analyse terminée" "Restrictions"
    Add-ProcedureStep 10 "Restrictions" "Sauvegarder les restrictions" "Générer restrictions_export.json." "Fichier local" "JSON présent" "Restrictions"
    Add-ProcedureStep 11 "Restrictions" "Lever temporairement les restrictions" "Lever les restrictions directes." "IHM + API" "Restrictions levées" "Restrictions"
    Add-ProcedureStep 12 "Migration" "Lancer la migration Cloud" "Exécuter l'outil de migration." "CCMA / Appfire" "Migration exécutée" "Procédure"
    Add-ProcedureStep 13 "Contrôle" "Vérifier les workflows dans Cloud" "Contrôler la reprise côté Cloud." "Confluence Cloud" "Contrôle OK" "Procédure"
    Add-ProcedureStep 14 "Cloud" "Reconfigurer les restrictions Cloud" "Ajuster les restrictions côté Cloud." "IHM Cloud" "Restrictions conformes" "Procédure"
    Add-ProcedureStep 15 "Data Center" "Restaurer les restrictions source" "Rétablir depuis le JSON." "IHM + API" "Source remise en état" "Restrictions"
    Add-ProcedureStep 16 "Traçabilité" "Archiver les traces" "Conserver logs, CSV et JSON." "Fichiers" "Archive complète" "Logs"
}

function Refresh-ProcedureSummary {
    if ($null -eq $script:ProcedureTable) { return }
    $done = @($script:ProcedureTable.Rows | Where-Object { [string]$_["statut"] -eq "Réalisé" }).Count
    $doing = @($script:ProcedureTable.Rows | Where-Object { [string]$_["statut"] -eq "En cours" }).Count
    $todo = @($script:ProcedureTable.Rows | Where-Object { [string]$_["statut"] -eq "À faire" }).Count
    $blocked = @($script:ProcedureTable.Rows | Where-Object { [string]$_["statut"] -eq "Bloqué" }).Count
    if ($null -ne $script:TxtProcedureSummary) { $script:TxtProcedureSummary.Text = "Réalisées : $done | En cours : $doing | À faire : $todo | Bloquées : $blocked" }
}

function Refresh-NextStep {
    if ($null -eq $script:TxtNextStepTitle) { return }
    $next = $script:ProcedureTable.Rows | Where-Object { [string]$_["statut"] -ne "Réalisé" } | Sort-Object { [int]$_["ordre"] } | Select-Object -First 1
    if ($null -eq $next) { $script:TxtNextStepTitle.Text = "Tout est terminé"; $script:TxtNextStepAction.Text = "Toutes les étapes sont réalisées."; return }
    $script:TxtNextStepTitle.Text = "Étape $($next['ordre']) — $($next['etape'])"
    $script:TxtNextStepAction.Text = "Section : $($next['section'])`nCible : $($next['cible'])`nAction : $($next['action'])"
}

function Set-ProcedureStepState {
    param([int]$Ordre,[string]$Statut,[string]$Preuve="")
    if ($null -eq $script:ProcedureTable) { return }
    foreach ($row in $script:ProcedureTable.Rows) {
        if ([int]$row["ordre"] -eq $Ordre) {
            $row["statut"] = $Statut
            $row["done"] = if ($Statut -eq "Réalisé") { "OK" } else { "" }
            if (-not [string]::IsNullOrWhiteSpace($Preuve)) { $row["preuve"] = $Preuve }
            break
        }
    }
    if ($null -ne $script:GridProcedure) { $script:GridProcedure.Items.Refresh() }
    Refresh-ProcedureSummary
    Refresh-NextStep
}

function Set-SelectedProcedureStatus {
    param([string]$Status)
    if ($script:GridProcedure.SelectedItems.Count -eq 0) { Show-MsgBox "Sélectionner au moins une étape." "Procédure" "Warning"; return }
    foreach ($item in $script:GridProcedure.SelectedItems) {
        $drv = [System.Data.DataRowView]$item
        $drv.Row["statut"] = $Status
        $drv.Row["done"] = if ($Status -eq "Réalisé") { "OK" } else { "" }
    }
    $script:GridProcedure.Items.Refresh()
    Refresh-ProcedureSummary
    Refresh-NextStep
}

function Set-ConfigReadyState {
    param([bool]$Ready)
    $script:ConfigReady = $Ready
    foreach ($tab in @($script:TabWorkflow,$script:TabRestrictions,$script:TabLogs)) { if ($null -ne $tab) { $tab.IsEnabled = $Ready } }
    if ($Ready) { Set-ProcedureStepState -Ordre 0 -Statut "Réalisé" -Preuve "Connexion valide" } else { Set-ProcedureStepState -Ordre 0 -Statut "À faire" -Preuve "Connexion à valider" }
}

function Get-AuthHeader {
    param([string]$Username,[string]$Password)
    $encoded = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes("$Username`:$Password"))
    return @{ "Authorization"="Basic $encoded"; "Accept"="application/json" }
}

function Invoke-ConfluenceApi {
    param([ValidateSet("GET","POST","PUT","DELETE")][string]$Method,[string]$Path,[object]$Body=$null,[int[]]$ExpectedStatusCodes=@(200))
    $uri = "$($script:ConfluenceUrl.TrimEnd('/'))$Path"
    $headers = Get-AuthHeader -Username $script:Username -Password $script:Password
    $err = $null
    $params = @{ Method=$Method; Uri=$uri; Headers=$headers; ContentType="application/json; charset=utf-8"; ErrorAction="SilentlyContinue"; ErrorVariable=$err}
    if ($null -ne $Body) {
        $jsonBody = ConvertTo-Json -InputObject $Body -Depth 80 -Compress
        $params.Body = $jsonBody
        Write-AppLog "[API][BODY] $Method $uri body=$jsonBody" "INFO"
    }
    $resp = Invoke-WebRequest -UseBasicParsing @params
    $code = [int]$resp.StatusCode
    # --- FIX ENCODAGE SUCCÈS ---
    # Au lieu de $content = [string]$resp.Content
    # On récupère les octets bruts et on force le décodage en UTF8
    $content = [System.Text.Encoding]::UTF8.GetString($resp.RawContentStream.ToArray())
    # ---------------------------
    <# $content = [string]$resp.Content #>
    if ($err) {
        $response = $err[0].Exception.Response
        if ($null -ne $response) {
            $code = [int]$response.StatusCode
            $bodyResp = ""
            try {
                $stream = $response.GetResponseStream()
                if ($null -ne $stream) {
                    $reader = New-Object System.IO.StreamReader($stream,[System.Text.Encoding]::UTF8,$true)
                    $bodyResp = $reader.ReadToEnd()
                    $reader.Close()
                }
            } catch {}
            if ($ExpectedStatusCodes -contains $code) {
                if ([string]::IsNullOrWhiteSpace($bodyResp)) { return $null }
                try { return $bodyResp | ConvertFrom-Json } catch { return $bodyResp }
            }
            throw "HTTP $code - $bodyResp"
        }
        throw $_.Exception.Message
    }
    if ([string]::IsNullOrWhiteSpace($content)) { return $null }
    try { return $content | ConvertFrom-Json } catch { return $content }
}

function Test-ConfluenceConnection {
    $r = Invoke-ConfluenceApi -Method "GET" -Path "/rest/api/user/current" -ExpectedStatusCodes @(200)
    if ($null -eq $r) { return "inconnu" }
    if ($r.username) { return $r.username }
    if ($r.name) { return $r.name }
    if ($r.displayName) { return $r.displayName }
    return "inconnu"
}

function Add-ConfluenceLabel {
    param([string]$PageId,[string]$Label)
    $cleanPageId = ConvertTo-CleanPageId $PageId
    if ([string]::IsNullOrWhiteSpace($cleanPageId)) { throw "pageId invalide : '$PageId'" }
    Invoke-ConfluenceApi -Method "POST" -Path "/rest/api/content/$cleanPageId/label" -Body @(@{ prefix="global"; name=$Label }) -ExpectedStatusCodes @(200,201) | Out-Null
}

function Find-CsvColumnName {
    param([string[]]$Candidates,[string[]]$AvailableColumns)
    foreach ($candidate in $Candidates) {
        $candidateNorm = ($candidate -replace "[^a-zA-Z0-9]","").ToLowerInvariant()
        foreach ($col in $AvailableColumns) {
            $colNorm = ($col -replace "[^a-zA-Z0-9]","").ToLowerInvariant()
            if ($colNorm -eq $candidateNorm) { return $col }
        }
    }
    return $null
}

function Get-CsvValueByColumn {
    param($Row,[AllowNull()][AllowEmptyString()][string]$ColumnName)
    if ([string]::IsNullOrWhiteSpace($ColumnName)) { return "" }
    $prop = $Row.PSObject.Properties[$ColumnName]
    if ($null -eq $prop) { return "" }
    return Normalize-DisplayText ([string]$prop.Value)
}

function Add-WorkflowRow {
    param([string]$PageId,[string]$SpaceKey,[string]$PageTitle,[string]$WorkflowName,[string]$WorkflowMarkup,[string]$PageUrl)
    $pageIdValue = ConvertTo-CleanPageId $PageId
    if ([string]::IsNullOrWhiteSpace($pageIdValue)) { return }
    $row = $script:WorkflowDataTable.NewRow()
    $row["pageId"] = $pageIdValue
    $row["spaceKey"] = ConvertTo-CleanCsvValue $SpaceKey
    $row["pageTitle"] = Normalize-DisplayText $PageTitle
    $row["workflowName"] = Normalize-DisplayText $WorkflowName
    $row["workflowMarkup"] = Normalize-DisplayText $WorkflowMarkup
    $row["labelToAdd"] = New-ComalaMigrationLabel -SpaceKey $SpaceKey -WorkflowName $WorkflowName
    $row["consolidationAction"] = "Consolidation Appfire"
    $row["consolidationStatus"] = "À faire"
    $row["consolidationComment"] = ""
    $row["businessValidation"] = "OK"
    $row["businessComment"] = ""
    $row["pageUrl"] = $PageUrl
    $row["apiStatus"] = ""
    $row["apiMessage"] = ""
    $row["restrictionState"] = ""
    $script:WorkflowDataTable.Rows.Add($row)
}

function Import-AppfirePageWorkflowsCsv {
    $dlg = New-Object System.Windows.Forms.OpenFileDialog
    $dlg.Filter = "Fichiers CSV (*.csv)|*.csv|Tous les fichiers (*.*)|*.*"
    if ($dlg.ShowDialog() -ne "OK") { return }
    try {
        $firstLine = Get-Content -Path $dlg.FileName -TotalCount 1 -Encoding UTF8
        $delimiter = if ($firstLine -match ';') { ';' } else { ',' }
        $rows = Import-Csv -Path $dlg.FileName -Delimiter $delimiter -Encoding UTF8
        if (@($rows).Count -eq 0) { Show-MsgBox "CSV vide." "Inventaire" "Warning"; return }
        $availableColumns = @($rows[0].PSObject.Properties.Name)
        $colPageId = Find-CsvColumnName -Candidates @("Content ID","ContentId","content_id","contentId","Page ID","PageId","page_id","id") -AvailableColumns $availableColumns
        $colSpaceKey = Find-CsvColumnName -Candidates @("Space Key","SpaceKey","space_key","spaceKey","space") -AvailableColumns $availableColumns
        $colTitle = Find-CsvColumnName -Candidates @("Title","Page Title","PageTitle","page_title","title") -AvailableColumns $availableColumns
        $colWorkflowName = Find-CsvColumnName -Candidates @("Workflow Name","WorkflowName","workflow_name","workflowName","workflow") -AvailableColumns $availableColumns
        $colWorkflowMarkup = Find-CsvColumnName -Candidates @("Workflow Markup","WorkflowMarkup","workflow_markup","markup") -AvailableColumns $availableColumns
        if ([string]::IsNullOrWhiteSpace($colPageId) -or [string]::IsNullOrWhiteSpace($colSpaceKey) -or [string]::IsNullOrWhiteSpace($colWorkflowName)) { Show-MsgBox "Colonnes manquantes`r`nContent ID / Space Key / Workflow Name" "Inventaire" "Error"; return }
        Initialize-WorkflowDataTable
        $imported = 0; $ignored = 0
        foreach ($csvRow in $rows) {
            $pageIds = @(Get-PageIdsFromCsvCell (Get-CsvValueByColumn -Row $csvRow -ColumnName $colPageId))
            $spaceKey = Get-CsvValueByColumn -Row $csvRow -ColumnName $colSpaceKey
            $title = Get-CsvValueByColumn -Row $csvRow -ColumnName $colTitle
            $workflowName = Get-CsvValueByColumn -Row $csvRow -ColumnName $colWorkflowName
            $workflowMarkup = Get-CsvValueByColumn -Row $csvRow -ColumnName $colWorkflowMarkup
            if ($pageIds.Count -eq 0 -or [string]::IsNullOrWhiteSpace($spaceKey) -or [string]::IsNullOrWhiteSpace($workflowName)) { $ignored++; continue }
            foreach ($pageId in $pageIds) {
                Add-WorkflowRow -PageId $pageId -SpaceKey $spaceKey -PageTitle $title -WorkflowName $workflowName -WorkflowMarkup $workflowMarkup -PageUrl "$($script:ConfluenceUrl.TrimEnd('/'))/pages/viewpage.action?pageId=$pageId"
                $imported++
            }
        }
        $script:GridWorkflow.ItemsSource = $script:WorkflowDataTable.DefaultView
        Refresh-WorkflowStats
        Update-WorkflowFilter
        Set-ProcedureStepState -Ordre 1 -Statut "Réalisé" -Preuve "$imported workflow(s)"
        Set-ProcedureStepState -Ordre 2 -Statut "Réalisé" -Preuve "$imported ligne(s)"
        $script:WorkflowTabs.SelectedItem = $script:TabTraitement
        Show-MsgBox "Import workflows`r`nImportés : $imported`r`nIgnorés : $ignored" "Inventaire"
    } catch { Write-AppLog "Erreur import workflows : $($_.Exception.Message)" "ERROR"; Show-MsgBox "Erreur import workflows`r`n$($_.Exception.Message)" "Inventaire" "Error" }
}

function Refresh-WorkflowStats {
    if ($null -eq $script:WorkflowDataTable -or $null -eq $script:LblWorkflowStats) { return }
    $total=0; $ok=0; $ko=0; $arb=0; $av=0; $labels=@{}; $done=0; $doing=0; $todo=0; $blocked=0; $dry=0; $err=0
    foreach ($row in $script:WorkflowDataTable.Rows) {
        $total++
        switch ([string]$row["businessValidation"]) { "OK" { $ok++ } "KO" { $ko++ } "A arbitrer" { $arb++ } default { $av++ } }
        switch ([string]$row["consolidationStatus"]) { "Réalisée" { $done++ } "En cours" { $doing++ } "Bloquée" { $blocked++ } "DRY-RUN" { $dry++ } "Erreur" { $err++ } default { $todo++ } }
        $lbl = [string]$row["labelToAdd"]
        if (-not [string]::IsNullOrWhiteSpace($lbl)) { if (-not $labels.ContainsKey($lbl)) { $labels[$lbl]=0 }; $labels[$lbl]++ }
    }
    $visible = if ($null -ne $script:WorkflowDataTable.DefaultView) { $script:WorkflowDataTable.DefaultView.Count } else { $total }
    $script:LblWorkflowStats.Content = "Pages : $total | Affichées : $visible | OK : $ok | KO : $ko | À arbitrer : $arb | À valider : $av | Labels : $($labels.Count) | Consolidation : $done OK, $doing en cours, $todo à faire, $blocked bloquées, $dry dry-run, $err erreurs"
}

function Get-SelectedWorkflowRows {
    $rows = New-Object System.Collections.ArrayList
    foreach ($item in $script:GridWorkflow.SelectedItems) { try { [void]$rows.Add(([System.Data.DataRowView]$item).Row) } catch {} }
    return @($rows)
}

function Set-ValidationOnSelectedWorkflows {
    param([string]$Value)
    $rows = @(Get-SelectedWorkflowRows)
    if ($rows.Count -eq 0) { Show-MsgBox "Sélection obligatoire." "Workflow" "Warning"; return }
    foreach ($row in $rows) { $row["businessValidation"] = $Value }
    $script:GridWorkflow.Items.Refresh()
    Refresh-WorkflowStats
}

function Set-LabelOnSelectedWorkflows {
    param([string]$Label)
    $rows = @(Get-SelectedWorkflowRows)
    if ($rows.Count -eq 0) { Show-MsgBox "Sélection obligatoire." "Workflow" "Warning"; return }
    if ([string]::IsNullOrWhiteSpace($Label)) { Show-MsgBox "Label obligatoire." "Workflow" "Warning"; return }
    foreach ($row in $rows) { $row["labelToAdd"] = $Label }
    $script:GridWorkflow.Items.Refresh()
    Refresh-WorkflowStats
}

function Set-ConsolidationStatusOnSelectedWorkflows {
    param([string]$Status)
    $rows = @(Get-SelectedWorkflowRows)
    if ($rows.Count -eq 0) { Show-MsgBox "Sélection obligatoire." "Consolidation" "Warning"; return }
    foreach ($row in $rows) { $row["consolidationStatus"] = $Status }
    $script:GridWorkflow.Items.Refresh()
    Refresh-WorkflowStats
}

function Regenerate-WorkflowLabels {
    if ($null -eq $script:WorkflowDataTable -or $script:WorkflowDataTable.Rows.Count -eq 0) { Show-MsgBox "Aucune donnée." "Workflow" "Warning"; return }
    foreach ($row in $script:WorkflowDataTable.Rows) { $row["labelToAdd"] = New-ComalaMigrationLabel -SpaceKey ([string]$row["spaceKey"]) -WorkflowName ([string]$row["workflowName"]) }
    $script:GridWorkflow.Items.Refresh()
    Refresh-WorkflowStats
}

function Open-SelectedWorkflowPage {
    $rows = @(Get-SelectedWorkflowRows)
    if ($rows.Count -eq 0) { Show-MsgBox "Sélection obligatoire." "Workflow" "Warning"; return }
    $urlValue = [string]$rows[0]["pageUrl"]
    if ([string]::IsNullOrWhiteSpace($urlValue)) {
        $pageIdValue = ConvertTo-CleanPageId ([string]$rows[0]["pageId"])
        if ([string]::IsNullOrWhiteSpace($pageIdValue)) { Show-MsgBox "pageId invalide." "Workflow" "Warning"; return }
        $urlValue = "$($script:ConfluenceUrl.TrimEnd('/'))/pages/viewpage.action?pageId=$pageIdValue"
    }
    Start-Process -FilePath $urlValue
}

function Export-ConsolidationPlanCsv {
    if ($null -eq $script:WorkflowDataTable -or $script:WorkflowDataTable.Rows.Count -eq 0) { Show-MsgBox "Aucune donnée." "Consolidation" "Warning"; return }
    $dlg = New-Object System.Windows.Forms.SaveFileDialog
    $dlg.Filter = "Fichiers CSV (*.csv)|*.csv"
    $dlg.FileName = "plan_consolidation_comala.csv"
    if ($dlg.ShowDialog() -eq "OK") {
        $objects = foreach ($row in $script:WorkflowDataTable.Rows) {
            [PSCustomObject]@{
                pageId="$($row['pageId'])"; pageUrl="$($row['pageUrl'])"; spaceKey="$($row['spaceKey'])"; pageTitle="$($row['pageTitle'])"; workflowName="$($row['workflowName'])"; workflowMarkup="$($row['workflowMarkup'])"; labelToAdd="$($row['labelToAdd'])"; consolidationAction="$($row['consolidationAction'])"; consolidationStatus="$($row['consolidationStatus'])"; consolidationComment="$($row['consolidationComment'])"; businessValidation="$($row['businessValidation'])"; businessComment="$($row['businessComment'])"; restrictionState="$($row['restrictionState'])"
            }
        }
        $objects | Export-Csv -Path $dlg.FileName -Encoding UTF8 -NoTypeInformation -Delimiter ";"
        Show-MsgBox "Plan exporté`r`n$($dlg.FileName)" "Consolidation"
    }
}

function Escape-RowFilterValue {
    param([AllowNull()][AllowEmptyString()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return "" }
    return ([string]$Value).Replace("'", "''").Replace("[", "[[]").Replace("%", "[%]").Replace("*", "[*]")
}

function Get-ComboText {
    param($Combo)
    if ($null -eq $Combo -or $null -eq $Combo.SelectedItem) { return "Tous" }
    try { return [string]$Combo.SelectedItem.Content } catch { return [string]$Combo.Text }
}

function Update-DryRunStatus {
    $modeText = if ($script:DryRun) { "Mode : DryRun" } else { "Mode : Réel" }
    $modeColor = if ($script:DryRun) { "#FBBF24" } else { "#86EFAC" }
    if ($null -ne $script:TxtDryRunStatus) {
        $script:TxtDryRunStatus.Text = $modeText
        try { $script:TxtDryRunStatus.Foreground = [System.Windows.Media.BrushConverter]::new().ConvertFromString($modeColor) } catch {}
    }
    if ($null -ne $script:TxtWorkflowDryRunInfo) { $script:TxtWorkflowDryRunInfo.Text = $modeText }
}

function Update-WorkflowFilter {
    if ($null -eq $script:WorkflowDataTable) { return }
    $filters = @()
    $validation = Get-ComboText $script:CmbFilterValidation
    $conso = Get-ComboText $script:CmbFilterConso
    $search = if ($null -ne $script:TxtWorkflowSearch) { $script:TxtWorkflowSearch.Text.Trim() } else { "" }
    if ($validation -ne "Tous") { $filters += "businessValidation = '$(Escape-RowFilterValue $validation)'" }
    if ($conso -ne "Tous") { $filters += "consolidationStatus = '$(Escape-RowFilterValue $conso)'" }
    if (-not [string]::IsNullOrWhiteSpace($search)) {
        $s = Escape-RowFilterValue $search
        $filters += "(pageId LIKE '%$s%' OR spaceKey LIKE '%$s%' OR pageTitle LIKE '%$s%' OR workflowName LIKE '%$s%' OR labelToAdd LIKE '%$s%')"
    }
    $script:WorkflowDataTable.DefaultView.RowFilter = ($filters -join " AND ")
    if ($null -ne $script:GridWorkflow) {
        $script:GridWorkflow.ItemsSource = $script:WorkflowDataTable.DefaultView
        $script:GridWorkflow.Items.Refresh()
    }
    Refresh-WorkflowStats
}

function Get-ComalaConsolidationGroups {
    param([ValidateSet("SpaceWorkflow","SpaceWorkflowMarkup")][string]$GroupingMode="SpaceWorkflow")
    if ($null -eq $script:WorkflowDataTable -or $script:WorkflowDataTable.Rows.Count -eq 0) { throw "Aucun workflow chargé." }
    $groups = @{}
    foreach ($row in $script:WorkflowDataTable.Rows) {
        if ([string]$row["businessValidation"] -ne "OK") { continue }
        $pageId = ConvertTo-CleanPageId ([string]$row["pageId"])
        $spaceKey = ConvertTo-CleanCsvValue ([string]$row["spaceKey"])
        $workflowName = ConvertTo-CleanCsvValue ([string]$row["workflowName"])
        $markup = [string]$row["workflowMarkup"]
        if ([string]::IsNullOrWhiteSpace($pageId) -or [string]::IsNullOrWhiteSpace($spaceKey) -or [string]::IsNullOrWhiteSpace($workflowName)) { continue }
        $key = if ($GroupingMode -eq "SpaceWorkflowMarkup") { "$spaceKey|||$workflowName|||$markup" } else { "$spaceKey|||$workflowName" }
        if (-not $groups.ContainsKey($key)) { $groups[$key] = [PSCustomObject]@{ spaceKey=$spaceKey; workflowName=$workflowName; markup=$markup; pageIds=New-Object System.Collections.ArrayList; rows=New-Object System.Collections.ArrayList } }
        [void]$groups[$key].pageIds.Add($pageId)
        [void]$groups[$key].rows.Add($row)
    }
    return $groups
}

function Invoke-ComalaBulkConsolidation {
    param([ValidateSet("SpaceWorkflow","SpaceWorkflowMarkup")][string]$GroupingMode="SpaceWorkflow")
    try { Read-ConnectionFromUi } catch { Show-MsgBox $_.Exception.Message "Consolidation" "Warning"; return }
    try { $groups = Get-ComalaConsolidationGroups -GroupingMode $GroupingMode } catch { Show-MsgBox $_.Exception.Message "Consolidation" "Warning"; return }
    if ($groups.Count -eq 0) { Show-MsgBox "Aucun groupe OK." "Consolidation" "Warning"; return }
    $confirm = [System.Windows.MessageBox]::Show("Consolidation Appfire`r`nGroupes : $($groups.Count)`r`nDryRun : $($script:DryRun)","Consolidation",[System.Windows.MessageBoxButton]::YesNo,[System.Windows.MessageBoxImage]::Question)
    if ($confirm -ne "Yes") { return }
    $labelCounters = @{}; $ok = 0; $errors = 0; $groupIndex = 0
    foreach ($key in $groups.Keys) {
        $groupIndex++
        $data = $groups[$key]
        $spaceKey = [string]$data.spaceKey
        $workflowName = [string]$data.workflowName
        $markup = [string]$data.markup
        $pageIds = @($data.pageIds | Select-Object -Unique)
        $preparedLabels = @($data.rows | ForEach-Object { ConvertTo-CleanCsvValue ([string]$_["labelToAdd"]) } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
        if ($preparedLabels.Count -eq 1) { $label = [string]$preparedLabels[0] } else { $baseLabel = [regex]::Replace($workflowName,'[^A-Za-z0-9]',''); if ([string]::IsNullOrWhiteSpace($baseLabel)) { $baseLabel = "Workflow" }; if (-not $labelCounters.ContainsKey($baseLabel)) { $labelCounters[$baseLabel]=0 }; $labelCounters[$baseLabel]++; $label = ConvertTo-AppfireConsolidationLabel -WorkflowName $workflowName -Counter $labelCounters[$baseLabel] }
        $payload = @{ contentIds=@($pageIds); label=$label; markup=$markup; workflowName=$workflowName }
        $path = "/rest/cw/1/workflows/$spaceKey/consolidatePageWorkflows"
        try {
            foreach ($r in @($data.rows)) { $r["labelToAdd"]=$label; $r["consolidationAction"]="POST $path"; $r["consolidationComment"]="Groupe=$groupIndex ; pages=$($pageIds.Count)" }
            if ($script:DryRun) { foreach ($r in @($data.rows)) { $r["consolidationStatus"]="DRY-RUN"; $r["apiStatus"]="DRY-RUN"; $r["apiMessage"]="Simulation OK" }; $ok++ }
            else { Invoke-ConfluenceApi -Method "POST" -Path $path -Body $payload -ExpectedStatusCodes @(200,201,204) | Out-Null; foreach ($r in @($data.rows)) { $r["consolidationStatus"]="Réalisée"; $r["apiStatus"]="OK"; $r["apiMessage"]="Consolidation OK" }; $ok++ }
        } catch { $errors++; foreach ($r in @($data.rows)) { $r["consolidationStatus"]="Erreur"; $r["apiStatus"]="ERROR"; $r["apiMessage"]=$_.Exception.Message }; Write-AppLog "Consolidation erreur space=$spaceKey workflow=$workflowName : $($_.Exception.Message)" "ERROR" }
        $script:GridWorkflow.Dispatcher.Invoke([action]{ $script:GridWorkflow.Items.Refresh() })
        [System.Windows.Forms.Application]::DoEvents()
    }
    Refresh-WorkflowStats
    Show-MsgBox "Consolidation Appfire`r`nOK : $ok`r`nErreurs : $errors" "Consolidation"
}

function Apply-WorkflowLabels {
    if ($null -eq $script:WorkflowDataTable -or $script:WorkflowDataTable.Rows.Count -eq 0) { Show-MsgBox "Aucune donnée." "Labels" "Warning"; return }
    try { Read-ConnectionFromUi } catch { Show-MsgBox $_.Exception.Message "Labels" "Warning"; return }
    $toProcess = @($script:WorkflowDataTable.Rows | Where-Object { [string]$_["businessValidation"] -eq "OK" -and -not [string]::IsNullOrWhiteSpace([string]$_["pageId"]) -and -not [string]::IsNullOrWhiteSpace([string]$_["labelToAdd"]) })
    if ($toProcess.Count -eq 0) { Show-MsgBox "Aucune ligne OK." "Labels" "Warning"; return }
    $confirm = [System.Windows.MessageBox]::Show("Pose labels`r`nPages : $($toProcess.Count)`r`nDryRun : $($script:DryRun)","Labels",[System.Windows.MessageBoxButton]::YesNo,[System.Windows.MessageBoxImage]::Warning)
    if ($confirm -ne "Yes") { return }
    $success = 0; $errors = 0
    foreach ($row in $toProcess) {
        $pageIdValue = ConvertTo-CleanPageId ([string]$row["pageId"])
        $labelValue = [string]$row["labelToAdd"]
        try { if ($script:DryRun) { $row["apiStatus"]="DRY-RUN"; $row["apiMessage"]="Simulation label" } else { Add-ConfluenceLabel -PageId $pageIdValue -Label $labelValue; $row["apiStatus"]="OK"; $row["apiMessage"]="Label posé" }; $success++ } catch { $row["apiStatus"]="ERROR"; $row["apiMessage"]=$_.Exception.Message; $errors++ }
        $script:GridWorkflow.Dispatcher.Invoke([action]{ $script:GridWorkflow.Items.Refresh() })
        [System.Windows.Forms.Application]::DoEvents()
    }
    Refresh-WorkflowStats
    Show-MsgBox "Labels`r`nOK : $success`r`nErreurs : $errors" "Labels"
}

function Add-UniqueStringToArrayList {
    param([AllowNull()]$List,[AllowNull()][AllowEmptyString()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return }
    if ($null -eq $List) { return }
    foreach ($existing in @($List)) { if ([string]$existing -eq $Value) { return } }
    try { [void]$List.Add($Value) } catch {}
}

function ConvertTo-RestrictionNameList {
    param([AllowNull()]$Value)
    $result = New-Object System.Collections.ArrayList
    foreach ($item in @($Value)) {
        if ($null -eq $item) { continue }
        $v = [string]$item
        foreach ($part in ($v -split "\s*[,;]\s*")) { $clean = ConvertTo-CleanCsvValue $part; if (-not [string]::IsNullOrWhiteSpace($clean)) { if (-not $result.Contains($clean)) { [void]$result.Add($clean) } } }
    }
    return @($result)
}

function Write-RestrictionsJsonFileSafe {
    param([AllowNull()]$Items)
    $itemsArray = @($Items)
    if ($itemsArray.Count -eq 0) { "[]" | Set-Content -Path $script:RestrictionsJsonFile -Encoding UTF8; return }
    $jsonOutput = "[$( ($itemsArray | ForEach-Object { $_ | ConvertTo-Json -Depth 80 -Compress }) -join ",`n")]"
    $jsonOutput | Set-Content -Path $script:RestrictionsJsonFile -Encoding UTF8
}

function Import-AppfireRestrictionCsv {
    $dlg = New-Object System.Windows.Forms.OpenFileDialog
    $dlg.Filter = "Fichiers CSV (*.csv)|*.csv|Tous les fichiers (*.*)|*.*"
    $dlg.Title = "Sélectionne le CSV Appfire/SQL des restrictions"
    if ($dlg.ShowDialog() -ne "OK") { return }

    $csvPath = $dlg.FileName
    Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Lecture $csvPath" "INFO"

    try {
        $firstLine = (Get-Content -Path $csvPath -TotalCount 1 -Encoding UTF8)
        $delimiter = if ($firstLine -match ';') { ';' } else { ',' }
        Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Délimiteur : '$delimiter'" "INFO"

        $rows = Import-Csv -Path $csvPath -Delimiter $delimiter -Encoding UTF8
        $totalRows = @($rows).Count
        Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Lignes CSV : $totalRows" "INFO"

        if ($totalRows -eq 0) {
            Show-MsgBox "Le CSV est vide." "Restrictions" "Warning"
            return
        }

        $firstRow = $rows[0]
        $availableColumns = @($firstRow.PSObject.Properties.Name)
        Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Colonnes détectées : $($availableColumns -join ' | ')" "INFO"

        function Find-ColumnName {
            param([string[]]$Candidates, [string[]]$AvailableColumns)
            foreach ($candidate in $Candidates) {
                $candidateNorm = ($candidate -replace "[^a-zA-Z0-9]", "").ToLowerInvariant()
                foreach ($col in $AvailableColumns) {
                    $colNorm = ($col -replace "[^a-zA-Z0-9]", "").ToLowerInvariant()
                    if ($colNorm -eq $candidateNorm) { return $col }
                }
            }
            return $null
        }

        $colContentId   = Find-ColumnName -Candidates @("Content ID", "ContentId", "content_id", "contentId", "id") -AvailableColumns $availableColumns
        $colTitle       = Find-ColumnName -Candidates @("Title", "title", "page_title", "pageTitle") -AvailableColumns $availableColumns
        $colSpaceKey    = Find-ColumnName -Candidates @("Space Key", "SpaceKey", "space_key", "spaceKey", "space") -AvailableColumns $availableColumns
        $colPermType    = Find-ColumnName -Candidates @("Permission Type", "PermissionType", "permission_type", "permissionType") -AvailableColumns $availableColumns
        $colUsername    = Find-ColumnName -Candidates @("Username", "username", "user_name", "userName") -AvailableColumns $availableColumns
        $colUserEmail   = Find-ColumnName -Candidates @("User email", "UserEmail", "user_email", "userEmail") -AvailableColumns $availableColumns
        $colUserKey     = Find-ColumnName -Candidates @("User Key", "UserKey", "user_key", "userKey") -AvailableColumns $availableColumns
        $colGroupName   = Find-ColumnName -Candidates @("Group name", "GroupName", "Group Name", "groupname", "group_name") -AvailableColumns $availableColumns
        $colRestSource  = Find-ColumnName -Candidates @("Restriction type", "RestrictionType", "restriction_type", "Restriction Type", "restriction_source", "RestrictionSource") -AvailableColumns $availableColumns
        $colAncestorId  = Find-ColumnName -Candidates @("Ancestor ID", "AncestorId", "ancestor_id", "ancestorId") -AvailableColumns $availableColumns

        Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Mapping : ContentId=$colContentId | Title=$colTitle | SpaceKey=$colSpaceKey | PermType=$colPermType | Username=$colUsername | UserKey=$colUserKey | GroupName=$colGroupName | RestSource=$colRestSource | AncestorId=$colAncestorId" "INFO"

        if ([string]::IsNullOrWhiteSpace($colContentId)) {
            Show-MsgBox "Colonne Content ID introuvable dans le CSV.`r`n`r`nColonnes détectées :`r`n$($availableColumns -join "`r`n")" "Restrictions" "Error"
            return
        }
        if ([string]::IsNullOrWhiteSpace($colPermType)) {
            Show-MsgBox "Colonne Permission Type introuvable dans le CSV.`r`n`r`nColonnes détectées :`r`n$($availableColumns -join "`r`n")" "Restrictions" "Error"
            return
        }

        function Get-CleanCellValue {
            param($Row, $ColumnName)
            if ([string]::IsNullOrWhiteSpace($ColumnName)) { return "" }
            $prop = $Row.PSObject.Properties[$ColumnName]
            if ($null -eq $prop) { return "" }
            $rawValue = [string]$prop.Value
            if ([string]::IsNullOrWhiteSpace($rawValue)) { return "" }
            $cleaned = $rawValue -replace "^'", ""
            $cleaned = Normalize-DisplayText $cleaned
            return $cleaned
        }

        $grouped = @{}
        $skippedNoId = 0

        foreach ($row in $rows) {
            $contentId = Get-CleanCellValue -Row $row -ColumnName $colAncestorId
            $herited = $true
            if ($contentId -eq "") {
                $contentId = Get-CleanCellValue -Row $row -ColumnName $colContentId
                $herited = $false
            }
            
            if ($contentId -eq "") {
                $skippedNoId++
                Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Ligne ignorée : Content ID nul" "WARN"
                continue
            }

            $permType = (Get-CleanCellValue -Row $row -ColumnName $colPermType).ToUpperInvariant()
            $username = Get-CleanCellValue -Row $row -ColumnName $colUsername
            $userEmail = Get-CleanCellValue -Row $row -ColumnName $colUserEmail
            $groupname = Get-CleanCellValue -Row $row -ColumnName $colGroupName

            if ([string]::IsNullOrWhiteSpace($username) -and -not [string]::IsNullOrWhiteSpace($colUserKey)) {
                $username = Get-CleanCellValue -Row $row -ColumnName $colUserKey
            }
            
            if (-not $grouped.ContainsKey($contentId)) {
                $title = Get-CleanCellValue -Row $row -ColumnName $colTitle
                $spaceKey = Get-CleanCellValue -Row $row -ColumnName $colSpaceKey
                if ($herited) {
                    $path = "/rest/api/content/${contentId}"
                    $result = Invoke-ConfluenceApi -Method "GET" -Path $path -ExpectedStatusCodes @(200)
                    if ($null -ne $result) {
                        $spaceKey = [string]$result.space.key
                        $title = [string]$result.title
                        Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Info API pour contentId=$contentId : spaceKey='$spaceKey' title='$title'" "INFO"
                    } else {
                        Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Échec appel API pour contentId=$contentId" "WARN"
                    }
                }
                $grouped[$contentId] = [PSCustomObject]@{
                    pageId            = $contentId
                    spaceKey          = $spaceKey
                    title             = $title
                    readUsers         = New-Object System.Collections.ArrayList
                    readUsersEmails   = New-Object System.Collections.ArrayList
                    readGroups        = New-Object System.Collections.ArrayList
                    updateUsers       = New-Object System.Collections.ArrayList
                    updateUsersEmails = New-Object System.Collections.ArrayList
                    updateGroups      = New-Object System.Collections.ArrayList
                }
            }

            $entry = $grouped[$contentId]

            if ($permType -eq "VIEW" -or $permType -eq "READ") {
                if (-not [string]::IsNullOrWhiteSpace($username))  { Add-UniqueStringToArrayList -List ([object]$entry.readUsers) -Value $username }
                if (-not [string]::IsNullOrWhiteSpace($userEmail)) { Add-UniqueStringToArrayList -List ([object]$entry.readUsersEmails) -Value $userEmail }
                if (-not [string]::IsNullOrWhiteSpace($groupname)) { Add-UniqueStringToArrayList -List ([object]$entry.readGroups) -Value $groupname }
            } elseif ($permType -eq "EDIT" -or $permType -eq "UPDATE") {
                if (-not [string]::IsNullOrWhiteSpace($username))  { Add-UniqueStringToArrayList -List ([object]$entry.updateUsers) -Value $username }
                if (-not [string]::IsNullOrWhiteSpace($userEmail)) { Add-UniqueStringToArrayList -List ([object]$entry.updateUsersEmails) -Value $userEmail }
                if (-not [string]::IsNullOrWhiteSpace($groupname)) { Add-UniqueStringToArrayList -List ([object]$entry.updateGroups) -Value $groupname }
            } else {
                Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Permission Type ignoré page=$contentId valeur='$permType'" "WARN"
            }
        }

        Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Pages distinctes : $($grouped.Count) | Lignes ignorées (pas de Content ID) : $skippedNoId" "INFO"

        Initialize-RestrictionDataTable
        $script:RestrictionJsonData = @()

        foreach ($key in $grouped.Keys) {
            $entry = $grouped[$key]
            $pageIdClean = ConvertTo-CleanPageId ([string]$entry.pageId)
            if ([string]::IsNullOrWhiteSpace($pageIdClean)) {
                Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Entrée groupée ignorée : pageId invalide='$($entry.pageId)'" "ERROR"
                continue
            }

            $rtRow = $script:RestrictionTable.NewRow()
            $rtRow["pageId"]            = $pageIdClean
            $rtRow["pageTitle"]         = $entry.title
            $rtRow["pageUrl"]           = "$($script:ConfluenceUrl.TrimEnd('/'))/pages/viewpage.action?pageId=$pageIdClean"
            $rtRow["spaceKey"]          = $entry.spaceKey
            $rtRow["workflowName"]      = ""

            $hasContent = (@($entry.readUsers).Count -gt 0 -or @($entry.readGroups).Count -gt 0 -or @($entry.updateUsers).Count -gt 0 -or @($entry.updateGroups).Count -gt 0)

            $principalSummary = Get-RestrictionPrincipalSummary -ReadUsers @($entry.readUsers) -ReadGroups @($entry.readGroups) -UpdateUsers @($entry.updateUsers) -UpdateGroups @($entry.updateGroups)

            if ($hasContent) {
                $rtRow["hasRestrictions"] = "Oui"
                $rtRow["actionRequired"]  = "Lever sur pageId"
                $rtRow["saved"]           = "Oui"
                $rtRow["removed"]         = "Non"
                $rtRow["restored"]        = "Non"
                $rtRow["message"]         = "Restriction directe importée depuis CSV Appfire/SQL"
                Set-RestrictionRealAction -Row $rtRow -Action "A_TRAITER_DIRECTE" -Reason "Restriction directe détectée sur cette page." -Result "PENDING"
            } else {
                $rtRow["hasRestrictions"] = "Non"
                $rtRow["actionRequired"]  = "Aucune"
                $rtRow["saved"]           = "Non"
                $rtRow["removed"]         = "Non"
                $rtRow["restored"]        = "Non"
                $rtRow["message"]         = "Aucune restriction directe exploitable dans le CSV"
                Set-RestrictionRealAction -Row $rtRow -Action "AUCUNE_ACTION" -Reason "Aucune restriction directe exploitable." -Result "SKIP"
            }

            $rtRow["principalSummary"] = $principalSummary
            $rtRow["readUsers"]    = (@($entry.readUsers)    -join ", ")
            $rtRow["readGroups"]   = (@($entry.readGroups)   -join ", ")
            $rtRow["updateUsers"]  = (@($entry.updateUsers)  -join ", ")
            $rtRow["updateGroups"] = (@($entry.updateGroups) -join ", ")
            $script:RestrictionTable.Rows.Add($rtRow)

            if ($hasContent) {
                $script:RestrictionJsonData += [PSCustomObject]@{
                    pageId       = $pageIdClean
                    spaceKey     = $entry.spaceKey
                    pageTitle    = $entry.title
                    readUsers    = @($entry.readUsersEmails)
                    readGroups   = @($entry.readGroups)
                    updateUsers  = @($entry.updateUsersEmails)
                    updateGroups = @($entry.updateGroups)
                }
            }
        }

        $script:GridRestrictions.ItemsSource = $script:RestrictionTable.DefaultView

        try {
            @($script:RestrictionJsonData) | ConvertTo-Json -Depth 50 | Set-Content -Path $script:RestrictionsJsonFile -Encoding UTF8
            Write-AppLog "[RESTRICTIONS][IMPORT-CSV] JSON généré : $script:RestrictionsJsonFile ($($script:RestrictionJsonData.Count) page(s) avec contenu)" "OK"
        } catch {
            Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Erreur écriture JSON : $($_.Exception.Message)" "ERROR"
        }

        Refresh-RestrictionStats
        Set-ProcedureStepState -Ordre 9  -Statut "Réalisé" -Preuve "Import CSV Appfire : $($grouped.Count) page(s)"
        Set-ProcedureStepState -Ordre 10 -Statut "Réalisé" -Preuve "JSON généré"

        Show-MsgBox @"
Import terminé.

Pages distinctes        : $($grouped.Count)
Pages avec restrictions : $($script:RestrictionJsonData.Count)
Lignes CSV traitées     : $totalRows
Lignes ignorées         : $skippedNoId

JSON sauvegardé :
$script:RestrictionsJsonFile
"@ "Restrictions"
    } catch {
        Write-AppLog "[RESTRICTIONS][IMPORT-CSV] Erreur : $($_.Exception.Message)" "ERROR"
        Show-MsgBox "Erreur import CSV : $($_.Exception.Message)" "Restrictions" "Error"
    }
}

# ============================================================
# ANALYSE REST
# ============================================================

function Analyze-Restrictions {
    if ($null -eq $script:WorkflowDataTable -or $script:WorkflowDataTable.Rows.Count -eq 0) { Show-MsgBox "Aucune donnée workflow chargée." "Restrictions" "Warning"; return }
    try { Read-ConnectionFromUi } catch { Show-MsgBox $_.Exception.Message "Restrictions" "Warning"; return }

    Initialize-RestrictionDataTable
    $script:RestrictionJsonData = @()

    $totalRows = $script:WorkflowDataTable.Rows.Count
    $indexRow = 0
    Write-AppLog "[RESTRICTIONS][COLLECTE] Début analyse totalPages=$totalRows" "INFO"

    foreach ($wfRow in $script:WorkflowDataTable.Rows) {
        $indexRow++
        $pageIdValue = ConvertTo-CleanPageId ([string]$wfRow["pageId"])
        $spaceKeyValue = [string]$wfRow["spaceKey"]
        $pageTitleValue = [string]$wfRow["pageTitle"]

        if ([string]::IsNullOrWhiteSpace($pageIdValue)) {
            Write-AppLog "[RESTRICTIONS][COLLECTE] [$indexRow/$totalRows] pageId invalide ignoré : $($wfRow['pageId'])" "ERROR"
            continue
        }

        Write-AppLog "[RESTRICTIONS][COLLECTE] [$indexRow/$totalRows] page=$pageIdValue" "INFO"

        $rtRow = $script:RestrictionTable.NewRow()
        $rtRow["pageId"]       = $pageIdValue
        $rtRow["pageUrl"]      = "$($script:ConfluenceUrl.TrimEnd('/'))/pages/viewpage.action?pageId=$pageIdValue"
        $rtRow["spaceKey"]     = $spaceKeyValue
        $rtRow["pageTitle"]    = Normalize-DisplayText $pageTitleValue
        $rtRow["workflowName"] = [string]$wfRow["workflowName"]
        try {
            $restrictionData = Get-ConfluenceRestrictions -PageId $pageIdValue
            $hasDirectRestrictions = Test-RestrictionObjectHasEntries -RestrictionObject $restrictionData

            if ($hasDirectRestrictions) {
                $rtRow["hasRestrictions"] = "Oui"
                $rtRow["restrictionSource"] = "explicit/rest"
                $rtRow["ancestorIds"] = ""
                $rtRow["actionRequired"] = "Lever sur pageId"
                $rtRow["readUsers"]       = (@($restrictionData.readUsers) -join ", ")
                $rtRow["readGroups"]      = (@($restrictionData.readGroups) -join ", ")
                $rtRow["updateUsers"]     = (@($restrictionData.updateUsers) -join ", ")
                $rtRow["updateGroups"]    = (@($restrictionData.updateGroups) -join ", ")
                $rtRow["saved"]           = "Oui"
                $rtRow["removed"]         = "Non"
                $rtRow["restored"]        = "Non"
                $rtRow["message"]         = "Restrictions directes sur la page"
                $rtRow["principalSummary"] = Get-RestrictionPrincipalSummary -ReadUsers @($restrictionData.readUsers) -ReadGroups @($restrictionData.readGroups) -UpdateUsers @($restrictionData.updateUsers) -UpdateGroups @($restrictionData.updateGroups)
                Set-RestrictionRealAction -Row $rtRow -Action "A_TRAITER_DIRECTE" -Reason "Restriction directe détectée par REST sur cette page." -Result "PENDING"
                $script:RestrictionJsonData += $restrictionData
                $wfRow["restrictionState"] = "Restrictions directes détectées"
            } else {
                $inherited = Get-InheritedRestrictionInfo -PageId $pageIdValue -SpaceKey $spaceKeyValue
                if ($null -ne $inherited) {
                    $src = $inherited.restrictions
                    $rtRow["hasRestrictions"] = "Héritées"
                    $rtRow["restrictionSource"] = "inherited"
                    $rtRow["ancestorIds"] = [string]$inherited.sourcePageId
                    $rtRow["actionRequired"] = "Validation parent requise"
                    $rtRow["readUsers"]       = (@($src.readUsers) -join ", ")
                    $rtRow["readGroups"]      = (@($src.readGroups) -join ", ")
                    $rtRow["updateUsers"]     = (@($src.updateUsers) -join ", ")
                    $rtRow["updateGroups"]    = (@($src.updateGroups) -join ", ")
                    $rtRow["saved"]           = "Non"
                    $rtRow["removed"]         = "Non"
                    $rtRow["restored"]        = "Non"
                    $rtRow["message"]         = "Restrictions héritées via $($inherited.mode). Source : $($inherited.sourcePageId)."
                    $rtRow["principalSummary"] = Get-RestrictionPrincipalSummary -ReadUsers @($src.readUsers) -ReadGroups @($src.readGroups) -UpdateUsers @($src.updateUsers) -UpdateGroups @($src.updateGroups)
                    $rtRow["removed"] = "IGNORÉ"
                    $rtRow["restored"] = "IGNORÉ"
                    Set-RestrictionRealAction -Row $rtRow -Action "IGNORE_HERITEE" -Reason "Restriction héritée depuis la page parente $($inherited.sourcePageId). Aucune suppression directe sur cette page enfant." -Result "SKIP"
                    $wfRow["restrictionState"] = "Restrictions héritées"
                } else {
                    $rtRow["hasRestrictions"] = "Non"
                    $rtRow["restrictionSource"] = "none"
                    $rtRow["ancestorIds"] = ""
                    $rtRow["actionRequired"] = "Aucune"
                    $rtRow["readUsers"] = ""; $rtRow["readGroups"] = ""; $rtRow["updateUsers"] = ""; $rtRow["updateGroups"] = ""
                    $rtRow["saved"] = "Oui"; $rtRow["removed"] = "Non"; $rtRow["restored"] = "Non"
                    $rtRow["message"] = "Aucune restriction directe ni héritée détectée"
                    $rtRow["principalSummary"] = ""
                    Set-RestrictionRealAction -Row $rtRow -Action "AUCUNE_ACTION" -Reason "Aucune restriction directe ni héritée détectée." -Result "SKIP"
                    $wfRow["restrictionState"] = "Aucune restriction"
                }
            }
        } catch {
            $rtRow["hasRestrictions"] = "Erreur"
            $rtRow["restrictionSource"] = "error"
            $rtRow["ancestorIds"] = ""
            $rtRow["actionRequired"] = "Corriger erreur API"
            $rtRow["saved"] = "Non"; $rtRow["removed"] = "Non"; $rtRow["restored"] = "Non"; $rtRow["message"] = $_.Exception.Message
            $wfRow["restrictionState"] = "Erreur restrictions"
            Write-AppLog "[RESTRICTIONS] page=$pageIdValue ERREUR $($_.Exception.Message)" "ERROR"
        }
        $script:RestrictionTable.Rows.Add($rtRow)
        [System.Windows.Forms.Application]::DoEvents()
    }

    $script:GridRestrictions.ItemsSource = $script:RestrictionTable.DefaultView
    $script:GridWorkflow.Items.Refresh()
    try {
        @($script:RestrictionJsonData) | ConvertTo-Json -Depth 50 | Set-Content -Path $script:RestrictionsJsonFile -Encoding UTF8
        Write-AppLog "[RESTRICTIONS] JSON généré : $script:RestrictionsJsonFile" "OK"
    } catch { Write-AppLog "Erreur écriture JSON : $($_.Exception.Message)" "ERROR" }

    Refresh-RestrictionStats
    Set-ProcedureStepState -Ordre 9  -Statut "Réalisé" -Preuve "Analyse restrictions terminée"
    Set-ProcedureStepState -Ordre 10 -Statut "Réalisé" -Preuve "JSON généré"
    Write-AppLog "[RESTRICTIONS][COLLECTE] Fin" "OK"
}

# ============================================================
# LEVÉE
# ============================================================

function Refresh-RestrictionStats {
    if ($null -eq $script:RestrictionTable) { return }
    $total = $script:RestrictionTable.Rows.Count
    $withRestrictions = @($script:RestrictionTable.Rows | Where-Object { ([string]$_["hasRestrictions"] -eq "Oui") -or ([string]$_["hasRestrictions"] -eq "Héritées") -or ([string]$_["hasRestrictions"] -eq "Oui + Héritées") }).Count
    $saved = @($script:RestrictionTable.Rows | Where-Object { [string]$_["saved"] -eq "Oui" }).Count
    $removed = @($script:RestrictionTable.Rows | Where-Object { ([string]$_["removed"] -eq "Oui") -or ([string]$_["removed"] -eq "DRY-RUN") }).Count
    $restored = @($script:RestrictionTable.Rows | Where-Object { ([string]$_["restored"] -eq "Oui") -or ([string]$_["restored"] -eq "DRY-RUN") }).Count
    $ignored = @($script:RestrictionTable.Rows | Where-Object { [string]$_["actionReelle"] -eq "IGNORE_HERITEE" }).Count
    if ($null -ne $script:LblRestrictionsStats) { $script:LblRestrictionsStats.Content = "Pages analysées : $total | Avec restrictions : $withRestrictions | Sauvegardées : $saved | Levées : $removed | Restaurées : $restored | Héritées ignorées : $ignored" }
}

function Get-ConfluenceRestrictions {
    param([Parameter(Mandatory=$true)][string]$PageId)
    $PageId = ConvertTo-CleanPageId $PageId
    if ([string]::IsNullOrWhiteSpace($PageId)) { throw "pageId invalide." }

    $readUsers = New-Object System.Collections.ArrayList
    $readGroups = New-Object System.Collections.ArrayList
    $updateUsers = New-Object System.Collections.ArrayList
    $updateGroups = New-Object System.Collections.ArrayList

    foreach ($op in @("read","update")) {
        $path = "/rest/api/content/${PageId}/restriction/byOperation/${op}?expand=restrictions.user,restrictions.group"
        $result = Invoke-ConfluenceApi -Method "GET" -Path $path -ExpectedStatusCodes @(200)

        if ($result -and $result.restrictions -and $result.restrictions.user -and $result.restrictions.user.results) {
            foreach ($u in @($result.restrictions.user.results)) {
                $name = ""
                if ($u.username) { $name = [string]$u.username }
                elseif ($u.name) { $name = [string]$u.name }
                elseif ($u.userKey) { $name = [string]$u.userKey }
                elseif ($u.accountId) { $name = [string]$u.accountId }
                elseif ($u.displayName) { $name = [string]$u.displayName }
                if ($op -eq "read") { Add-UniqueStringToArrayList -List ([object]$readUsers) -Value $name } else { Add-UniqueStringToArrayList -List ([object]$updateUsers) -Value $name }
            }
        }

        if ($result -and $result.restrictions -and $result.restrictions.group -and $result.restrictions.group.results) {
            foreach ($g in @($result.restrictions.group.results)) {
                $name = ""
                if ($g.name) { $name = [string]$g.name }
                elseif ($g.groupName) { $name = [string]$g.groupName }
                elseif ($g.displayName) { $name = [string]$g.displayName }
                if ($op -eq "read") { Add-UniqueStringToArrayList -List ([object]$readGroups) -Value $name } else { Add-UniqueStringToArrayList -List ([object]$updateGroups) -Value $name }
            }
        }
    }

    return [PSCustomObject]@{
        pageId = $PageId
        readUsers = @($readUsers)
        readGroups = @($readGroups)
        updateUsers = @($updateUsers)
        updateGroups = @($updateGroups)
    }
}

function Test-RestrictionObjectHasEntries {
    param([Parameter(Mandatory=$true)]$RestrictionObject)
    return (@($RestrictionObject.readUsers).Count -gt 0 -or @($RestrictionObject.readGroups).Count -gt 0 -or @($RestrictionObject.updateUsers).Count -gt 0 -or @($RestrictionObject.updateGroups).Count -gt 0)
}

function New-EmptyRestrictionPayload {
    return @(
        @{ operation="read"; restrictions=@{ user=@(); group=@() } },
        @{ operation="update"; restrictions=@{ user=@(); group=@() } }
    )
}

function Remove-ConfluenceRestrictions {
    param([Parameter(Mandatory=$true)][string]$PageId)
    $PageId = ConvertTo-CleanPageId $PageId
    if ([string]::IsNullOrWhiteSpace($PageId)) { throw "pageId invalide." }
    Invoke-ConfluenceApi -Method "PUT" -Path "/rest/api/content/$PageId/restriction" -Body (New-EmptyRestrictionPayload) -ExpectedStatusCodes @(200,204) | Out-Null
}

function New-ConfluenceRestrictionUserObject {
    param(
        [Parameter(Mandatory = $true)]
        [string]$UserIdentifier
    )

    $cleanUser = ConvertTo-CleanCsvValue $UserIdentifier

    if ([string]::IsNullOrWhiteSpace($cleanUser)) {
        return $null
    }

    return @{
        type     = "known"
        username = $cleanUser
    }
}

function New-ConfluenceRestrictionGroupObject {
    param(
        [Parameter(Mandatory = $true)]
        [string]$GroupName
    )

    $cleanGroup = ConvertTo-CleanCsvValue $GroupName

    if ([string]::IsNullOrWhiteSpace($cleanGroup)) {
        return $null
    }

    return @{
        type = "group"
        name = $cleanGroup
    }
}

function New-ConfluenceRestrictionArrayPayload {
    param(
        [AllowNull()]$ReadUsers,
        [AllowNull()]$ReadGroups,
        [AllowNull()]$UpdateUsers,
        [AllowNull()]$UpdateGroups,
        [AllowNull()][AllowEmptyString()][string]$SafetyAdminUserName = ""
    )

    $payload = New-Object System.Collections.ArrayList

    $readUserObjects = New-Object System.Collections.ArrayList
    $readGroupObjects = New-Object System.Collections.ArrayList
    $updateUserObjects = New-Object System.Collections.ArrayList
    $updateGroupObjects = New-Object System.Collections.ArrayList

    foreach ($u in @($ReadUsers)) {
        $uo = New-ConfluenceRestrictionUserObject -UserIdentifier ([string]$u)
        if ($null -ne $uo) {
            [void]$readUserObjects.Add($uo)
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($SafetyAdminUserName)) {
        $alreadyPresent = $false

        foreach ($existingUser in @($readUserObjects)) {
            if ([string]$existingUser.username -eq $SafetyAdminUserName) {
                $alreadyPresent = $true
                break
            }
        }

        if (-not $alreadyPresent) {
            $adminObject = New-ConfluenceRestrictionUserObject -UserIdentifier $SafetyAdminUserName
            if ($null -ne $adminObject) {
                [void]$readUserObjects.Add($adminObject)
            }
        }
    }

    foreach ($g in @($ReadGroups)) {
        $go = New-ConfluenceRestrictionGroupObject -GroupName ([string]$g)
        if ($null -ne $go) {
            [void]$readGroupObjects.Add($go)
        }
    }

    foreach ($u in @($UpdateUsers)) {
        $uo = New-ConfluenceRestrictionUserObject -UserIdentifier ([string]$u)
        if ($null -ne $uo) {
            [void]$updateUserObjects.Add($uo)
        }
    }

    # Sécurité Confluence Data Center : si des restrictions EDIT/UPDATE sont restaurées,
    # le compte courant doit aussi rester explicitement autorisé en UPDATE.
    # Sinon Confluence peut refuser le PUT avec HTTP 400, même si le compte est déjà en READ.
    if (-not [string]::IsNullOrWhiteSpace($SafetyAdminUserName)) {
        $hasUpdateRestriction = (@($UpdateUsers).Count -gt 0 -or @($UpdateGroups).Count -gt 0)
        if ($hasUpdateRestriction) {
            $alreadyPresentUpdate = $false

            foreach ($existingUpdateUser in @($updateUserObjects)) {
                if ([string]$existingUpdateUser.username -eq $SafetyAdminUserName) {
                    $alreadyPresentUpdate = $true
                    break
                }
            }

            if (-not $alreadyPresentUpdate) {
                $adminUpdateObject = New-ConfluenceRestrictionUserObject -UserIdentifier $SafetyAdminUserName
                if ($null -ne $adminUpdateObject) {
                    [void]$updateUserObjects.Add($adminUpdateObject)
                }
            }
        }
    }

    foreach ($g in @($UpdateGroups)) {
        $go = New-ConfluenceRestrictionGroupObject -GroupName ([string]$g)
        if ($null -ne $go) {
            [void]$updateGroupObjects.Add($go)
        }
    }

    if ($readUserObjects.Count -gt 0 -or $readGroupObjects.Count -gt 0) {
        [void]$payload.Add(
            @{
                operation = "read"
                restrictions = @{
                    user  = @($readUserObjects)
                    group = @($readGroupObjects)
                }
            }
        )
    }

    if ($updateUserObjects.Count -gt 0 -or $updateGroupObjects.Count -gt 0) {
        [void]$payload.Add(
            @{
                operation = "update"
                restrictions = @{
                    user  = @($updateUserObjects)
                    group = @($updateGroupObjects)
                }
            }
        )
    }

    return ,@($payload)
}

function Restore-ConfluenceRestrictions {
    param(
        [Parameter(Mandatory = $true)]
        $RestrictionObject
    )

    $pageIdRaw = [string]$RestrictionObject.pageId
    $pageIdValue = ConvertTo-CleanPageId $pageIdRaw

    if ([string]::IsNullOrWhiteSpace($pageIdValue)) {
        throw "Objet restriction invalide : pageId absent, multiple ou non numérique. Valeur reçue='$pageIdRaw'"
    }

    $readUserCount    = @($RestrictionObject.readUsers).Count
    $readGroupCount   = @($RestrictionObject.readGroups).Count
    $updateUserCount  = @($RestrictionObject.updateUsers).Count
    $updateGroupCount = @($RestrictionObject.updateGroups).Count

    if (($readUserCount + $readGroupCount + $updateUserCount + $updateGroupCount) -eq 0) {
        Write-AppLog "[RESTRICTIONS][RESTORE] page=$pageIdValue aucun user/groupe à restaurer, ignorée" "WARN"
        return
    }

    Write-AppLog "[RESTRICTIONS][RESTORE] Début page=$pageIdValue readUsers=$readUserCount readGroups=$readGroupCount updateUsers=$updateUserCount updateGroups=$updateGroupCount" "INFO"

    $safetyAdmin = $script:Username

    if ([string]::IsNullOrWhiteSpace($safetyAdmin)) {
        $safetyAdmin = "admin_abu17616"
    }

    $arrayPayload = New-ConfluenceRestrictionArrayPayload `
        -ReadUsers @($RestrictionObject.readUsers) `
        -ReadGroups @($RestrictionObject.readGroups) `
        -UpdateUsers @($RestrictionObject.updateUsers) `
        -UpdateGroups @($RestrictionObject.updateGroups) `
        -SafetyAdminUserName $safetyAdmin

    if ($null -eq $arrayPayload -or @($arrayPayload).Count -eq 0) {
        throw "Payload vide pour page=$pageIdValue"
    }

    $payloadLog = ConvertTo-Json -InputObject $arrayPayload -Depth 30 -Compress
    Write-AppLog "[RESTRICTIONS][RESTORE] PUT TABLEAU page=$pageIdValue payload=$payloadLog" "INFO"

    try {
        Invoke-ConfluenceApi `
            -Method "PUT" `
            -Path "/rest/api/content/$pageIdValue/restriction" `
            -Body $arrayPayload `
            -ExpectedStatusCodes @(200,204) | Out-Null

        Write-AppLog "[RESTRICTIONS][RESTORE] OK page=$pageIdValue" "OK"
        return
    }
    catch {
        throw "Erreur restauration restrictions page=$pageIdValue : $($_.Exception.Message)"
    }
}

function Remove-DetectedRestrictions {
    if ($null -eq $script:RestrictionTable -or $script:RestrictionTable.Rows.Count -eq 0) { Show-MsgBox "Aucune restriction." "Restrictions" "Warning"; return }
    try { Read-ConnectionFromUi } catch { Show-MsgBox $_.Exception.Message "Restrictions" "Warning"; return }

    Reset-StopRequest

    $rows = @($script:RestrictionTable.Rows | Where-Object {
        ([string]$_["hasRestrictions"] -eq "Oui") -and
        ([string]$_["actionRequired"] -eq "Lever sur pageId")
    })

    if ($rows.Count -eq 0) { Show-MsgBox "Aucune restriction directe. Les restrictions héritées sont marquées IGNORÉ / IGNORE_HERITEE dans le rapport." "Restrictions"; return }

    $confirm = Show-ConfirmBox -Msg "Levée restrictions`r`nPages directes : $($rows.Count)`r`nDryRun : $($script:DryRun)" -Title "Restrictions" -Icon "Warning"
    if ($confirm -ne "Yes") { return }

    $ok = 0
    $errors = 0

    foreach ($row in $rows) {
        try { Test-StopRequested } catch { Write-AppLog $_.Exception.Message "WARN"; break }

        $pageIdValue = ConvertTo-CleanPageId ([string]$row["pageId"])
        try {
            if ([string]::IsNullOrWhiteSpace($pageIdValue)) { throw "pageId invalide : $($row['pageId'])" }

            if ($script:DryRun) {
                $row["removed"] = "DRY-RUN"
                $row["message"] = "Simulation levée"
                Set-RestrictionRealAction -Row $row -Action "SUPPRESSION_DIRECTE_DRYRUN" -Reason "Restriction directe ciblée ; simulation uniquement." -Result "DRY-RUN"
                Write-AppLog "DRY-RUN levée restriction pageId=$pageIdValue" "WARN"
            } else {
                Remove-ConfluenceRestrictions -PageId $pageIdValue
                $row["removed"] = "Oui"
                $row["message"] = "Restrictions levées"
                Set-RestrictionRealAction -Row $row -Action "SUPPRESSION_DIRECTE" -Reason "Restriction directe supprimée sur la page cible." -Result "200/204"
                Write-AppLog "Levée restriction réalisée pageId=$pageIdValue" "OK"
            }
            $ok++
        } catch {
            $row["removed"] = "Erreur"
            $row["message"] = $_.Exception.Message
            Set-RestrictionRealAction -Row $row -Action "ERREUR_SUPPRESSION" -Reason $_.Exception.Message -Result "ERROR"
            $errors++
            Write-AppLog "Erreur levée restriction pageId=$pageIdValue : $($_.Exception.Message)" "ERROR"
        }

        if ($null -ne $script:GridRestrictions) { try { $script:GridRestrictions.Dispatcher.Invoke([action]{ $script:GridRestrictions.Items.Refresh() }) } catch {} }
        [System.Windows.Forms.Application]::DoEvents()
    }

    Refresh-RestrictionStats
    if ($errors -eq 0 -and $ok -gt 0) { Set-ProcedureStepState -Ordre 11 -Statut "Réalisé" -Preuve "$ok levée(s)" }
    elseif ($ok -gt 0) { Set-ProcedureStepState -Ordre 11 -Statut "En cours" -Preuve "$ok OK / $errors erreur(s)" }
    else { Set-ProcedureStepState -Ordre 11 -Statut "Bloqué" -Preuve "$errors erreur(s)" }

    Show-MsgBox "Levée restrictions`r`nOK : $ok`r`nErreurs : $errors" "Restrictions"
}

function Restore-RestrictionsFromJson {
    if (-not (Test-Path $script:RestrictionsJsonFile)) {
        Show-MsgBox "Fichier JSON restrictions introuvable : $script:RestrictionsJsonFile" "Restrictions" "Warning"
        return
    }

    try {
        $jsonRaw = Get-Content -Path $script:RestrictionsJsonFile -Raw -Encoding UTF8
        $jsonData = $jsonRaw | ConvertFrom-Json
        $json = @($jsonData)
        if ($null -eq $json -or $json.Count -eq 0) {
            Show-MsgBox "Le JSON est vide. Aucune restriction à restaurer." "Restrictions" "Warning"
            return
        }
    } catch {
        Show-MsgBox "Erreur lecture JSON : $($_.Exception.Message)" "Restrictions" "Error"
        return
    }

    try { Read-ConnectionFromUi } catch {
        Show-MsgBox $_.Exception.Message "Restrictions" "Warning"
        return
    }

    $validItems = @()
    $invalidItems = 0
    foreach ($item in $json) {
        $pageIdRaw = [string]$item.pageId
        $pageIdValue = ConvertTo-CleanPageId $pageIdRaw
        if ([string]::IsNullOrWhiteSpace($pageIdValue)) {
            Write-AppLog "[RESTRICTIONS][RESTORE] Entrée JSON invalide ignorée : pageId='$pageIdRaw'" "ERROR"
            $invalidItems++
            continue
        }
        $validItems += $item
    }

    if ($validItems.Count -eq 0) {
        Show-MsgBox "Aucune entrée JSON valide. Vérifie que pageId contient un seul nombre par entrée." "Restrictions" "Error"
        return
    }

    $totalPages = $validItems.Count
    $totalReadUsers = 0; $totalReadGroups = 0; $totalUpdateUsers = 0; $totalUpdateGroups = 0
    foreach ($item in $validItems) {
        $totalReadUsers    += @($item.readUsers).Count
        $totalReadGroups   += @($item.readGroups).Count
        $totalUpdateUsers  += @($item.updateUsers).Count
        $totalUpdateGroups += @($item.updateGroups).Count
    }

    $confirmMsg = @"
Restauration des restrictions.

Pages à traiter : $totalPages
Entrées invalides ignorées : $invalidItems
Utilisateurs en lecture : $totalReadUsers
Groupes en lecture : $totalReadGroups
Utilisateurs en modification : $totalUpdateUsers
Groupes en modification : $totalUpdateGroups

Mode simulation : $($script:DryRun)

Continuer ?
"@

    $confirm = [System.Windows.MessageBox]::Show($confirmMsg, "Confirmation restauration", [System.Windows.MessageBoxButton]::YesNo, [System.Windows.MessageBoxImage]::Question)
    if ($confirm -ne "Yes") { return }

    Write-AppLog "[RESTRICTIONS][RESTORE] === Début restauration globale ===" "INFO"
    Write-AppLog "[RESTRICTIONS][RESTORE] Pages=$totalPages Invalides=$invalidItems DryRun=$($script:DryRun)" "INFO"

    $okCount = 0
    $errorCount = 0
    $errorDetails = New-Object System.Collections.ArrayList

    foreach ($item in $validItems) {
        $pageIdRaw = [string]$item.pageId
        $pageIdValue = ConvertTo-CleanPageId $pageIdRaw

        if ([string]::IsNullOrWhiteSpace($pageIdValue)) {
            Write-AppLog "[RESTRICTIONS][RESTORE] Entrée ignorée : pageId invalide ou multiple='$pageIdRaw'" "ERROR"
            $errorCount++
            continue
        }

        $matchingRow = $null
        if ($null -ne $script:RestrictionTable) {
            foreach ($r in $script:RestrictionTable.Rows) {
                if ([string]$r["pageId"] -eq $pageIdValue) { $matchingRow = $r; break }
            }
        }

        try {
            if ($script:DryRun) {
                Write-AppLog "[DRY-RUN] Restauration page=$pageIdValue" "WARN"
                if ($null -ne $matchingRow) {
                    $matchingRow["restored"] = "DRY-RUN"
                    $matchingRow["message"] = "Simulation restauration"
                    Set-RestrictionRealAction -Row $matchingRow -Action "RESTAURATION_DIRECTE_DRYRUN" -Reason "Restriction directe restaurable ; simulation uniquement." -Result "DRY-RUN"
                }
            } else {
                Restore-ConfluenceRestrictions -RestrictionObject $item
                Write-AppLog "Restauration OK page=$pageIdValue" "OK"
                if ($null -ne $matchingRow) {
                    $matchingRow["restored"] = "Oui"
                    $matchingRow["message"] = "Restrictions restaurées"
                    Set-RestrictionRealAction -Row $matchingRow -Action "RESTAURATION_DIRECTE" -Reason "Restrictions directes restaurées depuis le JSON." -Result "200/204"
                }
            }
            $okCount++
        } catch {
            Write-AppLog "Erreur restauration page=$pageIdValue : $($_.Exception.Message)" "ERROR"
            [void]$errorDetails.Add([PSCustomObject]@{
                pageId  = $pageIdValue
                message = $_.Exception.Message
            })
            if ($null -ne $matchingRow) {
                $matchingRow["restored"] = "Erreur"
                $matchingRow["message"] = $_.Exception.Message
                Set-RestrictionRealAction -Row $matchingRow -Action "ERREUR_RESTAURATION" -Reason $_.Exception.Message -Result "ERROR"
            }
            $errorCount++
        }

        if ($null -ne $script:GridRestrictions) {
            $script:GridRestrictions.Dispatcher.Invoke([action]{ $script:GridRestrictions.Items.Refresh() })
        }
        [System.Windows.Forms.Application]::DoEvents()
    }

    Refresh-RestrictionStats
    Write-AppLog "[RESTRICTIONS][RESTORE] === Fin : OK=$okCount Erreurs=$errorCount Invalides=$invalidItems ===" "OK"

    if ($errorCount -eq 0 -and $okCount -gt 0) {
        Set-ProcedureStepState -Ordre 15 -Statut "Réalisé" -Preuve "$okCount restrictions restaurées"
    } elseif ($okCount -gt 0) {
        Set-ProcedureStepState -Ordre 15 -Statut "En cours" -Preuve "$okCount OK / $errorCount erreur(s)"
    }

    $errorSummary = ""

    if ($errorDetails.Count -gt 0) {
        $errorSummaryLines = New-Object System.Collections.ArrayList
        [void]$errorSummaryLines.Add("Bilan des erreurs :")
        [void]$errorSummaryLines.Add("")

        foreach ($err in @($errorDetails | Select-Object -First 20)) {
            $shortMessage = [string]$err.message
            if ($shortMessage.Length -gt 260) {
                $shortMessage = $shortMessage.Substring(0,260) + "..."
            }
            [void]$errorSummaryLines.Add("- pageId=$($err.pageId) : $shortMessage")
        }

        if ($errorDetails.Count -gt 20) {
            [void]$errorSummaryLines.Add("")
            [void]$errorSummaryLines.Add("... $($errorDetails.Count - 20) erreur(s) supplémentaire(s) dans le journal.")
        }

        $errorSummary = "`r`n`r`n" + (@($errorSummaryLines) -join "`r`n")

        Write-AppLog "[RESTRICTIONS][RESTORE][BILAN] Erreurs=$($errorDetails.Count)" "ERROR"
        foreach ($err in @($errorDetails)) {
            Write-AppLog "[RESTRICTIONS][RESTORE][BILAN] pageId=$($err.pageId) erreur=$($err.message)" "ERROR"
        }
    }

    Show-MsgBox "Restauration terminée.`r`nSuccès : $okCount`r`nErreurs : $errorCount`r`nInvalides ignorées : $invalidItems$errorSummary`r`n`r`nJournal : $script:LogFile" "Restrictions"
}

function Export-RestrictionCsv {
    if ($null -eq $script:RestrictionTable -or $script:RestrictionTable.Rows.Count -eq 0) { Show-MsgBox "Aucune donnée." "Restrictions" "Warning"; return }
    $dlg = New-Object System.Windows.Forms.SaveFileDialog
    $dlg.Filter = "Fichiers CSV (*.csv)|*.csv"
    $dlg.FileName = "restrictions_actions_reelles_comala.csv"
    if ($dlg.ShowDialog() -eq "OK") {
        $objects = foreach ($row in $script:RestrictionTable.Rows) { [PSCustomObject]@{ pageId="$($row['pageId'])"; pageUrl="$($row['pageUrl'])"; spaceKey="$($row['spaceKey'])"; pageTitle="$($row['pageTitle'])"; workflowName="$($row['workflowName'])"; hasRestrictions="$($row['hasRestrictions'])"; restrictionSource="$($row['restrictionSource'])"; ancestorIds="$($row['ancestorIds'])"; actionRequired="$($row['actionRequired'])"; actionReelle="$($row['actionReelle'])"; raisonAction="$($row['raisonAction'])"; principalSummary="$($row['principalSummary'])"; dateAction="$($row['dateAction'])"; resultatHttp="$($row['resultatHttp'])"; readUsers="$($row['readUsers'])"; readGroups="$($row['readGroups'])"; updateUsers="$($row['updateUsers'])"; updateGroups="$($row['updateGroups'])"; saved="$($row['saved'])"; removed="$($row['removed'])"; restored="$($row['restored'])"; message="$($row['message'])" } }
        $objects | Export-Csv -Path $dlg.FileName -Encoding UTF8 -NoTypeInformation -Delimiter ";"
        Show-MsgBox "CSV exporté`r`n$($dlg.FileName)" "Restrictions"
    }
}

function Save-Session {
    try {
        $workflowRows = @()
        if ($null -ne $script:WorkflowDataTable) { foreach ($row in $script:WorkflowDataTable.Rows) { $workflowRows += [PSCustomObject]@{ pageId="$($row['pageId'])"; spaceKey="$($row['spaceKey'])"; pageTitle="$($row['pageTitle'])"; workflowName="$($row['workflowName'])"; workflowMarkup="$($row['workflowMarkup'])"; labelToAdd="$($row['labelToAdd'])"; consolidationAction="$($row['consolidationAction'])"; consolidationStatus="$($row['consolidationStatus'])"; consolidationComment="$($row['consolidationComment'])"; businessValidation="$($row['businessValidation'])"; businessComment="$($row['businessComment'])"; pageUrl="$($row['pageUrl'])"; apiStatus="$($row['apiStatus'])"; apiMessage="$($row['apiMessage'])"; restrictionState="$($row['restrictionState'])" } } }
        $restrictionRows = @()
        if ($null -ne $script:RestrictionTable) { foreach ($row in $script:RestrictionTable.Rows) { $restrictionRows += [PSCustomObject]@{ pageId="$($row['pageId'])"; pageUrl="$($row['pageUrl'])"; spaceKey="$($row['spaceKey'])"; pageTitle="$($row['pageTitle'])"; workflowName="$($row['workflowName'])"; hasRestrictions="$($row['hasRestrictions'])"; restrictionSource="$($row['restrictionSource'])"; ancestorIds="$($row['ancestorIds'])"; actionRequired="$($row['actionRequired'])"; actionReelle="$($row['actionReelle'])"; raisonAction="$($row['raisonAction'])"; principalSummary="$($row['principalSummary'])"; dateAction="$($row['dateAction'])"; resultatHttp="$($row['resultatHttp'])"; readUsers="$($row['readUsers'])"; readGroups="$($row['readGroups'])"; updateUsers="$($row['updateUsers'])"; updateGroups="$($row['updateGroups'])"; saved="$($row['saved'])"; removed="$($row['removed'])"; restored="$($row['restored'])"; message="$($row['message'])" } } }
        $session = [PSCustomObject]@{ ConfluenceUrl=$script:ConfluenceUrl; Username=$script:Username; Password=$script:Password; DryRun=$script:DryRun; ConfigReady=$script:ConfigReady; WorkflowRows=$workflowRows; RestrictionRows=$restrictionRows }
        $session | ConvertTo-Json -Depth 50 | Set-Content -Path $script:SessionFile -Encoding UTF8
        Write-AppLog "Session sauvegardée" "OK"
    } catch { Write-AppLog "Erreur session : $($_.Exception.Message)" "WARN" }
}

function Load-Session {
    if (-not (Test-Path $script:SessionFile)) { Show-MsgBox "Aucune session." "Session"; return }
    try {
        $session = Get-Content -Path $script:SessionFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $script:ConfluenceUrl = [string]$session.ConfluenceUrl
        $script:Username = [string]$session.Username
        $script:Password = [string]$session.Password
        $script:DryRun = [bool]$session.DryRun
        $script:ConfigReady = [bool]$session.ConfigReady
        if ([string]::IsNullOrWhiteSpace($script:ConfluenceUrl) -or $script:ConfluenceUrl -eq "http://localhost:8090") {
            $script:ConfluenceUrl = $script:DefaultConfluenceUrl
        }
        $script:TxtCfgUrl.Text = $script:ConfluenceUrl
        $script:TxtCfgUser.Text = $script:Username
        $script:PwdCfgPassword.Password = $script:Password
        $script:TxtCfgPassword.Text = $script:Password
        $script:ChkCfgDryRun.IsChecked = $script:DryRun
        Update-DryRunStatus
        Initialize-WorkflowDataTable
        foreach ($r in @($session.WorkflowRows)) { $row = $script:WorkflowDataTable.NewRow(); foreach ($c in @("pageId","spaceKey","pageTitle","workflowName","workflowMarkup","labelToAdd","consolidationAction","consolidationStatus","consolidationComment","businessValidation","businessComment","pageUrl","apiStatus","apiMessage","restrictionState")) { $prop = $r.PSObject.Properties[$c]; $row[$c] = if ($null -ne $prop) { [string]$prop.Value } else { "" } }; $script:WorkflowDataTable.Rows.Add($row) }
        $script:GridWorkflow.ItemsSource = $script:WorkflowDataTable.DefaultView
        Initialize-RestrictionDataTable
        foreach ($r in @($session.RestrictionRows)) { $row = $script:RestrictionTable.NewRow(); foreach ($c in @("pageId","pageUrl","spaceKey","pageTitle","workflowName","hasRestrictions","restrictionSource","ancestorIds","actionRequired","actionReelle","raisonAction","principalSummary","dateAction","resultatHttp","readUsers","readGroups","updateUsers","updateGroups","saved","removed","restored","message")) { $prop = $r.PSObject.Properties[$c]; $row[$c] = if ($null -ne $prop) { [string]$prop.Value } else { "" } }; $script:RestrictionTable.Rows.Add($row) }
        $script:GridRestrictions.ItemsSource = $script:RestrictionTable.DefaultView
        Refresh-WorkflowStats
        Refresh-RestrictionStats
        foreach ($tab in @($script:TabWorkflow,$script:TabRestrictions,$script:TabLogs)) { if ($null -ne $tab) { $tab.IsEnabled = $script:ConfigReady } }
        Refresh-ProcedureSummary
        Refresh-NextStep
        Update-WorkflowFilter
        Write-AppLog "Session rechargée" "OK"
    } catch { Show-MsgBox "Erreur session`r`n$($_.Exception.Message)" "Session" "Error" }
}

[xml]$xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" Title="Comala Migration - v1.0.0" Height="960" Width="1600" MinHeight="720" MinWidth="1100" WindowStartupLocation="CenterScreen" WindowState="Maximized" Background="#F3F4F6" FontFamily="Segoe UI" FontSize="13" ResizeMode="CanResizeWithGrip" UseLayoutRounding="True" SnapsToDevicePixels="True">
<Window.Resources>
<Style x:Key="PrimaryButton" TargetType="Button"><Setter Property="Background" Value="#2563EB"/><Setter Property="Foreground" Value="White"/><Setter Property="Height" Value="34"/><Setter Property="VerticalContentAlignment" Value="Center"/><Setter Property="Padding" Value="14,0"/><Setter Property="Margin" Value="0,0,8,8"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="Cursor" Value="Hand"/><Setter Property="MinWidth" Value="90"/></Style>
<Style x:Key="SecondaryButton" TargetType="Button"><Setter Property="Background" Value="White"/><Setter Property="Foreground" Value="#1D4ED8"/><Setter Property="BorderBrush" Value="#CBD5E1"/><Setter Property="BorderThickness" Value="1"/><Setter Property="Height" Value="34"/><Setter Property="VerticalContentAlignment" Value="Center"/><Setter Property="Padding" Value="14,0"/><Setter Property="Margin" Value="0,0,8,8"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="Cursor" Value="Hand"/><Setter Property="MinWidth" Value="90"/></Style>
<Style x:Key="CardBorder" TargetType="Border"><Setter Property="Background" Value="White"/><Setter Property="BorderBrush" Value="#E2E8F0"/><Setter Property="BorderThickness" Value="1"/><Setter Property="CornerRadius" Value="12"/><Setter Property="Padding" Value="12"/><Setter Property="Margin" Value="0,0,0,10"/></Style>
<Style x:Key="ModernTab" TargetType="TabItem"><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="Padding" Value="12,6"/><Setter Property="MinWidth" Value="110"/></Style>
<Style TargetType="TextBox"><Setter Property="Height" Value="32"/><Setter Property="Padding" Value="8,0"/><Setter Property="VerticalContentAlignment" Value="Center"/></Style>
<Style TargetType="PasswordBox"><Setter Property="Height" Value="30"/><Setter Property="Padding" Value="6,2"/></Style>
<Style TargetType="ComboBox"><Setter Property="Height" Value="32"/><Setter Property="Padding" Value="6,0"/><Setter Property="VerticalContentAlignment" Value="Center"/></Style>
<Style TargetType="DataGrid"><Setter Property="AutoGenerateColumns" Value="False"/><Setter Property="CanUserAddRows" Value="False"/><Setter Property="CanUserDeleteRows" Value="False"/><Setter Property="CanUserSortColumns" Value="True"/><Setter Property="SelectionMode" Value="Extended"/><Setter Property="SelectionUnit" Value="FullRow"/><Setter Property="AlternatingRowBackground" Value="#F8FAFC"/><Setter Property="RowHeight" Value="28"/><Setter Property="GridLinesVisibility" Value="Horizontal"/><Setter Property="BorderBrush" Value="#E2E8F0"/><Setter Property="BorderThickness" Value="1"/><Setter Property="ScrollViewer.VerticalScrollBarVisibility" Value="Auto"/><Setter Property="ScrollViewer.HorizontalScrollBarVisibility" Value="Auto"/></Style>
</Window.Resources>
<Grid Background="#F3F4F6" HorizontalAlignment="Stretch" VerticalAlignment="Stretch">
<Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
<Border Grid.Row="0" Background="White" BorderBrush="#E2E8F0" BorderThickness="0,0,0,1" Padding="12,6"><DockPanel><TextBlock DockPanel.Dock="Right" Text="© Groupe OPEN – 2026 – Version 1.0.0 – Tous droits réservés" Foreground="#64748B" FontSize="12" VerticalAlignment="Center"/><TextBlock Text="Comala Migration - v1.0.0" FontSize="16" FontWeight="Bold" Foreground="#0F172A"/></DockPanel></Border>
<TabControl Grid.Row="1" Name="MainTabs" Margin="8" Background="#F3F4F6" BorderThickness="0" HorizontalAlignment="Stretch" VerticalAlignment="Stretch" HorizontalContentAlignment="Stretch" VerticalContentAlignment="Stretch">
<TabItem Header="Procédure" Name="TabProcedure" Style="{StaticResource ModernTab}">
<Grid Margin="4" Background="#F3F4F6"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="*"/></Grid.RowDefinitions>
<Grid Grid.Row="0"><Grid.ColumnDefinitions><ColumnDefinition Width="2*"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
<Border Grid.Column="0" Style="{StaticResource CardBorder}" Margin="0,0,8,10"><StackPanel><TextBlock Text="Résumé" FontSize="16" FontWeight="Bold"/><TextBlock Name="TxtProcedureSummary" Margin="0,8,0,0" Foreground="#64748B" TextWrapping="Wrap"/></StackPanel></Border>
<Border Grid.Column="1" Style="{StaticResource CardBorder}" Margin="0,0,0,10"><StackPanel><TextBlock Text="Prochaine étape" FontSize="16" FontWeight="Bold"/><TextBlock Name="TxtNextStepTitle" Margin="0,8,0,2" FontWeight="SemiBold" Foreground="#2563EB" TextWrapping="Wrap"/><TextBlock Name="TxtNextStepAction" Foreground="#64748B" TextWrapping="Wrap"/></StackPanel></Border>
</Grid>
<Border Grid.Row="1" Style="{StaticResource CardBorder}"><WrapPanel><Button Name="BtnProcedureTodo" Content="À faire" Style="{StaticResource SecondaryButton}"/><Button Name="BtnProcedureDoing" Content="En cours" Style="{StaticResource SecondaryButton}"/><Button Name="BtnProcedureDone" Content="Réalisé" Style="{StaticResource SecondaryButton}"/><Button Name="BtnProcedureBlocked" Content="Bloqué" Style="{StaticResource SecondaryButton}"/></WrapPanel></Border>
<Border Grid.Row="2" Style="{StaticResource CardBorder}"><DataGrid Name="GridProcedure" CanUserSortColumns="False"><DataGrid.Columns><DataGridTextColumn Header="#" Binding="{Binding [ordre]}" Width="45"/><DataGridTextColumn Header="OK" Binding="{Binding [done]}" Width="55"/><DataGridTextColumn Header="Statut" Binding="{Binding [statut]}" Width="110"/><DataGridTextColumn Header="Catégorie" Binding="{Binding [categorie]}" Width="120"/><DataGridTextColumn Header="Étape" Binding="{Binding [etape]}" Width="280"/><DataGridTextColumn Header="Section" Binding="{Binding [section]}" Width="130"/><DataGridTextColumn Header="Cible" Binding="{Binding [cible]}" Width="260"/><DataGridTextColumn Header="Action" Binding="{Binding [action]}" Width="330"/><DataGridTextColumn Header="Outil" Binding="{Binding [outil]}" Width="160"/><DataGridTextColumn Header="Contrôle" Binding="{Binding [controle]}" Width="180"/><DataGridTextColumn Header="Preuve" Binding="{Binding [preuve]}" Width="240"/></DataGrid.Columns></DataGrid></Border>
</Grid>
</TabItem>
<TabItem Header="Configuration" Name="TabConfiguration" Style="{StaticResource ModernTab}">
<ScrollViewer VerticalScrollBarVisibility="Auto" Background="#F3F4F6"><StackPanel Margin="4"><Border Style="{StaticResource CardBorder}"><StackPanel><TextBlock Text="Configuration" FontSize="18" FontWeight="Bold" Margin="0,0,0,14"/><Grid><Grid.ColumnDefinitions><ColumnDefinition Width="180"/><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><Grid.RowDefinitions><RowDefinition Height="36"/><RowDefinition Height="36"/><RowDefinition Height="36"/><RowDefinition Height="36"/></Grid.RowDefinitions><Label Grid.Row="0" Grid.Column="0" Content="URL Confluence"/><TextBox Grid.Row="0" Grid.Column="1" Name="TxtCfgUrl"/><Label Grid.Row="1" Grid.Column="0" Content="Compte"/><TextBox Grid.Row="1" Grid.Column="1" Name="TxtCfgUser"/><Label Grid.Row="2" Grid.Column="0" Content="Token / mot de passe"/><Grid Grid.Row="2" Grid.Column="1"><PasswordBox Name="PwdCfgPassword"/><TextBox Name="TxtCfgPassword" Visibility="Collapsed"/></Grid><CheckBox Grid.Row="2" Grid.Column="2" Name="ChkCfgShowPassword" Content="Afficher" VerticalAlignment="Center" Margin="10,0,0,0"/><CheckBox Grid.Row="3" Grid.Column="1" Name="ChkCfgDryRun" Content="DryRun" VerticalAlignment="Center"/></Grid><WrapPanel Margin="0,16,0,0"><Button Name="BtnCfgSave" Content="Enregistrer" Style="{StaticResource PrimaryButton}"/><Button Name="BtnCfgReload" Content="Recharger" Style="{StaticResource SecondaryButton}"/><Button Name="BtnCfgTest" Content="Tester connexion" Style="{StaticResource SecondaryButton}"/><Button Name="BtnCfgLoadSession" Content="Recharger session" Style="{StaticResource SecondaryButton}"/><Button Name="BtnCfgSaveSession" Content="Sauvegarder session" Style="{StaticResource SecondaryButton}"/><Button Name="BtnCfgOpenFile" Content="Ouvrir config" Style="{StaticResource SecondaryButton}"/></WrapPanel><Border Name="BrdCfgStatus" Margin="0,12,0,0" Background="#F8FAFC" BorderBrush="#CBD5E1" BorderThickness="1" CornerRadius="8" Padding="10,6"><TextBlock Name="TxtCfgStatus" Text="En attente" Foreground="#64748B"/></Border></StackPanel></Border></StackPanel></ScrollViewer>
</TabItem>
<TabItem Header="Workflow" Name="TabWorkflow" Style="{StaticResource ModernTab}" IsEnabled="False">
<Grid Margin="4" Background="#F3F4F6"><TabControl Name="WorkflowTabs" Background="Transparent" BorderThickness="0">
<TabItem Header="1 - Inventaire" Name="TabExtraction" Style="{StaticResource ModernTab}">
<Grid Margin="4" Background="#F3F4F6"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="160"/></Grid.RowDefinitions><Border Grid.Row="0" Style="{StaticResource CardBorder}"><DockPanel LastChildFill="False">
    <StackPanel Orientation="Horizontal" DockPanel.Dock="Left">
        <Button Name="BtnWorkflowImportPageWorkflows" Content="Importer CSV workflows" Style="{StaticResource PrimaryButton}"/>
        <Button Name="BtnWorkflowExport" Content="Export plan" Style="{StaticResource SecondaryButton}"/>
        <Label Content="Espaces" VerticalAlignment="Center" Margin="12,0,4,0"/>
        <TextBox Name="TxtExtractSpaces" Width="220" Margin="0,0,8,0"/>
        <Button Name="BtnExtract" Content="Extraction API" Style="{StaticResource SecondaryButton}"/>
        <Button Name="BtnExtractSave" Content="Export CSV" Style="{StaticResource SecondaryButton}" IsEnabled="False"/>
        <Button Name="BtnLoadFromExtract" Content="Charger grille" Style="{StaticResource SecondaryButton}" IsEnabled="False"/>
        <Label Name="LblExtractStatus" Content="En attente" FontWeight="SemiBold" Foreground="#334155" VerticalContentAlignment="Center" Padding="8,0,0,0"/>
    </StackPanel>
    <Button Name="BtnWorkflowStop1" Content="STOP" Style="{StaticResource SecondaryButton}" DockPanel.Dock="Right" Margin="20,0,0,0"/>
</DockPanel></Border><Border Grid.Row="1" Style="{StaticResource CardBorder}"><DataGrid Name="GridExtract" CanUserSortColumns="False"><DataGrid.Columns><DataGridTextColumn Header="pageId" Binding="{Binding pageId}" Width="95"/><DataGridTextColumn Header="spaceKey" Binding="{Binding spaceKey}" Width="90"/><DataGridTextColumn Header="pageTitle" Binding="{Binding pageTitle}" Width="400"/><DataGridTextColumn Header="workflowName" Binding="{Binding workflowName}" Width="280"/><DataGridTextColumn Header="pageUrl" Binding="{Binding pageUrl}" Width="*"/></DataGrid.Columns></DataGrid></Border><Border Grid.Row="2" Style="{StaticResource CardBorder}"><Border Background="#0F172A" CornerRadius="8"><ScrollViewer Name="ScrollExtractLog" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Auto" Padding="6"><TextBlock Name="TxtExtractLog" FontFamily="Consolas" FontSize="12" Foreground="#E2E8F0" TextWrapping="NoWrap"/></ScrollViewer></Border></Border></Grid>
</TabItem>
<TabItem Header="2 - Consolidation" Name="TabTraitement" Style="{StaticResource ModernTab}">
<Grid Margin="4" Background="#F3F4F6"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="*"/></Grid.RowDefinitions>
<Border Grid.Row="0" Style="{StaticResource CardBorder}"><DockPanel LastChildFill="True"><TextBlock Text="Consolidation Appfire" FontSize="15" FontWeight="Bold" Foreground="#0F172A" DockPanel.Dock="Left" Margin="0,0,18,0"/><TextBlock Name="TxtWorkflowDryRunInfo" Text="Mode piloté depuis Configuration" DockPanel.Dock="Right" VerticalAlignment="Center" Foreground="#64748B" FontWeight="SemiBold"/></DockPanel></Border>
<Border Grid.Row="1" Style="{StaticResource CardBorder}" BorderBrush="#2563EB" BorderThickness="2"><StackPanel><WrapPanel><Button Name="BtnWorkflowLabelOk" Content="OK" Style="{StaticResource PrimaryButton}"/><Button Name="BtnWorkflowLabelKo" Content="KO" Style="{StaticResource PrimaryButton}"/><Button Name="BtnWorkflowLabelArb" Content="À arbitrer" Style="{StaticResource PrimaryButton}"/><Separator Width="16" Opacity="0"/><Button Name="BtnWorkflowRegen" Content="Générer labels" Style="{StaticResource PrimaryButton}"/><TextBox Name="TxtWorkflowManualLabel" Width="220" Margin="0,0,8,8"/><Button Name="BtnWorkflowApplyManualLabel" Content="Appliquer label" Style="{StaticResource PrimaryButton}"/><Separator Width="16" Opacity="0"/><Button Name="BtnWorkflowBulkConsoSW" Content="Consolider" Style="{StaticResource PrimaryButton}"/><Button Name="BtnWorkflowBulkConsoMarkup" Content="Consolider + markup" Style="{StaticResource PrimaryButton}"/><Button Name="BtnWorkflowApplyAll" Content="Pose labels secours" Style="{StaticResource PrimaryButton}"/><Button Name="BtnWorkflowStop2" Content="STOP" Style="{StaticResource SecondaryButton}"/></WrapPanel><WrapPanel Margin="0,8,0,0"><TextBlock Text="Changer statut consolidation :" VerticalAlignment="Center" FontWeight="SemiBold" Margin="0,0,10,8"/><Button Name="BtnWorkflowConsoTodo" Content="À faire" Style="{StaticResource SecondaryButton}"/><Button Name="BtnWorkflowConsoDoing" Content="En cours" Style="{StaticResource SecondaryButton}"/><Button Name="BtnWorkflowConsoDone" Content="Réalisée" Style="{StaticResource SecondaryButton}"/><Button Name="BtnWorkflowConsoBlocked" Content="Bloquée" Style="{StaticResource SecondaryButton}"/></WrapPanel></StackPanel></Border>
<Border Grid.Row="2" Style="{StaticResource CardBorder}" BorderBrush="#F59E0B" BorderThickness="2"><StackPanel><TextBlock Text="Filtres / recherche" FontWeight="Bold" Foreground="#B45309" Margin="0,0,0,8"/><WrapPanel><Label Content="Validation métier" VerticalContentAlignment="Center" Padding="0,0,6,8"/><ComboBox Name="CmbFilterValidation" Width="150" Height="30" Margin="0,0,12,8"><ComboBoxItem Content="Tous" IsSelected="True"/><ComboBoxItem Content="OK"/><ComboBoxItem Content="KO"/><ComboBoxItem Content="A arbitrer"/></ComboBox><Label Content="Consolidation" VerticalContentAlignment="Center" Padding="0,0,6,8"/><ComboBox Name="CmbFilterConso" Width="160" Height="30" Margin="0,0,12,8"><ComboBoxItem Content="Tous" IsSelected="True"/><ComboBoxItem Content="À faire"/><ComboBoxItem Content="En cours"/><ComboBoxItem Content="Réalisée"/><ComboBoxItem Content="Bloquée"/><ComboBoxItem Content="DRY-RUN"/><ComboBoxItem Content="Erreur"/></ComboBox><Label Content="Recherche" VerticalContentAlignment="Center" Padding="0,0,6,8"/><TextBox Name="TxtWorkflowSearch" Width="260" Margin="0,0,8,8"/><Button Name="BtnWorkflowClearFilters" Content="Réinitialiser filtres" Style="{StaticResource SecondaryButton}"/></WrapPanel></StackPanel></Border>
<Border Grid.Row="3" Style="{StaticResource CardBorder}"><Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/></Grid.RowDefinitions><Border Grid.Row="0" Background="#EEF4FF" BorderBrush="#BDD0F0" BorderThickness="1" CornerRadius="8" Padding="8,4" Margin="0,0,0,8"><DockPanel><WrapPanel DockPanel.Dock="Right"><Button Name="BtnWorkflowOpenPage" Content="Ouvrir page" Style="{StaticResource SecondaryButton}"/><Button Name="BtnWorkflowExportConsoCompact" Content="Export plan" Style="{StaticResource SecondaryButton}"/></WrapPanel><Label Name="LblWorkflowStats" Content="Pages : 0" FontWeight="SemiBold" Foreground="#1A4A8A" Padding="0"/></DockPanel></Border><DataGrid Grid.Row="1" Name="GridWorkflow" EnableRowVirtualization="False" EnableColumnVirtualization="False" CanUserSortColumns="False"><DataGrid.Columns><DataGridTextColumn Header="pageId" Binding="{Binding [pageId]}" Width="95"/><DataGridTextColumn Header="spaceKey" Binding="{Binding [spaceKey]}" Width="85"/><DataGridTextColumn Header="pageTitle" Binding="{Binding [pageTitle]}" Width="250"/><DataGridTextColumn Header="workflowName" Binding="{Binding [workflowName]}" Width="220"/><DataGridTextColumn Header="workflowMarkup" Binding="{Binding [workflowMarkup]}" Width="220"/><DataGridTextColumn Header="labelToAdd" Binding="{Binding [labelToAdd]}" Width="240"/><DataGridTextColumn Header="consolidationStatus" Binding="{Binding [consolidationStatus]}" Width="135"/><DataGridTextColumn Header="businessValidation" Binding="{Binding [businessValidation]}" Width="125"/><DataGridTextColumn Header="apiStatus" Binding="{Binding [apiStatus]}" Width="95"/><DataGridTextColumn Header="apiMessage" Binding="{Binding [apiMessage]}" Width="260"/><DataGridTextColumn Header="pageUrl" Binding="{Binding [pageUrl]}" Width="260"/></DataGrid.Columns></DataGrid></Grid></Border>
</Grid>
</TabItem>
</TabControl></Grid>
</TabItem>
<TabItem Header="Restrictions" Name="TabRestrictions" Style="{StaticResource ModernTab}" IsEnabled="False"><Grid Margin="4" Background="#F3F4F6"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="*"/></Grid.RowDefinitions><Border Grid.Row="0" Style="{StaticResource CardBorder}"><WrapPanel><Button Name="BtnRestrictionsImportAppfireCsv" Content="Importer CSV" Style="{StaticResource PrimaryButton}"/><Button Name="BtnRestrictionsAnalyze" Content="Analyse REST" Style="{StaticResource SecondaryButton}"/><Button Name="BtnRestrictionsRemove" Content="Lever restrictions" Style="{StaticResource SecondaryButton}"/><Button Name="BtnRestrictionsRestore" Content="Restaurer restrictions" Style="{StaticResource PrimaryButton}"/><Button Name="BtnRestrictionsExportCsv" Content="Export CSV" Style="{StaticResource SecondaryButton}"/><Button Name="BtnRestrictionsOpenJson" Content="Ouvrir JSON" Style="{StaticResource SecondaryButton}"/><Button Name="BtnRestrictionsStop" Content="STOP" Style="{StaticResource SecondaryButton}"/></WrapPanel></Border><Border Grid.Row="1" Background="#EEF4FF" BorderBrush="#BDD0F0" BorderThickness="1" CornerRadius="10" Padding="10,6" Margin="0,0,0,10"><Label Name="LblRestrictionsStats" Content="Pages : 0" FontWeight="SemiBold" Foreground="#1A4A8A" Padding="0"/></Border><Border Grid.Row="2" Style="{StaticResource CardBorder}"><DataGrid Name="GridRestrictions" CanUserSortColumns="False"><DataGrid.Columns><DataGridTextColumn Header="pageId" Binding="{Binding [pageId]}" Width="90"/><DataGridTextColumn Header="pageUrl" Binding="{Binding [pageUrl]}" Width="330"/><DataGridTextColumn Header="spaceKey" Binding="{Binding [spaceKey]}" Width="85"/><DataGridTextColumn Header="pageTitle" Binding="{Binding [pageTitle]}" Width="220"/><DataGridTextColumn Header="workflowName" Binding="{Binding [workflowName]}" Width="180"/><DataGridTextColumn Header="hasRestrictions" Binding="{Binding [hasRestrictions]}" Width="120"/><DataGridTextColumn Header="restrictionSource" Binding="{Binding [restrictionSource]}" Width="140"/><DataGridTextColumn Header="ancestorIds" Binding="{Binding [ancestorIds]}" Width="140"/><DataGridTextColumn Header="actionRequired" Binding="{Binding [actionRequired]}" Width="210"/><DataGridTextColumn Header="actionReelle" Binding="{Binding [actionReelle]}" Width="170"/><DataGridTextColumn Header="raisonAction" Binding="{Binding [raisonAction]}" Width="360"/><DataGridTextColumn Header="principalSummary" Binding="{Binding [principalSummary]}" Width="360"/><DataGridTextColumn Header="dateAction" Binding="{Binding [dateAction]}" Width="140"/><DataGridTextColumn Header="resultatHttp" Binding="{Binding [resultatHttp]}" Width="100"/><DataGridTextColumn Header="readUsers" Binding="{Binding [readUsers]}" Width="170"/><DataGridTextColumn Header="readGroups" Binding="{Binding [readGroups]}" Width="170"/><DataGridTextColumn Header="updateUsers" Binding="{Binding [updateUsers]}" Width="170"/><DataGridTextColumn Header="updateGroups" Binding="{Binding [updateGroups]}" Width="170"/><DataGridTextColumn Header="saved" Binding="{Binding [saved]}" Width="70"/><DataGridTextColumn Header="removed" Binding="{Binding [removed]}" Width="80"/><DataGridTextColumn Header="restored" Binding="{Binding [restored]}" Width="80"/><DataGridTextColumn Header="message" Binding="{Binding [message]}" Width="520"/></DataGrid.Columns></DataGrid></Border></Grid></TabItem>
<TabItem Header="Logs" Name="TabLogs" Style="{StaticResource ModernTab}" IsEnabled="False"><Grid Margin="4" Background="#F3F4F6"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/></Grid.RowDefinitions><Border Grid.Row="0" Style="{StaticResource CardBorder}"><WrapPanel><Button Name="BtnLogsOpen" Content="Ouvrir log" Style="{StaticResource SecondaryButton}"/><Button Name="BtnLogsClear" Content="Vider" Style="{StaticResource SecondaryButton}"/><Button Name="BtnLogsStop" Content="STOP" Style="{StaticResource SecondaryButton}"/></WrapPanel></Border><Border Grid.Row="1" Style="{StaticResource CardBorder}"><Border Background="#0F172A" CornerRadius="10"><ScrollViewer Name="ScrollLog" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Auto" Padding="8"><TextBlock Name="TxtLog" FontFamily="Consolas" FontSize="12" Foreground="#E2E8F0" TextWrapping="NoWrap"/></ScrollViewer></Border></Border></Grid></TabItem>
<TabItem Header="À propos" Name="TabAbout" Style="{StaticResource ModernTab}"><Grid Margin="30"><Border Style="{StaticResource CardBorder}" HorizontalAlignment="Center" VerticalAlignment="Center" Width="760" Padding="36"><StackPanel><TextBlock Text="Comala Migration" FontSize="28" FontWeight="Bold" Foreground="#0F172A" HorizontalAlignment="Center"/><StackPanel Margin="0,20,0,0" HorizontalAlignment="Center"><TextBlock Text="Conception et développement : ABU17616" HorizontalAlignment="Center" Foreground="#334155"/><TextBlock Text="Version 1.0.0" HorizontalAlignment="Center" Foreground="#334155" Margin="0,8,0,0"/><TextBlock Text="© Groupe OPEN – 2026 – Tous droits réservés" HorizontalAlignment="Center" Foreground="#334155" Margin="0,8,0,0"/></StackPanel></StackPanel></Border></Grid></TabItem>
</TabControl>
<Border Grid.Row="2" Background="#0F172A" BorderBrush="#1E293B" BorderThickness="0,1,0,0" Padding="16,10"><DockPanel><TextBlock Name="TxtDryRunStatus" Text="Mode : DryRun" Foreground="#FBBF24" FontSize="12" FontWeight="SemiBold" DockPanel.Dock="Right"/><TextBlock Name="TxtGlobalStatus" Text="Prêt" Foreground="#E2E8F0" FontSize="12"/></DockPanel></Border>
</Grid>
</Window>
'@

$reader = New-Object System.Xml.XmlNodeReader $xaml
$window = [System.Windows.Markup.XamlReader]::Load($reader)
try { $window.Background = [System.Windows.Media.Brushes]::White } catch {}
function Get-Ctrl { param([string]$Name) return $window.FindName($Name) }

$script:BtnWorkflowStop1 = Get-Ctrl "BtnWorkflowStop1"
$script:BtnWorkflowStop2 = Get-Ctrl "BtnWorkflowStop2"
$script:BtnRestrictionsStop = Get-Ctrl "BtnRestrictionsStop"
$script:BtnLogsStop = Get-Ctrl "BtnLogsStop"
$script:MainTabs = Get-Ctrl "MainTabs"
$script:TabProcedure = Get-Ctrl "TabProcedure"
$script:TabConfiguration = Get-Ctrl "TabConfiguration"
$script:TabWorkflow = Get-Ctrl "TabWorkflow"
$script:WorkflowTabs = Get-Ctrl "WorkflowTabs"
$script:TabExtraction = Get-Ctrl "TabExtraction"
$script:TabTraitement = Get-Ctrl "TabTraitement"
$script:TabRestrictions = Get-Ctrl "TabRestrictions"
$script:TabLogs = Get-Ctrl "TabLogs"
$script:TabAbout = Get-Ctrl "TabAbout"
$script:TxtGlobalStatus = Get-Ctrl "TxtGlobalStatus"
$script:TxtProcedureSummary = Get-Ctrl "TxtProcedureSummary"
$script:TxtNextStepTitle = Get-Ctrl "TxtNextStepTitle"
$script:TxtNextStepAction = Get-Ctrl "TxtNextStepAction"
$script:GridProcedure = Get-Ctrl "GridProcedure"
$script:BtnProcedureTodo = Get-Ctrl "BtnProcedureTodo"
$script:BtnProcedureDoing = Get-Ctrl "BtnProcedureDoing"
$script:BtnProcedureDone = Get-Ctrl "BtnProcedureDone"
$script:BtnProcedureBlocked = Get-Ctrl "BtnProcedureBlocked"
$script:TxtCfgUrl = Get-Ctrl "TxtCfgUrl"
$script:TxtCfgUser = Get-Ctrl "TxtCfgUser"
$script:PwdCfgPassword = Get-Ctrl "PwdCfgPassword"
$script:TxtCfgPassword = Get-Ctrl "TxtCfgPassword"
$script:ChkCfgShowPassword = Get-Ctrl "ChkCfgShowPassword"
$script:ChkCfgDryRun = Get-Ctrl "ChkCfgDryRun"
$script:BtnCfgSave = Get-Ctrl "BtnCfgSave"
$script:BtnCfgReload = Get-Ctrl "BtnCfgReload"
$script:BtnCfgTest = Get-Ctrl "BtnCfgTest"
$script:BtnCfgLoadSession = Get-Ctrl "BtnCfgLoadSession"
$script:BtnCfgSaveSession = Get-Ctrl "BtnCfgSaveSession"
$script:BtnCfgOpenFile = Get-Ctrl "BtnCfgOpenFile"
$script:TxtCfgStatus = Get-Ctrl "TxtCfgStatus"
$script:BrdCfgStatus = Get-Ctrl "BrdCfgStatus"
$script:TxtExtractSpaces = Get-Ctrl "TxtExtractSpaces"
$script:BtnExtract = Get-Ctrl "BtnExtract"
$script:BtnExtractSave = Get-Ctrl "BtnExtractSave"
$script:BtnLoadFromExtract = Get-Ctrl "BtnLoadFromExtract"
$script:LblExtractStatus = Get-Ctrl "LblExtractStatus"
$script:GridExtract = Get-Ctrl "GridExtract"
$script:TxtExtractLog = Get-Ctrl "TxtExtractLog"
$script:ScrollExtractLog = Get-Ctrl "ScrollExtractLog"
$script:ChkWorkflowDryRun = $null
$script:TxtWorkflowDryRunInfo = Get-Ctrl "TxtWorkflowDryRunInfo"
$script:TxtDryRunStatus = Get-Ctrl "TxtDryRunStatus"
$script:BtnWorkflowImportPageWorkflows = Get-Ctrl "BtnWorkflowImportPageWorkflows"
$script:BtnWorkflowRegen = Get-Ctrl "BtnWorkflowRegen"
$script:BtnWorkflowConsoTodo = Get-Ctrl "BtnWorkflowConsoTodo"
$script:BtnWorkflowConsoDoing = Get-Ctrl "BtnWorkflowConsoDoing"
$script:BtnWorkflowConsoDone = Get-Ctrl "BtnWorkflowConsoDone"
$script:BtnWorkflowConsoBlocked = Get-Ctrl "BtnWorkflowConsoBlocked"
$script:BtnWorkflowExportConso = Get-Ctrl "BtnWorkflowExportConso"
$script:BtnWorkflowExport = Get-Ctrl "BtnWorkflowExport"
if ($null -eq $script:BtnWorkflowExportConso) { $script:BtnWorkflowExportConso = $script:BtnWorkflowExport }
$script:BtnWorkflowExportConsoCompact = Get-Ctrl "BtnWorkflowExportConsoCompact"
$script:BtnWorkflowBulkConsoSW = Get-Ctrl "BtnWorkflowBulkConsoSW"
$script:BtnWorkflowBulkConsoMarkup = Get-Ctrl "BtnWorkflowBulkConsoMarkup"
$script:TxtWorkflowManualLabel = Get-Ctrl "TxtWorkflowManualLabel"
$script:BtnWorkflowApplyManualLabel = Get-Ctrl "BtnWorkflowApplyManualLabel"
$script:BtnWorkflowOpenPage = Get-Ctrl "BtnWorkflowOpenPage"
$script:BtnWorkflowApplyAll = Get-Ctrl "BtnWorkflowApplyAll"
$script:BtnWorkflowLabelOk = Get-Ctrl "BtnWorkflowLabelOk"
$script:BtnWorkflowLabelKo = Get-Ctrl "BtnWorkflowLabelKo"
$script:BtnWorkflowLabelArb = Get-Ctrl "BtnWorkflowLabelArb"
$script:LblWorkflowStats = Get-Ctrl "LblWorkflowStats"
$script:GridWorkflow = Get-Ctrl "GridWorkflow"
$script:CmbFilterValidation = Get-Ctrl "CmbFilterValidation"
$script:CmbFilterConso = Get-Ctrl "CmbFilterConso"
$script:TxtWorkflowSearch = Get-Ctrl "TxtWorkflowSearch"
$script:BtnWorkflowClearFilters = Get-Ctrl "BtnWorkflowClearFilters"
$script:BtnRestrictionsAnalyze = Get-Ctrl "BtnRestrictionsAnalyze"
$script:BtnRestrictionsImportAppfireCsv = Get-Ctrl "BtnRestrictionsImportAppfireCsv"
$script:BtnRestrictionsRemove = Get-Ctrl "BtnRestrictionsRemove"
$script:BtnRestrictionsRestore = Get-Ctrl "BtnRestrictionsRestore"
$script:BtnRestrictionsExportCsv = Get-Ctrl "BtnRestrictionsExportCsv"
$script:BtnRestrictionsOpenJson = Get-Ctrl "BtnRestrictionsOpenJson"
$script:LblRestrictionsStats = Get-Ctrl "LblRestrictionsStats"
$script:GridRestrictions = Get-Ctrl "GridRestrictions"
$script:BtnLogsOpen = Get-Ctrl "BtnLogsOpen"
$script:BtnLogsClear = Get-Ctrl "BtnLogsClear"
$script:TxtLog = Get-Ctrl "TxtLog"
$script:ScrollLog = Get-Ctrl "ScrollLog"

$script:ChkCfgShowPassword.Add_Checked({ $script:TxtCfgPassword.Text = $script:PwdCfgPassword.Password; $script:PwdCfgPassword.Visibility = [System.Windows.Visibility]::Collapsed; $script:TxtCfgPassword.Visibility = [System.Windows.Visibility]::Visible })
$script:ChkCfgShowPassword.Add_Unchecked({ $script:PwdCfgPassword.Password = $script:TxtCfgPassword.Text; $script:TxtCfgPassword.Visibility = [System.Windows.Visibility]::Collapsed; $script:PwdCfgPassword.Visibility = [System.Windows.Visibility]::Visible })
$script:BtnCfgSave.Add_Click({ if (Save-ConfigFile) { Update-DryRunStatus; Show-MsgBox "Configuration enregistrée." "Configuration" } })
$script:BtnCfgReload.Add_Click({ if (Load-ConfigFile) { Update-DryRunStatus; Show-MsgBox "Configuration rechargée." "Configuration" } })
$script:BtnCfgOpenFile.Add_Click({ if (Test-Path $script:ConfigFile) { Start-Process -FilePath notepad.exe -ArgumentList "`"$script:ConfigFile`"" } else { Show-MsgBox "config.txt introuvable." "Configuration" "Warning" } })
$script:BtnCfgTest.Add_Click({ try { Read-ConnectionFromUi; Update-DryRunStatus; $userValue = Test-ConfluenceConnection; $script:TxtCfgStatus.Text = "Connexion OK : $userValue"; Set-ConfigReadyState -Ready $true; Show-MsgBox "Connexion OK`r`nCompte : $userValue" "Configuration" } catch { $script:TxtCfgStatus.Text = "Erreur : $($_.Exception.Message)"; Set-ConfigReadyState -Ready $false; Show-MsgBox $_.Exception.Message "Configuration" "Error" } })
$script:BtnCfgSaveSession.Add_Click({ Save-Session })
$script:BtnCfgLoadSession.Add_Click({ Load-Session })
$script:BtnWorkflowImportPageWorkflows.Add_Click({ Import-AppfirePageWorkflowsCsv })
if ($null -ne $script:BtnWorkflowExportConso) { $script:BtnWorkflowExportConso.Add_Click({ Export-ConsolidationPlanCsv }) }
if ($null -ne $script:BtnWorkflowExport) { $script:BtnWorkflowExport.Add_Click({ Export-ConsolidationPlanCsv }) }
$script:BtnWorkflowRegen.Add_Click({ Regenerate-WorkflowLabels })
$script:BtnWorkflowConsoTodo.Add_Click({ Set-ConsolidationStatusOnSelectedWorkflows "À faire" })
$script:BtnWorkflowConsoDoing.Add_Click({ Set-ConsolidationStatusOnSelectedWorkflows "En cours" })
$script:BtnWorkflowConsoDone.Add_Click({ Set-ConsolidationStatusOnSelectedWorkflows "Réalisée" })
$script:BtnWorkflowConsoBlocked.Add_Click({ Set-ConsolidationStatusOnSelectedWorkflows "Bloquée" })
$script:BtnWorkflowExportConsoCompact.Add_Click({ Export-ConsolidationPlanCsv })
$script:BtnWorkflowBulkConsoSW.Add_Click({ Invoke-ComalaBulkConsolidation -GroupingMode "SpaceWorkflow" })
$script:BtnWorkflowBulkConsoMarkup.Add_Click({ Invoke-ComalaBulkConsolidation -GroupingMode "SpaceWorkflowMarkup" })
$script:BtnWorkflowApplyManualLabel.Add_Click({ Set-LabelOnSelectedWorkflows $script:TxtWorkflowManualLabel.Text })
$script:BtnWorkflowOpenPage.Add_Click({ Open-SelectedWorkflowPage })
$script:BtnWorkflowApplyAll.Add_Click({ Apply-WorkflowLabels })
$script:BtnWorkflowLabelOk.Add_Click({ Set-ValidationOnSelectedWorkflows "OK" })
$script:BtnWorkflowLabelKo.Add_Click({ Set-ValidationOnSelectedWorkflows "KO" })
$script:BtnWorkflowLabelArb.Add_Click({ Set-ValidationOnSelectedWorkflows "A arbitrer" })
$script:CmbFilterValidation.Add_SelectionChanged({ Update-WorkflowFilter })
$script:CmbFilterConso.Add_SelectionChanged({ Update-WorkflowFilter })
$script:TxtWorkflowSearch.Add_TextChanged({ Update-WorkflowFilter })
$script:BtnWorkflowClearFilters.Add_Click({ $script:CmbFilterValidation.SelectedIndex = 0; $script:CmbFilterConso.SelectedIndex = 0; $script:TxtWorkflowSearch.Text = ""; Update-WorkflowFilter })
$script:BtnRestrictionsAnalyze.Add_Click({ Analyze-Restrictions })
$script:BtnRestrictionsImportAppfireCsv.Add_Click({ Import-AppfireRestrictionCsv })
$script:BtnRestrictionsRemove.Add_Click({ Remove-DetectedRestrictions })
$script:BtnRestrictionsRestore.Add_Click({ Restore-RestrictionsFromJson })
$script:BtnRestrictionsExportCsv.Add_Click({ Export-RestrictionCsv })
$script:BtnRestrictionsOpenJson.Add_Click({ if (Test-Path $script:RestrictionsJsonFile) { Start-Process -FilePath notepad.exe -ArgumentList "`"$script:RestrictionsJsonFile`"" } else { Show-MsgBox "JSON introuvable." "Restrictions" "Warning" } })
$script:BtnProcedureTodo.Add_Click({ Set-SelectedProcedureStatus "À faire" })
$script:BtnProcedureDoing.Add_Click({ Set-SelectedProcedureStatus "En cours" })
$script:BtnProcedureDone.Add_Click({ Set-SelectedProcedureStatus "Réalisé" })
$script:BtnProcedureBlocked.Add_Click({ Set-SelectedProcedureStatus "Bloqué" })
$script:BtnLogsOpen.Add_Click({ if (Test-Path $script:LogFile) { Start-Process -FilePath notepad.exe -ArgumentList "`"$script:LogFile`"" } else { Show-MsgBox "Log introuvable." "Logs" "Warning" } })
$script:BtnLogsClear.Add_Click({ $script:TxtLog.Text = "" })
foreach ($stopButton in @($script:BtnWorkflowStop1,$script:BtnWorkflowStop2,$script:BtnRestrictionsStop,$script:BtnLogsStop)) {
    if ($null -ne $stopButton) { $stopButton.Add_Click({ Stop-CurrentProcess }) }
}

$window.Add_Loaded({
    try {
        $window.Background = New-Object System.Windows.Media.SolidColorBrush ([System.Windows.Media.ColorConverter]::ConvertFromString("#F3F4F6"))
        $script:MainTabs.Background = $window.Background
    } catch {}
    Optimize-WindowForScreen
    Initialize-Procedure
    Initialize-WorkflowDataTable
    Initialize-RestrictionDataTable
    $script:GridProcedure.ItemsSource = $script:ProcedureTable.DefaultView
    $script:GridWorkflow.ItemsSource = $script:WorkflowDataTable.DefaultView
    $script:GridRestrictions.ItemsSource = $script:RestrictionTable.DefaultView
    Refresh-ProcedureSummary
    Refresh-NextStep
    Load-ConfigFile | Out-Null
    Set-ConfigReadyState -Ready $false
    Refresh-WorkflowStats
    Refresh-RestrictionStats
    Update-DryRunStatus
    Write-AppLog "Comala Migration démarrée" "OK"
})
$window.Add_Closing({ try { Save-Session } catch {} })
try { $window.ShowDialog() | Out-Null } catch { Write-Host "ERREUR ShowDialog : $($_.Exception.Message)" -ForegroundColor Red; if ($_.Exception.InnerException) { Write-Host "Inner : $($_.Exception.InnerException.Message)" -ForegroundColor Yellow } }