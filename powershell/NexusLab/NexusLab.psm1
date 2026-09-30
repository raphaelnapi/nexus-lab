#requires -Version 7.6
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$script:ConfigPath = $env:NEXUSLAB_CONFIG
$script:ActiveCase = $null

function Invoke-NexusProcessJson {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Executable,
        [Parameter(Mandatory)][string[]]$ArgumentList,
        [Parameter(Mandatory)][hashtable]$Request,
        [hashtable]$Environment = @{}
    )
    $start = [System.Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $Executable
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.StandardInputEncoding = [System.Text.UTF8Encoding]::new($false)
    $start.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $start.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)
    foreach ($argument in $ArgumentList) { [void]$start.ArgumentList.Add($argument) }
    foreach ($key in $Environment.Keys) { $start.Environment[$key] = [string]$Environment[$key] }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $start
    if (-not $process.Start()) { throw "Unable to start $Executable" }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $json = $Request | ConvertTo-Json -Depth 30 -Compress
    $process.StandardInput.Write($json)
    $process.StandardInput.Close()
    $process.WaitForExit()
    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    if ($process.ExitCode -ne 0) {
        try { $detail = ($stderr | ConvertFrom-Json -Depth 30).error.message } catch { $detail = $stderr.Trim() }
        throw "Nexus core failed ($($process.ExitCode)): $detail"
    }
    return ($stdout | ConvertFrom-Json -Depth 30).result
}

function Get-NexusConfigPath {
    param([string]$ConfigPath)
    $candidate = if ($ConfigPath) { $ConfigPath } elseif ($script:ConfigPath) { $script:ConfigPath } else { Join-Path $script:RepositoryRoot 'nexus-lab.config.json' }
    return [System.IO.Path]::GetFullPath($candidate)
}

function Invoke-NexusCore {
    param([Parameter(Mandatory)][string]$Action, [Parameter(Mandatory)][hashtable]$Request, [string]$ConfigPath, [string]$PythonExecutable = 'python')
    $arguments = @('-m','nexus_lab.cli',$Action)
    if ($Action -notin @('initialize-config','migration-preview')) { $arguments += @('--config',(Get-NexusConfigPath $ConfigPath)) }
    $existing = $env:PYTHONPATH
    $pythonPath = Join-Path $script:RepositoryRoot 'python'
    if ($existing) { $pythonPath = "$pythonPath$([System.IO.Path]::PathSeparator)$existing" }
    Invoke-NexusProcessJson -Executable $PythonExecutable -ArgumentList $arguments -Request $Request -Environment @{ PYTHONPATH = $pythonPath; PYTHONUTF8 = '1' }
}

function Get-NexusCaseId {
    param([string]$CaseId)
    $value = if ($CaseId) { $CaseId } else { $script:ActiveCase }
    if (-not $value) { throw 'No case ID supplied and no active case context exists.' }
    return $value
}

function Initialize-NexusLab {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$EvidenceRoot,
        [Parameter(Mandatory)][string]$CaseRoot,
        [Parameter(Mandatory)][string]$ToolRoot,
        [string]$ConfigPath = (Join-Path $script:RepositoryRoot 'nexus-lab.config.json'),
        [string]$PythonExecutable = 'python',
        [switch]$CreateRoots
    )
    if ($PSCmdlet.ShouldProcess($ConfigPath, 'Create Nexus-Lab v2 configuration')) {
        $result = Invoke-NexusCore -Action 'initialize-config' -PythonExecutable $PythonExecutable -Request @{
            repository_root=$script:RepositoryRoot; evidence_root=$EvidenceRoot; case_root=$CaseRoot;
            tool_root=$ToolRoot; config_path=$ConfigPath; python_executable=$PythonExecutable;
            create_roots=[bool]$CreateRoots
        }
        $script:ConfigPath = $result.config_path
        return $result
    }
}

