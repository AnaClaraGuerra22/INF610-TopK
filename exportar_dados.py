"""Refaz o pacote de dados reais do INF610 usando o ChromaDB do TCC.

Roda no Windows, na pasta do trabalho. Nao altera o banco original.
"""

import argparse
import hashlib
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

MODELO = "sentence-transformers/all-mpnet-base-v2"
COLECAO = "langchain"
LOTE = 300


def sha256(arquivo):
    h = hashlib.sha256()
    with arquivo.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def copiar_banco(banco, copia):
    """Faz uma copia de trabalho. O Chroma vai abrir so essa copia."""
    db = banco / "chroma.sqlite3"
    if not db.is_file():
        raise FileNotFoundError(f"Nao achei o ChromaDB em: {db}")
    copia.mkdir(parents=True, exist_ok=True)
    for item in banco.iterdir():
        destino = copia / item.name
        if item.is_dir():
            shutil.copytree(item, destino)
        elif item.name == "chroma.sqlite3":
            # SQLite backup copia um snapshot consistente, inclusive com WAL ativo.
            uri = db.resolve().as_uri() + "?mode=ro"
            with sqlite3.connect(uri, uri=True) as origem:
                with sqlite3.connect(destino) as saida:
                    origem.backup(saida)
        elif item.name not in {"chroma.sqlite3-wal", "chroma.sqlite3-shm"}:
            shutil.copy2(item, destino)


def ler_chunks(copia):
    import chromadb
    from chromadb.config import Settings

    cliente = chromadb.PersistentClient(
        path=str(copia), settings=Settings(anonymized_telemetry=False)
    )
    nomes = [c if isinstance(c, str) else c.name for c in cliente.list_collections()]
    if COLECAO not in nomes:
        raise ValueError(f"Colecao '{COLECAO}' nao encontrada. Disponiveis: {nomes}")
    colecao = cliente.get_collection(COLECAO)
    total = colecao.count()
    if total == 0:
        raise ValueError("A colecao esta vazia")

    ids, vetores, metas = [], [], []
    for inicio in range(0, total, LOTE):
        lote = colecao.get(
            limit=min(LOTE, total - inicio), offset=inicio,
            include=["embeddings", "metadatas", "documents"],
        )
        novos_ids = lote["ids"]
        emb = lote["embeddings"]
        if emb is None or len(emb) != len(novos_ids):
            raise ValueError("O Chroma nao retornou todos os embeddings")
        vetores.extend(np.asarray(emb, dtype=np.float32))
        ids.extend(str(x) for x in novos_ids)
        for chunk_id, meta, documento in zip(
            novos_ids, lote.get("metadatas") or [None] * len(novos_ids),
            lote.get("documents") or [None] * len(novos_ids),
        ):
            meta = meta or {}
            num_palavras = meta.get("numero_palavras")
            if num_palavras is None and documento is not None:
                num_palavras = len(documento.split())
            metas.append({
                "chunk_id": str(chunk_id),
                "chapter_number": meta.get("chapter_number"),
                "source": meta.get("source"),
                "page": meta.get("page"),
                "numero_palavras": int(num_palavras) if num_palavras is not None else None,
            })
        print(f"Chunks: {min(inicio + LOTE, total)}/{total}")

    if len(ids) != total or len(set(ids)) != total:
        raise ValueError("Quantidade de IDs diferente ou IDs repetidos")
    # Ordeno por ID pra ordem nao depender da paginacao do Chroma.
    ordem = sorted(range(total), key=lambda i: ids[i])
    X = np.asarray([vetores[i] for i in ordem], dtype=np.float32)
    ids = [ids[i] for i in ordem]
    metas = [metas[i] for i in ordem]
    if X.ndim != 2 or not np.isfinite(X).all() or (np.linalg.norm(X, axis=1) == 0).any():
        raise ValueError("Embeddings de chunks invalidos")
    if X.shape[1] != 768:
        raise ValueError(f"Esperava 768 dimensoes, encontrei {X.shape[1]}")
    if total != 6900:
        print(f"AVISO: o registro anterior tinha 6900 chunks; achei {total}.")
    return ids, X, metas


def extrair_copia_em_outro_processo(copia, pasta_temporaria):
    # O processo separado libera todos os arquivos do Chroma ao terminar.
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()),
         "--extrair-copia", str(copia), str(pasta_temporaria)],
        check=True,
    )
    with np.load(pasta_temporaria / "chunks_temp.npz", allow_pickle=False) as arq:
        X = np.asarray(arq["embeddings"], dtype=np.float32)
        ids = arq["ids"].astype(str).tolist()
    metas = json.loads((pasta_temporaria / "metadados_temp.json").read_text(encoding="utf-8"))
    if len(ids) != len(X) or len(metas) != len(X):
        raise ValueError("Arquivos temporarios com quantidades diferentes")
    return ids, X, metas


def executar_extracao(copia, pasta_temporaria):
    ids, X, metas = ler_chunks(copia)
    np.savez_compressed(
        pasta_temporaria / "chunks_temp.npz",
        embeddings=X, ids=np.asarray(ids, dtype=str),
    )
    (pasta_temporaria / "metadados_temp.json").write_text(
        json.dumps(metas, ensure_ascii=False), encoding="utf-8"
    )


