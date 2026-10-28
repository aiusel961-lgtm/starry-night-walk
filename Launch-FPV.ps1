[CmdletBinding()]
param([switch]$CheckOnly)

$ErrorActionPreference = 'Stop'
$sceneRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$sceneFile = Join-Path $sceneRoot 'index.html'
if (-not (Test-Path -LiteralPath $sceneFile -PathType Leaf)) { throw "Scene file missing: $sceneFile" }

$browserCandidates = @(
    (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe')
)
$sceneBrowser = $browserCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $sceneBrowser) { throw 'Please install Chrome or Microsoft Edge, then launch again.' }

# A project-only profile starts a separate GPU process instead of reusing a browser
# that has already selected the integrated adapter. No system GPU settings change.
$sceneProfile = Join-Path $sceneRoot '.fpv-browser'
$sceneUri = ([Uri]$sceneFile).AbsoluteUri
$launchArgs = @(
    '--use-angle=d3d11',
    '--force_high_performance_gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-mode',
    ('--user-data-dir="' + $sceneProfile + '"'),
    ('--app="' + $sceneUri + '"')
)

if ($CheckOnly) {
    [pscustomobject]@{
        Browser = $sceneBrowser
        Scene = $sceneUri
        Profile = $sceneProfile
        Arguments = $launchArgs
        Preference = 'Discrete GPU first; browser uses available hardware when absent.'
    } | ConvertTo-Json -Depth 3
    exit 0
}

# Hidden launch avoids a flashing helper console; the browser owns its app window.
Start-Process -FilePath $sceneBrowser -ArgumentList $launchArgs -WorkingDirectory $sceneRoot -WindowStyle Hidden | Out-Null
