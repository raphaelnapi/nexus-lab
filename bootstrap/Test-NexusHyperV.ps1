[CmdletBinding()]
param([string]$VmName)

$getVm = Get-Command Get-VM -ErrorAction SilentlyContinue
if (-not $getVm) {
    [pscustomobject]@{ Ready=$false; Reason='Hyper-V cmdlets are unavailable'; VmName=$VmName }
    return
}
$vm = if ($VmName) { Get-VM -Name $VmName -ErrorAction SilentlyContinue } else { $null }
[pscustomobject]@{
    Ready = [bool]$vm
    HyperVCmdlets = $true
    VmName = $VmName
    VmState = if ($vm) { [string]$vm.State } else { $null }
    ExternalNetworkingAuthorized = $false
    Note = 'Network topology, image hash, SSH key, and tool validation require an administrative worker record.'
}
