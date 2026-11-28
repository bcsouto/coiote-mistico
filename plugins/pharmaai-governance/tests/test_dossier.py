import copy, hashlib, importlib.util, json, subprocess, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def changed(base,path,value):
    d=copy.deepcopy(base);o=d
    for p in path[:-1]:o=o[p]
    o[path[-1]]=value;return d

S=ROOT/'skills/auditar-evidencias';v=module('pharma',S/'scripts/validate_dossier.py')
BASE=read(S/'assets/dossie-ficticio.json');TEXTS=read(S/'assets/textos-ficticios.json');LEGACY=read(ROOT/'tests/fixtures/legacy-1.0.0.json')
def revision():
    d=copy.deepcopy(BASE);d.update(versao_dossie='2',revisao_anterior={'localizacao':'arquivo:anterior.json','versao_dossie':'1','material_id':'material-ficticio','versao_material':None,'sha256_arquivo':None},mudancas=[{'afirmacao_id':'a1','tipo':'alterada','estado_anterior':'SUSTENTADA','estado_atual':'SUSTENTADA','motivo':'Condição explicitada sem mudar o estado de suporte.','evidencia_ids':['e1']}]);return d
class DossierTests(unittest.TestCase):
    def test_json_profundo(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            arq=Path(d)/'profundo.json';arq.write_text('['*100000,encoding='utf-8')
            r=subprocess.run([sys.executable,'-I',str(S/'scripts/validate_dossier.py'),str(arq)],capture_output=True,text=True)
            self.assertEqual(r.returncode,2);self.assertFalse(json.loads(r.stdout)['valido']);self.assertNotIn('Traceback',r.stderr)
    def test_examples(self):
        self.assertTrue(v.validate(BASE,TEXTS)['valido']);self.assertTrue(v.validate(LEGACY,TEXTS)['valido'])
    def test_revision(self):self.assertTrue(v.validate(revision(),TEXTS)['valido'])
    def test_revision_requires_previous(self):self.assertFalse(v.validate(changed(revision(),['revisao_anterior'],None))['valido'])
    def test_revision_distinct(self):self.assertFalse(v.validate(changed(revision(),['versao_dossie'],'1'))['valido'])
    def test_revision_state(self):self.assertFalse(v.validate(changed(revision(),['mudancas',0,'estado_atual'],'CONTRADITA'))['valido'])
    def test_revision_evidence(self):self.assertFalse(v.validate(changed(revision(),['mudancas',0,'evidencia_ids'],['missing']))['valido'])
    def test_removed_claim(self):
        d=revision();d['mudancas']=[{'afirmacao_id':'removed','tipo':'removida','estado_anterior':'NAO_VERIFICADA','estado_atual':None,'motivo':'Fora do escopo da nova versão.','evidencia_ids':[]}];self.assertTrue(v.validate(d)['valido'])
        d['mudancas'][0]['afirmacao_id']='a1';self.assertFalse(v.validate(d)['valido'])
    def test_added_claim(self):
        d=revision();d['mudancas'][0].update(tipo='incluida',estado_anterior=None);self.assertTrue(v.validate(d)['valido'])
        d['mudancas'][0]['estado_anterior']='SUSTENTADA';self.assertFalse(v.validate(d)['valido'])
    def test_material_required(self):
        d=copy.deepcopy(BASE);del d['material_auditado'];self.assertFalse(v.validate(d)['valido'])
    def test_unknown_material_metadata(self):self.assertTrue(v.validate(BASE)['valido'])
    def test_material_hash_format(self):self.assertFalse(v.validate(changed(BASE,['material_auditado','sha256_arquivo'],'x'*64))['valido'])
    def test_source_hash(self):
        d=copy.deepcopy(BASE);d['fontes'][0]['sha256_texto']=hashlib.sha256(TEXTS['f1'].encode()).hexdigest();self.assertTrue(v.validate(d,TEXTS)['valido'])
        d['fontes'][0]['sha256_texto']='0'*64;self.assertFalse(v.validate(d,TEXTS)['valido'])
    def test_quote_mismatch(self):self.assertFalse(v.validate(changed(BASE,['evidencias',0,'trecho'],'Trecho inexistente.'),TEXTS)['valido'])
    def test_unknown_evidence(self):self.assertFalse(v.validate(changed(BASE,['afirmacoes',0,'evidencias',0,'evidencia_id'],'missing'))['valido'])
    def test_closed_current(self):self.assertFalse(v.validate(changed(BASE,['afirmacoes',0,'verificacao_atual'],True))['valido'])
    def test_current_open(self):
        d=copy.deepcopy(BASE);d['escopo']['universo']='aberto';d['fontes'][0].update(origem='web',temporalidade='consulta_atual');d['afirmacoes'][0]['verificacao_atual']=True;self.assertTrue(v.validate(d)['valido'])
    def test_invalid_time_and_unicode(self):
        self.assertFalse(v.validate(changed(BASE,['escopo','data_consulta'],'2026-10-03T12:00:00+00:99'))['valido'])
        self.assertFalse(v.validate(changed(BASE,['titulo'],chr(0xd800)))['valido'])
    def test_cli(self):
        proc=subprocess.run([sys.executable,'-B',str(v.__file__),str(S/'assets/dossie-ficticio.json'),'--texts',str(S/'assets/textos-ficticios.json')],capture_output=True,encoding='utf-8');self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
    def test_previous_real_change(self):
        d=revision();d['afirmacoes'][0]['texto'] += ' Condição adicional.'
        self.assertTrue(v.validate(d,TEXTS,BASE)['valido'])
    def test_previous_omitted_change(self):
        d=revision();d['afirmacoes'][0]['texto'] += ' Condição adicional.';d['mudancas']=[]
        self.assertFalse(v.validate(d,TEXTS,BASE)['valido'])
    def test_previous_invented_change(self):self.assertFalse(v.validate(revision(),TEXTS,BASE)['valido'])
    def test_previous_wrong_identity(self):
        d=revision();d['afirmacoes'][0]['texto'] += ' Condição adicional.';d['revisao_anterior']['material_id']='wrong'
        self.assertFalse(v.validate(d,TEXTS,BASE)['valido'])
    def test_previous_wrong_state(self):
        d=revision();d['afirmacoes'][0]['texto'] += ' Condição adicional.';d['mudancas'][0]['estado_anterior']='CONTRADITA'
        self.assertFalse(v.validate(d,TEXTS,BASE)['valido'])
    def test_previous_file_hash(self):
        d=revision();d['afirmacoes'][0]['texto'] += ' Condição adicional.';d['revisao_anterior']['sha256_arquivo']='1'*64
        self.assertFalse(v.validate(d,TEXTS,BASE,'0'*64)['valido'])
        self.assertTrue(v.validate(d,TEXTS,BASE,'1'*64)['valido'])
    def test_previous_evidence_changed(self):
        d=revision();d['evidencias'][0]['localizador'] += ' (detalhe)'
        self.assertTrue(v.validate(d,TEXTS,BASE)['valido'])
    def test_previous_cli(self):
        import tempfile
        d=revision();d['afirmacoes'][0]['texto'] += ' Condição adicional.'
        with tempfile.TemporaryDirectory() as tmp:
            now=Path(tmp)/'atual.json';now.write_text(json.dumps(d),encoding='utf-8')
            proc=subprocess.run([sys.executable,'-B',str(v.__file__),str(now),'--previous',str(S/'assets/dossie-ficticio.json')],capture_output=True,encoding='utf-8')
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
if __name__=='__main__':unittest.main()
