"""Validate the bundled dossier contract and optional local evidence text; offline."""
import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

VERSION = '1.1.0'
SKILL = Path(__file__).resolve().parents[1]
KEYWORDS = {'$schema', '$id', '$defs', '$ref', 'title', 'description', 'type',
            'properties', 'required', 'additionalProperties', 'items', 'minItems',
            'maxItems', 'uniqueItems', 'minLength', 'maxLength', 'pattern',
            'format', 'enum', 'const'}

def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Chave JSON duplicada: ' + key)
        result[key] = value
    return result

def load_json(path):
    text = Path(path).read_bytes().decode('utf-8-sig')
    return json.loads(text, object_pairs_hook=no_duplicates,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Número JSON inválido: '+x)))

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def check_schema(schema):
    unknown = set(schema) - KEYWORDS
    if unknown:
        raise ValueError('Termos não suportados no schema: '+str(sorted(unknown)))
    for child in schema.get('$defs', {}).values(): check_schema(child)
    for child in schema.get('properties', {}).values(): check_schema(child)
    if 'items' in schema: check_schema(schema['items'])

def timestamp(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value):
        raise ValueError('Data/hora exige ISO 8601 com fuso')
    if not value.endswith('Z'):
        hours,minutes=map(int,value[-5:].split(':'))
        if hours > 23 or minutes > 59: raise ValueError('Fuso inválido')
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

def structural(value, schema, root, path='$'):
    if '$ref' in schema:
        reference=schema['$ref']
        if not reference.startswith('#/$defs/'): raise ValueError('Referência externa não suportada')
        return structural(value,root['$defs'][reference.split('/')[-1]],root,path)
    errors=[]
    def fail(message): errors.append(path+': '+message)
    types=schema.get('type')
    if types:
        types=[types] if isinstance(types,str) else types
        matches={'null':value is None,'string':isinstance(value,str),'object':isinstance(value,dict),
                 'array':isinstance(value,list),'boolean':type(value) is bool}
        if not any(matches.get(kind,False) for kind in types):
            fail('tipo inválido'); return errors
    if 'const' in schema and canonical(value)!=canonical(schema['const']): fail('valor constante inválido')
    if 'enum' in schema and canonical(value) not in [canonical(v) for v in schema['enum']]: fail('valor fora da enumeração')
    if isinstance(value,dict):
        props=schema.get('properties',{})
        for key in schema.get('required',[]):
            if key not in value: fail('campo obrigatório ausente: '+key)
        if schema.get('additionalProperties') is False:
            for key in set(value)-set(props): fail('campo extra: '+key)
        for key in value.keys() & props.keys(): errors.extend(structural(value[key],props[key],root,path+'.'+key))
    elif isinstance(value,list):
        if len(value)<schema.get('minItems',0): fail('itens insuficientes')
        if 'maxItems' in schema and len(value)>schema['maxItems']: fail('itens excedentes')
        if schema.get('uniqueItems') and len({canonical(v) for v in value})!=len(value): fail('itens duplicados')
        if 'items' in schema:
            for i,item in enumerate(value): errors.extend(structural(item,schema['items'],root,path+'['+str(i)+']'))
    elif isinstance(value,str):
        try: value.encode('utf-8',errors='strict')
        except UnicodeEncodeError: fail('Unicode inválido')
        if len(value)<schema.get('minLength',0) or not value.strip(): fail('texto vazio')
        if 'maxLength' in schema and len(value)>schema['maxLength']: fail('texto longo demais')
        if 'pattern' in schema and re.search(schema['pattern'],value) is None: fail('padrão inválido')
        try:
            if schema.get('format')=='date': date.fromisoformat(value)
            elif schema.get('format')=='date-time': timestamp(value)
        except (ValueError,OverflowError): fail('data ou fuso inválido')
    return errors

def validate(data, texts=None, previous=None, previous_sha256=None):
    version=data.get('schema_version') if isinstance(data,dict) else None
    schema=load_json(SKILL/('schemas/dossie-1.0.0.schema.json' if version=='1.0.0' else 'schemas/dossie.schema.json'))
    check_schema(schema)
    errors=structural(data,schema,schema)
    scope='estrutura_e_coerencia' if texts is None else 'estrutura_coerencia_e_textos'
    if previous is not None: scope += '_e_dossie_anterior'
    limit='Não verifica verdade factual, autenticidade, qualidade científica, atualidade da web ou interpretação jurídica.'
    if previous is None: limit += ' Sem --previous, a proveniência é apenas declarada; IDs e mudanças não são cotejados com a versão anterior.'
    def result(): return {'valido':not errors,'erros':errors,'escopo':scope,'helper_version':VERSION,'limite':limit}
    if errors: return result()
    if previous is not None and version != '1.1.0':
        errors.append('--previous requer contrato atual 1.1.0; não migre dados por mera troca da versão')
        return result()
    def fail(message): errors.append(message)
    def index(name):
        output={}
        for item in data[name]:
            if item['id'] in output: fail(name+': ID duplicado '+item['id'])
            output[item['id']]=item
        return output
    sources=index('fontes'); evidences=index('evidencias'); claims=index('afirmacoes'); gaps=index('pendencias')
    requested=set(data['escopo']['afirmacoes_solicitadas'])
    if requested != set(claims): fail('Afirmações exportadas devem corresponder ao escopo solicitado')
    consulted=timestamp(data['escopo']['data_consulta'])
    closed=data['escopo']['universo']=='fechado'
    for source in sources.values():
        if closed and source['origem']!='fornecida': fail(source['id']+': fonte web em universo fechado')
        if closed and source['temporalidade']=='consulta_atual': fail(source['id']+': atualidade web em universo fechado')
        if source['temporalidade']=='consulta_atual' and source['origem']!='web': fail(source['id']+': consulta atual exige origem web')
        if source['acesso']!='indisponivel' and source['consultada_em'] is None: fail(source['id']+': falta data real de acesso')
        if source['consultada_em'] and timestamp(source['consultada_em'])>consulted: fail(source['id']+': acesso posterior ao registro da consulta')
        if source['sha256_texto'] and source['acesso']=='indisponivel': fail(source['id']+': hash de texto indisponível')
    for ev in evidences.values():
        source=sources.get(ev['fonte_id'])
        if source is None: fail(ev['id']+': fonte inexistente')
        elif source['acesso']=='indisponivel': fail(ev['id']+': evidência em fonte indisponível')
    gapped=set()
    for gap in gaps.values():
        for cid in gap['afirmacao_ids']:
            if cid not in claims: fail(gap['id']+': afirmação inexistente')
            gapped.add(cid)
    used_sources=set()
    for claim in claims.values():
        links=claim['evidencias']
        link_ids=[l['evidencia_id'] for l in links]
        if len(link_ids)!=len(set(link_ids)): fail(claim['id']+': evidência repetida com relações distintas')
        support=[]; contradiction=[]
        for link in links:
            ev=evidences.get(link['evidencia_id'])
            if ev is None: fail(claim['id']+': evidência inexistente'); continue
            source=sources.get(ev['fonte_id'])
            if source: used_sources.add(source['id'])
            if link['relacao']=='APOIA' and source: support.append(source)
            elif link['relacao']=='CONTRADIZ': contradiction.append(ev)
        state=claim['estado']
        if state=='SUSTENTADA' and (not support or contradiction): fail(claim['id']+': sustentada exige apoio sem contradição')
        if state=='PARCIALMENTE_SUSTENTADA' and (not support or not claim['limitacoes']): fail(claim['id']+': apoio parcial exige apoio e limites')
        if state=='CONTRADITA' and not contradiction: fail(claim['id']+': contradita exige evidência de contradição')
        if state=='NAO_VERIFICADA' and (not claim['limitacoes'] or claim['id'] not in gapped): fail(claim['id']+': não verificada exige limite e pendência')
        if claim['verificacao_atual']:
            if closed or state not in ('SUSTENTADA','PARCIALMENTE_SUSTENTADA','CONTRADITA'):
                fail(claim['id']+': verificação atual incompatível com escopo/estado')
            relevant=support if state!='CONTRADITA' else [sources.get(ev['fonte_id']) for ev in contradiction]
            if not relevant or any(s is None or s['origem']!='web' or s['temporalidade']!='consulta_atual' or s['acesso']=='indisponivel' or not s['consultada_em'] or timestamp(s['consultada_em']).astimezone(consulted.tzinfo).date()!=consulted.date() for s in relevant):
                fail(claim['id']+': falta suporte consultado na data com origem e temporalidade adequadas')
    if data['cobertura']=='integral':
        if not claims or gaps or any(c['estado']=='NAO_VERIFICADA' for c in claims.values()): fail('Cobertura integral incompatível com lacunas ou escopo vazio')
        if any(sources[s]['acesso']!='completo' for s in used_sources): fail('Cobertura integral com evidência parcial')
    if version=='1.1.0':
        errors.extend(provenance(data))
        if previous is not None: errors.extend(compare_previous(data,previous,previous_sha256))
    if texts is not None:
        if not isinstance(texts,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in texts.items()):
            fail('--texts exige objeto fonte_id para texto'); return result()
        for sid,txt in texts.items():
            if sid not in sources: fail('Texto de fonte desconhecida: '+sid)
            try: txt.encode('utf-8',errors='strict')
            except UnicodeEncodeError: fail('Texto Unicode inválido: '+sid)
        text_sources=used_sources | {ev['fonte_id'] for ev in evidences.values()} | {s['id'] for s in sources.values() if s['sha256_texto']}
        for sid in text_sources:
            if sid not in texts: fail('Texto necessário ausente: '+sid)
        for sid,source in sources.items():
            if sid in texts and source['sha256_texto']:
                try: actual=hashlib.sha256(texts[sid].encode('utf-8')).hexdigest()
                except UnicodeEncodeError: continue
                if actual!=source['sha256_texto']: fail('Hash não corresponde ao texto: '+sid)
        for ev in evidences.values():
            if ev['fonte_id'] in texts and ev['trecho'] not in texts[ev['fonte_id']]: fail('Trecho literal ausente: '+ev['id'])
    return result()

def provenance(data):
    errors=[]
    previous=data['revisao_anterior']
    changes=data['mudancas']
    claims={c['id']:c for c in data['afirmacoes']}
    evidences={e['id'] for e in data['evidencias']}
    if changes and previous is None: errors.append('Mudanças exigem identificação do dossiê anterior')
    if previous and previous['versao_dossie']==data['versao_dossie']:
        errors.append('Revisão deve ter versão distinta do dossiê anterior')
    seen=set()
    for change in changes:
        cid=change['afirmacao_id']
        if cid in seen: errors.append(cid+': mudança repetida')
        seen.add(cid)
        if change['tipo']=='removida':
            if cid in claims or change['estado_atual'] is not None or change['estado_anterior'] is None:
                errors.append(cid+': remoção exige estado anterior, ausência no conjunto atual e estado atual null')
        else:
            if cid not in claims or change['estado_atual'] != claims[cid]['estado']:
                errors.append(cid+': mudança incompatível com a afirmação atual')
            if change['tipo']=='incluida' and change['estado_anterior'] is not None:
                errors.append(cid+': inclusão não possui estado anterior')
            if change['tipo']=='alterada' and change['estado_anterior'] is None:
                errors.append(cid+': alteração exige estado anterior')
        for eid in change['evidencia_ids']:
            if eid not in evidences: errors.append(cid+': evidência de mudança inexistente')
    return errors


def compare_previous(data, previous, previous_sha256=None):
    errors=[]
    result=validate(previous)
    if not result['valido']: return ['Dossiê anterior inválido: '+str(result['erros'])]
    reference=data['revisao_anterior']
    if reference is None: return ['--previous exige revisao_anterior identificada']
    if 'versao_dossie' in previous and reference['versao_dossie'] != previous['versao_dossie']:
        errors.append('Versão anterior declarada não corresponde ao arquivo fornecido')
    if 'material_auditado' in previous:
        material=previous['material_auditado']
        if reference['material_id'] != material['id'] or reference['versao_material'] != material['versao']:
            errors.append('Identificação anterior do material não corresponde ao dossiê fornecido')
    if reference['sha256_arquivo'] is not None:
        if previous_sha256 is None:
            errors.append('Hash anterior declarado exige bytes originais; use CLI --previous')
        elif reference['sha256_arquivo'] != previous_sha256:
            errors.append('Hash do dossiê anterior não corresponde aos bytes fornecidos')
    before={c['id']:c for c in previous['afirmacoes']}
    after={c['id']:c for c in data['afirmacoes']}
    changes={c['afirmacao_id']:c for c in data['mudancas']}
    def fingerprint(claim,dossier):
        evs={e['id']:e for e in dossier['evidencias']}
        sources={s['id']:s for s in dossier['fontes']}
        linked=[]
        for link in claim['evidencias']:
            ev=evs.get(link['evidencia_id'])
            source=sources.get(ev['fonte_id']) if ev else None
            linked.append({'relacao':link['relacao'],'evidencia':ev,'fonte':{k:source.get(k) for k in ('id','titulo','data_documento','localizacao','natureza')} if source else None})
        return canonical({'afirmacao':{k:claim[k] for k in ('texto','estado','camada','limitacoes','justificativa')},'suporte':sorted(linked,key=canonical)})
    expected={cid:'removida' for cid in before.keys()-after.keys()}
    expected.update({cid:'incluida' for cid in after.keys()-before.keys()})
    expected.update({cid:'alterada' for cid in before.keys()&after.keys() if fingerprint(before[cid],previous)!=fingerprint(after[cid],data)})
    if set(changes)!=set(expected):
        errors.append('Lista de mudanças não corresponde às diferenças materiais entre os dossiês')
    for cid,change in changes.items():
        if expected.get(cid)!=change['tipo']:errors.append(cid+': tipo de mudança não corresponde ao dossiê anterior')
        if change['estado_anterior'] != (before[cid]['estado'] if cid in before else None):
            errors.append(cid+': estado anterior não corresponde ao arquivo anterior')
    return errors


def main():
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dossie',type=Path)
    parser.add_argument('--texts',type=Path)
    parser.add_argument('--previous',type=Path,help='Dossiê anterior para cotejo de IDs, estados, mudanças e hash declarado')
    args=parser.parse_args()
    try:
        result=validate(load_json(args.dossie),load_json(args.texts) if args.texts else None,
                        load_json(args.previous) if args.previous else None,
                        hashlib.sha256(args.previous.read_bytes()).hexdigest() if args.previous else None)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result['valido'] else 1
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,RecursionError) as exc:
        print(json.dumps({'valido':False,'erro_execucao':str(exc)},ensure_ascii=False))
        return 2

if __name__=='__main__': sys.exit(main())
