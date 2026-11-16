# INF 610 — Trabalho final: comparacao de algoritmos Top-k

Comparei tres jeitos de selecionar os `k` maiores scores: **Min-Heap**, **Quickselect aleatorizado** e **Median of Medians (BFPRT)**. A aplicacao vem da recuperacao de chunks do meu projeto AmazoniaExpert.IA, usando as 130 perguntas do SPAmazon-QA.

O objetivo e comparar **comparacoes, movimentacoes, tempo e memoria da selecao**, e nao o tempo do ChromaDB, da criacao dos embeddings ou da geracao de respostas por LLM.

## Reproduzir no Google Colab (mais simples)

1. Abra [`topk.ipynb`](topk.ipynb) pelo GitHub ou no [Google Colab](https://colab.research.google.com/) (menu **Arquivo > Abrir notebook > GitHub**; procure `AnaClaraGuerra22/INF610-TopK`).
2. Execute **Ambiente de execucao > Executar tudo**.
3. No Colab, se os arquivos nao estiverem no diretorio atual, a primeira celula baixa automaticamente `SPAmazon-QA.json` e `dados/reais/dados_colab_publicacao.zip` deste repositorio. Ela verifica o SHA-256 do ZIP real.
4. Os CSVs ficam em `resultados/` e os graficos em `resultados/graficos/` do ambiente Colab. Para mante-los apos fechar a sessao, baixe os arquivos gerados.

**Pre-requisito:** o arquivo [`dados/reais/dados_colab_publicacao.zip`](dados/reais/dados_colab_publicacao.zip) precisa estar publicado neste repositorio. Sem ele, os testes sinteticos rodam, mas **os resultados reais nao podem ser reproduzidos**. Confirme a presenca do ZIP antes da avaliacao.

## Reproduzir localmente

```bash
python -m pip install -r requirements.txt
jupyter notebook topk.ipynb
```

Rode o notebook na pasta raiz do projeto, mantendo o ZIP real em `dados/reais/`. `jupyter` e `ipykernel` podem ser instalados separadamente se ainda nao estiverem disponiveis no ambiente. O projeto usa Python 3 e numpy/matplotlib; o exportador (nao necessario pra reproduzir com o ZIP) exige `chromadb` e `sentence-transformers`.

## Dados reais

- `SPAmazon-QA.json`: 130 perguntas, gabaritos e capitulos-alvo.
- `dados/reais/dados_colab_publicacao.zip`: exportacao autocontida do ChromaDB original, com 6.900 embeddings de chunks, 130 embeddings de perguntas e metadados alinhados. O ZIP guarda `embeddings_chunks.npz`, `embeddings_perguntas.npz`, `metadados_chunks.json`, `perguntas.json`, `auditoria_exportacao.json`.
- Os vetores tem 768 dimensoes. Para as **perguntas**, usei `sentence-transformers/all-mpnet-base-v2`; os embeddings de chunks foram preservados do ChromaDB do TCC.
- Os **scores nao sao fabricados nem enviados em um arquivo redundante**: cada score e o cosseno entre o embedding da pergunta e o do chunk. Isso gera uma matriz `(130, 6900)` antes do benchmark. O calculo de scores fica fora da medicao de selecao.
- O registro da exportacao foi de **6.900**, diferente dos 6.899 descritos na proposta inicial; mantive todos os chunks presentes na colecao `langchain`, sem remover registros artificialmente.
- SHA-256 do ZIP real exportado em 16/11/2026:

```text
cc852d73ff862e50d69a9f7920b3059122e593478ac45d78d19a10cc1f02e570
```

O ChromaDB original (`C:\TCCII\VECTOR_DB`) **nao e necessario pro professor**. Se for preciso recriar o ZIP a partir desse banco original no Windows, basta usar `exportar_dados.py` conforme a secao seguinte.

## Como o benchmark foi feito

- Desempate deterministico: score maior primeiro; se houver empate, chunk de indice original menor primeiro.
- Os tres algoritmos retornam **exatamente os mesmos indices** de uma ordenacao de referencia, e o Top-k final e ordenado com o **mesmo MergeSort** nos tres casos.
- Sinteticos: `n = [300, 1500, 6000, 12000]`, `k = [1, 5, 20, n//10]`, quatro distribuicoes (uniforme, crescente, decrescente e empates), cinco repeticoes e semente `6102026`.
- Reais: as 130 perguntas, `k = [1,3,5,8,10,20]`, tres repeticoes, quando o ZIP esta presente.
- Conto comparacoes de chaves e escritas/movimentacoes em estruturas internas. O tempo e medido separadamente, com contadores desligados. A memoria adicional e medida com `tracemalloc`.
- Hit@k significa que **algum chunk do Top-k vem do capitulo-alvo** da pergunta; nao e a qualidade da resposta produzida pelo RAG. O volume de contexto esta em *palavras*, nao em tokens.

Os resultados sinteticos ja incluidos em `resultados/` sao um exemplo da execucao anterior. Tempos e picos de memoria variam conforme maquina, dependencias e carga do sistema. Os resultados reais so aparecem nos CSVs depois de rodar o notebook com o ZIP de dados.

## Para quem tem o banco original e quer reexportar

O `exportar_dados.py` **le uma copia temporaria** do ChromaDB e gera somente `dados/reais/dados_colab_publicacao.zip`. Ele nao modifica `VECTOR_DB`. No Windows:

```powershell
py -m pip install chromadb sentence-transformers numpy
py .\exportar_dados.py
```

O script espera encontrar o banco em `C:\TCCII\VECTOR_DB`; para outro caminho, use `--banco`.

## Arquivos principais

```text
INF610-TopK/
  topk.ipynb                    # unico notebook do trabalho
  SPAmazon-QA.json              # conjunto de perguntas original
  exportar_dados.py             # recriacao opcional do ZIP a partir do ChromaDB
  publicar_github.ps1           # publica esta pasta no GitHub (Windows)
  requirements.txt
  README.md
  .gitignore
  dados/reais/dados_colab_publicacao.zip  # NECESSARIO para a parte real
  resultados/                   # CSVs e graficos; atualizados pelo notebook
```

## Referencias

- Cormen et al. (2012), *Algoritmos: teoria e pratica*, capitulos 6 e 9.
- Blum et al. (1973), *Time Bounds for Selection*.
- Proposta do trabalho final INF 610 e projeto AmazoniaExpert.IA/SPAmazon-QA.
