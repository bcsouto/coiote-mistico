import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SKILL = RAIZ / "skills/consulta-oracular"
SCRIPT = SKILL / "scripts/tiragem.py"


def rodar(home, *args, entrada=None):
    ambiente = {"HOME": home, "PATH": os.environ.get("PATH", "")}
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), *args], input=entrada, capture_output=True, text=True, env=ambiente)
    return r.returncode, json.loads(r.stdout)


class Integridade(unittest.TestCase):
    def test_hash_da_skill_confere_com_o_script(self):
        texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        declarado = re.search(r"^H=([0-9a-f]{64})$", texto, re.M).group(1)
        self.assertEqual(declarado, hashlib.sha256(SCRIPT.read_bytes()).hexdigest())

    def test_versao_do_script_e_do_manifesto(self):
        versao = json.loads((RAIZ / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
        self.assertIn(f"Coiote Místico {versao}:", SCRIPT.read_text(encoding="utf-8"))

    def test_skill_sem_pasta_fixa_nem_busca_na_raiz(self):
        texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("/tmp/coiote-mistico", texto)
        self.assertNotIn("find / ", texto)
        self.assertIn("mktemp -d", texto)

    def test_sem_variaveis_de_ambiente_que_trocam_dados(self):
        codigo = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("COIOTE_DIR", codigo)
        self.assertNotIn("COIOTE_CATALOGO", codigo)


class Fluxo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def selar(self):
        codigo, saida = rodar(self.home, "selar", entrada=json.dumps(["a?", "b?", "c?"]))
        self.assertEqual(codigo, 0)
        return saida["selo"]

    def test_selar_e_abrir_com_permissoes_restritas(self):
        selo = self.selar()
        pasta = Path(self.home) / ".coiote-mistico"
        self.assertEqual(pasta.stat().st_mode & 0o777, 0o700)
        self.assertEqual((pasta / f"{selo}.json").stat().st_mode & 0o777, 0o600)
        codigo, saida = rodar(self.home, "abrir", selo, "1 2 3")
        self.assertEqual(codigo, 0)
        self.assertTrue(saida["verificado"])
        self.assertEqual((pasta / f"{selo}.abertura.json").stat().st_mode & 0o777, 0o600)

    def test_reabrir_com_outras_posicoes_e_recusado(self):
        selo = self.selar()
        rodar(self.home, "abrir", selo, "1 2 3")
        self.assertEqual(rodar(self.home, "abrir", selo, "1 2 3")[0], 0)
        self.assertEqual(rodar(self.home, "abrir", selo, "4 5 6")[1]["erro"], "rodada_ja_aberta")

    def test_marcador_adulterado_ou_trocado_e_recusado(self):
        a, b = self.selar(), self.selar()
        rodar(self.home, "abrir", a, "1 2 3")
        rodar(self.home, "abrir", b, "1 2 3")
        pasta = Path(self.home) / ".coiote-mistico"
        (pasta / f"{a}.abertura.json").write_text((pasta / f"{b}.abertura.json").read_text())
        self.assertEqual(rodar(self.home, "abrir", a, "1 2 3")[1]["erro"], "marcador_invalido")
        (pasta / f"{b}.abertura.json").write_text("[1, 2, 3]")
        self.assertEqual(rodar(self.home, "abrir", b, "1 2 3")[1]["erro"], "marcador_invalido")

    def test_json_profundo_nao_gera_traceback(self):
        codigo, saida = rodar(self.home, "selar", entrada="[" * 100000)
        self.assertEqual(codigo, 2)
        self.assertEqual(saida["erro"], "entrada_invalida")


if __name__ == "__main__":
    unittest.main()