function Test-NexusLabEnvironment {
    [CmdletBinding()]
    param([string]$ConfigPath)
    $required = @('pwsh','python','sqlite3','ssh','sftp')
    $commands = foreach ($name in $required) {
        $command = Get-Command -Name $name -ErrorAction SilentlyContinue | Select-Object -First 1
        [pscustomobject]@{ Name=$name; Available=[bool]$command; Path=if($command){$command.Source}else{$null}; Version=if($command){[string]$command.Version}else{$null} }
    }
    [pscustomobject]@{
        PowerShellVersion = [string]$PSVersionTable.PSVersion
        IsSupportedPowerShell = $PSVersionTable.PSVersion -ge [version]'7.6'
        ConfigPath = Get-NexusConfigPath $ConfigPath
        ConfigExists = Test-Path -LiteralPath (Get-NexusConfigPath $ConfigPath) -PathType Leaf
        HyperVCmdlets = [bool](Get-Command Get-VM -ErrorAction SilentlyContinue)
        Pester5 = [bool](Get-Module -ListAvailable Pester | Where-Object Version -ge ([version]'5.0'))
        Commands = $commands
    }
}

function Get-NexusCapability {
    [CmdletBinding()]
    param([string]$Id,[string]$ConfigPath)
    $catalog = Get-Content -LiteralPath (Join-Path $script:RepositoryRoot 'tools\catalog.json') -Raw -Encoding utf8 | ConvertFrom-Json -Depth 20
    $validated=@();$configuration=$null;$configurationPath=Get-NexusConfigPath $ConfigPath
    if(Test-Path -LiteralPath $configurationPath -PathType Leaf){
        $configuration=Get-Content -LiteralPath $configurationPath -Raw -Encoding utf8|ConvertFrom-Json
        $validatedPath=Join-Path $configuration.tool_root 'validated-tools.json'
        if(Test-Path -LiteralPath $validatedPath -PathType Leaf){$validated=(Get-Content -LiteralPath $validatedPath -Raw -Encoding utf8|ConvertFrom-Json -Depth 20).tools}
    }
    $values = $catalog.capabilities
    if ($Id) { $values = $values | Where-Object id -eq $Id }
    foreach ($capability in $values) {
        $available = foreach ($provider in $capability.providers) {
            $command = Get-Command -Name $provider.command -ErrorAction SilentlyContinue | Select-Object -First 1
            $record=$validated|Where-Object provider_id -eq $provider.id|Select-Object -First 1
            $validatedPathValue=$null;$hashMatches=$false
            if($record -and $configuration){
                $toolRootFull=[IO.Path]::GetFullPath($configuration.tool_root).TrimEnd([IO.Path]::DirectorySeparatorChar)+[IO.Path]::DirectorySeparatorChar
                $validatedPathValue=[IO.Path]::GetFullPath((Join-Path $configuration.tool_root $record.relative_path))
                $inside=$validatedPathValue.StartsWith($toolRootFull,[StringComparison]::OrdinalIgnoreCase)
                if($inside -and (Test-Path -LiteralPath $validatedPathValue -PathType Leaf)){$hashMatches=(Get-FileHash -LiteralPath $validatedPathValue -Algorithm SHA256).Hash.ToLowerInvariant() -eq $record.binary_sha256.ToLowerInvariant()}
            }
            [pscustomobject]@{ Provider=$provider.id; Command=$provider.command; Available=[bool]$command; Path=if($hashMatches){$validatedPathValue}else{if($command){$command.Source}else{$null}}; Validated=$hashMatches; ValidationRecord=$record; Origin=$provider.origin }
        }
        [pscustomobject]@{ Id=$capability.id; Disposition=$capability.disposition; Providers=$available }
    }
}

function New-NexusCase {
    [CmdletBinding(SupportsShouldProcess)]
    param([Parameter(Mandatory)][string]$CaseId,[Parameter(Mandatory)][string]$Authority,[Parameter(Mandatory)][string]$Scope,[Parameter(Mandatory)][string]$Question,[Parameter(Mandatory)][string]$Examiner,[string]$Title,[string]$ConfigPath)
    if ($PSCmdlet.ShouldProcess($CaseId,'Create external case workspace')) {
        Invoke-NexusCore -Action 'new-case' -ConfigPath $ConfigPath -Request @{case_id=$CaseId;authority=$Authority;scope=$Scope;question=$Question;examiner=$Examiner;title=$Title}
    }
}

