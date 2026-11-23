# INF 610 - Trabalho final

Neste trabalho, comparei três algoritmos pra resolver o problema Top-k: **Min-Heap**, **Quickselect aleatorizado** e **Median of Medians (BFPRT)**. A ideia foi analisar a complexidade de cada um e comparar o número de comparações, movimentações, tempo de execução e memória usada nos experimentos.

Também usei dados do **AmazoniaExpert.IA**, projeto que desenvolvi no meu TCC. Nesse projeto, as perguntas são comparadas com trechos de documentos (*chunks*) por meio de embeddings. Aqui, usei os scores de similaridade já calculados pra testar a seleção dos k maiores valores. Não estou medindo o tempo de gerar embeddings, consultar o ChromaDB ou produzir respostas com o RAG.

## Como rodar no Google Colab

1. Abra o arquivo [`topk.ipynb`](topk.ipynb) pelo GitHub ou entre no [Google Colab](https://colab.research.google.com/) e escolha **Arquivo > Abrir notebook > GitHub**.
2. Procure pelo repositório `AnaClaraGuerra22/INF610-TopK` e abra `topk.ipynb`.
3. Vá em **Ambiente de execução > Executar tudo**.
4. A primeira célula baixa os dados do próprio repositório, se eles não estiverem na sessão, e confere o arquivo ZIP.

Os arquivos CSV e os gráficos gerados ficam na pasta `resultados/`. Como os arquivos da sessão do Colab podem ser perdidos quando ela é encerrada, é bom baixar os resultados caso queira guardá-los.

**Importante:** pra executar a parte com dados reais, o arquivo [`dados/reais/dados_colab_publicacao.zip`](dados/reais/dados_colab_publicacao.zip) precisa estar disponível. Sem ele, ainda dá pra rodar os experimentos sintéticos.

## Como rodar no computador

Com Python instalado, abra o terminal na pasta do projeto e execute:

```powershell
py -m pip install -r requirements.txt jupyter
py -m jupyter notebook topk.ipynb
```

O notebook usa NumPy e Matplotlib. Pra reproduzir os experimentos reais, mantenha o ZIP na pasta `dados/reais/`.

## Experimentos

Antes dos testes, comparei os resultados dos algoritmos com uma ordenação de referência feita com `sorted`, incluindo casos com empates, valores negativos e diferentes valores de k. No notebook foram feitos **249 testes de corretude**.

**Dados sintéticos:** usei `n = 300, 1500, 6000 e 12000`, com `k = 1, 5, 20 e n/10`. Testei as distribuições uniforme, crescente, decrescente e com muitos empates. Cada caso foi repetido cinco vezes pra cada algoritmo, totalizando **960 execuções**. A semente usada foi `6102026`.

**Dados reais:** usei **130 perguntas** do SPAmazon-QA e **6.900 chunks** do banco vetorial do AmazoniaExpert.IA. Os embeddings têm 768 dimensões, e os scores são calculados pela similaridade do cosseno entre as perguntas e os chunks. Pra cada pergunta, testei `k = 1, 3, 5, 8, 10 e 20`, com três repetições por algoritmo, totalizando **7.020 medições**.

As principais medidas foram as **comparações de chaves** e as **movimentações** contadas no código. O tempo foi medido separadamente, sem os contadores ativos, e a memória adicional foi medida com `tracemalloc`. Os gráficos usam as medianas das repetições.

Nos casos de empate, o elemento com menor índice original tem prioridade. Depois da seleção, os três algoritmos usam o mesmo **MergeSort** pra ordenar os k resultados. Assim, todos retornam os mesmos elementos na mesma ordem.

Também calculei o **Hit@k por capítulo-alvo** nos dados reais. Considerei um acerto quando pelo menos um dos chunks selecionados pertence ao capítulo esperado pra pergunta. Essa medida serve pra observar a cobertura conforme k aumenta, e não a qualidade das respostas do RAG.

## Dados e arquivos do projeto

- `topk.ipynb`: notebook com os algoritmos, testes e experimentos.
- `SPAmazon-QA.json`: conjunto com as 130 perguntas e seus dados de referência.
- `dados/reais/dados_colab_publicacao.zip`: embeddings e metadados exportados do projeto anterior.
- `resultados/`: CSVs e gráficos dos experimentos.
- `requirements.txt`: bibliotecas necessárias pro notebook.
- `exportar_dados.py`: script usado pra exportar novamente os dados do ChromaDB original, caso seja necessário.
- `publicar_github.ps1`: script usado na publicação do repositório.

O ZIP de dados reais contém os embeddings das perguntas, os embeddings dos chunks e os metadados. O arquivo foi exportado a partir do banco do meu TCC, então não é necessário ter o ChromaDB original pra executar o notebook. Na exportação foram encontrados 6.900 chunks, que foi a quantidade usada nos experimentos.

O SHA-256 do ZIP publicado é:

```text
cc852d73ff862e50d69a9f7920b3059122e593478ac45d78d19a10cc1f02e570
```

Se for preciso refazer a exportação no Windows, com o banco original disponível em `C:\TCCII\VECTOR_DB`, os comandos são:

```powershell
py -m pip install chromadb sentence-transformers numpy
py .\exportar_dados.py
```

O script lê uma cópia temporária do banco, sem alterar o original. Se o banco estiver em outro caminho, dá pra informar esse caminho com `--banco`.

## Referências

- CORMEN, T. H. et al. *Algoritmos: teoria e prática*. 3. ed. Elsevier, 2012. Capítulos 6 e 9.
- BLUM, M. et al. *Time bounds for selection*. Journal of Computer and System Sciences, 1973.
- TORRES, Ana Clara Guerra. *AmazoniaExpert.IA: desenvolvimento de uma arquitetura RAG e criação de um conjunto de dados curado para avaliação de grandes modelos de linguagem no domínio da Amazônia*. TCC, Universidade Federal de Viçosa, 2026.
