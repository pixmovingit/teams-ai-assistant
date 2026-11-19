param(
    [string]$ClientId = 'e8907370-77d6-4c55-917c-e177de591b07',
    [string]$TenantId = '93acd104-0887-4c59-bb44-885eb0e256ba'
)

$ErrorActionPreference = 'Stop'
$source = $PSScriptRoot
$destination = Join-Path $env:USERPROFILE '.codex\skills\teams-ai-assistant'
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw '未找到 Python，请先安装 Python 3.9 或更高版本。'
}
& python -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)'
if ($LASTEXITCODE -ne 0) { throw '需要 Python 3.9 或更高版本。' }
if (Test-Path -LiteralPath $destination) {
    throw "目标已存在：$destination。请先检查已有技能，避免覆盖本地修改。"
}
New-Item -ItemType Directory -Path (Join-Path $destination 'scripts') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $source 'SKILL.md'), (Join-Path $source 'README.md') -Destination $destination
Copy-Item -LiteralPath (Join-Path $source 'scripts\teams.py') -Destination (Join-Path $destination 'scripts\teams.py')
Copy-Item -LiteralPath (Join-Path $source 'requirements.txt') -Destination $destination
& python -m venv (Join-Path $destination '.venv')
if ($LASTEXITCODE -ne 0) { throw '创建虚拟环境失败。' }
& (Join-Path $destination '.venv\Scripts\python.exe') -m pip install -r (Join-Path $destination 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败，请检查网络及目标目录后重试。' }
[Environment]::SetEnvironmentVariable('TEAMS_CLIENT_ID', $ClientId, 'User')
[Environment]::SetEnvironmentVariable('TEAMS_TENANT_ID', $TenantId, 'User')
$env:TEAMS_CLIENT_ID = $ClientId
$env:TEAMS_TENANT_ID = $TenantId
Write-Output "技能安装完成：$destination"
Write-Output '请重新启动 Codex，随后使用 Teams AI Assistant 登录公司账号。'
Write-Output "也可立即运行：& `"$destination\.venv\Scripts\python.exe`" `"$destination\scripts\teams.py`" login"
