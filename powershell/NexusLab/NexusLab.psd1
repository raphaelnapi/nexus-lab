@{
    RootModule = 'NexusLab.psm1'
    ModuleVersion = '2.0.0'
    GUID = '4bda9415-4982-44a8-86bc-59f51f22bb57'
    Author = 'Nexus-Lab'
    CompanyName = 'Nexus-Lab'
    Copyright = '(c) Nexus-Lab contributors'
    Description = 'Windows-first orchestration for controlled digital-forensics examinations.'
    PowerShellVersion = '7.6'
    CompatiblePSEditions = @('Core')
    FunctionsToExport = @(
        'Initialize-NexusLab','Test-NexusLabEnvironment','Get-NexusCapability',
        'New-NexusCase','Enter-NexusCase','Get-NexusCase',
        'Register-NexusEvidence','Test-NexusEvidence','New-NexusWorkingCopy',
        'Get-NexusMethod','Approve-NexusMethod','Invoke-NexusMethod','Get-NexusRun',
        'Add-NexusArtifact','Add-NexusFinding','New-NexusTimeline',
        'New-NexusReport','Export-NexusCaseManifest','New-NexusLedgerCheckpoint',
        'Test-NexusLedger','Invoke-NexusMigrationPreview','Invoke-NexusMigration'
    )
    CmdletsToExport = @()
    VariablesToExport = @()
    AliasesToExport = @()
    PrivateData = @{
        PSData = @{
            Tags = @('DFIR','Forensics','Windows','ChainOfCustody')
            ProjectUri = 'https://github.com/'
        }
    }
}

