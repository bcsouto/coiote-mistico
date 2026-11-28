#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Bruno Corrêa Souto
"""Coiote Místico 1.2.3: selo e abertura verificáveis de tiragens Rider-Waite-Smith."""
import hashlib
import json
import os
import re
import secrets
import sys
from pathlib import Path

VERSAO = "TARO-RWS-3Q-V1"
PASTA = Path.home() / ".coiote-mistico"

CATALOGO_SHA256 = "39f9962ec406e05aef102f29ec7e446e4a6f2ce49c96196d1c97633a28e0e250"
AQUI = Path(__file__).resolve().parent
CATALOGO_CANDIDATOS = (AQUI / "catalogo.json", AQUI.parent / "references" / "catalogo.json")
CAMPOS = {"id": int, "nome": str, "nome_en": str, "numeral_face": (str, type(None)), "inscricao_topo": (str, type(None)), "inscricao_base": (str, type(None)), "elementos": str}


def saida(codigo, **dados):
    dados["ok"] = codigo == 0
    print(json.dumps(dados, ensure_ascii=False, indent=2))
    sys.exit(codigo)


def serializar(registro):
    return json.dumps(registro, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256(dados):
    return hashlib.sha256(dados).hexdigest()


def limpar_pergunta(ordem, texto):
    texto = texto.strip()
    marcador = re.match(rf"{ordem}\s*(?:[.)\-:ºª°]|\u2013|\u2014)(?!\d)\s*", texto)
    if marcador and texto[marcador.end():].strip():
        texto = texto[marcador.end():].strip()
    return texto


def carregar_catalogo():
    caminho = next((c for c in CATALOGO_CANDIDATOS if c.is_file()), CATALOGO_CANDIDATOS[0])
    if not caminho.is_file():
        saida(3, erro="catalogo_ausente", mensagem="O catálogo das cartas não foi encontrado.")
    dados = caminho.read_bytes()
    if sha256(dados) != CATALOGO_SHA256:
        saida(3, erro="catalogo_divergente", mensagem="O catálogo das cartas não confere com o hash esperado.")
    try:
        catalogo = json.loads(dados.decode("utf-8"))
    except (ValueError, RecursionError):
        saida(3, erro="catalogo_invalido", mensagem="O catálogo das cartas tem estrutura inválida.")
    valido = (
        isinstance(catalogo, list) and len(catalogo) == 78
        and all(isinstance(c, dict) and set(c) == set(CAMPOS)
                and all(isinstance(c[k], t) and type(c[k]) is not bool for k, t in CAMPOS.items())
                and c["id"] == i for i, c in enumerate(catalogo))
    )
    if not valido:
        saida(3, erro="catalogo_invalido", mensagem="O catálogo das cartas tem estrutura inválida.")
    return catalogo


def preparar_pasta():
    PASTA.mkdir(mode=0o700, parents=True, exist_ok=True)
    if hasattr(os, "geteuid") and PASTA.stat().st_uid != os.geteuid():
        saida(3, erro="pasta_alheia", mensagem="A pasta de registros pertence a outro usuário.")
    os.chmod(PASTA, 0o700)


def gravar_novo(caminho, dados):
    try:
        fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except FileExistsError:
        if caminho.is_file() and not caminho.is_symlink() and caminho.read_bytes() == dados:
            return
        saida(3, erro="gravacao_falhou", mensagem="Já existe um arquivo diferente para este registro.")
    with os.fdopen(fd, "wb") as arquivo:
        arquivo.write(dados)


def ligacao(dados, posicoes):
    return sha256(dados + b"|" + json.dumps(posicoes).encode("utf-8"))


def selar():
    carregar_catalogo()
    try:
        perguntas = json.loads(sys.stdin.read())
    except json.JSONDecodeError as erro:
        saida(2, erro="entrada_invalida", mensagem=f"JSON inválido: {erro}")
    except RecursionError:
        saida(2, erro="entrada_invalida", mensagem="JSON com aninhamento excessivo.")
    if not (isinstance(perguntas, list) and len(perguntas) == 3
            and all(isinstance(p, str) and p.strip() for p in perguntas)):
        saida(2, erro="entrada_invalida", mensagem="Envie um array JSON com exatamente três perguntas não vazias.")
    perguntas = [limpar_pergunta(i, p) for i, p in enumerate(perguntas, start=1)]
    baralho = list(range(78))
    secrets.SystemRandom().shuffle(baralho)
    if sorted(baralho) != list(range(78)):
        saida(3, erro="baralho_invalido", mensagem="Falha ao embaralhar.")
    dados = serializar([VERSAO, perguntas, secrets.token_hex(32), baralho])
    selo = sha256(dados)
    preparar_pasta()
    caminho = PASTA / f"{selo}.json"
    gravar_novo(caminho, dados)
    if sha256(caminho.read_bytes()) != selo:
        saida(3, erro="gravacao_falhou", mensagem="O registro gravado não reproduz o selo.")
    saida(0, selo=selo, perguntas=perguntas)


def carregar(selo):
    if not re.fullmatch(r"[0-9a-f]{64}", selo):
        saida(2, erro="selo_invalido", mensagem="O selo deve ter 64 caracteres hexadecimais minúsculos.")
    caminho = PASTA / f"{selo}.json"
    if not caminho.is_file():
        saida(3, erro="registro_ausente", mensagem="Não há registro para este selo neste ambiente.")
    dados = caminho.read_bytes()
    if sha256(dados) != selo:
        saida(3, erro="hash_divergente", mensagem="O registro não reproduz o selo publicado.")
    try:
        registro = json.loads(dados.decode("utf-8"))
        versao, perguntas, nonce, baralho = registro
    except (ValueError, TypeError, UnicodeDecodeError, RecursionError):
        saida(3, erro="registro_corrompido", mensagem="O registro não tem a estrutura esperada.")
    valido = (
        versao == VERSAO
        and isinstance(perguntas, list) and len(perguntas) == 3
        and all(isinstance(p, str) for p in perguntas)
        and isinstance(nonce, str) and re.fullmatch(r"[0-9a-f]{64}", nonce)
        and isinstance(baralho, list)
        and all(type(c) is int for c in baralho)
        and sorted(baralho) == list(range(78))
        and serializar(registro) == dados
    )
    if not valido:
        saida(3, erro="registro_invalido", mensagem="O registro falhou na validação.")
    return dados, perguntas, baralho


def ler_posicoes(texto):
    partes = [p for p in re.split(r"[\s,;]+", texto.strip()) if p]
    if len(partes) != 3 or not all(re.fullmatch(r"\d+", p) for p in partes):
        saida(2, erro="escolha_invalida", mensagem="Envie exatamente três números inteiros.")
    posicoes = [int(p) for p in partes]
    if any(not 1 <= p <= 78 for p in posicoes):
        saida(2, erro="escolha_invalida", mensagem="Os números devem estar entre 1 e 78.")
    if len(set(posicoes)) != 3:
        saida(2, erro="escolha_invalida", mensagem="Os três números devem ser diferentes.")
    return posicoes


def abrir(selo, texto):
    posicoes = ler_posicoes(texto)
    dados, perguntas, baralho = carregar(selo)
    catalogo = carregar_catalogo()
    marca = PASTA / f"{selo}.abertura.json"
    if marca.is_symlink():
        saida(3, erro="marcador_invalido", mensagem="O registro de abertura desta rodada está corrompido.")
    if marca.is_file():
        try:
            gravado = json.loads(marca.read_text(encoding="utf-8"))
            anteriores = gravado["posicoes"]
            valido = (isinstance(anteriores, list) and len(anteriores) == 3
                      and all(type(p) is int and 1 <= p <= 78 for p in anteriores)
                      and gravado["ligacao"] == ligacao(dados, anteriores)
                      and set(gravado) == {"posicoes", "ligacao"})
        except (ValueError, UnicodeDecodeError, KeyError, TypeError, RecursionError):
            valido = False
        if not valido:
            saida(3, erro="marcador_invalido", mensagem="O registro de abertura desta rodada está corrompido.")
        if anteriores != posicoes:
            saida(4, erro="rodada_ja_aberta", posicoes_fixadas=anteriores,
                  mensagem="Esta rodada já foi aberta com outras posições. Uma nova escolha exige novo selo.")
    else:
        gravar_novo(marca, json.dumps({"posicoes": posicoes, "ligacao": ligacao(dados, posicoes)}).encode("utf-8"))
    cartas = []
    for ordem, (pergunta, posicao) in enumerate(zip(perguntas, posicoes), start=1):
        carta = catalogo[baralho[posicao - 1]]
        cartas.append({"ordem": ordem, "pergunta": pergunta, "posicao": posicao, **carta})
    saida(0, selo=selo, verificado=True, cartas=cartas, registro_json=dados.decode("utf-8"))


def verificar():
    carregar_catalogo()
    saida(0, catalogo="OK", cartas=78)


def conferir():
    linha = sys.stdin.read()
    if linha.endswith("\n"):
        linha = linha[:-1]
    saida(0, sha256=sha256(linha.encode("utf-8")))


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "selar" and len(sys.argv) == 2:
        selar()
    elif len(sys.argv) == 4 and sys.argv[1] == "abrir":
        abrir(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 2 and sys.argv[1] == "conferir":
        conferir()
    elif len(sys.argv) == 2 and sys.argv[1] == "verificar":
        verificar()
    else:
        saida(2, erro="uso", mensagem='Uso: verificar | selar < perguntas.json | abrir SELO "n1 n2 n3" | conferir < linha.txt')


if __name__ == "__main__":
    main()
