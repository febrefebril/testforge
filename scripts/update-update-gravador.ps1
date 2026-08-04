
[CmdletBinding()]
param(
    [string]$SourceBranch = "",
    [string]$TargetBranch = "update-gravador",
    [string]$Remote = "origin",
    [switch]$AllowMergeCommit,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    $output = & git @Args 2>&1
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $cmd = "git " + ($Args -join " ")
        $msg = ($output | Out-String).Trim()
        throw "Falha ao executar: $cmd`n$msg"
    }

    return ($output | Out-String).Trim()
}

function Test-GitRefExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Ref
    )

    & git rev-parse --verify --quiet $Ref *> $null
    return ($LASTEXITCODE -eq 0)
}

Write-Host "==> Validando ambiente Git..." -ForegroundColor Cyan
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git nao encontrado no PATH."
}

$repoRoot = Invoke-Git -Args @("rev-parse", "--show-toplevel")
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($SourceBranch)) {
    $SourceBranch = Invoke-Git -Args @("rev-parse", "--abbrev-ref", "HEAD")
}

Write-Host "==> Repositorio: $repoRoot"
Write-Host "==> Origem: $SourceBranch"
Write-Host "==> Destino: $TargetBranch"
Write-Host "==> Remoto: $Remote"

$status = Invoke-Git -Args @("status", "--porcelain")
if (-not [string]::IsNullOrWhiteSpace($status)) {
    throw "Working tree com alteracoes pendentes. Commit/stash antes de rodar o script."
}

Write-Host "==> Atualizando refs remotas..." -ForegroundColor Cyan
Invoke-Git -Args @("fetch", $Remote, "--prune") | Out-Null

$sourceRemoteRef = "refs/remotes/$Remote/$SourceBranch"
$targetRemoteRef = "refs/remotes/$Remote/$TargetBranch"
$sourceLocalRef = "refs/heads/$SourceBranch"
$targetLocalRef = "refs/heads/$TargetBranch"

$sourceExistsRemote = Test-GitRefExists -Ref $sourceRemoteRef
$sourceExistsLocal = Test-GitRefExists -Ref $sourceLocalRef
if (-not $sourceExistsRemote -and -not $sourceExistsLocal) {
    throw "Branch de origem nao encontrada: $SourceBranch"
}

if ($sourceExistsRemote) {
    $sourceRefForMerge = "$Remote/$SourceBranch"
}
else {
    $sourceRefForMerge = $SourceBranch
}

$targetExistsLocal = Test-GitRefExists -Ref $targetLocalRef
$targetExistsRemote = Test-GitRefExists -Ref $targetRemoteRef

if ($targetExistsLocal) {
    Write-Host "==> Checkout da branch de destino local..." -ForegroundColor Cyan
    Invoke-Git -Args @("checkout", $TargetBranch) | Out-Null
}
elseif ($targetExistsRemote) {
    Write-Host "==> Criando branch local de destino rastreando remoto..." -ForegroundColor Cyan
    Invoke-Git -Args @("checkout", "-b", $TargetBranch, "--track", "$Remote/$TargetBranch") | Out-Null
}
else {
    Write-Host "==> Branch de destino nao existe. Criando a partir da origem..." -ForegroundColor Yellow
    Invoke-Git -Args @("checkout", "-b", $TargetBranch, $sourceRefForMerge) | Out-Null
}

if ($targetExistsRemote) {
    Write-Host "==> Atualizando branch de destino com remoto..." -ForegroundColor Cyan
    Invoke-Git -Args @("pull", "--ff-only", $Remote, $TargetBranch) | Out-Null
}

if ($AllowMergeCommit) {
    Write-Host "==> Fazendo merge com commit explicito..." -ForegroundColor Cyan
    Invoke-Git -Args @("merge", "--no-ff", "--no-edit", $sourceRefForMerge) | Out-Null
}
else {
    Write-Host "==> Fazendo merge fast-forward only (seguro)..." -ForegroundColor Cyan
    Invoke-Git -Args @("merge", "--ff-only", $sourceRefForMerge) | Out-Null
}

if (-not $NoPush) {
    Write-Host "==> Enviando $TargetBranch para $Remote..." -ForegroundColor Cyan
    Invoke-Git -Args @("push", $Remote, $TargetBranch) | Out-Null
}
else {
    Write-Host "==> Push desabilitado por parametro -NoPush" -ForegroundColor Yellow
}

Write-Host "==> Retornando para branch de origem: $SourceBranch" -ForegroundColor Cyan
Invoke-Git -Args @("checkout", $SourceBranch) | Out-Null

Write-Host "Concluido: $TargetBranch atualizado com $SourceBranch." -ForegroundColor Green

