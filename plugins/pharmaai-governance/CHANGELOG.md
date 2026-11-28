# Histórico

## 1.0.5, 28/11/2026

- `validate_dossier.py`: JSON com aninhamento excessivo agora devolve `erro_execucao` e código de saída 2, em vez de um traceback (`RecursionError` incluído no tratamento de erros de `main`); teste de regressão adicionado.
- `plugin.json`: removido o e-mail do autor, que ficava exposto no repositório público.

## 1.0.4, 28/11/2026

- Removido `assets/logo-dark.svg`, não referenciado por nenhum arquivo: o diretório só aceita SVG como ícone do plugin (`assets/logo.svg`). Nenhuma mudança de comportamento.

## 1.0.3, 28/11/2026

- Texto de documentação reescrito (`CHANGELOG.md` e `evals/COMO-AVALIAR.md`) para eliminar o aviso RUNTIME_FETCH_EXEC da validação do diretório; nenhuma mudança de comportamento.

## 1.0.2, 26/11/2026

- Repositório do marketplace renomeado para `bcsouto/brunocsouto`; endereços de instalação, `homepage` e `repository` atualizados.

## 1.0.1, 26/11/2026

- Protocolo AnvisaLegis com 8 passos: "ver mais detalhes" também de cada ato do histórico (alteradores e revogados), datas de assinatura e de publicação no DOU separadas, republicação tratada como pendência de vigência, conferência dos dispositivos de vigência e prazos e registro de divergências do próprio AnvisaLegis.
- Núcleo: material citado e não fornecido é informado na primeira linha; encaminhamento entre skills declarado em uma linha; recomendação separada dos fatos também na redação.
- `analisar-regulacao`: tabela de vigência com uma linha por ato (situação, papel, assinatura, publicação, vigência, pendência).
- `auditar-evidencias`: declara o encaminhamento para outra skill e abre com a falta de material.
- Cenário de teste `r29-rdc-978-vigencia-sem-relatorio`, com 6 avaliadores, criado a partir da consulta refeita da RDC nº 978/2025 (29 cenários no total).

## 1.0.0, 26/11/2026

Primeira versão publicada no Claude.

- Sete skills: `auditar-evidencias`, `analisar-regulacao`, `acompanhar-mudancas`, `comparar-politicas`, `avaliar-governanca-ia`, `revisar-fornecedor-ia` e `configurar-assessoria`.
- Referências comuns: núcleo com tabela única de estados de suporte, tratamento de fontes com protocolo AnvisaLegis, módulo de evidência científica e comercial e módulo de saúde e medicamentos.
- Modelos de perfil, registro de evidências, lacunas e avaliação de IA.
- Contrato de dossiê JSON 1.1.0 com validador offline em Python e leitura do contrato 1.0.0.
- 28 cenários de avaliação no formato da avaliação de plugins do Claude Code.
- Licença dupla: MIT para o código, CC BY-NC-ND 4.0 para o restante.