def ler_perguntas(caminho):
    if not caminho.is_file():
        raise FileNotFoundError(f"Nao achei: {caminho}")
    qa = json.loads(caminho.read_text(encoding="utf-8-sig"))
    if not isinstance(qa, list) or not qa:
        raise ValueError("SPAmazon-QA.json nao e uma lista de perguntas")
    perguntas = []
    for registro in qa:
        perguntas.append({
            "id_questao": registro["id_questao"],
            "pergunta": registro["conjunto_curado"]["pergunta"],
            "capitulo_alvo": registro["metadados_pergunta"]["capitulo_alvo"],
        })
    if len(set(x["id_questao"] for x in perguntas)) != len(perguntas):
        raise ValueError("IDs de perguntas repetidos")
    if len(perguntas) != 130:
        print(f"AVISO: o SPAmazon-QA anterior tinha 130 perguntas; achei {len(perguntas)}.")
    return perguntas


def gerar_embeddings_perguntas(perguntas, dimensao):
    from sentence_transformers import SentenceTransformer

    print("Carregando modelo:", MODELO)
    print("Na primeira vez, pode baixar os pesos do modelo.")
    modelo = SentenceTransformer(MODELO)
    vetores = modelo.encode(
        [p["pergunta"] for p in perguntas],
        batch_size=16,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    Q = np.asarray(vetores, dtype=np.float32)
    if Q.shape != (len(perguntas), dimensao) or not np.isfinite(Q).all():
        raise ValueError(f"Embeddings de perguntas invalidos: {Q.shape}")
    return Q


def guardar_npz(vetores, ids=None):
    b = io.BytesIO()
    if ids is None:
        np.savez_compressed(b, embeddings=vetores)
    else:
        np.savez_compressed(b, embeddings=vetores, ids=np.asarray(ids, dtype=str))
    return b.getvalue()


def exportar(banco, projeto):
    perguntas = ler_perguntas(projeto / "SPAmazon-QA.json")
    destino = projeto / "dados" / "reais" / "dados_colab_publicacao.zip"
    destino.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="inf610_chroma_") as tmp:
        copia = Path(tmp) / "VECTOR_DB"
        print("Copiando o banco pra pasta temporaria, sem alterar o original...", flush=True)
        copiar_banco(banco, copia)
        ids, X, metas = extrair_copia_em_outro_processo(copia, Path(tmp))

    Q = gerar_embeddings_perguntas(perguntas, X.shape[1])
    if (np.linalg.norm(X, axis=1) <= 0).any():
        raise ValueError("Embeddings de chunk com norma zero")

    # So estes cinco arquivos entram no ZIP. Nao cria CSVs de entrada.
    manifesto = {
        "origem": "ChromaDB do TCC (copia temporaria)",
        "colecao": COLECAO,
        "modelo_perguntas": MODELO,
        "n_chunks": len(X),
        "dimensoes": int(X.shape[1]),
        "n_perguntas": len(Q),
        "sha256_spamazon_qa": sha256(projeto / "SPAmazon-QA.json"),
        "ordem_chunks": "ids em ordem lexicografica",
        "scores": "cosseno, calculados no topk.ipynb",
    }
    temporario = destino.with_suffix(".zip.part")
    try:
        with zipfile.ZipFile(temporario, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            z.writestr("embeddings_chunks.npz", guardar_npz(X, ids))
            z.writestr("embeddings_perguntas.npz", guardar_npz(Q))
            z.writestr("metadados_chunks.json", json.dumps(metas, ensure_ascii=False))
            z.writestr("perguntas.json", json.dumps(perguntas, ensure_ascii=False))
            z.writestr("auditoria_exportacao.json", json.dumps(manifesto, indent=2, ensure_ascii=False))
        # Confere o formato que o notebook le, antes de substituir o ZIP.
        with zipfile.ZipFile(temporario) as z:
            assert z.testzip() is None
            with np.load(io.BytesIO(z.read("embeddings_chunks.npz")), allow_pickle=False) as arq:
                assert arq["embeddings"].shape == X.shape
                assert arq["ids"].astype(str).tolist() == ids
            with np.load(io.BytesIO(z.read("embeddings_perguntas.npz")), allow_pickle=False) as arq:
                assert arq["embeddings"].shape == Q.shape
            assert len(json.loads(z.read("perguntas.json"))) == len(Q)
            assert len(json.loads(z.read("metadados_chunks.json"))) == len(X)
        os.replace(temporario, destino)
    finally:
        temporario.unlink(missing_ok=True)

    print("\nPronto:", destino)
    print(f"{len(Q)} perguntas x {len(X)} chunks | {X.shape[1]} dimensoes")
    print("SHA256:", sha256(destino))
    print("Agora rode topk.ipynb de cima pra baixo.")


def main():
    projeto = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Exportar dados reais do ChromaDB pro topk.ipynb")
    parser.add_argument("--banco", type=Path, default=projeto.parent.parent / "VECTOR_DB",
                        help="Pasta que contem chroma.sqlite3")
    args = parser.parse_args()
    exportar(args.banco.expanduser().resolve(), projeto)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--extrair-copia":
        executar_extracao(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        main()
