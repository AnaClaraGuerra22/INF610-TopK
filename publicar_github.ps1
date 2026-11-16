# Publica a propria pasta INF610- TRAB FINAL no GitHub, sem criar copia local.
# Requer Git e GitHub CLI (gh) autenticado: gh auth login
# O ZIP real deve estar dentro de dados/reais/ antes de rodar.
$ErrorActionPreference = 'Stop'
$repo = 'AnaClaraGuerra22/INF610-TopK'
$projeto = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projeto

function Checar-Programa($nome) {
    if (-not (Get-Command $nome -ErrorAction SilentlyContinue)) {
        throw "Falta '$nome'. Instale Git e GitHub CLI, conforme o README."
    }
}
function Executar($programa, [string[]]$parametros) {
    & $programa @parametros
    if ($LASTEXITCODE -ne 0) { throw "Comando falhou: $programa $($parametros -join ' ')" }
}

Checar-Programa 'git'
Checar-Programa 'gh'

$zip = Join-Path $projeto 'dados\reais\dados_colab_publicacao.zip'
if (-not (Test-Path -LiteralPath $zip -PathType Leaf)) {
    throw 'Falta dados/reais/dados_colab_publicacao.zip. Nao publico um benchmark real sem os dados.'
}
$esperado = 'cc852d73ff862e50d69a9f7920b3059122e593478ac45d78d19a10cc1f02e570'
$encontrado = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($encontrado -ne $esperado) {
    throw "SHA-256 do ZIP nao confere! Encontrado: $encontrado`nEsperado: $esperado. Confira antes de publicar."
}

$notebooks = @(Get-ChildItem -LiteralPath $projeto -File -Filter '*.ipynb')
if ($notebooks.Count -ne 1 -or $notebooks[0].Name -ne 'topk.ipynb') {
    throw 'Organizacao inesperada: deve existir somente topk.ipynb na raiz.'
}
& gh auth status
if ($LASTEXITCODE -ne 0) { throw 'Faca login uma vez com: gh auth login' }

if (-not (Test-Path -LiteralPath (Join-Path $projeto '.git') -PathType Container)) {
    Executar 'git' @('init')
    Executar 'git' @('branch','-M','main')
}

# Adiciona somente os arquivos do trabalho. Nunca adiciona VECTOR_DB.
$arquivos = @('.gitignore','README.md','requirements.txt','SPAmazon-QA.json',
              'topk.ipynb','exportar_dados.py','publicar_github.ps1',
              'dados/reais/dados_colab_publicacao.zip','resultados')
Executar 'git' (@('add','--') + $arquivos)

& git diff --cached --quiet
$codigoDiff = $LASTEXITCODE
if ($codigoDiff -eq 1) {
    Executar 'git' @('commit','-m','Publica trabalho final INF610 com dados e resultados')
} elseif ($codigoDiff -ne 0) {
    throw "Nao consegui conferir o Git staging (codigo $codigoDiff)."
}

$existentes = & gh repo list 'AnaClaraGuerra22' --limit 100 --json name --jq '.[] | .name'
if ($LASTEXITCODE -ne 0) { throw 'Nao consegui consultar seus repositorios com gh.' }
$jaExiste = @($existentes) -contains 'INF610-TopK'
if (-not $jaExiste) {
    Write-Host 'Criando repositorio publico:' $repo
    Executar 'gh' @('repo','create',$repo,'--public',
                    '--description','INF 610: comparacao de Min-Heap, Quickselect e BFPRT no Top-k do SPAmazon-QA',
                    '--source','.','--remote','origin','--push')
} else {
    Write-Host 'Repositorio ja existe; vou usar o mesmo, sem criar duplicata.'
    $remotos = @(& git remote)
    if ($remotos -notcontains 'origin') {
        Executar 'git' @('remote','add','origin',"https://github.com/$repo.git")
    } else {
        $origin = & git remote get-url origin
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao conferir o remote origin.' }
        if ($origin -notmatch '(^|[:/])AnaClaraGuerra22/INF610-TopK(\.git)?$') {
            throw "Origin aponta para outro repositorio: $origin"
        }
    }
    Executar 'git' @('push','-u','origin','main')
}
Write-Host "Publicado: https://github.com/$repo"
Write-Host 'Confira se dados/reais/dados_colab_publicacao.zip aparece no GitHub.'