function Enter-NexusCase { [CmdletBinding()] param([Parameter(Mandatory)][string]$CaseId,[string]$ConfigPath) $null=Invoke-NexusCore -Action 'get-case' -ConfigPath $ConfigPath -Request @{case_id=$CaseId}; $script:ActiveCase=$CaseId; Get-NexusCase -CaseId $CaseId -ConfigPath $ConfigPath }
function Get-NexusCase { [CmdletBinding()] param([string]$CaseId,[string]$ConfigPath) Invoke-NexusCore -Action 'get-case' -ConfigPath $ConfigPath -Request @{case_id=(Get-NexusCaseId $CaseId)} }

function Register-NexusEvidence {
    [CmdletBinding(SupportsShouldProcess)]
    param([string]$CaseId,[Parameter(Mandatory)][string]$EvidenceId,[Parameter(Mandatory)][string]$SourcePath,[Parameter(Mandatory)][string]$EvidenceType,[Parameter(Mandatory)][string]$Operator,[string]$Description,[ValidateSet('observed','reported','not-determined')][string]$WriteProtection='reported',[string]$ConfigPath)
    $id=Get-NexusCaseId $CaseId
    if($PSCmdlet.ShouldProcess($SourcePath,"Register and hash evidence as $EvidenceId")){ Invoke-NexusCore -Action 'register-evidence' -ConfigPath $ConfigPath -Request @{case_id=$id;evidence_id=$EvidenceId;source_path=$SourcePath;evidence_type=$EvidenceType;operator=$Operator;description=$Description;write_protection=$WriteProtection} }
}
function Test-NexusEvidence { [CmdletBinding()] param([string]$CaseId,[Parameter(Mandatory)][string]$EvidenceId,[string]$ConfigPath) Invoke-NexusCore -Action 'verify-evidence' -ConfigPath $ConfigPath -Request @{case_id=(Get-NexusCaseId $CaseId);evidence_id=$EvidenceId} }
function New-NexusWorkingCopy {
    [CmdletBinding(SupportsShouldProcess,ConfirmImpact='High')]
    param([string]$CaseId,[Parameter(Mandatory)][string]$EvidenceId,[Parameter(Mandatory)][string]$WorkingCopyId,[Parameter(Mandatory)][string]$Operator,[Parameter(Mandatory)][string]$AuthorizationReference,[string]$ConfigPath)
    $id=Get-NexusCaseId $CaseId
    if($PSCmdlet.ShouldProcess($EvidenceId,"Create verified working copy $WorkingCopyId")){ Invoke-NexusCore -Action 'new-working-copy' -ConfigPath $ConfigPath -Request @{case_id=$id;evidence_id=$EvidenceId;working_copy_id=$WorkingCopyId;operator=$Operator;authorization_reference=$AuthorizationReference} }
}

function Get-NexusMethod { [CmdletBinding()] param([string]$MethodId) $files=Get-ChildItem -LiteralPath (Join-Path $script:RepositoryRoot 'methods') -Filter '*.json'; foreach($file in $files){$value=Get-Content -LiteralPath $file.FullName -Raw -Encoding utf8|ConvertFrom-Json -Depth 20;if(-not $MethodId -or $value.method_id -eq $MethodId){$value}} }
function Approve-NexusMethod {
    [CmdletBinding(SupportsShouldProcess,ConfirmImpact='High')]
    param([string]$CaseId,[Parameter(Mandatory)][string]$MethodId,[Parameter(Mandatory)][string]$ApprovedBy,[Parameter(Mandatory)][datetime]$ExpiresAtUtc,[Parameter(Mandatory)][hashtable]$ParameterBounds,[string]$ConfigPath)
    $id=Get-NexusCaseId $CaseId
    if($PSCmdlet.ShouldProcess("$id/$MethodId",'Record bounded method approval')){ Invoke-NexusCore -Action 'approve-method' -ConfigPath $ConfigPath -Request @{case_id=$id;method_id=$MethodId;approved_by=$ApprovedBy;expires_at_utc=$ExpiresAtUtc.ToUniversalTime().ToString('o');parameter_bounds=$ParameterBounds} }
}

