param(
    [ValidateSet('start', 'status', 'stop', 'adopt', 'handoff', 'review', 'locate-token')]
    [string]$Action = 'start',
    [ValidateSet(5210, 5211)]
    [int]$Port = 5210,
    [string]$VaultId = ''
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venv = Join-Path $root '.venv'
$python = Join-Path $venv 'Scripts\python.exe'
$helper = Join-Path $root 'tools\kb_local_web_lifecycle.py'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    if ($Action -in @('status', 'stop')) {
        Write-Error '本机运行环境尚未安装。请先运行 KnowledgeWorkspace.ps1 -Action start。'
        exit 2
    }
    & py -3 -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error '无法创建 Python 环境。请安装 Python 3.11 或更新版本后重试。'
        exit 2
    }
}

$pipReady = & $python -c "import importlib.util; print('present' if importlib.util.find_spec('pip') else 'missing')"
if ($LASTEXITCODE -ne 0) {
    Write-Error '无法检查 Python 包安装器；请修复本机 Python 环境后重试。'
    exit 2
}
if ((@($pipReady) -join '').Trim() -ne 'present') {
    & $python -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        Write-Error '当前 Python 环境没有 pip，且无法使用内置 ensurepip 修复。'
        exit 2
    }
}

$installed = & $python -m pip show vault-workspace 2>$null
if ($LASTEXITCODE -ne 0) {
    & $python -m pip install --disable-pip-version-check --no-cache-dir -e (Join-Path $root 'tools\vault-workspace')
    if ($LASTEXITCODE -ne 0) {
        Write-Error '无法安装 Vault Workspace 的本机读取依赖；原有服务未被停止。'
        exit 2
    }
}

if (-not (Test-Path -LiteralPath $helper -PathType Leaf)) {
    Write-Error '启动器文件不完整；请从干净的 Knowledge Workspace 检出运行。'
    exit 2
}

$arguments = @($helper, $Action, '--port', [string]$Port)
if ($Action -eq 'review') {
    if ([string]::IsNullOrWhiteSpace($VaultId)) {
        Write-Error 'review 操作需要 -VaultId。每个待复核文件必须逐项确认。'
        exit 2
    }
    $arguments += @('--vault-id', $VaultId)
}
& $python @arguments
exit $LASTEXITCODE
