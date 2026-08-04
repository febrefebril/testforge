
﻿[CmdletBinding()]
param(
  [string]$RepoRoot="C:\Desenvolvimento\AUTOMATA-PRIMUS",
  [string]$Manifest="",
  [string]$Branch="fix/testforge-piloto-integrado",
  [string]$Python="",
  [string]$OutputRoot="",
  [ValidateSet("Snapshot","Validate","Apply","All","Status","Cleanup")][string]$Action="Snapshot",
  [switch]$Resume,
  [switch]$NoCommit,
  [switch]$KeepFailedChanges,
  [string]$DownloadsRoot="$env:USERPROFILE\Downloads",
  [int]$SnapshotMaxFileMB=2,
  [int]$SnapshotMaxTotalMB=50
)
Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Write-Step([string]$Text){Write-Host "`n=== $Text ===" -ForegroundColor Cyan}
function Write-Ok([string]$Text){Write-Host "[OK] $Text" -ForegroundColor Green}
function Write-Warn([string]$Text){Write-Host "[WARN] $Text" -ForegroundColor Yellow}

function Invoke-Native{
  param([string]$File,[string[]]$Arguments=@(),[string]$LogPath,[switch]$AllowFailure)
  Write-Host ("> "+$File+" "+($Arguments -join " ")) -ForegroundColor DarkGray
  & $File @Arguments 2>&1 | Tee-Object -FilePath $LogPath -Append
  $rc=$LASTEXITCODE
  if($rc -ne 0 -and -not $AllowFailure){throw "Comando falhou com codigo ${rc}: $File"}
  return $rc
}
function Read-Json([string]$Path){
  try{return Get-Content -LiteralPath $Path -Raw -Encoding UTF8|ConvertFrom-Json}
  catch{throw "JSON invalido em ${Path}: $($_.Exception.Message)"}
}
function Resolve-Python{
  if(-not [string]::IsNullOrWhiteSpace($Python)){return $Python}
  $candidate=Join-Path $RepoRoot ".venv\Scripts\python.exe"
  if(Test-Path -LiteralPath $candidate -PathType Leaf){return $candidate}
  return "python"
}
function Safe-Target([string]$RelativePath){
  if([string]::IsNullOrWhiteSpace($RelativePath)){throw "Caminho vazio no patch"}
  if([IO.Path]::IsPathRooted($RelativePath)){throw "Caminho absoluto no patch: $RelativePath"}
  $root=[IO.Path]::GetFullPath($RepoRoot).TrimEnd('\','/')+[IO.Path]::DirectorySeparatorChar
  $target=[IO.Path]::GetFullPath((Join-Path $RepoRoot $RelativePath))
  if(-not $target.StartsWith($root,[StringComparison]::OrdinalIgnoreCase)){throw "Patch tenta sair do repositorio: $RelativePath"}
  return $target
}
function Initialize-RunDirectory{
  $gitInfo=Join-Path $RepoRoot ".git\info"
  if(-not(Test-Path -LiteralPath $gitInfo)){throw ".git\info nao encontrado"}
  $exclude=Join-Path $gitInfo "exclude";$entry=".testforge-patch-run/"
  $current=if(Test-Path -LiteralPath $exclude){@(Get-Content -LiteralPath $exclude)}else{@()}
  if($current -notcontains $entry){Add-Content -LiteralPath $exclude -Value $entry -Encoding UTF8}
  $script:RunDir=if([string]::IsNullOrWhiteSpace($OutputRoot)){Join-Path $RepoRoot ".testforge-patch-run"}else{[IO.Path]::GetFullPath($OutputRoot)}
  New-Item -ItemType Directory -Path $script:RunDir -Force|Out-Null
  $script:StatePath=Join-Path $script:RunDir "state.json"
  $script:MainLog=Join-Path $script:RunDir "patch-flow.log"
}
function New-ProjectSnapshot([string]$Destination){
  Write-Step "Gerar snapshot git-aware do projeto"
  $ext=@('.py','.pyi','.js','.mjs','.cjs','.ts','.tsx','.jsx','.json','.jsonl','.yml','.yaml','.toml','.ini','.cfg','.conf','.md','.rst','.txt','.ps1','.psm1','.psd1','.bat','.cmd','.feature','.html','.css','.scss','.xml','.properties','.sql')
  $names=@('VERSION','Dockerfile','Makefile','.gitignore','.gitattributes','.editorconfig')
  $excluded=@('.git/','.venv/','venv/','env/','node_modules/','dist/','build/','target/','coverage/','htmlcov/','recordings/','recordings_failed/','submissions/','diagnostic/','trace/','traces/','screenshot/','screenshots/','video/','videos/','wheelhouse/','.testforge-patch-run/','docs/conhecimento_ancestral/')
  $segmentPattern='(^|/)(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.tox|\.nox|\.idea|\.vscode)(/|$)'
  $maxFile=[int64]$SnapshotMaxFileMB*1MB;$maxTotal=[int64]$SnapshotMaxTotalMB*1MB;$included=[int64]0
  $m=[ordered]@{schema_version=4;tool_version='1.0.3';snapshot_mode='git-aware-source-only';generated_at=(Get-Date).ToUniversalTime().ToString('o');root=$RepoRoot;git=[ordered]@{};included_files=@();skipped=[ordered]@{excluded_directory=0;unsupported_extension=0;oversized=0;total_limit=0;binary=0;missing=0}}
  $m.git.branch=(& git -C $RepoRoot branch --show-current).Trim();$m.git.commit=(& git -C $RepoRoot rev-parse HEAD).Trim();$m.git.status=@(& git -C $RepoRoot status --porcelain)
  $lines=[Collections.Generic.List[string]]::new();$lines.Add('# TestForge project snapshot');$lines.Add('# tool_version: 1.0.3');$lines.Add('# mode: git-aware-source-only');$lines.Add('# includes_tests: true');$lines.Add("# generated_at: $($m.generated_at)");$lines.Add("# branch: $($m.git.branch)");$lines.Add("# commit: $($m.git.commit)");$lines.Add('')
  $tracked=@(& git -C $RepoRoot ls-files --cached);if($LASTEXITCODE -ne 0){throw "Falha em git ls-files --cached"}
  $untracked=@(& git -C $RepoRoot ls-files --others --exclude-standard);if($LASTEXITCODE -ne 0){throw "Falha em git ls-files --others"}
  $files=@($tracked+$untracked|Where-Object{-not[string]::IsNullOrWhiteSpace($_)}|Sort-Object -Unique)
  foreach($raw in $files){
    $rel=([string]$raw).Replace('\','/').TrimStart('.','/');$skip=$false
    foreach($prefix in $excluded){if($rel.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){$skip=$true;break}}
    if($skip -or $rel -match $segmentPattern){$m.skipped.excluded_directory++;continue}
    $full=Join-Path $RepoRoot $rel
    if(-not(Test-Path -LiteralPath $full -PathType Leaf)){$m.skipped.missing++;continue}
    $info=Get-Item -LiteralPath $full
    if(($ext -notcontains $info.Extension.ToLowerInvariant())-and($names -notcontains $info.Name)){$m.skipped.unsupported_extension++;continue}
    if($info.Length -gt $maxFile){$m.skipped.oversized++;continue}
    if(($included+$info.Length)-gt $maxTotal){$m.skipped.total_limit++;continue}
    $bytes=[IO.File]::ReadAllBytes($full);$probe=[Math]::Min($bytes.Length,8192);$binary=$false
    for($i=0;$i -lt $probe;$i++){if($bytes[$i]-eq 0){$binary=$true;break}}
    if($binary){$m.skipped.binary++;continue}
    $text=[Text.Encoding]::UTF8.GetString($bytes);$hash=(Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
    $m.included_files+=[ordered]@{file=$rel;sha256=$hash;bytes=$info.Length};$included+=$info.Length
    $lines.Add("===== FILE: $rel =====");$lines.Add("# sha256: $hash");$lines.Add('');$lines.Add($text);$lines.Add("===== END FILE: $rel =====");$lines.Add('')
  }
  $m.included_count=@($m.included_files).Count;$m.included_bytes=$included;$m.max_file_mb=$SnapshotMaxFileMB;$m.max_total_mb=$SnapshotMaxTotalMB
  $lines.Add('===== MANIFEST JSON =====');$lines.Add(($m|ConvertTo-Json -Depth 8));$lines.Add('===== END MANIFEST JSON =====')
  Set-Content -LiteralPath $Destination -Value $lines -Encoding UTF8
  Write-Ok "Snapshot: $Destination";Write-Ok "Testes incluidos: sim";Write-Ok "Arquivos incluidos: $($m.included_count)";Write-Ok "Conteudo incluido: $([Math]::Round($included/1MB,2)) MiB";Write-Ok "Ignorados pelo limite total: $($m.skipped.total_limit)";Write-Ok "SHA256: $((Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash)"
}
function Test-Patch([object]$Patch,[string]$PatchPath){
  $n=0
  foreach($c in @($Patch.changes)){$n++;$type=[string]$c.type;$target=Safe-Target([string]$c.file)
    switch($type){
      'create_file'{if(Test-Path -LiteralPath $target){throw "Mudanca ${n}: arquivo ja existe: $($c.file)"};if($null -eq $c.content){throw "Mudanca ${n}: content ausente"}}
      'text_replace'{if(-not(Test-Path -LiteralPath $target -PathType Leaf)){throw "Mudanca ${n}: arquivo ausente: $($c.file)"};$old=[string]$c.old;if([string]::IsNullOrEmpty($old)){throw "Mudanca ${n}: old vazio"};$current=Get-Content -LiteralPath $target -Raw -Encoding UTF8;$found=([regex]::Matches($current,[regex]::Escape($old))).Count;$expected=if($null-ne$c.count){[int]$c.count}else{1};if($found-ne$expected){throw "Mudanca ${n}: ocorrencias em $($c.file): encontradas=$found esperadas=$expected"};foreach($anchor in @($c.must_contain)){if(-not$current.Contains([string]$anchor)){throw "Mudanca ${n}: ancora ausente: $anchor"}}}
      'delete_file'{if(-not(Test-Path -LiteralPath $target -PathType Leaf)){throw "Mudanca ${n}: arquivo ausente: $($c.file)"}}
      default{throw "Mudanca ${n}: tipo nao suportado: $type"}
    }
  }
  Write-Ok "Patch validado: $(Split-Path $PatchPath -Leaf)"
}
function Apply-Patch([object]$Patch,[string]$PatchPath,[string]$ReportPath){
  Test-Patch $Patch $PatchPath;$report=[ordered]@{schema_version=1;patch=$PatchPath;applied_at=(Get-Date).ToUniversalTime().ToString('o');changes=@()};$n=0
  foreach($c in @($Patch.changes)){$n++;$type=[string]$c.type;$target=Safe-Target([string]$c.file)
    switch($type){
      'create_file'{$parent=Split-Path -Parent $target;if(-not(Test-Path -LiteralPath $parent)){New-Item -ItemType Directory -Path $parent -Force|Out-Null};[IO.File]::WriteAllText($target,[string]$c.content,[Text.UTF8Encoding]::new($false))}
      'text_replace'{$current=Get-Content -LiteralPath $target -Raw -Encoding UTF8;[IO.File]::WriteAllText($target,$current.Replace([string]$c.old,[string]$c.new),[Text.UTF8Encoding]::new($false))}
      'delete_file'{Remove-Item -LiteralPath $target -Force}
    }
    $report.changes+=[ordered]@{index=$n;type=$type;file=[string]$c.file}
  }
  $report|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $ReportPath -Encoding UTF8;Write-Ok "Patch aplicado: $(Split-Path $PatchPath -Leaf)"
}
function Invoke-Tests([object]$Step,[string]$LogPath){foreach($t in @($Step.tests)){$args=@('-m','pytest')+@($t.args|ForEach-Object{[string]$_});Invoke-Native -File $script:PythonExe -Arguments $args -LogPath $LogPath|Out-Null}}
function Invoke-Manifest([switch]$ValidateOnly){
  $data=Read-Json $Manifest;if([int]$data.schemaVersion-ne 1){throw "schemaVersion nao suportada"};$completed=@();if($Resume-and(Test-Path -LiteralPath $script:StatePath)){$completed=@((Read-Json $script:StatePath).completed)}
  foreach($step in @($data.steps)){$id=[string]$step.id;if($completed-contains$id){Write-Warn "SKIP $id";continue};Write-Step "$id - $($step.name)";$log=Join-Path $script:RunDir "$id.log";$baseline=(& git -C $RepoRoot rev-parse HEAD).Trim();$patchRel=[string]$step.patch
    try{
      if(-not[string]::IsNullOrWhiteSpace($patchRel)){$patchPath=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $Manifest) $patchRel));if(-not(Test-Path -LiteralPath $patchPath)){throw "Patch ausente: $patchPath"};$patch=Read-Json $patchPath;Test-Patch $patch $patchPath;if(-not$ValidateOnly){Apply-Patch $patch $patchPath (Join-Path $script:RunDir "$id-apply-report.json")}}
      if(-not$ValidateOnly){Invoke-Tests $step $log;Invoke-Native -File git -Arguments @('-C',$RepoRoot,'diff','--check') -LogPath $log|Out-Null;$changes=@(git -C $RepoRoot status --porcelain);if($changes.Count-gt 0){if(-not$NoCommit){Invoke-Native -File git -Arguments @('-C',$RepoRoot,'add','--all') -LogPath $log|Out-Null;Invoke-Native -File git -Arguments @('-C',$RepoRoot,'commit','-m',[string]$step.commit) -LogPath $log|Out-Null}}elseif(-not[string]::IsNullOrWhiteSpace($patchRel)){throw "Patch nao produziu alteracoes"};$completed+=$id;[ordered]@{schema_version=1;branch=$Branch;completed=$completed;updated_at=(Get-Date).ToString('o')}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $script:StatePath -Encoding UTF8}
      Write-Ok $id
    }catch{Write-Host "[FALHA] ${id}: $($_.Exception.Message)" -ForegroundColor Red;if(-not$ValidateOnly-and-not$KeepFailedChanges){& git -C $RepoRoot reset --hard $baseline|Out-File $log -Append;& git -C $RepoRoot clean -fd|Out-File $log -Append};throw}
  }
}
function Cleanup-Tools{
  Write-Step "Arquivar ferramentas antigas";$archive=Join-Path $DownloadsRoot ('TestForge-Tools-Archive-'+(Get-Date -Format 'yyyyMMdd-HHmmss'));New-Item -ItemType Directory -Path $archive -Force|Out-Null;$moved=@()
  $files=Get-ChildItem -LiteralPath $DownloadsRoot -File -Recurse -ErrorAction SilentlyContinue|Where-Object{$_.Name-match'^code2txt2code.*\.py$'-or$_.Name-in@('Apply-TestForgePatches.ps1','TestForgePatches.ps1')}
  foreach($f in $files){if($f.FullName-eq$PSCommandPath-or$f.FullName.StartsWith($archive)){continue};$dest=Join-Path $archive (($f.FullName.Substring($DownloadsRoot.Length).TrimStart('\'))-replace'[\\/:*?"<>|]','__');$hash=(Get-FileHash $f.FullName -Algorithm SHA256).Hash;Move-Item $f.FullName $dest -Force;$moved+=[ordered]@{source=$f.FullName;destination=$dest;sha256=$hash}}
  $moved|ConvertTo-Json -Depth 5|Set-Content (Join-Path $archive 'archive-manifest.json') -Encoding UTF8;Write-Ok "Arquivados $($moved.Count) arquivos em $archive"
}
if(-not(Test-Path -LiteralPath $RepoRoot -PathType Container)){throw "Repositorio nao encontrado: $RepoRoot"};$RepoRoot=(Resolve-Path $RepoRoot).Path;& git -C $RepoRoot rev-parse --is-inside-work-tree *>$null;if($LASTEXITCODE-ne 0){throw "Nao e repositorio Git"}
Initialize-RunDirectory;$script:PythonExe=Resolve-Python
if($Action-in@('Validate','Apply','All')){if([string]::IsNullOrWhiteSpace($Manifest)-or-not(Test-Path -LiteralPath $Manifest)){throw "Manifesto ausente"};$Manifest=(Resolve-Path $Manifest).Path}
if($Action-in@('Apply','All')){$dirty=@(git -C $RepoRoot status --porcelain);if($dirty.Count-gt 0-and-not$Resume){throw "Arvore Git precisa estar limpa"};$current=(& git -C $RepoRoot branch --show-current).Trim();if($current-ne$Branch){$exists=(& git -C $RepoRoot branch --list $Branch).Trim();if($exists){Invoke-Native git @('-C',$RepoRoot,'switch',$Branch) $script:MainLog|Out-Null}else{Invoke-Native git @('-C',$RepoRoot,'switch','-c',$Branch) $script:MainLog|Out-Null}}}
if($Action-in@('Snapshot','All')){New-ProjectSnapshot (Join-Path $script:RunDir ('snapshot_testforge_'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.txt'))}
if($Action-eq'Validate'){Invoke-Manifest -ValidateOnly};if($Action-in@('Apply','All')){Invoke-Manifest};if($Action-eq'Status'){git -C $RepoRoot status --short;git -C $RepoRoot log --oneline --decorate -15};if($Action-eq'Cleanup'){Cleanup-Tools};Write-Ok "Fluxo concluido: $script:RunDir"