function Invoke-NexusMethod {
    [CmdletBinding(SupportsShouldProcess,ConfirmImpact='High')]
    param(
        [string]$CaseId,[Parameter(Mandatory)][string]$MethodId,[Parameter(Mandatory)][string]$ApprovalId,
        [Parameter(Mandatory)][hashtable]$Parameters,[Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][object[]]$Inputs,[Parameter(Mandatory)][string[]]$OutputPaths,
        [Parameter(Mandatory)][string]$Purpose,[Parameter(Mandatory)][string]$ParameterExplanation,
        [Parameter(Mandatory)][string]$Operator,[string]$RetryOf,[string]$ConfigPath
    )
    $id=Get-NexusCaseId $CaseId
    $method=Get-NexusMethod -MethodId $MethodId
    if(-not $method){throw "Unknown method: $MethodId"}
    if($method.execution.backend -ne 'windows'){throw "Method $MethodId requires backend $($method.execution.backend); use the Hyper-V worker workflow."}
    foreach($argument in $Arguments){
        $matched=$false
        foreach($pattern in $method.execution.argument_patterns){if($argument -match $pattern){$matched=$true;break}}
        if(-not $matched){throw "Argument is not allowed by method pack: $argument"}
    }
    $capability=Get-NexusCapability -Id $method.capability_id -ConfigPath $ConfigPath
    $provider=$capability.Providers|Where-Object Validated|Select-Object -First 1
    if(-not $provider){throw "No tool-root binary with a matching validation manifest is available for capability $($method.capability_id)"}
    $command=@($provider.Path)+$Arguments
    if(-not $PSCmdlet.ShouldProcess(($command -join ' '),"Execute approved method $MethodId")){return}
    $toolRecord=$provider.ValidationRecord
    $environment=@{os_description=[Runtime.InteropServices.RuntimeInformation]::OSDescription;os_architecture=[string][Runtime.InteropServices.RuntimeInformation]::OSArchitecture;process_architecture=[string][Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture;powerShell_version=[string]$PSVersionTable.PSVersion;powerShell_edition=[string]$PSVersionTable.PSEdition;machine_name=[Environment]::MachineName;user_name=[Environment]::UserName;timezone=[TimeZoneInfo]::Local.Id;captured_at_utc=[datetime]::UtcNow.ToString('o')}
    $start=Invoke-NexusCore -Action 'run-start' -ConfigPath $ConfigPath -Request @{case_id=$id;approval_id=$ApprovalId;method_id=$MethodId;parameters=$Parameters;command=$command;purpose=$Purpose;parameter_explanation=$ParameterExplanation;operator=$Operator;inputs=$Inputs;planned_outputs=$OutputPaths;tool=@{provider_id=$toolRecord.provider_id;tool_name=$toolRecord.tool_name;version=$toolRecord.version;executable_path=$provider.Path;binary_sha256=$toolRecord.binary_sha256;signature_status=$toolRecord.signature_status;validated_at_utc=$toolRecord.validated_at_utc;validation_reference=$toolRecord.validation_reference};environment=$environment;retry_of=$RetryOf}
    $config=Get-Content -LiteralPath (Get-NexusConfigPath $ConfigPath) -Raw -Encoding utf8|ConvertFrom-Json
    $caseDir=Join-Path $config.case_root $id
    $logDir=Join-Path $caseDir 'logs\tool-runs'
    $stdoutPath=Join-Path $logDir "$($start.tool_run_id).stdout.log"
    $stderrPath=Join-Path $logDir "$($start.tool_run_id).stderr.log"
    $status='failed';$exitCode=$null;$limitations=$null
    try{
        $psi=[System.Diagnostics.ProcessStartInfo]::new();$psi.FileName=$provider.Path;$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true;$psi.StandardOutputEncoding=[Text.UTF8Encoding]::new($false);$psi.StandardErrorEncoding=[Text.UTF8Encoding]::new($false)
        foreach($argument in $Arguments){[void]$psi.ArgumentList.Add($argument)}
        $process=[Diagnostics.Process]::new();$process.StartInfo=$psi
        if(-not $process.Start()){throw 'Native process did not start'}
        $outTask=$process.StandardOutput.ReadToEndAsync();$errTask=$process.StandardError.ReadToEndAsync()
        if(-not $process.WaitForExit([int]$method.execution.timeout_seconds*1000)){$process.Kill($true);$status='timed-out';$limitations='Process exceeded the method timeout.'}else{$exitCode=$process.ExitCode;$status=if($method.execution.allowed_exit_codes -contains $exitCode){'succeeded'}else{'failed'}}
        [IO.File]::WriteAllText($stdoutPath,$outTask.GetAwaiter().GetResult(),[Text.UTF8Encoding]::new($false));[IO.File]::WriteAllText($stderrPath,$errTask.GetAwaiter().GetResult(),[Text.UTF8Encoding]::new($false))
    }catch{$limitations=$_.Exception.Message;if(-not(Test-Path -LiteralPath $stdoutPath)){[IO.File]::WriteAllText($stdoutPath,'',[Text.UTF8Encoding]::new($false))};if(-not(Test-Path -LiteralPath $stderrPath)){[IO.File]::WriteAllText($stderrPath,$limitations,[Text.UTF8Encoding]::new($false))}}
    finally{Invoke-NexusCore -Action 'run-finish' -ConfigPath $ConfigPath -Request @{case_id=$id;tool_run_id=$start.tool_run_id;status=$status;exit_status=$exitCode;stdout_path=$stdoutPath;stderr_path=$stderrPath;output_paths=$OutputPaths;output_summary="Method $MethodId finished with status $status";limitations=$limitations;operator=$Operator}}
}

function Get-NexusRun { [CmdletBinding()] param([string]$CaseId,[Parameter(Mandatory)][string]$ToolRunId,[string]$ConfigPath) Invoke-NexusCore -Action 'get-run' -ConfigPath $ConfigPath -Request @{case_id=(Get-NexusCaseId $CaseId);tool_run_id=$ToolRunId} }
function Add-NexusArtifact { [CmdletBinding(SupportsShouldProcess)] param([string]$CaseId,[string]$ArtifactId,[string]$EvidenceId,[string]$WorkingCopyId,[string]$ToolRunId,[Parameter(Mandatory)][string]$ArtifactType,[Parameter(Mandatory)][string]$SourceLocator,[hashtable]$Attributes=@{},[Parameter(Mandatory)][string]$Operator,[string]$ConfigPath) $id=Get-NexusCaseId $CaseId;if($PSCmdlet.ShouldProcess($id,'Register artifact')){Invoke-NexusCore -Action 'add-artifact' -ConfigPath $ConfigPath -Request @{case_id=$id;artifact_id=$ArtifactId;evidence_id=$EvidenceId;working_copy_id=$WorkingCopyId;tool_run_id=$ToolRunId;artifact_type=$ArtifactType;source_locator=$SourceLocator;attributes=$Attributes;operator=$Operator}} }
function Add-NexusFinding { [CmdletBinding(SupportsShouldProcess)] param([string]$CaseId,[string]$FindingId,[Parameter(Mandatory)][string]$Title,[Parameter(Mandatory)][object[]]$Statements,[string]$Limitations,[Parameter(Mandatory)][string]$Operator,[string]$ConfigPath) $id=Get-NexusCaseId $CaseId;if($PSCmdlet.ShouldProcess($id,'Register finding and epistemic statements')){Invoke-NexusCore -Action 'add-finding' -ConfigPath $ConfigPath -Request @{case_id=$id;finding_id=$FindingId;title=$Title;statements=$Statements;limitations=$Limitations;operator=$Operator}} }
function New-NexusTimeline { [CmdletBinding(SupportsShouldProcess)] param([string]$CaseId,[Parameter(Mandatory)][string]$ArtifactId,[Parameter(Mandatory)][string]$OriginalTimestamp,[Parameter(Mandatory)][string]$TimestampSemantics,[string]$SourceTimezone='unknown',[string]$NormalizedUtc,[string]$Resolution,[string]$Uncertainty,[Parameter(Mandatory)][string]$Description,[Parameter(Mandatory)][ValidateSet('observed','derived','inferred','not-determined')][string]$InterpretationStatus,[Parameter(Mandatory)][string]$Operator,[string]$ConfigPath) $id=Get-NexusCaseId $CaseId;if($PSCmdlet.ShouldProcess($id,'Register timeline event')){Invoke-NexusCore -Action 'add-timeline-event' -ConfigPath $ConfigPath -Request @{case_id=$id;artifact_id=$ArtifactId;original_timestamp=$OriginalTimestamp;timestamp_semantics=$TimestampSemantics;source_timezone=$SourceTimezone;normalized_utc=$NormalizedUtc;resolution=$Resolution;uncertainty=$Uncertainty;description=$Description;interpretation_status=$InterpretationStatus;operator=$Operator}} }
function New-NexusReport { [CmdletBinding(SupportsShouldProcess)] param([string]$CaseId,[Parameter(Mandatory)][string]$Operator,[string]$ConfigPath) $id=Get-NexusCaseId $CaseId;if($PSCmdlet.ShouldProcess($id,'Create versioned technical report')){Invoke-NexusCore -Action 'new-report' -ConfigPath $ConfigPath -Request @{case_id=$id;operator=$Operator}} }
function Export-NexusCaseManifest { [CmdletBinding(SupportsShouldProcess)] param([string]$CaseId,[Parameter(Mandatory)][string]$Operator,[string]$ConfigPath) $id=Get-NexusCaseId $CaseId;if($PSCmdlet.ShouldProcess($id,'Create case manifest export')){Invoke-NexusCore -Action 'export-manifest' -ConfigPath $ConfigPath -Request @{case_id=$id;operator=$Operator}} }
function New-NexusLedgerCheckpoint { [CmdletBinding(SupportsShouldProcess)] param([string]$CaseId,[Parameter(Mandatory)][string]$Operator,[string]$ConfigPath) $id=Get-NexusCaseId $CaseId;if($PSCmdlet.ShouldProcess($id,'Create unsigned ledger checkpoint')){Invoke-NexusCore -Action 'new-checkpoint' -ConfigPath $ConfigPath -Request @{case_id=$id;operator=$Operator}} }
function Test-NexusLedger { [CmdletBinding()] param([string]$CaseId,[string]$ConfigPath) Invoke-NexusCore -Action 'verify-ledger' -ConfigPath $ConfigPath -Request @{case_id=(Get-NexusCaseId $CaseId)} }
function Invoke-NexusMigrationPreview { [CmdletBinding()] param([Parameter(Mandatory)][string]$LegacyDatabase,[string]$LegacyRegistry,[string]$ConfigPath) Invoke-NexusCore -Action 'migration-preview' -ConfigPath $ConfigPath -Request @{legacy_database=$LegacyDatabase;legacy_registry=$LegacyRegistry} }
function Invoke-NexusMigration { [CmdletBinding(SupportsShouldProcess,ConfirmImpact='High')] param([Parameter(Mandatory)][string]$LegacyDatabase,[string]$LegacyRegistry,[Parameter(Mandatory)][string]$Authority,[Parameter(Mandatory)][string]$Scope,[Parameter(Mandatory)][string]$Question,[Parameter(Mandatory)][string]$Examiner,[string]$ConfigPath) if($PSCmdlet.ShouldProcess($LegacyDatabase,'Create non-destructive v2 migration')){Invoke-NexusCore -Action 'migration-run' -ConfigPath $ConfigPath -Request @{legacy_database=$LegacyDatabase;legacy_registry=$LegacyRegistry;authority=$Authority;scope=$Scope;question=$Question;examiner=$Examiner}} }

Export-ModuleMember -Function @(
    'Initialize-NexusLab','Test-NexusLabEnvironment','Get-NexusCapability','New-NexusCase','Enter-NexusCase','Get-NexusCase',
    'Register-NexusEvidence','Test-NexusEvidence','New-NexusWorkingCopy','Get-NexusMethod','Approve-NexusMethod','Invoke-NexusMethod','Get-NexusRun',
    'Add-NexusArtifact','Add-NexusFinding','New-NexusTimeline','New-NexusReport','Export-NexusCaseManifest','New-NexusLedgerCheckpoint',
    'Test-NexusLedger','Invoke-NexusMigrationPreview','Invoke-NexusMigration'
)
