param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
    throw 'Close Unreal Editor before exporting a consistent asset snapshot.'
}
$paths = @(& git -C $project ls-files --others --ignored --exclude-standard -- Content/Assets)
if ($LASTEXITCODE -ne 0 -or $paths.Count -eq 0) { throw 'No ignored art found, or Git failed.' }
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$version = Get-Date -Format 'yyyyMMdd-HHmmss'
$archiveName = "GaesinLight-Art-$version.zip"
$archivePath = Join-Path $OutputDirectory $archiveName
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::Open($archivePath, [IO.Compression.ZipArchiveMode]::Create)
try {
    $records = foreach ($path in $paths) {
        $file = Get-Item -LiteralPath (Join-Path $project $path)
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $file.FullName, $path, [IO.Compression.CompressionLevel]::Optimal) | Out-Null
        [ordered]@{path=$path; bytes=$file.Length; sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash}
    }
} finally { $zip.Dispose() }
$manifest = [ordered]@{
    version=$version
    archive=$archiveName
    archiveSha256=(Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
    files=@($records)
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $project 'ArtManifest.json') -Encoding UTF8
Write-Output "Exported $($paths.Count) files: $archivePath"
Write-Output 'Commit ArtManifest.json together with the code/map changes that require this asset version.'
