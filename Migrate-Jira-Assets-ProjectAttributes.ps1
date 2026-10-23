#Requires -Version 5.1

<#
.SYNOPSIS
    Migrates Jira Assets project attributes (type 6) from Jira Data Center to Jira Cloud.

.DESCRIPTION
    The script reads object schemas, object types and project attributes from a Data Center
    Jira Assets instance, finds matching objects in Jira Cloud by label, and updates the Cloud
    object attributes with the corresponding Cloud project IDs.

.NOTES
    Hardcoded configuration values are defined in the script body.
    Update the token and credentials before running.
#>

# ============================================================================
# Configuration is selected by environment keys in environment_config.json.
# ============================================================================
$environmentConfigPath = Join-Path $PSScriptRoot 'environment_config.json'
$environmentConfig = Get-Content -LiteralPath $environmentConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
$cloudEnvironment = $environmentConfig.environments.cloud.open_groupe_sandbox_source
$dataCenterEnvironment = $environmentConfig.environments.data_center.open_groupe_preprod
$dataCenterBaseUrl = $dataCenterEnvironment.jira_base_url
$dataCenterPAT = $dataCenterEnvironment.jira_pat
$cloudUrl = $cloudEnvironment.jira_base_url
$cloudUsername = $cloudEnvironment.username
$cloudToken = $cloudEnvironment.user_token
$DRY_RUN = $false

$logFilePath = Join-Path $PSScriptRoot "Migrate Jira Assets Logs.csv"
if (-not (Test-Path $logFilePath)) {
    "Timestamp,Level,Message" | Out-File -FilePath $logFilePath -Encoding UTF8
}

# ============================================================================
# Helper functions
# ============================================================================

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet("INFO","WARNING","ERROR","SUCCESS")]
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $output = "[$timestamp] [$Level] $Message"
    switch ($Level) {
        "INFO"    { Write-Host $output -ForegroundColor White }
        "WARNING" { Write-Host $output -ForegroundColor Yellow }
        "ERROR"   { Write-Host $output -ForegroundColor Red }
        "SUCCESS" { Write-Host $output -ForegroundColor Green }
    }
    $escapedMessage = $Message -replace '"', '""'
    $csvLine = "`"$timestamp`",`"$Level`",`"$escapedMessage`""
    Add-Content -Path $logFilePath -Value $csvLine -Encoding UTF8
}

function Get-RequestHeaders {
    param(
        [ValidateSet("DataCenter","Cloud")]
        [string]$Environment
    )

    switch ($Environment) {
        "DataCenter" {
            return @{ "Authorization" = "Bearer $dataCenterPAT"; "Accept" = "application/json" }
        }
        "Cloud" {
            $basic = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes("$cloudUsername`:$cloudToken"))
            return @{ "Authorization" = "Basic $basic"; "Accept" = "application/json" }
        }
    }
}

function Invoke-Api {
    param(
        [ValidateSet("GET","POST","PUT","DELETE")]
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers,
        [object]$Body = $null
    )

    $params = @{ Method = $Method; Uri = $Uri; Headers = $Headers; ContentType = "application/json; charset=utf-8"; ErrorAction = 'Stop' }
    if ($null -ne $Body) {
        $params.Body = ConvertTo-Json -InputObject $Body -Depth 100
    }

    try {
        $response = Invoke-WebRequest @params
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
            if ([string]::IsNullOrWhiteSpace($response.Content)) {
                return $null
            }

            try {
                return $response.Content | ConvertFrom-Json -ErrorAction Stop
            } catch {
                return $response.Content
            }
        }

        throw "HTTP $($response.StatusCode)"
    } catch {
        $message = $_.Exception.Message
        if ($null -ne $_.Exception.Response) {
            try {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $body = $reader.ReadToEnd()
                if (-not [string]::IsNullOrWhiteSpace($body)) {
                    $message += " - $body"
                }
                $reader.Close()
            } catch {}
        }
        Write-Log "API request failed: $Uri ($message)" -Level "ERROR"
        return $null
    }
}

function ConvertTo-EscapedQueryValue {
    param([string]$Value)
    return [uri]::EscapeDataString($Value)
}

