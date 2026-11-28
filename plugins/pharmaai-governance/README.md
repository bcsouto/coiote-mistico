# PharmaAI Governance 1.0.4

Autor: Bruno Corrêa Souto · /in/brunocsouto

Categoria: Regulatório (subcategorias: Compliance e Governança de IA)

Assessoria regulatória e de governança de IA com auditoria rastreável de evidências para o setor farmacêutico e da saúde.

## Funções

1. Auditar afirmações e fontes de documentos técnicos, com matriz de evidências e dossiê verificável.
2. Analisar natureza, vigência e aplicabilidade de normas, guias e atas.
3. Acompanhar mudanças regulatórias, consultas públicas e prazos em uma janela de datas.
4. Comparar políticas internas com normas e registrar lacunas e remediação.
5. Avaliar governança, risco e impacto de sistemas de IA.
6. Revisar contratos e evidências de fornecedores de IA.
7. Organizar perfil regulatório e casos, somente quando pedido.

## Skills correspondentes

| Skill | Quando é acionada | Entrega principal |
|---|---|---|
| `auditar-evidencias` | Conferir afirmações, fontes, extrapolações; revisão técnica; dossiê | Matriz de afirmações, curadoria, dossiê JSON validável |
| `analisar-regulacao` | Natureza, vigência e aplicabilidade de atos | Requisito, sujeito, status, fundamento e pendência |
| `acompanhar-mudancas` | Novidades entre datas, consultas públicas, prazos | Tabela de eventos e cobertura de fontes |
| `comparar-politicas` | Lacunas entre norma e política, plano de adequação | Registro de lacunas e redação proposta |
| `avaliar-governanca-ia` | Inventário, triagem e avaliação de impacto de IA | Proposta de condições, riscos e controles |
| `revisar-fornecedor-ia` | Contratos, DPA e evidências de fornecedores de IA | Pontos de risco, perguntas e cláusulas |
| `configurar-assessoria` | Somente sob pedido explícito de perfil ou continuidade | Perfil regulatório e índice de casos |

As skills compartilham `references/NUCLEO.md` (princípios, tabela única de estados de suporte e mapa de passagem entre skills), `references/FONTES.md` (tratamento de fontes, mapa por jurisdição e protocolo AnvisaLegis), `references/EVIDENCIA-CIENTIFICA-E-COMERCIAL.md` (estudos, métricas de IA e anúncios) e `references/SAUDE-E-FARMA.md` (módulo setorial). Os modelos de registro ficam em `templates/`.

## Como usar

No claude.ai: Personalizar, Plugins, Adicionar, Adicionar marketplace, informe `bcsouto/brunocsouto` e instale o PharmaAI Governance.

No Claude Code:

```bash
claude plugin marketplace add bcsouto/brunocsouto
claude plugin install pharmaai-governance@brunocsouto
```

Para teste local: `claude --plugin-dir ./pharmaai-governance`. As skills são acionadas pela descrição ou pelo nome, por exemplo `/pharmaai-governance:auditar-evidencias`.

## Limites

Acesso à web, leitura de arquivos, OCR e execução de Python dependem das ferramentas da sessão. O plugin não inclui servidor MCP, banco de dados, memória própria nem agendamento; consulta pontual não cria vigilância contínua. Não certifica conformidade, verdade das afirmações, eficácia clínica ou resultado financeiro. Estados de suporte descrevem a relação com as evidências consultadas.

## Verificação

```text
claude plugin validate .
python3 tests/test_estrutura.py
python3 tests/test_dossier.py
claude plugin eval . --allow-tools Write,Edit,Bash
```

O último comando roda os 29 cenários de `evals/` com e sem o plugin; são execuções reais do modelo, cobradas na conta.

## Licença

O plugin usa duas licenças. O código (o validador `validate_dossier.py`, os esquemas JSON do dossiê e os testes) está sob a licença MIT. Todo o restante (instruções das skills, referências, modelos, cenários, README e ícone) está sob a Creative Commons Atribuição-NãoComercial-SemDerivações 4.0 Internacional (CC BY-NC-ND 4.0): pode ser copiado e redistribuído sem alterações, com crédito ao autor e sem fins comerciais. Versões modificadas e uso comercial dependem de autorização prévia e por escrito. Veja `LICENSE` e `LICENSES/`.

Versões: plugin 1.0.4. O formato do dossiê JSON tem numeração própria, 1.1.0, e o validador também lê o formato 1.0.0. Proveniência em `NOTICE.md`; documentação oficial consultada em `docs/ANTHROPIC.md`.
