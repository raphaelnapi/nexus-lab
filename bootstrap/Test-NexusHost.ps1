[CmdletBinding()]
param()

$required = @('pwsh','python','sqlite3','ssh','sftp')
$commands = foreach ($name in $required) {
    $command = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
    [pscustomobject]@{
        Name = $name
        Available = [bool]$command
        Path = if ($command) { $command.Source } else { $null }
        Version = if ($command) { [string]$command.Version } else { $null }
    }
}

[pscustomobject]@{
    TimestampUtc = [datetime]::UtcNow.ToString('o')
    PowerShellVersion = [string]$PSVersionTable.PSVersion
    PowerShell76 = $PSVersionTable.PSVersion -ge [version]'7.6'
    Pester5 = [bool](Get-Module -ListAvailable Pester | Where-Object Version -ge ([version]'5.0'))
    HyperVCmdlets = [bool](Get-Command Get-VM -ErrorAction SilentlyContinue)
    Commands = $commands
}