function Get-ProjectAttributeQuery {
    param(
        [string[]]$AttributeNames
    )
    if (-not $AttributeNames -or $AttributeNames.Count -eq 0) {
        return $null
    }

    $clauses = $AttributeNames | ForEach-Object {
        $escapedName = $_ -replace '"', '"'
        "`"$escapedName`" is not empty"
    }
    return ($clauses -join " OR ")
}

function Get-AttributeProjectKeys {
    param($Attribute)
    $keys = @()
    if ($null -eq $Attribute) { return $keys }

    if ($Attribute.objectAttributeValues) {
        foreach ($value in $Attribute.objectAttributeValues) {
            $project = $null
            if ($value.project) {
                $project = $value.project
            }
            if ($project -and $project.key) {
                $keys += $project.key
            }
        }
    }

    return $keys | Where-Object { $_ } | Select-Object -Unique
}

# ============================================================================
# Data Center functions
# ============================================================================

function Get-DataCenterObjectSchemas {
    $uri = "$dataCenterBaseUrl/rest/assets/latest/objectschema/list"
    $result = Invoke-Api -Method GET -Uri $uri -Headers (Get-RequestHeaders -Environment DataCenter)
    if ($null -ne $result -and $null -ne $result.objectschemas) {
        return $result.objectschemas
    } else {
        return $null
    }
}

function Get-DataCenterObjectTypes {
    param([string]$ObjectSchemaId)
    $uri = "$dataCenterBaseUrl/rest/assets/latest/objectschema/$ObjectSchemaId/objecttypes/flat"
    return Invoke-Api -Method GET -Uri $uri -Headers (Get-RequestHeaders -Environment DataCenter)
}

function Get-DataCenterObjectTypeAttributes {
    param([string]$ObjectTypeId)
    $uri = "$dataCenterBaseUrl/rest/assets/latest/objecttype/$ObjectTypeId/attributes"
    return Invoke-Api -Method GET -Uri $uri -Headers (Get-RequestHeaders -Environment DataCenter)
}

function Get-DataCenterObjectsByAql {
    param(
        [string]$IqlQuery
    )

    $objects = @()
    $page = 1
    $headers = Get-RequestHeaders -Environment DataCenter
    $encodedQuery = ConvertTo-EscapedQueryValue -Value $IqlQuery

    while ($true) {
        $uri = "$dataCenterBaseUrl/rest/assets/latest/aql/objects?includeTypeAttributes=true&iql=$encodedQuery&page=$page"
        $result = Invoke-Api -Method GET -Uri $uri -Headers $headers
        if (-not $result) {
            break
        }

        $pageObjects = $result.objectEntries
        if (-not $pageObjects) {
            $pageObjects = $result
        }
        if ($pageObjects) {
            $objects += $pageObjects
        }

        $totalFilterCount = $result.totalFilterCount
        $toIndex = $result.toIndex
        if (-not $totalFilterCount -or -not $toIndex) {
            break
        }

        Write-Log "Loaded page $page, toIndex=$toIndex, totalFilterCount=$totalFilterCount" -Level "INFO"
        if ($toIndex -ge $totalFilterCount) {
            break
        }

        $page++
    }

    return $objects
}

# ============================================================================
# Cloud functions
# ============================================================================

function Get-WorkspaceId {
    $uri = "$cloudUrl/rest/servicedeskapi/assets/workspace"
    $result = Invoke-Api -Method GET -Uri $uri -Headers (Get-RequestHeaders -Environment Cloud)
    if (-not $result) {
        return $null
    }
    $values = $result.values
    if (-not $values -or $values.Count -eq 0) {
        return $null
    }
    return $values[0].workspaceId
}

function Get-CloudObjectSchemas {
    $uri = "$cloudAssetsBaseUrl/v1/objectschema/list"
    $result = Invoke-Api -Method GET -Uri $uri -Headers (Get-RequestHeaders -Environment Cloud)
    if ($null -ne $result -and $null -ne $result.values) {
        return $result.values
    } else {
        return $null
    }
}

function Get-CloudObjectTypes {
    param([string]$ObjectSchemaId)
    $uri = "$cloudAssetsBaseUrl/v1/objectschema/$ObjectSchemaId/objecttypes/flat"
    return Invoke-Api -Method GET -Uri $uri -Headers (Get-RequestHeaders -Environment Cloud)
}

function Get-CloudAttributes {
    param([string]$ObjectTypeId)
    $uri = "$cloudAssetsBaseUrl/v1/objecttype/$ObjectTypeId/attributes"
    return Invoke-Api -Method GET -Uri $uri -Headers (Get-RequestHeaders -Environment Cloud)
}

function Get-CloudProjects {
    param(
        [int]$MaxResults = 50
    )
    $projects = @()
    $startAt = 0

    while ($true) {
        $uri = "$cloudUrl/rest/api/3/project?startAt=$startAt&maxResults=$MaxResults"
        $result = Invoke-Api -Method GET -Uri $uri -Headers (Get-RequestHeaders -Environment Cloud)
        if (-not $result) {
            break
        }

        if ($result -is [System.Collections.IEnumerable] -and -not ($result.PSObject.Properties.Name -contains 'values')) {
            $projects += $result
            break
        }

        if ($null -ne $result.values) {
            $projects += $result.values
        }

        if ($result.isLast -eq $true) {
            break
        }

        if ($null -eq $result.startAt -or $null -eq $result.maxResults) {
            break
        }

        $startAt = $result.startAt + $result.maxResults
    }

    return $projects
}

function Find-CloudObjectByLabel {
    param([string]$Label)
    $uri = "$cloudAssetsBaseUrl/v1/object/aql"
    $escapedLabel = $Label -replace '"', '""' -replace '(^\s+|\s+$)',''
    $qlQuery = "label = `"$escapedLabel`""
    $body = @{ qlQuery = $qlQuery }
    $result = Invoke-Api -Method POST -Uri $uri -Headers (Get-RequestHeaders -Environment Cloud) -Body $body
    if (-not $result) {
        return $null
    }
    if ($result.values) {
        return $result.values
    }
    return @()
}

function Update-CloudObjectAttributes {
    param(
        [string]$ObjectId,
        [array]$Attributes
    )
    $uri = "$cloudAssetsBaseUrl/v1/object/$ObjectId"
    $body = @{ attributes = $Attributes }
    $bodyJson = ConvertTo-Json -InputObject $body -Depth 10
    Write-Log "Calling Update API: URI: $uri, Payload: $bodyJson" -Level "INFO"
    if (-not $DRY_RUN) {
        return Invoke-Api -Method PUT -Uri $uri -Headers (Get-RequestHeaders -Environment Cloud) -Body $body
    }
    return $null;
}

# ============================================================================
# Main script
# ============================================================================

Write-Log "Starting Jira Assets project attribute migration" -Level "SUCCESS"

$dataCenterSchemas = Get-DataCenterObjectSchemas
if (-not $dataCenterSchemas) {
    Write-Log "No Data Center object schemas were found or API call failed." -Level "ERROR"
    exit 1
}

$cloudWorkspaceId = $cloudEnvironment.assets_workspace_id
if (-not $cloudWorkspaceId) { $cloudWorkspaceId = Get-WorkspaceId }
if (-not $cloudWorkspaceId) {
    Write-Log "Could not determine Cloud workspace ID." -Level "ERROR"
    exit 1
}
$cloudAssetsBaseUrl = "https://api.atlassian.com/jsm/assets/workspace/$cloudWorkspaceId"

$cloudSchemas = Get-CloudObjectSchemas
if (-not $cloudSchemas) {
    Write-Log "No Cloud object schemas were found or API call failed." -Level "ERROR"
    exit 1
}

$cloudProjects = Get-CloudProjects
if (-not $cloudProjects) {
    Write-Log "No Cloud projects were found or API call failed." -Level "ERROR"
    exit 1
}

$cloudProjectMap = @{}
foreach ($project in $cloudProjects) {
    if ($project.key -and $project.id) {
        $cloudProjectMap[$project.key] = $project.id
    }
}

foreach ($schema in $dataCenterSchemas) {
    $schemaName = $schema.name
    $schemaId = $schema.id
    Write-Log "Processing Data Center schema '$schemaName' (id=$schemaId)" -Level "INFO"

    $matchingCloudSchema = $cloudSchemas | Where-Object { $_.name -eq $schemaName }
    if (-not $matchingCloudSchema) {
        Write-Log "Skipping schema '$schemaName' because it is not present in Cloud." -Level "WARNING"
        continue
    }

    $cloudSchemaId = $matchingCloudSchema.id
    Write-Log "Found matching Cloud schema '$schemaName' (id=$cloudSchemaId)" -Level "INFO"

    $dataCenterTypes = Get-DataCenterObjectTypes -ObjectSchemaId $schemaId
    if (-not $dataCenterTypes) {
        Write-Log "No object types found for schema '$schemaName' in Data Center." -Level "WARNING"
        continue
    }

    $projectAttributesMap = @{}
    $projectAttributeNames = @()
    $dataCenterObjects = @()

    foreach ($objectType in $dataCenterTypes) {
        $objectTypeName = $objectType.name
        $objectTypeId = $objectType.id
        Write-Log "Loading attributes for Data Center object type '$objectTypeName'" -Level "INFO"

        $attributes = Get-DataCenterObjectTypeAttributes -ObjectTypeId $objectTypeId
        if (-not $attributes) {
            continue
        }

        foreach ($attribute in $attributes) {
            if ($attribute.type -eq 6) {
                $key = "$objectTypeName||$($attribute.name)"
                $projectAttributesMap[$key] = @{ objectTypeName = $objectTypeName; attributeName = $attribute.name }
                $projectAttributeNames += $attribute.name
            }
        }
    }

    $projectAttributeNames = $projectAttributeNames | Select-Object -Unique
    if (-not $projectAttributeNames -or $projectAttributeNames.Count -eq 0) {
        Write-Log "No project attributes of type 6 found for schema '$schemaName'." -Level "WARNING"
        continue
    }

    $aqlQuery = Get-ProjectAttributeQuery -AttributeNames $projectAttributeNames
    if (-not $aqlQuery) {
        Write-Log "Could not build AQL query for schema '$schemaName'." -Level "ERROR"
        continue
    }
    $aqlQuery = "$aqlQuery AND key = CDS-13314"

    Write-Log "Executing Data Center AQL query for schema '$schemaName': $aqlQuery" -Level "INFO"
    $dcObjects = Get-DataCenterObjectsByAql -IqlQuery $aqlQuery
    if (-not $dcObjects -or $dcObjects.Count -eq 0) {
        Write-Log "No Data Center objects returned for schema '$schemaName'." -Level "WARNING"
        continue
    }

    foreach ($dcObject in $dcObjects) {
        $objectTypeName = $dcObject.objectType.name
        $objectLabel = $dcObject.label
        if (-not $objectTypeName -or -not $objectLabel) {
            continue
        }

        $mappedAttributes = @()
        if ($dcObject.attributes) {
            foreach ($attr in $dcObject.attributes) {
                $attrType = $attr.objectTypeAttribute.type
                if ($attrType -ne 6) { continue }

                $attrName = $attr.objectTypeAttribute.name
                $projectKeys = Get-AttributeProjectKeys -Attribute $attr
                if (-not $attrName -or $projectKeys.Count -eq 0) { continue }

                $mappedAttributes += [PSCustomObject]@{
                    ObjectTypeName = $objectTypeName
                    AttributeName = $attrName
                    ProjectKeys = $projectKeys
                }
            }
        }

        if ($mappedAttributes.Count -gt 0) {
            $dataCenterObjects += [PSCustomObject]@{
                SchemaName = $schemaName
                ObjectTypeName = $objectTypeName
                Label = $objectLabel
                Attributes = $mappedAttributes
            }
        }
    }

    if ($dataCenterObjects.Count -eq 0) {
        Write-Log "No Data Center objects with type-6 project attributes were stored for schema '$schemaName'." -Level "WARNING"
        continue
    }

    Write-Log "Preparing Cloud attribute mappings for schema '$schemaName'" -Level "INFO"
    $cloudTypes = Get-CloudObjectTypes -ObjectSchemaId $cloudSchemaId
    if (-not $cloudTypes) {
        Write-Log "No Cloud object types found for schema '$schemaName'." -Level "ERROR"
        continue
    }

    $cloudObjectTypeMap = @{}
    foreach ($type in $cloudTypes) {
        if ($type.name -and $type.id) {
            $cloudObjectTypeMap[$type.name] = $type.id
        }
    }

    $cloudAttributeMap = @{}
    foreach ($dataCenterObjectTypeName in $dataCenterObjects | Select-Object -ExpandProperty ObjectTypeName | Select-Object -Unique) {
        if (-not $cloudObjectTypeMap.ContainsKey($dataCenterObjectTypeName)) {
            Write-Log "Cloud object type missing for '$dataCenterObjectTypeName' in schema '$schemaName'" -Level "WARNING"
            continue
        }

        $cloudTypeId = $cloudObjectTypeMap[$dataCenterObjectTypeName]
        $cloudAttributes = Get-CloudAttributes -ObjectTypeId $cloudTypeId
        if (-not $cloudAttributes) {
            Write-Log "No Cloud attributes found for object type '$dataCenterObjectTypeName'." -Level "WARNING"
            continue
        }

        foreach ($cloudAttribute in $cloudAttributes) {
            if ($cloudAttribute.name -and $cloudAttribute.id) {
                $cloudAttributeMap["$dataCenterObjectTypeName||$($cloudAttribute.name)"] = $cloudAttribute.id
            }
        }
    }

    Write-Log "Migrating objects for schema '$schemaName'" -Level "INFO"
    foreach ($dcObject in $dataCenterObjects) {
        $label = $dcObject.Label
        $objectTypeName = $dcObject.ObjectTypeName
        Write-Log "Searching Cloud object for label '$label'" -Level "INFO"

        $cloudObjects = Find-CloudObjectByLabel -Label $label
        if (-not $cloudObjects -or $cloudObjects.Count -eq 0) {
            Write-Log "No Cloud object found for label '$label'. Skipping." -Level "WARNING"
            continue
        }

        if ($cloudObjects.Count -gt 1) {
            Write-Log "Multiple Cloud objects found for label '$label'. Using the first result." -Level "WARNING"
        }

        $cloudObjectId = $cloudObjects[0].id
        if (-not $cloudObjectId) {
            Write-Log "Cloud object ID missing for label '$label'. Skipping." -Level "ERROR"
            continue
        }

        $updateAttributes = @()
        foreach ($attrItem in $dcObject.Attributes) {
            $key = "$($attrItem.ObjectTypeName)||$($attrItem.AttributeName)"
            if (-not $cloudAttributeMap.ContainsKey($key)) {
                Write-Log "Skipping attribute '$($attrItem.AttributeName)' for object type '$($attrItem.ObjectTypeName)' because Cloud mapping is missing." -Level "WARNING"
                continue
            }

            $cloudAttrId = $cloudAttributeMap[$key]
            $cloudValues = @()
            foreach ($projectKey in $attrItem.ProjectKeys) {
                if ($cloudProjectMap.ContainsKey($projectKey)) {
                    $cloudValues += @{ value = $cloudProjectMap[$projectKey] }
                } else {
                    Write-Log "Cloud project key '$projectKey' not found in Cloud project map." -Level "WARNING"
                }
            }

            if ($cloudValues.Count -gt 0) {
                $updateAttributes += @{ objectTypeAttributeId = $cloudAttrId; objectAttributeValues = $cloudValues }
            }
        }

        if ($updateAttributes.Count -eq 0) {
            Write-Log "No valid project attribute values found for Cloud object '$label'. Skipping update." -Level "WARNING"
            continue
        }

        Write-Log "Preparing to update Cloud object '$label' (id=$cloudObjectId) with $($updateAttributes.Count) project attributes" -Level "INFO"
        $result = Update-CloudObjectAttributes -ObjectId $cloudObjectId -Attributes $updateAttributes
        if ($result) {
            Write-Log "Successfully updated Cloud object '$label' (id=$cloudObjectId)." -Level "SUCCESS"
        } else {
            Write-Log "Failed to update Cloud object '$label' (id=$cloudObjectId)." -Level "ERROR"
        }

    }
}

Write-Log "Jira Assets project attribute migration complete." -Level "SUCCESS"



