BeforeAll {
    $Repository = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    $Manifest = Join-Path $Repository 'powershell\NexusLab\NexusLab.psd1'
    $ModuleText = Get-Content -LiteralPath (Join-Path $Repository 'powershell\NexusLab\NexusLab.psm1') -Raw -Encoding utf8
}

Describe 'NexusLab module contracts' {
    It 'declares PowerShell 7.6' {
        (Import-PowerShellDataFile -LiteralPath $Manifest).PowerShellVersion | Should -Be '7.6'
    }
    It 'does not use Invoke-Expression' {
        $ModuleText | Should -Not -Match '(?i)Invoke-Expression'
    }
    It 'does not construct native commands through cmd.exe' {
        $ModuleText | Should -Not -Match '(?i)cmd\.exe|/c\s'
    }
    It 'uses ProcessStartInfo ArgumentList' {
        $ModuleText | Should -Match 'ArgumentList\.Add'
    }
    It 'exports the planned public cmdlets' {
        $data = Import-PowerShellDataFile -LiteralPath $Manifest
        foreach ($name in @('Initialize-NexusLab','New-NexusCase','Register-NexusEvidence','Approve-NexusMethod','Invoke-NexusMethod','Invoke-NexusMigrationPreview')) {
            $data.FunctionsToExport | Should -Contain $name
        }
    }
}
