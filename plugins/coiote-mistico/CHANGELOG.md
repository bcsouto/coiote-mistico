# Histórico

## 1.2.3, 28/11/2026

Correções de uma revisão de segurança; nenhuma mudança na leitura nem no baralho.

- `SKILL.md`: a pasta de trabalho passou de `/tmp/coiote-mistico` (caminho previsível) para `mktemp -d` com permissão restrita ao usuário, e o caminho é repassado a cada comando; a busca do script deixou de percorrer `/` e passou a olhar apenas as pastas do usuário, de montagem e de instalação, até 12 níveis, sempre exigindo o SHA-256 do script.
- `tiragem.py`: removidas as variáveis `COIOTE_DIR` e `COIOTE_CATALOGO`; pasta de registros criada com permissão 700 e verificada quanto ao dono; arquivos gravados sem sobrescrever, sem seguir ligação simbólica e com permissão 600.
- `tiragem.py`: o marcador de abertura passou a registrar uma ligação SHA-256 com o registro da rodada e as posições, de modo que um marcador trocado, copiado de outra rodada ou editado é recusado. É detecção de adulteração, não proteção contra quem já controla a pasta do usuário.
- `tiragem.py`: JSON com aninhamento excessivo devolve erro tratado, sem traceback.
- Testes novos em `tests/test_integridade.py`, incluindo a conferência de que o hash do `SKILL.md` confere com o script, para impedir que os dois se separem em uma edição futura.
