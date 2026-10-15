"""Real local Vault reader tests; the production Web must never fall back to samples."""
from contextlib import contextmanager
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import sys
from threading import Event, Thread

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from kb_core.members import MemberStore
from kb_core.operations import Coordinator
from kb_core.display_policy import PolicyService, proposal_hash

TEST_ACCESS_TOKEN = 'a' * 64


def api():
    assert importlib.util.find_spec('kb_core.local_vault_web') is not None, 'local real Vault Web module missing'
    from kb_core import local_vault_web
    return local_vault_web


def fixture(tmp_path, *, deny=False):
    instance = tmp_path / 'instance'; instance.mkdir()
    MemberStore(instance / 'members.json').create()
    vault = tmp_path / 'vault'; (vault / 'wiki/frameworks').mkdir(parents=True)
    index = '- [[frameworks/F-C06-001-mem0|mem0]]\n'
    card = ('---\nid: F-C06-001\ntitle: mem0 memory layer\nrepo_local_path: E:/private/repo\n---\n'
            '# mem0\nReal indexed knowledge.\n')
    (vault / 'wiki/index.md').write_text(index, encoding='utf-8')
    card_path = 'wiki/frameworks/F-C06-001-mem0.md'
    (vault / card_path).write_text(card, encoding='utf-8')
    member = {'schema_version':'kb-contracts-1.0','revision':1,'vault_id':'kb-arch','aliases':['vault②'],
        'name':'agent架构','purpose_ref':'purpose.md','agents_ref':'AGENTS.md','navigation_refs':[],
        'core_version':'unknown','profiles':[],'location_ref':'kb-arch-local','display_ref':None,'enabled':True}
    Coordinator(instance).execute('register-kb-arch','register',{'member':member,'root':str(vault),
        'expected_collection_revision':1,'expected_binding_revision':0,'expected_generation':0})
    policy_root=tmp_path/'policy'; policy_root.mkdir()
    policy=PolicyService(instance,policy_root)
    document={'policy_revision':1,'vault_id':'kb-arch','allow':['wiki/index.md',card_path],
        'deny':[card_path] if deny else [],'revoked':[],'channel':'web'}
    policy.save('kb-arch',document,authorized_target=policy.get('kb-arch','web')['metadata_path'],
        expected_source=policy.get('kb-arch','web')['source'],reviewed_proposal_hash=proposal_hash(document,legacy=None),
        review_ref='owner-request/real-vault-web.md',legacy=None)
    config_path=tmp_path/'catalog.json'
    config_path.write_text(json.dumps({'vaults':{'kb-arch':{'kind':'wiki-index','index':'wiki/index.md',
        'content_roots':['wiki/frameworks']}}}),encoding='utf-8')
    card_bytes=(vault/card_path).read_bytes(); index_bytes=(vault/'wiki/index.md').read_bytes()
    auth_path=tmp_path/'read-authorization.json'
    access_token_path=tmp_path/'browser-access-token.txt'
    access_token_path.write_text(TEST_ACCESS_TOKEN+'\n',encoding='ascii')
    authorization_doc=tmp_path/'owner-approved-scope.md'
    authorization_doc.write_text('Owner approved this local test scope.\n',encoding='utf-8')
    auth_path.write_text(json.dumps({'schema_version':'local-vault-read-1','authorization_ref':'owner-request/real-vault-web.md',
        'authorization_sha256':hashlib.sha256(authorization_doc.read_bytes()).hexdigest(),
        'authorization_document_path':str(authorization_doc.resolve()),'bindings':{'kb-arch':1},'entries':{'kb-arch':{
            'wiki/index.md':hashlib.sha256(index_bytes).hexdigest(),card_path:hashlib.sha256(card_bytes).hexdigest()}}}),encoding='utf-8')
    return {'instance':instance,'policy_root':policy_root,'catalog_config':config_path,'authorization_path':auth_path,
        'access_token_path':access_token_path,
        'authorization_document':authorization_doc,'vault':vault,'card_path':card_path,'card_bytes':card_bytes}


def add_search_document(data, path='wiki/frameworks/second.md'):
    """Extend only the isolated fixture's native index and exact read grants."""
    module=api();path=module.relative_path(path);vault=data['vault'];extra=vault/path
    extra.parent.mkdir(parents=True,exist_ok=True)
    extra.write_text('# second\nReal indexed knowledge.\n',encoding='utf-8')
    index=vault/'wiki/index.md'
    index.write_text(index.read_text(encoding='utf-8')+'- [[frameworks/second|second]]\n',encoding='utf-8')
    service=PolicyService(data['instance'],data['policy_root']);current=service.get('kb-arch','web')
    revised=dict(current['policy']);revised['policy_revision']+=1;revised['allow']=[*revised['allow'],path]
    service.save('kb-arch',revised,authorized_target=current['metadata_path'],expected_source=current['source'],
        reviewed_proposal_hash=proposal_hash(revised,legacy=None),review_ref='owner-request/fixture-search-scope.md',legacy=None)
    authorization=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    authorization['entries']['kb-arch'][path]=hashlib.sha256(extra.read_bytes()).hexdigest()
    authorization['entries']['kb-arch']['wiki/index.md']=hashlib.sha256(index.read_bytes()).hexdigest()
    data['authorization_path'].write_text(json.dumps(authorization),encoding='utf-8')
    data['extra_path']=path
    return path


def add_second_member(data):
    """Add a second isolated member to exercise one shared-instance Hub response."""
    module=api(); vault=data['vault'].parent/'vault-second'; (vault/'wiki/frameworks').mkdir(parents=True)
    index='- [[frameworks/second|second]]\n'; card='# second\nSecond indexed knowledge.\n'
    (vault/'wiki/index.md').write_text(index,encoding='utf-8')
    card_path='wiki/frameworks/second.md'; (vault/card_path).write_text(card,encoding='utf-8')
    member={'schema_version':'kb-contracts-1.0','revision':1,'vault_id':'kb-other','aliases':[],
        'name':'second test member','purpose_ref':'purpose.md','agents_ref':'AGENTS.md','navigation_refs':[],
        'core_version':'unknown','profiles':[],'location_ref':'kb-other-local','display_ref':None,'enabled':True}
    Coordinator(data['instance']).execute('register-kb-other','register',{'member':member,'root':str(vault),
        'expected_collection_revision':2,'expected_binding_revision':0,'expected_generation':0})
    policy=PolicyService(data['instance'],data['policy_root']); before=policy.get('kb-other','web')
    document={'policy_revision':1,'vault_id':'kb-other','allow':['wiki/index.md',card_path],
        'deny':[],'revoked':[],'channel':'web'}
    policy.save('kb-other',document,authorized_target=before['metadata_path'],expected_source=before['source'],
        reviewed_proposal_hash=proposal_hash(document,legacy=None),review_ref='owner-request/second-member-fixture.md',legacy=None)
    config=json.loads(data['catalog_config'].read_text(encoding='utf-8'))
    config['vaults']['kb-other']={'kind':'wiki-index','index':'wiki/index.md','content_roots':['wiki/frameworks']}
    data['catalog_config'].write_text(json.dumps(config),encoding='utf-8')
    authorization=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    authorization['bindings']['kb-other']=1
    authorization['entries']['kb-other']={'wiki/index.md':hashlib.sha256((vault/'wiki/index.md').read_bytes()).hexdigest(),
        card_path:hashlib.sha256((vault/card_path).read_bytes()).hexdigest()}
    data['authorization_path'].write_text(json.dumps(authorization),encoding='utf-8')
    data['second_vault']=vault
    return module


def withdraw_search_document(data,path):
    """Publish a valid revised owner scope that removes one fixture document."""
    data['authorization_document'].write_text('Owner withdrew one local test document.\n',encoding='utf-8')
    authorization=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    authorization['authorization_sha256']=hashlib.sha256(data['authorization_document'].read_bytes()).hexdigest()
    authorization['entries']['kb-arch'].pop(path,None)
    data['authorization_path'].write_text(json.dumps(authorization),encoding='utf-8')


@contextmanager
def running(config):
    config={**config,'access_token_file':Path(config['authorization_path']).parent/'browser-access-token.txt'}
    server=api().create_server(**config,read_authorized=True,port=0)
    thread=Thread(target=server.serve_forever,kwargs={'poll_interval':0.01},daemon=True); thread.start()
    try: yield server.server_port
    finally:
        server.shutdown(); thread.join(timeout=5); server.server_close(); assert not thread.is_alive()


def get(port,path,headers=None,*,authenticated=True):
    client=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    try:
        request_headers=dict(headers or {})
        if authenticated: request_headers.setdefault('Authorization','Bearer '+TEST_ACCESS_TOKEN)
        client.request('GET',path,headers=request_headers)
        response=client.getresponse(); return response.status,dict(response.getheaders()),response.read()
    finally: client.close()


def test_real_catalog_reads_native_index_and_page_is_bounded(tmp_path):
    data=fixture(tmp_path)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,headers,body=get(port,'/api/vaults')
        assert status==200 and headers['Cache-Control']=='no-store'
        listing=json.loads(body)
        assert [row['vault_id'] for row in listing['vaults']]==['kb-arch']
        assert listing['vaults'][0]['asset_count']==1
        assert listing['vaults'][0]['scope_entry_count']==1
        assert listing['vaults'][0]['catalog_entry_count']==1
        assert listing['vaults'][0]['authorized_scope_count']==1
        assert listing['vaults'][0]['successful_read_count']==0
        assert str(data['vault']).encode() not in body
        status,_,body=get(port,'/api/catalog?vault_id=kb-arch&offset=0&limit=10')
        assert status==200
        page=json.loads(body)
        assert page['total']==1 and page['scope_entry_total']==1 and page['items'][0]['path']==data['card_path']
        assert page['items'][0]['status']=='in_scope'
        assert 'source_sha256' not in page['items'][0]
        status,_,body=get(port,'/api/read?vault_id=kb-arch&path='+data['card_path'])
        assert status==200 and json.loads(body)['source_sha256']==hashlib.sha256(data['card_bytes']).hexdigest()
        listing=json.loads(get(port,'/api/vaults')[2])
        assert listing['vaults'][0]['successful_read_count']==1


def test_health_endpoint_is_unauthenticated_but_exposes_only_build_identity(tmp_path):
    data=fixture(tmp_path)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],
                  'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,headers,body=get(port,'/healthz',authenticated=False)
        foreign_status,_,_=get(port,'/healthz',{'Host':'example.invalid'},authenticated=False)
    result=json.loads(body)
    assert status==200 and headers['Cache-Control']=='no-store'
    assert result['status']=='ok' and result['port']==port
    assert len(result['build_id'])==64 and all(char in '0123456789abcdef' for char in result['build_id'])
    assert not {'vaults','vault_count','paths','token','access_token'} & result.keys()
    assert foreign_status==403


def test_private_api_requires_per_request_bearer_and_rotation_revokes_old_token(tmp_path):
    data=fixture(tmp_path)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        for path in ('/api/vaults','/api/catalog?vault_id=kb-arch','/api/read?vault_id=kb-arch&path='+data['card_path']):
            status,_,body=get(port,path,authenticated=False)
            assert status==401 and json.loads(body)['error']['code']=='local_session_unauthorized'
        assert get(port,'/api/read?vault_id=kb-arch&path='+data['card_path'],{'Authorization':'Bearer wrong'})[0]==401
        status,_,body=get(port,'/api/read?vault_id=kb-arch&path='+data['card_path'])
        assert status==200 and json.loads(body)['source_sha256']==hashlib.sha256(data['card_bytes']).hexdigest()
        data['access_token_path'].write_text('b'*64+'\n',encoding='ascii')
        assert get(port,'/api/vaults',{'Authorization':'Bearer '+TEST_ACCESS_TOKEN})[0]==401
        assert get(port,'/api/vaults',{'Authorization':'Bearer '+'b'*64})[0]==200


def test_revoked_token_file_fails_closed_until_a_new_token_is_issued(tmp_path):
    data=fixture(tmp_path)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        assert get(port,'/api/vaults')[0]==200
        data['access_token_path'].unlink()
        status,_,body=get(port,'/api/vaults')
        assert status==503 and json.loads(body)['error']['code']=='local_access_token_unavailable'
        replacement='c'*64
        data['access_token_path'].write_text(replacement+'\n',encoding='ascii')
        assert get(port,'/api/vaults')[0]==401
        assert get(port,'/api/vaults',{'Authorization':'Bearer '+replacement},authenticated=False)[0]==200


def test_browser_static_response_prevents_referrer_and_token_query_transport(tmp_path):
    data=fixture(tmp_path)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,headers,script=get(port,'/app.js',authenticated=False)
        assert status==200 and headers['Cache-Control']=='no-store'
        assert headers['Referrer-Policy']=='no-referrer'
        assert "credentials:'omit'" in script.decode('utf-8')
        assert "headers:{Authorization:`Bearer ${token}`}" in script.decode('utf-8')
        assert get(port,'/api/vaults?access_token='+TEST_ACCESS_TOKEN)[0]==400
        assert get(port,'/api/vaults?token='+TEST_ACCESS_TOKEN)[0]==400


def test_external_link_sanitizer_is_served_with_the_browser_bundle(tmp_path):
    data=fixture(tmp_path)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],
                  'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        index_status,_,index=get(port,'/',authenticated=False)
        helper_status,headers,helper=get(port,'/safe_external_url.js',authenticated=False)
    assert index_status==200 and b'./safe_external_url.js' in index
    assert helper_status==200
    assert headers['Content-Type'].startswith('text/javascript;')
    assert headers['Cache-Control']=='no-store'
    assert headers['Referrer-Policy']=='no-referrer'
    assert b'url.username' in helper and b'url.password' in helper


@pytest.mark.parametrize('route,match_payload', [
    ('/api/vaults', lambda payload: payload.get('data_kind') == 'owner-local real Vaults'),
    ('/api/catalog?vault_id=kb-arch&offset=0&limit=10', lambda payload: payload.get('vault_id') == 'kb-arch'),
    ('/api/resolve?vault_id=kb-arch&source_path=wiki%2Findex.md&target=frameworks%2FF-C06-001-mem0',
     lambda payload: payload.get('path') == 'wiki/frameworks/F-C06-001-mem0.md'),
])
def test_http_metadata_responses_hold_policy_guard_through_send(tmp_path, monkeypatch, route, match_payload):
    data=fixture(tmp_path); module=api(); policy=PolicyService(data['instance'],data['policy_root']); attempts=[]
    replacement={'policy_revision':2,'vault_id':'kb-arch','allow':['wiki/index.md',data['card_path']],
        'deny':[data['card_path']],'revoked':[],'channel':'web'}
    original_send=module._Handler._send
    def revoke_during_send(handler,status,payload,*,mime='application/json; charset=utf-8',headers=None):
        if status==200 and isinstance(payload,dict) and match_payload(payload):
            try:
                before=policy.get('kb-arch','web')
                policy.save('kb-arch',replacement,authorized_target=before['metadata_path'],expected_source=before['source'],
                    reviewed_proposal_hash=proposal_hash(replacement,legacy=None),
                    review_ref='owner-request/revoke-before-metadata-send.md',legacy=None)
                attempts.append('committed')
            except module.PolicyError as error:
                attempts.append(error.code)
        return original_send(handler,status,payload,mime=mime,headers=headers)
    monkeypatch.setattr(module._Handler,'_send',revoke_during_send)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],
                  'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,route)
    assert status==200
    assert attempts==['policy_busy']


def test_hub_holds_multiple_vault_scopes_without_relocking_shared_authority(tmp_path,monkeypatch):
    data=fixture(tmp_path); module=add_second_member(data)
    policy=PolicyService(data['instance'],data['policy_root']); attempts=[]
    original_send=module._Handler._send
    def revoke_during_send(handler,status,payload,*,mime='application/json; charset=utf-8',headers=None):
        if status==200 and isinstance(payload,dict) and payload.get('data_kind')=='owner-local real Vaults':
            for identity in ('kb-arch','kb-other'):
                current=policy.get(identity,'web'); replacement={**current['policy'],
                    'policy_revision':current['policy']['policy_revision']+1}
                try:
                    policy.save(identity,replacement,authorized_target=current['metadata_path'],
                        expected_source=current['source'],reviewed_proposal_hash=proposal_hash(replacement,legacy=None),
                        review_ref='owner-request/multi-member-response-guard.md',legacy=None)
                    attempts.append('committed')
                except module.PolicyError as error:
                    attempts.append(error.code)
        return original_send(handler,status,payload,mime=mime,headers=headers)
    monkeypatch.setattr(module._Handler,'_send',revoke_during_send)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],
                  'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/vaults')
    result=json.loads(body)
    assert status==200
    assert {row['vault_id'] for row in result['vaults']}=={'kb-arch','kb-other'}
    assert all(row['status']=='online' for row in result['vaults'])
    assert attempts==['policy_busy','policy_busy']


def test_hub_can_report_offline_member_when_no_content_scope_is_delivered(tmp_path):
    data=fixture(tmp_path); data['vault'].rename(tmp_path/'vault-offline')
    with running({'instance':data['instance'],'policy_root':data['policy_root'],
                  'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/vaults')
    result=json.loads(body)
    assert status==200
    assert result['vaults']==[{'vault_id':'kb-arch','name':'agent架构','status':'offline','asset_count':None,
        'scope_entry_count':0,'catalog_entry_count':None,'authorized_scope_count':0,'successful_read_count':0,
        'count_basis':'unavailable'}]


def test_hub_reprojects_when_one_vault_goes_offline_after_projection(tmp_path,monkeypatch):
    data=fixture(tmp_path); module=add_second_member(data)
    original=module.NativeCatalog.vaults_with_delivery; moved=[]
    def go_offline_after_projection(catalog):
        result=original(catalog)
        if not moved:
            data['vault'].rename(tmp_path/'vault-offline')
            moved.append(True)
        return result
    monkeypatch.setattr(module.NativeCatalog,'vaults_with_delivery',go_offline_after_projection)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],
                  'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/vaults')
    assert status==200
    result=json.loads(body)
    rows={row['vault_id']:row for row in result['vaults']}
    assert rows['kb-arch']['status']=='offline' and rows['kb-arch']['asset_count'] is None
    assert rows['kb-other']['status']=='online'


def test_hub_does_not_retry_after_response_send_begins(tmp_path,monkeypatch):
    data=fixture(tmp_path); module=api(); sends=[]; guards=[]; projections=[]; finished=Event()
    original_projection=module.NativeCatalog.vaults_with_delivery
    def count_projection(catalog):
        projections.append(None)
        return original_projection(catalog)
    @contextmanager
    def fail_after_response(catalog,deliveries):
        guards.append(None)
        yield
        if len(guards)==1: raise module.LocalWebError('post_send_guard_error',503)
    original_send=module._Handler._send
    original_finish=module._Handler.finish
    def count_send(handler,status,payload,*,mime='application/json; charset=utf-8',headers=None):
        sends.append(status)
        return original_send(handler,status,payload,mime=mime,headers=headers)
    def signal_finish(handler):
        try: return original_finish(handler)
        finally: finished.set()
    monkeypatch.setattr(module.NativeCatalog,'guard_deliveries',fail_after_response)
    monkeypatch.setattr(module.NativeCatalog,'vaults_with_delivery',count_projection)
    monkeypatch.setattr(module._Handler,'_send',count_send)
    monkeypatch.setattr(module._Handler,'finish',signal_finish)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],
                  'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,_=get(port,'/api/vaults')
    assert finished.wait(5)
    assert status==200
    assert sends==[200] and len(guards)==1 and len(projections)==1


def test_search_marks_results_incomplete_when_safe_scan_byte_limit_is_reached(tmp_path, monkeypatch):
    data=fixture(tmp_path); module=api(); monkeypatch.setattr(module,'_MAX_LOCAL_SEARCH_BYTES',1)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],
                  'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/search?vault_id=kb-arch&q=Real%20indexed%20knowledge')
        static_status,_,script=get(port,'/app.js',authenticated=False)
    result=json.loads(body)
    assert status==200 and result['complete'] is False
    assert static_status==200 and '搜索结果不完整' in script.decode('utf-8')


def test_search_marks_results_incomplete_when_an_authorized_file_exceeds_reader_limit(tmp_path,monkeypatch):
    data=fixture(tmp_path);module=api()
    index_size=(data['vault']/'wiki/index.md').stat().st_size
    card_size=(data['vault']/data['card_path']).stat().st_size
    assert index_size<card_size
    monkeypatch.setattr(module._reader,'MAX_FILE_BYTES',(index_size+card_size)//2)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    result=catalog.search('kb-arch','Real indexed knowledge',0,10)
    assert result['complete'] is False and result['items']==[]


def test_search_marks_results_incomplete_when_an_authorized_candidate_cannot_be_read(tmp_path,monkeypatch):
    data=fixture(tmp_path);module=api();original=module._stable_read
    def fail_candidate(root,path):
        if path==data['card_path']:
            raise OSError('private local read failure')
        return original(root,path)
    monkeypatch.setattr(module,'_stable_read',fail_candidate)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    result=catalog.search('kb-arch','Real indexed knowledge',0,10)
    assert result['complete'] is False and result['items']==[]


def test_real_read_returns_canonical_hash_but_redacts_machine_path(tmp_path):
    data=fixture(tmp_path)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        path='/api/read?vault_id=kb-arch&path='+data['card_path']
        status,headers,body=get(port,path)
    result=json.loads(body)
    assert status==200 and headers['Cache-Control']=='no-store'
    assert result['source_sha256']==hashlib.sha256(data['card_bytes']).hexdigest()
    assert 'Real indexed knowledge.' in result['text']
    assert 'E:/private/repo' not in result['text']
    assert '[本机绝对路径已隐藏]' in result['text']
    assert result['path']==data['card_path']


def test_scoped_live_search_uses_only_authorized_current_native_entries(tmp_path):
    data=fixture(tmp_path)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/search?vault_id=kb-arch&q=Real%20indexed%20knowledge')
        assert status==200
        result=json.loads(body)
        assert result['total']==1 and result['items'][0]['path']==data['card_path']
        assert result['items'][0]['source_hash']==hashlib.sha256(data['card_bytes']).hexdigest()
        assert not {'restricted_count','native_entry_count','issues','search_bytes','scanned_count','scan_complete'} & result.keys()
        status,_,body=get(port,'/api/search?vault_id=kb-arch&q=Real',authenticated=False)
        assert status==401
        status,_,body=get(port,'/api/read?vault_id=kb-arch&path='+data['card_path'])
        assert status==200 and 'search_text' not in json.loads(body)


def test_scoped_live_search_omits_denied_entries_and_bounds_query(tmp_path):
    data=fixture(tmp_path,deny=True)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/search?vault_id=kb-arch&q=Real%20indexed%20knowledge')
        result=json.loads(body)
        assert status==200 and result['items']==[] and result['total']==0
        assert not {'restricted_count','native_entry_count','issues','search_bytes','scanned_count','scan_complete'} & result.keys()
        assert get(port,'/api/search?vault_id=kb-arch&q='+('x'*2001))[0]==400


def test_search_response_does_not_disclose_denied_entry_count_or_path(tmp_path):
    data=fixture(tmp_path,deny=True)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/search?vault_id=kb-arch&q=Real%20indexed%20knowledge')
    result=json.loads(body)
    assert status==200 and result['items']==[] and result['total']==0
    assert data['card_path'] not in body.decode('utf-8')
    assert not {'restricted_count','native_entry_count','issues','search_bytes','scanned_count','scan_complete'} & result.keys()


def test_wiki_search_holds_one_live_policy_guard_for_its_bounded_file_set(tmp_path,monkeypatch):
    data=fixture(tmp_path); module=api()
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    original=catalog.policy.guard; guard_calls=[]
    def counted(*args,**kwargs):
        guard_calls.append(args[1]);return original(*args,**kwargs)
    monkeypatch.setattr(catalog.policy,'guard',counted)
    result=catalog.search('kb-arch','Real indexed knowledge',0,10)
    assert result['total']==1 and result['items'][0]['path']==data['card_path']
    assert guard_calls==['wiki/index.md'], 'per-card policy checks use one cooperative bounded batch guard'


def test_wiki_search_rejects_an_index_change_during_scan(tmp_path,monkeypatch):
    data=fixture(tmp_path); module=api(); original=module._stable_read; changed=False
    def change_index_after_card(root,path):
        nonlocal changed
        result=original(root,path)
        if path==data['card_path'] and not changed:
            changed=True;(data['vault']/'wiki/index.md').write_text('[[frameworks/second.md]]\n',encoding='utf-8')
        return result
    monkeypatch.setattr(module,'_stable_read',change_index_after_card)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    with pytest.raises(module.LocalWebError) as changed_index:
        catalog.search('kb-arch','Real',0,10)
    assert changed_index.value.code=='local_source_changed_review_required'


def test_wikilink_resolution_stays_inside_authorized_native_catalog(tmp_path):
    data=fixture(tmp_path)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        base='/api/resolve?vault_id=kb-arch&source_path=wiki/index.md&target='
        status,_,body=get(port,base+'frameworks%2FF-C06-001-mem0%7Cmem0')
        assert status==200
        assert json.loads(body)['path']==data['card_path']
        assert get(port,base+'missing-card')[0]==404
    denied_root=tmp_path/'denied'; denied_root.mkdir()
    denied=fixture(denied_root,deny=True)
    with running({'instance':denied['instance'],'policy_root':denied['policy_root'],'catalog_config':denied['catalog_config'],'authorization_path':denied['authorization_path']}) as port:
        status,_,body=get(port,'/api/resolve?vault_id=kb-arch&source_path=wiki/index.md&target=frameworks%2FF-C06-001-mem0')
        assert status==403 and json.loads(body)['error']['code']=='policy_denied'


def test_wikilink_resolution_preserves_heading_anchor_without_widening_path_scope(tmp_path):
    data=fixture(tmp_path)
    (data['vault']/data['card_path']).write_text(
        '---\nid: F-C06-001\ntitle: mem0 memory layer\n---\n# mem0\n## 设计特点\nBody.\n',encoding='utf-8')
    from kb_core.local_vault_web import authorize_current_scope
    authorize_current_scope(instance=data['instance'],policy_root=data['policy_root'],catalog_config=data['catalog_config'],
        authorization_path=data['authorization_path'],authorization_document=data['authorization_document'],
        authorization_ref='owner-request/real-vault-web.md',vault_id='kb-arch',path=data['card_path'])
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        target='frameworks%2FF-C06-001-mem0%23%E8%AE%BE%E8%AE%A1%E7%89%B9%E7%82%B9%7C%E8%AE%B0%E5%BF%86%E8%AE%BE%E8%AE%A1'
        status,_,body=get(port,'/api/resolve?vault_id=kb-arch&source_path=wiki/index.md&target='+target)
    result=json.loads(body)
    assert status==200 and result['path']==data['card_path']
    assert result['anchor']=='设计特点'


def test_real_read_preserves_web_source_urls_while_hiding_local_paths():
    module=api()
    text='Source: https://github.com/example/project; local: E:/private/repo'
    redacted,changed=module._redact(text)
    assert 'https://github.com/example/project' in redacted
    assert 'E:/private/repo' not in redacted
    assert '[本机绝对路径已隐藏]' in redacted and changed


def test_local_web_rechecks_exact_policy_and_does_not_read_unindexed_files(tmp_path):
    data=fixture(tmp_path,deny=True)
    (data['vault']/'wiki/frameworks/secret.md').write_text('NEVER READ',encoding='utf-8')
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/read?vault_id=kb-arch&path='+data['card_path'])
        assert status==403 and json.loads(body)['error']['code']=='policy_denied'
        status,_,body=get(port,'/api/catalog?vault_id=kb-arch&offset=0&limit=10')
        item=json.loads(body)['items'][0]
        assert status==200 and item['status']=='restricted' and item['reason']=='policy_denied'
        status,_,body=get(port,'/api/read?vault_id=kb-arch&path=wiki/frameworks/secret.md')
        assert status==404 and json.loads(body)['error']['code']=='local_resource_not_indexed'


def test_local_read_rejects_manifest_missing_target_before_opening_body(tmp_path, monkeypatch):
    data=fixture(tmp_path)
    authorization=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    authorization['entries']['kb-arch'].pop(data['card_path'])
    data['authorization_path'].write_text(json.dumps(authorization),encoding='utf-8')
    module=api(); opened=[]; original=module._stable_read
    def track(root,path):
        opened.append(path)
        return original(root,path)
    monkeypatch.setattr(module,'_stable_read',track)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    with pytest.raises(module.LocalWebError) as denied:
        catalog._checked_read('kb-arch',data['card_path'])
    assert denied.value.code=='local_read_not_authorized'
    assert data['card_path'] not in opened


def test_local_web_rejects_foreign_origin_and_unbounded_page_input(tmp_path):
    data=fixture(tmp_path)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        assert get(port,'/api/vaults',{'Origin':'https://example.invalid'})[0]==403
        status,_,body=get(port,'/api/catalog?vault_id=kb-arch&offset=0&limit=1000')
        assert status==400 and json.loads(body)['error']['code']=='local_request_invalid'


def test_read_rejects_encoded_path_traversal_before_opening_any_vault_file(tmp_path,monkeypatch):
    data=fixture(tmp_path); module=api(); opened=[]; original=module._stable_read
    def track(root,path):
        opened.append(path)
        return original(root,path)
    monkeypatch.setattr(module,'_stable_read',track)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/read?vault_id=kb-arch&path=..%2F..%2Foutside.md')
    assert status==400 and json.loads(body)['error']['code']=='local_path_invalid'
    assert opened==[]


def test_cross_vault_path_reference_cannot_read_another_members_card(tmp_path):
    data=fixture(tmp_path); other=tmp_path/'other-vault'; (other/'wiki/frameworks').mkdir(parents=True)
    foreign_path='wiki/frameworks/foreign-card.md'; foreign=b'# Other Vault secret\nOnly the other member may read this.\n'
    other_index=b'- [[frameworks/foreign-card|Foreign card]]\n'
    (other/'wiki/index.md').write_bytes(other_index); (other/foreign_path).write_bytes(foreign)
    coordinator=Coordinator(data['instance'])
    member={'schema_version':'kb-contracts-1.0','revision':1,'vault_id':'kb-other','aliases':[],
        'name':'other test vault','purpose_ref':'purpose.md','agents_ref':'AGENTS.md','navigation_refs':[],
        'core_version':'unknown','profiles':[],'location_ref':'kb-other-local','display_ref':None,'enabled':True}
    coordinator.execute('register-kb-other','register',{'member':member,'root':str(other),
        'expected_collection_revision':2,'expected_binding_revision':0,'expected_generation':0})
    policy=PolicyService(data['instance'],data['policy_root'])
    document={'policy_revision':1,'vault_id':'kb-other','allow':['wiki/index.md',foreign_path],
        'deny':[],'revoked':[],'channel':'web'}
    policy.save('kb-other',document,authorized_target=policy.get('kb-other','web')['metadata_path'],
        expected_source=policy.get('kb-other','web')['source'],reviewed_proposal_hash=proposal_hash(document,legacy=None),
        review_ref='owner-request/cross-vault-test.md',legacy=None)
    config=json.loads(data['catalog_config'].read_text(encoding='utf-8'))
    config['vaults']['kb-other']={'kind':'wiki-index','index':'wiki/index.md','content_roots':['wiki/frameworks']}
    data['catalog_config'].write_text(json.dumps(config),encoding='utf-8')
    authorization=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    authorization['authorization_sha256']=hashlib.sha256(data['authorization_document'].read_bytes()).hexdigest()
    authorization['bindings']['kb-other']=coordinator.bindings.claim('kb-other-local')['generation']
    authorization['entries']['kb-other']={'wiki/index.md':hashlib.sha256(other_index).hexdigest(),
        foreign_path:hashlib.sha256(foreign).hexdigest()}
    data['authorization_path'].write_text(json.dumps(authorization),encoding='utf-8')
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/read?vault_id=kb-other&path='+foreign_path)
        assert status==200 and b'Only the other member may read this.' in body
        status,_,body=get(port,'/api/read?vault_id=kb-arch&path='+foreign_path)
    assert status==404 and b'Other Vault secret' not in body


def test_local_server_requires_explicit_read_authorization_and_loopback():
    module=api()
    with pytest.raises(module.LocalWebError) as denied:
        module.create_server(instance=Path('C:/invalid'),policy_root=Path('C:/invalid'),catalog_config=Path('C:/invalid'),authorization_path=Path('C:/invalid'),access_token_file=Path('C:/invalid'),read_authorized=False,port=0)
    assert denied.value.code=='local_read_unauthorized'
    with pytest.raises(module.LocalWebError) as nonlocal_bind:
        module.create_server(instance=Path('C:/invalid'),policy_root=Path('C:/invalid'),catalog_config=Path('C:/invalid'),authorization_path=Path('C:/invalid'),access_token_file=Path('C:/invalid'),read_authorized=True,host='0.0.0.0',port=0)
    assert nonlocal_bind.value.code=='local_host_not_loopback'


def test_changed_owner_authorization_document_revokes_local_reads(tmp_path):
    data=fixture(tmp_path)
    data['authorization_document'].write_text('scope withdrawn\n',encoding='utf-8')
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/read?vault_id=kb-arch&path=wiki/index.md')
    assert status==403 and json.loads(body)['error']['code']=='local_authorization_changed'


def test_read_rechecks_owner_scope_if_document_changes_during_body_read(tmp_path,monkeypatch):
    data=fixture(tmp_path); module=api(); original=module._stable_read; changed=False
    def withdraw_after_body(root,path):
        nonlocal changed
        result=original(root,path)
        if path==data['card_path'] and not changed:
            changed=True
            data['authorization_document'].write_text('scope withdrawn during read\n',encoding='utf-8')
        return result
    monkeypatch.setattr(module,'_stable_read',withdraw_after_body)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    with pytest.raises(module.LocalWebError) as withdrawn:
        catalog._checked_read('kb-arch',data['card_path'])
    assert withdrawn.value.code=='local_authorization_changed'


def test_search_rechecks_owner_scope_if_document_changes_during_body_read(tmp_path,monkeypatch):
    data=fixture(tmp_path); module=api(); original=module._stable_read; changed=False
    def withdraw_during_search(root,path):
        nonlocal changed
        result=original(root,path)
        if path==data['card_path'] and not changed:
            changed=True
            data['authorization_document'].write_text('search scope withdrawn\n',encoding='utf-8')
        return result
    monkeypatch.setattr(module,'_stable_read',withdraw_during_search)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    with pytest.raises(module.LocalWebError) as withdrawn:
        catalog.search('kb-arch','Real indexed knowledge',0,10)
    assert withdrawn.value.code=='local_authorization_changed'


def test_search_rechecks_owner_scope_for_non_page_documents_used_in_ranking(tmp_path,monkeypatch):
    data=fixture(tmp_path);extra=add_search_document(data);module=api()
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    baseline=catalog.search('kb-arch','Real indexed knowledge',0,1)
    assert baseline['total']==2
    non_page=next(path for path in (data['card_path'],extra) if path!=baseline['items'][0]['path'])
    original=module._stable_read;changed=False
    def withdraw_non_page_after_read(root,path):
        nonlocal changed
        result=original(root,path)
        if path==non_page and not changed:
            changed=True;withdraw_search_document(data,non_page)
        return result
    monkeypatch.setattr(module,'_stable_read',withdraw_non_page_after_read)
    with pytest.raises(module.LocalWebError) as withdrawn:
        catalog.search('kb-arch','Real indexed knowledge',0,1)
    assert changed and withdrawn.value.code=='local_authorization_changed'


def test_http_body_read_holds_policy_guard_through_response_send(tmp_path,monkeypatch):
    data=fixture(tmp_path); module=api(); policy=PolicyService(data['instance'],data['policy_root']); attempts=[]
    replacement={'policy_revision':2,'vault_id':'kb-arch','allow':['wiki/index.md',data['card_path']],
        'deny':[data['card_path']],'revoked':[],'channel':'web'}
    original_send=module._Handler._send
    def revoke_during_send(handler,status,payload,*,mime='application/json; charset=utf-8',headers=None):
        if status==200 and isinstance(payload,dict) and payload.get('path')==data['card_path']:
            try:
                before=policy.get('kb-arch','web')
                policy.save('kb-arch',replacement,authorized_target=before['metadata_path'],expected_source=before['source'],
                    reviewed_proposal_hash=proposal_hash(replacement,legacy=None),
                    review_ref='owner-request/revoke-before-response-send.md',legacy=None)
                attempts.append('committed')
            except module.PolicyError as error:
                attempts.append(error.code)
        return original_send(handler,status,payload,mime=mime,headers=headers)
    monkeypatch.setattr(module._Handler,'_send',revoke_during_send)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/read?vault_id=kb-arch&path='+data['card_path'])
    assert status==200 and json.loads(body)['source_sha256']==hashlib.sha256(data['card_bytes']).hexdigest()
    assert attempts==['policy_busy']


def test_http_search_holds_guard_for_every_ranked_document_through_response_send(tmp_path,monkeypatch):
    data=fixture(tmp_path);extra=add_search_document(data);module=api()
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    baseline=catalog.search('kb-arch','Real indexed knowledge',0,1)
    non_page=next(path for path in (data['card_path'],extra) if path!=baseline['items'][0]['path'])
    policy=PolicyService(data['instance'],data['policy_root']);attempts=[]
    replacement={'policy_revision':3,'vault_id':'kb-arch','allow':['wiki/index.md',data['card_path'],extra],
        'deny':[non_page],'revoked':[],'channel':'web'}
    original_send=module._Handler._send
    def revoke_during_send(handler,status,payload,*,mime='application/json; charset=utf-8',headers=None):
        if status==200 and isinstance(payload,dict) and payload.get('query')=='Real indexed knowledge':
            try:
                before=policy.get('kb-arch','web')
                policy.save('kb-arch',replacement,authorized_target=before['metadata_path'],expected_source=before['source'],
                    reviewed_proposal_hash=proposal_hash(replacement,legacy=None),
                    review_ref='owner-request/revoke-non-page-before-search-send.md',legacy=None)
                attempts.append('committed')
            except module.PolicyError as error:
                attempts.append(error.code)
        return original_send(handler,status,payload,mime=mime,headers=headers)
    monkeypatch.setattr(module._Handler,'_send',revoke_during_send)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/search?vault_id=kb-arch&q=Real%20indexed%20knowledge&limit=1')
    result=json.loads(body)
    assert status==200 and result['total']==2 and len(result['items'])==1
    assert attempts==['policy_busy']
    assert non_page not in body.decode('utf-8')


def test_http_search_rejects_revocation_between_scan_and_response_guard(tmp_path,monkeypatch):
    data=fixture(tmp_path);extra=add_search_document(data);module=api()
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    baseline=catalog.search('kb-arch','Real indexed knowledge',0,1)
    non_page=next(path for path in (data['card_path'],extra) if path!=baseline['items'][0]['path'])
    policy=PolicyService(data['instance'],data['policy_root'])
    replacement={'policy_revision':3,'vault_id':'kb-arch','allow':['wiki/index.md',data['card_path'],extra],
        'deny':[non_page],'revoked':[],'channel':'web'}
    original_search=module.NativeCatalog.search_with_delivery
    def revoke_after_scan(self,identity,query,offset,limit):
        result,scope=original_search(self,identity,query,offset,limit)
        if query=='Real indexed knowledge':
            before=policy.get('kb-arch','web')
            policy.save('kb-arch',replacement,authorized_target=before['metadata_path'],expected_source=before['source'],
                reviewed_proposal_hash=proposal_hash(replacement,legacy=None),
                review_ref='owner-request/revoke-non-page-after-search-scan.md',legacy=None)
        return result,scope
    monkeypatch.setattr(module.NativeCatalog,'search_with_delivery',revoke_after_scan)
    with running({'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/search?vault_id=kb-arch&q=Real%20indexed%20knowledge&limit=1')
    assert status==403 and json.loads(body)['error']['code']=='policy_denied'


def test_k06_revocation_serializes_with_an_admitted_body_read(tmp_path,monkeypatch):
    data=fixture(tmp_path); module=api(); policy=PolicyService(data['instance'],data['policy_root'])
    original=module._stable_read; attempts=[]; replacement={'policy_revision':2,'vault_id':'kb-arch',
        'allow':['wiki/index.md',data['card_path']],'deny':[data['card_path']],'revoked':[],'channel':'web'}
    def revoke_while_body_is_read(root,path):
        raw,text=original(root,path)
        if path==data['card_path'] and not attempts:
            attempts.append(True)
            with pytest.raises(module.PolicyError) as busy:
                policy.save('kb-arch',replacement,authorized_target=policy.get('kb-arch','web')['metadata_path'],
                    expected_source=policy.get('kb-arch','web')['source'],
                    reviewed_proposal_hash=proposal_hash(replacement,legacy=None),
                    review_ref='owner-request/revoke-during-read.md',legacy=None)
            assert busy.value.code=='policy_busy'
        return raw,text
    monkeypatch.setattr(module,'_stable_read',revoke_while_body_is_read)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    assert catalog._checked_read('kb-arch',data['card_path'])['source_sha256']==hashlib.sha256(data['card_bytes']).hexdigest()
    policy.save('kb-arch',replacement,authorized_target=policy.get('kb-arch','web')['metadata_path'],
        expected_source=policy.get('kb-arch','web')['source'],reviewed_proposal_hash=proposal_hash(replacement,legacy=None),
        review_ref='owner-request/revoke-after-read.md',legacy=None)
    with pytest.raises(module.LocalWebError) as denied:
        catalog._checked_read('kb-arch',data['card_path'])
    assert denied.value.code=='policy_denied'


def test_video_native_check_is_shipped_and_does_not_change_import_state(tmp_path):
    module=api()
    root=tmp_path/'video'; tools=root/'00-system/tools'; tools.mkdir(parents=True)
    before=list(sys.path)
    checker=module._video_integrity(root)
    assert checker is module.video_visibility.check_card
    assert sys.path==before


def test_video_integrity_does_not_execute_vault_python(tmp_path):
    module=api()
    root=tmp_path/'video'; tools=root/'00-system/tools'; tools.mkdir(parents=True)
    marker=tmp_path/'executed.txt'
    (tools/'vault_integrity.py').write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\ndef check_card(*args): return []\n",
        encoding='utf-8')
    module._video_integrity(root)
    assert not marker.exists()


def test_video_catalog_never_opens_a_denied_indexed_card(tmp_path, monkeypatch):
    data=fixture(tmp_path)
    card_path='wiki/cards/str/STR-LOCAL-001.md'
    index_text='- STR-LOCAL-001 | active | digest=sha256:'+'a'*64+' | source=SRC-1 | transaction=tx-1\n'
    (data['vault']/'wiki/index.md').write_text(index_text,encoding='utf-8')
    target=data['vault']/card_path; target.parent.mkdir(parents=True)
    target.write_text('PRIVATE DENIED CARD\n',encoding='utf-8')
    module=api(); config=json.loads(data['catalog_config'].read_text(encoding='utf-8'))
    config['vaults']['kb-arch']={'kind':'video-active','index':'wiki/index.md','content_roots':['wiki/cards']}
    data['catalog_config'].write_text(json.dumps(config),encoding='utf-8')
    policy=PolicyService(data['instance'],data['policy_root']); current=policy.get('kb-arch','web')
    document={'policy_revision':2,'vault_id':'kb-arch','allow':['wiki/index.md',card_path],
        'deny':[card_path],'revoked':[],'channel':'web'}
    policy.save('kb-arch',document,authorized_target=current['metadata_path'],expected_source=current['source'],
        reviewed_proposal_hash=proposal_hash(document,legacy=None),review_ref='owner-request/real-vault-web.md',legacy=None)
    doc=data['authorization_document']; doc_hash=hashlib.sha256(doc.read_bytes()).hexdigest()
    data['authorization_path'].write_text(json.dumps({'schema_version':'local-vault-read-1',
        'authorization_ref':'owner-request/real-vault-web.md','authorization_sha256':doc_hash,
        'authorization_document_path':str(doc.resolve()),'bindings':{'kb-arch':1},'entries':{'kb-arch':{
            'wiki/index.md':hashlib.sha256((data['vault']/'wiki/index.md').read_bytes()).hexdigest(),
            card_path:hashlib.sha256(target.read_bytes()).hexdigest()}}}),encoding='utf-8')
    opened=[]; original=module._stable_read
    def track(root,path):
        opened.append(path)
        return original(root,path)
    monkeypatch.setattr(module,'_stable_read',track)
    monkeypatch.setattr(module,'_video_check_card',lambda *_: pytest.fail('denied card reached native checker'))
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    result=catalog.vaults()
    assert result['vaults'][0]['status']=='online'
    assert result['vaults'][0]['asset_count'] is None
    assert result['vaults'][0]['catalog_entry_count']==1
    assert card_path not in opened
    opened.clear()
    page=catalog.catalog('kb-arch',0,10)
    assert page['items']==[{'path':card_path,'status':'restricted','reason':'policy_denied'}]
    assert card_path not in opened
    with pytest.raises(module.LocalWebError) as denied_read:
        catalog._checked_read('kb-arch',card_path)
    assert denied_read.value.code=='policy_denied'
    assert card_path not in opened


def test_inspiration_catalog_never_opens_a_denied_indexed_card(tmp_path, monkeypatch):
    data=fixture(tmp_path)
    card_path='30-cards/prj/PRJ-001.md'; (data['vault']/'30-cards/prj').mkdir(parents=True)
    index_path=data['vault']/'wiki/index.md'; index_path.write_text('| [[PRJ-001]] | 1.0.0 | sha256:0123456789abcdef |\n',encoding='utf-8')
    target=data['vault']/card_path; target.write_text('PRIVATE DENIED CARD\n',encoding='utf-8')
    descriptor=data['vault']/'descriptor.json'; descriptor.write_text('{}',encoding='utf-8')
    module=api(); config=json.loads(data['catalog_config'].read_text(encoding='utf-8'))
    config['vaults']['kb-arch']={'kind':'inspiration-active','descriptor_path':str(descriptor)}
    data['catalog_config'].write_text(json.dumps(config),encoding='utf-8')
    policy=PolicyService(data['instance'],data['policy_root']); current=policy.get('kb-arch','web')
    document={'policy_revision':2,'vault_id':'kb-arch','allow':['wiki/index.md',card_path],
        'deny':[card_path],'revoked':[],'channel':'web'}
    policy.save('kb-arch',document,authorized_target=current['metadata_path'],expected_source=current['source'],
        reviewed_proposal_hash=proposal_hash(document,legacy=None),review_ref='owner-request/real-vault-web.md',legacy=None)
    doc=data['authorization_document']; doc_hash=hashlib.sha256(doc.read_bytes()).hexdigest()
    data['authorization_path'].write_text(json.dumps({'schema_version':'local-vault-read-1',
        'authorization_ref':'owner-request/real-vault-web.md','authorization_sha256':doc_hash,
        'authorization_document_path':str(doc.resolve()),'bindings':{'kb-arch':1},'entries':{'kb-arch':{
            'wiki/index.md':hashlib.sha256(index_path.read_bytes()).hexdigest(),
            card_path:hashlib.sha256(target.read_bytes()).hexdigest()}}}),encoding='utf-8')
    monkeypatch.setattr(module._inspiration_visibility,'enabled',lambda _descriptor:True)
    monkeypatch.setattr(module._source_reader,'configuration',lambda _descriptor:None)
    monkeypatch.setattr(module._inspiration_visibility,'published',lambda _root,_text=None:{'PRJ-001':('1.0.0','sha256:0123456789abcdef')})
    checked=[]; monkeypatch.setattr(module._inspiration_visibility,'check_card',lambda *_:checked.append(True))
    opened=[]; original=module._stable_read
    def track(root,path):
        opened.append(path)
        return original(root,path)
    monkeypatch.setattr(module,'_stable_read',track)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    result=catalog.vaults()
    assert result['vaults'][0]['status']=='online'
    assert result['vaults'][0]['asset_count']==1
    assert card_path not in opened and not checked
    page=catalog.catalog('kb-arch',0,10)
    assert page['items'][0]['status']=='restricted' and page['items'][0]['reason']=='policy_denied'


def inspiration_fixture(data, *, blocked_paths=()):
    module=api()
    card_path='30-cards/prj/PRJ-001.md'
    body='# Published project\n\nBLOCKED_UNIQUE_NEEDLE\n'
    digest='sha256:'+hashlib.sha256(body.encode('utf-8')).hexdigest()[:16]
    card=(f'---\nid: PRJ-001\ntype: PRJ\nstatus: active\nversion: 1.0.0\ndigest: {digest}\n---\n{body}')
    target=data['vault']/card_path; target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(card,encoding='utf-8',newline='\n')
    index_path=data['vault']/'wiki/index.md'
    index_path.write_text(f'| [[PRJ-001]] | 1.0.0 | {digest} |\n',encoding='utf-8',newline='\n')
    descriptor={"extensions":{
        "workspace_visibility":{"adapter_id":module._inspiration_visibility.ADAPTER_ID},
        "workspace_source_reader":{"adapter_id":module._source_reader.ADAPTER_ID,
            "manifest_ref":"sources/accepted-manifest.json","manifest_sha256":"a"*64,
            "blocked_read_paths":list(blocked_paths)}}}
    descriptor_path=data['vault']/'descriptor.json'
    descriptor_path.write_text(json.dumps(descriptor),encoding='utf-8')
    config=json.loads(data['catalog_config'].read_text(encoding='utf-8'))
    config['vaults']['kb-arch']={'kind':'inspiration-active','descriptor_path':str(descriptor_path)}
    data['catalog_config'].write_text(json.dumps(config),encoding='utf-8')
    transactions=data['vault']/'.transactions'; transactions.mkdir(exist_ok=True)
    (transactions/'.gitkeep').write_bytes(b'')
    policy=PolicyService(data['instance'],data['policy_root']); current=policy.get('kb-arch','web')
    document={'policy_revision':2,'vault_id':'kb-arch','allow':['wiki/index.md',card_path],
        'deny':[],'revoked':[],'channel':'web'}
    policy.save('kb-arch',document,authorized_target=current['metadata_path'],expected_source=current['source'],
        reviewed_proposal_hash=proposal_hash(document,legacy=None),review_ref='owner-request/real-vault-web.md',legacy=None)
    auth=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    auth['entries']['kb-arch'].update({'wiki/index.md':hashlib.sha256(index_path.read_bytes()).hexdigest(),
        card_path:hashlib.sha256(target.read_bytes()).hexdigest()})
    data['authorization_path'].write_text(json.dumps(auth),encoding='utf-8')
    return module,card_path,target,index_path


def test_inspiration_catalog_uses_one_shared_batch_guard_per_page(tmp_path,monkeypatch):
    data=fixture(tmp_path)
    module,card_path,_,_=inspiration_fixture(data)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    index_calls=[]; guard_calls=[]
    original_authorized=catalog._authorized_native_call
    original_guard=catalog.policy.guard_many
    def observe_authorized(identity,root,path,callback):
        index_calls.append(path)
        return original_authorized(identity,root,path,callback)
    def observe_guard(identity,resources,channel,**kwargs):
        guard_calls.append((identity,tuple(resources),channel,kwargs))
        return original_guard(identity,resources,channel,**kwargs)
    monkeypatch.setattr(catalog,'_authorized_native_call',observe_authorized)
    monkeypatch.setattr(catalog.policy,'guard_many',observe_guard)
    page=catalog.catalog('kb-arch',0,30)
    assert page['total']==1 and page['items']==[{'name':'PRJ-001','path':card_path,'status':'in_scope'}]
    assert index_calls==['wiki/index.md']
    assert guard_calls==[('kb-arch',('30-cards/prj/PRJ-001.md','wiki/index.md'),'web',{'read_authorized':True})]


def test_inspiration_descriptor_block_excludes_card_from_catalog_search_and_read(tmp_path,monkeypatch):
    data=fixture(tmp_path)
    module,card_path,_,_=inspiration_fixture(data,blocked_paths=['30-cards/prj/PRJ-001.md'])
    opened=[]; original=module._stable_read
    def track(root,path):
        opened.append(path)
        return original(root,path)
    monkeypatch.setattr(module,'_stable_read',track)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])

    page=catalog.catalog('kb-arch',0,10)
    assert page['items']==[{'path':card_path,'status':'restricted','reason':'local_source_read_blocked'}]
    assert card_path not in opened

    opened.clear()
    result=catalog.search('kb-arch','BLOCKED_UNIQUE_NEEDLE',0,10)
    assert result['items']==[] and result['total']==0
    assert card_path not in opened

    opened.clear()
    with pytest.raises(module.LocalWebError) as blocked:
        catalog._checked_read('kb-arch',card_path)
    assert blocked.value.code=='local_source_read_blocked'
    assert card_path not in opened

    with running({'instance':data['instance'],'policy_root':data['policy_root'],
                  'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/read?vault_id=kb-arch&path='+card_path)
    assert status==403 and json.loads(body)['error']['code']=='local_source_read_blocked'
    assert card_path not in opened


def test_inspiration_search_response_hides_descriptor_blocked_path_and_counts(tmp_path):
    data=fixture(tmp_path)
    _,card_path,_,_=inspiration_fixture(data,blocked_paths=['30-cards/prj/PRJ-001.md'])
    with running({'instance':data['instance'],'policy_root':data['policy_root'],
                  'catalog_config':data['catalog_config'],'authorization_path':data['authorization_path']}) as port:
        status,_,body=get(port,'/api/search?vault_id=kb-arch&q=BLOCKED_UNIQUE_NEEDLE')
    result=json.loads(body)
    assert status==200 and result['items']==[] and result['total']==0
    assert card_path not in body.decode('utf-8')
    assert not {'restricted_count','native_entry_count','issues','search_bytes','scanned_count','scan_complete'} & result.keys()


@pytest.mark.parametrize('mutation',('pending-transaction','index-removal'))
def test_inspiration_read_rechecks_publication_before_returning_body(tmp_path,monkeypatch,mutation):
    data=fixture(tmp_path)
    module,card_path,target,index_path=inspiration_fixture(data)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    original=catalog._authorized_native_call; changed=False
    def change_after_initial_index_check(identity,root,path,callback):
        nonlocal changed
        if path==card_path and not changed:
            changed=True
            if mutation=='pending-transaction':
                pending=data['vault']/'.transactions'/'pending.json'
                pending.write_text('{"phase":"unknown"}',encoding='utf-8')
            else:
                index_path.write_text('<!-- published card removed -->\n',encoding='utf-8',newline='\n')
        return original(identity,root,path,callback)
    monkeypatch.setattr(catalog,'_authorized_native_call',change_after_initial_index_check)

    with pytest.raises(module.LocalWebError) as changed_publication:
        catalog._checked_read('kb-arch',card_path)
    assert changed
    assert changed_publication.value.code in {
        'native_publication_blocked','local_source_changed_review_required','policy_authority_invalid'}


def test_inspiration_search_fails_closed_if_transaction_starts_after_card_read(tmp_path,monkeypatch):
    data=fixture(tmp_path)
    module,card_path,_,_=inspiration_fixture(data)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    original=module._stable_read; changed=False
    def start_transaction_after_card_read(root,path):
        nonlocal changed
        result=original(root,path)
        if path==card_path and not changed:
            changed=True
            (data['vault']/'.transactions'/'pending.json').write_text('{"phase":"unknown"}',encoding='utf-8')
        return result
    monkeypatch.setattr(module,'_stable_read',start_transaction_after_card_read)

    with pytest.raises(module.LocalWebError) as changed_publication:
        catalog.search('kb-arch','BLOCKED_UNIQUE_NEEDLE',0,10)
    assert changed
    assert changed_publication.value.code in {'native_publication_blocked','policy_authority_invalid'}


def test_inspiration_search_rechecks_descriptor_blocks_before_returning_results(tmp_path,monkeypatch):
    data=fixture(tmp_path)
    module,card_path,_,_=inspiration_fixture(data)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    descriptor_path=data['vault']/'descriptor.json'
    original=module._stable_read; changed=False
    def add_block_after_card_read(root,path):
        nonlocal changed
        result=original(root,path)
        if path==card_path and not changed:
            changed=True
            descriptor=json.loads(descriptor_path.read_text(encoding='utf-8'))
            descriptor['extensions']['workspace_source_reader']['blocked_read_paths']=[card_path]
            descriptor_path.write_text(json.dumps(descriptor),encoding='utf-8')
        return result
    monkeypatch.setattr(module,'_stable_read',add_block_after_card_read)

    with pytest.raises(module.LocalWebError) as changed_authority:
        catalog.search('kb-arch','BLOCKED_UNIQUE_NEEDLE',0,10)
    assert changed
    assert changed_authority.value.code in {'local_source_read_blocked','local_source_changed_review_required'}


def test_inspiration_catalog_rechecks_descriptor_blocks_before_returning_items(tmp_path,monkeypatch):
    data=fixture(tmp_path)
    module,card_path,_,_=inspiration_fixture(data)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    descriptor_path=data['vault']/'descriptor.json'
    original=module._stable_read; changed=False
    def add_block_after_card_read(root,path):
        nonlocal changed
        result=original(root,path)
        if path==card_path and not changed:
            changed=True
            descriptor=json.loads(descriptor_path.read_text(encoding='utf-8'))
            descriptor['extensions']['workspace_source_reader']['blocked_read_paths']=[card_path]
            descriptor_path.write_text(json.dumps(descriptor),encoding='utf-8')
        return result
    monkeypatch.setattr(module,'_stable_read',add_block_after_card_read)

    page=catalog.catalog('kb-arch',0,10)
    assert changed
    assert page['items']==[{'path':card_path,'status':'restricted','reason':'local_source_read_blocked'}]


def test_inspiration_catalog_rejects_card_changed_during_publication_check(tmp_path, monkeypatch):
    data=fixture(tmp_path)
    module=api()
    card_path='30-cards/prj/PRJ-001.md'; target=data['vault']/card_path
    target.parent.mkdir(parents=True)
    body='# A published project\n'
    digest='sha256:'+hashlib.sha256(body.encode()).hexdigest()[:16]
    card=f'---\nid: PRJ-001\ntype: PRJ\nstatus: active\nversion: 1.0.0\ndigest: {digest}\n---\n{body}'
    index_path=data['vault']/'wiki/index.md'
    index_path.write_text(f'| [[PRJ-001]] | 1.0.0 | {digest} |\n',encoding='utf-8',newline='\n')
    target.write_text(card,encoding='utf-8',newline='\n')
    descriptor=data['vault']/'descriptor.json'; descriptor.write_text('{}',encoding='utf-8')
    config=json.loads(data['catalog_config'].read_text(encoding='utf-8'))
    config['vaults']['kb-arch']={'kind':'inspiration-active','descriptor_path':str(descriptor)}
    data['catalog_config'].write_text(json.dumps(config),encoding='utf-8')
    policy=PolicyService(data['instance'],data['policy_root']); current=policy.get('kb-arch','web')
    document={'policy_revision':2,'vault_id':'kb-arch','allow':['wiki/index.md',card_path],
        'deny':[],'revoked':[],'channel':'web'}
    policy.save('kb-arch',document,authorized_target=current['metadata_path'],expected_source=current['source'],
        reviewed_proposal_hash=proposal_hash(document,legacy=None),review_ref='owner-request/real-vault-web.md',legacy=None)
    auth=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    auth['entries']['kb-arch'].update({
        'wiki/index.md':hashlib.sha256(index_path.read_bytes()).hexdigest(),
        card_path:hashlib.sha256(target.read_bytes()).hexdigest()})
    data['authorization_path'].write_text(json.dumps(auth),encoding='utf-8')
    monkeypatch.setattr(module._inspiration_visibility,'enabled',lambda _descriptor:True)
    monkeypatch.setattr(module._source_reader,'configuration',lambda _descriptor:None)
    checked_texts=[]; original_check=module._inspiration_visibility.check_card
    def observe_check(*args):
        checked_texts.append(args[3])
        return original_check(*args)
    monkeypatch.setattr(module._inspiration_visibility,'check_card',observe_check)
    opened=[]; original=module._stable_read; changed=False
    def change_after_capture(root,path):
        nonlocal changed
        result=original(root,path)
        opened.append(path)
        if path==card_path and not changed:
            changed=True
            target.write_text(card.replace('status: active','status: candidate'),encoding='utf-8',newline='\n')
        return result
    monkeypatch.setattr(module,'_stable_read',change_after_capture)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    page=catalog.catalog('kb-arch',0,10)
    assert checked_texts==[card,card]
    assert page['items'][0]['status']=='restricted'
    assert page['items'][0]['reason']=='local_source_changed_review_required'
    assert card_path in opened


def test_video_shipped_gate_accepts_a_current_receipt_and_rejects_inactive_card():
    module=api(); card_id='STR-LOCAL-001'; path=f'wiki/cards/str/{card_id}.md'
    projection={'card_id':card_id,'status':'active','version':'1.0.0','summary':'fixture'}
    digest='sha256:'+hashlib.sha256(json.dumps(projection,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()
    projection={**projection,'payload_digest':digest}
    transaction='tx-local-1'; source_id='SRC-LOCAL-1'; receipt_id='receipt-local-1'
    note=('---\ncard_id: STR-LOCAL-001\nstatus: active\nversion: 1.0.0\ntransaction_id: tx-local-1\n'
          f'source_record_id: SRC-LOCAL-1\npayload_digest: {digest}\n---\n# Local fixture\n\n```json\n'
          +json.dumps(projection,ensure_ascii=False)+'\n```\n')
    data={
        path:note,
        'wiki/index.md':f'- {card_id} | active | digest={digest} | source={source_id} | transaction={transaction}\n',
        '00-system/registries/cards.md':f'| {card_id} | 1.0.0 | active | {path} | 2026-10-10 |\n',
        'wiki/log.md':f'| promote_active | {card_id} (transaction={transaction}) |\n',
        f'.transactions/committed/{transaction}.json':json.dumps({'status':'COMMITTED','transaction_id':transaction,
            'source_content_sha256':'a'*64,'cards':[{'card_id':card_id,'payload_digest':digest,'version':'1.0.0',
                'path':path,'receipt_id':receipt_id}]}),
        f'sources/{source_id}.json':json.dumps({'source_id':source_id,'status':'verified','content_sha256':'a'*64}),
        f'wiki/cards/str/{card_id}.mg_receipt.json':json.dumps({'schema_version':'1','receipt_id':receipt_id,
            'card_id':card_id,'payload_digest':digest,'producer':'test','timestamp':'2026-10-10T00:00:00Z',
            'gates':{f'MG{i:02d}':'PASS' for i in range(1,10)}}),
    }
    read_text=data.__getitem__
    assert module.video_visibility.check_card(card_id,read_text)==[]
    data[path]=note.replace('status: active','status: candidate',1)
    assert 'note_not_active' in module.video_visibility.check_card(card_id,read_text)


def test_video_authorization_pins_native_verification_inputs_and_preserves_denies(tmp_path,monkeypatch):
    module=api()
    data=fixture(tmp_path)
    card_path='wiki/cards/str/STR-LOCAL-001.md'
    card='---\ncard_id: STR-LOCAL-001\nstatus: active\nversion: 1.0.0\ntransaction_id: tx-1\nsource_record_id: SRC-1\n---\n# card\n'
    index=data['vault']/'wiki/index.md'
    index.write_text('- STR-LOCAL-001 | active | digest=sha256:'+'a'*64+' | source=SRC-1 | transaction=tx-1\n',encoding='utf-8')
    target=data['vault']/card_path; target.parent.mkdir(parents=True); target.write_text(card,encoding='utf-8')
    (data['vault']/'00-system/registries').mkdir(parents=True)
    (data['vault']/'00-system/registries/cards.md').write_text('registry\n',encoding='utf-8')
    (data['vault']/'wiki/log.md').write_text('log\n',encoding='utf-8')
    (data['vault']/'.transactions/committed').mkdir(parents=True)
    (data['vault']/'.transactions/committed/tx-1.json').write_text('{}',encoding='utf-8')
    (data['vault']/'sources').mkdir()
    (data['vault']/'sources/SRC-1.json').write_text('{}',encoding='utf-8')
    (target.with_suffix('.mg_receipt.json')).write_text('{}',encoding='utf-8')
    config={'vaults':{'kb-arch':{'kind':'video-active','index':'wiki/index.md','content_roots':['wiki/cards']}}}
    data['catalog_config'].write_text(json.dumps(config),encoding='utf-8')
    policy=PolicyService(data['instance'],data['policy_root']); current=policy.get('kb-arch','web')
    document={'policy_revision':2,'vault_id':'kb-arch','allow':['wiki/index.md',data['card_path']],
        'deny':['wiki/blocked.md'],'revoked':[],'channel':'web'}
    policy.save('kb-arch',document,authorized_target=current['metadata_path'],expected_source=current['source'],
        reviewed_proposal_hash=proposal_hash(document,legacy=None),review_ref='owner-request/real-vault-web.md',legacy=None)
    from kb_core.local_vault_web import authorize_current_scope
    result=authorize_current_scope(instance=data['instance'],policy_root=data['policy_root'],catalog_config=data['catalog_config'],
        authorization_path=data['authorization_path'],authorization_document=data['authorization_document'],
        authorization_ref='owner-request/real-vault-web.md',vault_id='kb-arch')
    manifest=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    checked=manifest['entries']['kb-arch']
    for path in ('00-system/registries/cards.md','wiki/log.md','.transactions/committed/tx-1.json',
                 'sources/SRC-1.json','wiki/cards/str/STR-LOCAL-001.mg_receipt.json'):
        assert path in checked
    current=policy.get('kb-arch','web')['policy']
    assert current['deny']==['wiki/blocked.md']
    assert '00-system/registries/cards.md' in current['allow']
    assert result['content_counts']['kb-arch']==1
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    log_path=data['vault']/'wiki/log.md'
    monkeypatch.setattr(module,'_video_check_card',lambda *_:[])
    assert catalog._video_issues('kb-arch',data['vault'],card_path)==[]
    def mutate_shared_evidence(*_):
        log_path.write_text('concurrent changed promotion log\n',encoding='utf-8')
        return []
    monkeypatch.setattr(module,'_video_check_card',mutate_shared_evidence)
    with pytest.raises(module.LocalWebError) as changed_dependency:
        catalog._video_issues('kb-arch',data['vault'],card_path)
    assert changed_dependency.value.code=='local_source_changed_review_required'


def test_video_integrity_does_not_open_authorized_but_k06_denied_support_file(tmp_path,monkeypatch):
    module=api(); data=fixture(tmp_path)
    card_path='wiki/cards/str/STR-LOCAL-001.md'
    card='---\ncard_id: STR-LOCAL-001\nstatus: active\nversion: 1.0.0\ntransaction_id: tx-1\nsource_record_id: SRC-1\n---\n# local\n'
    index=data['vault']/'wiki/index.md'
    index.write_text('- STR-LOCAL-001 | active | digest=sha256:'+'a'*64+' | source=SRC-1 | transaction=tx-1\n',encoding='utf-8')
    target=data['vault']/card_path; target.parent.mkdir(parents=True); target.write_text(card,encoding='utf-8')
    files={
        '00-system/registries/cards.md':'registry\n',
        'wiki/log.md':'promotion log\n',
        '.transactions/committed/tx-1.json':'{}',
        'sources/SRC-1.json':'{}',
        'wiki/cards/str/STR-LOCAL-001.mg_receipt.json':'{}',
    }
    for relative,content in files.items():
        path=data['vault']/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content,encoding='utf-8')
    data['catalog_config'].write_text(json.dumps({'vaults':{'kb-arch':{
        'kind':'video-active','index':'wiki/index.md','content_roots':['wiki/cards']}}}),encoding='utf-8')
    policy=PolicyService(data['instance'],data['policy_root']); current=policy.get('kb-arch','web')
    document={'policy_revision':2,'vault_id':'kb-arch','allow':['wiki/index.md',card_path],
        'deny':[],'revoked':[],'channel':'web'}
    policy.save('kb-arch',document,authorized_target=current['metadata_path'],expected_source=current['source'],
        reviewed_proposal_hash=proposal_hash(document,legacy=None),review_ref='owner-request/real-vault-web.md',legacy=None)
    from kb_core.local_vault_web import authorize_current_scope
    authorize_current_scope(instance=data['instance'],policy_root=data['policy_root'],catalog_config=data['catalog_config'],
        authorization_path=data['authorization_path'],authorization_document=data['authorization_document'],
        authorization_ref='owner-request/real-vault-web.md',vault_id='kb-arch')
    manifest=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    assert 'wiki/log.md' in manifest['entries']['kb-arch']
    current=policy.get('kb-arch','web'); policy_doc=current['policy']
    denied_policy={**policy_doc,'policy_revision':policy_doc['policy_revision']+1,
        'allow':[path for path in policy_doc['allow'] if path!='wiki/log.md'],'deny':['wiki/log.md']}
    policy.save('kb-arch',denied_policy,authorized_target=current['metadata_path'],expected_source=current['source'],
        reviewed_proposal_hash=proposal_hash(denied_policy,legacy=None),review_ref='owner-request/real-vault-web.md',
        legacy=current['legacy_constraints'] if current['legacy_constraints']['source_ref'] else None)
    opened=[]; stable_read=module._stable_read
    def track(root,path):
        opened.append(path)
        return stable_read(root,path)
    monkeypatch.setattr(module,'_stable_read',track)
    monkeypatch.setattr(module,'_video_check_card',lambda *_:pytest.fail('integrity checker must not receive a denied dependency'))
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    with pytest.raises(module.LocalWebError) as denied_dependency:
        catalog._video_issues('kb-arch',data['vault'],card_path)
    assert denied_dependency.value.code=='native_integrity_support_restricted'
    assert opened==[card_path]


def test_large_vault_uses_bounded_k06_batches_and_exact_changed_file_reauthorization(tmp_path):
    data=fixture(tmp_path)
    cards=[f'wiki/frameworks/card-{number:03}.md' for number in range(300)]
    for path in cards:
        target=data['vault']/path; target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(f'# {target.stem}\nOriginal body.\n',encoding='utf-8')
    (data['vault']/'wiki/index.md').write_text(
        ''.join(f'[[frameworks/{Path(path).stem}]]\n' for path in cards),encoding='utf-8')
    from kb_core.local_vault_web import authorize_current_scope
    kwargs={'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],
        'authorization_path':data['authorization_path'],'authorization_document':data['authorization_document'],
        'authorization_ref':'owner-request/real-vault-web.md','vault_id':'kb-arch'}
    first=authorize_current_scope(**kwargs,offset=0,limit=255)
    policy=PolicyService(data['instance'],data['policy_root'])
    assert first['catalog_entry_count']==300 and first['authorized_scope_count']==255
    assert first['manifest_path_count']==256
    assert len(policy.get('kb-arch','web')['policy']['allow'])==256
    second=authorize_current_scope(**kwargs,offset=255,limit=45)
    assert second['authorized_scope_count']==45 and second['authorized_content_count']==45
    assert second['manifest_path_count']==46
    current_policy=policy.get('kb-arch','web')['policy']
    assert len(current_policy['allow'])==46
    manifest=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    assert set(manifest['entries']['kb-arch'])=={'wiki/index.md',*cards[255:]}
    catalog=api().NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    with pytest.raises(api().LocalWebError) as old_batch:
        catalog._checked_read('kb-arch',cards[0])
    assert old_batch.value.code=='local_read_not_authorized'
    target=data['vault']/cards[255]
    before=dict(manifest['entries']['kb-arch'])
    target.write_text('# Updated card\nOwner reviewed this exact path.\n',encoding='utf-8')
    with pytest.raises(api().LocalWebError) as stale:
        catalog._checked_read('kb-arch',cards[255])
    assert stale.value.code=='local_source_changed_review_required'
    refreshed=authorize_current_scope(**kwargs,path=cards[255])
    assert refreshed['reauthorized_paths']==[cards[255]]
    manifest=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    after=manifest['entries']['kb-arch']
    assert after['wiki/index.md']==before['wiki/index.md']
    assert after[cards[255]]==hashlib.sha256(target.read_bytes()).hexdigest()
    assert all(after[path]==digest for path,digest in before.items() if path!=cards[255])
    assert 'Owner reviewed this exact path.' in catalog._checked_read('kb-arch',cards[255])['text']


def test_http_search_and_read_converge_after_exact_file_authorization_refresh(tmp_path):
    data=fixture(tmp_path)
    from kb_core.contracts import LayerResult
    from kb_core.writer import Authorization, LocalWriter
    kwargs={'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],
        'authorization_path':data['authorization_path'],'authorization_document':data['authorization_document'],
        'authorization_ref':'owner-request/real-vault-web.md','vault_id':'kb-arch'}
    target=data['vault']/data['card_path']
    updated=b'---\nid: F-C06-001\ntitle: mem0 memory layer\n---\n# mem0\nOwner-reviewed refresh phrase.\n'
    with running({key:kwargs[key] for key in ('instance','policy_root','catalog_config','authorization_path')}) as port:
        coordinator=Coordinator(data['instance']); evidence=tmp_path/'writer-evidence'; evidence.mkdir()
        writer=LocalWriter(coordinator.members,coordinator.bindings,'vault②',
            authorization=Authorization('kb-arch','kb-arch-local','native',True),evidence_root=evidence)
        before=target.read_bytes()
        writer.write(data['card_path'],updated,expected_hash=hashlib.sha256(before).hexdigest())
        native_check=evidence/'checks/validation.md';native_check.parent.mkdir()
        assert updated.startswith(b'---\nid: F-C06-001') and b'Owner-reviewed refresh phrase.' in updated
        native_check.write_text('Isolated card metadata and content check passed.\n',encoding='utf-8')
        writer_receipt=writer.complete(
            domain_result=LayerResult(status='succeeded',evidence_refs=['checks/validation.md']),
            domain_sources={data['card_path']:hashlib.sha256(updated).hexdigest()})
        assert writer_receipt.domain_result.status=='succeeded'
        status,_,body=get(port,'/api/search?vault_id=kb-arch&q=Owner-reviewed%20refresh%20phrase')
        result=json.loads(body)
        assert status==200 and result['items']==[] and result['total']==0
        assert not {'restricted_count','native_entry_count','issues','search_bytes','scanned_count','scan_complete'} & result.keys()
        refreshed=api().authorize_current_scope(**kwargs,path=data['card_path'])
        assert refreshed['reauthorized_paths']==[data['card_path']]
        status,_,body=get(port,'/api/search?vault_id=kb-arch&q=Owner-reviewed%20refresh%20phrase')
        result=json.loads(body)
        assert status==200 and result['total']==1 and result['items'][0]['path']==data['card_path']
        status,_,body=get(port,'/api/read?vault_id=kb-arch&path='+data['card_path'])
        result=json.loads(body)
    assert status==200 and result['source_sha256']==hashlib.sha256(updated).hexdigest()
    assert 'Owner-reviewed refresh phrase.' in result['text']


def test_pending_authorization_changes_separates_index_and_new_card_for_individual_review(tmp_path):
    data=fixture(tmp_path)
    module=api()
    existing=data['vault']/data['card_path']
    new_path='wiki/frameworks/F-C06-002-new.md'
    new_card=data['vault']/new_path
    index=data['vault']/'wiki/index.md'
    old_card=existing.read_bytes(); old_index=index.read_bytes()
    updated_card=old_card+b'Changed after owner authorization.\n'
    new_bytes=b'# New card\nNot authorized until individually approved.\n'
    updated_index=old_index+b'- [[frameworks/F-C06-002-new|new]]\n'
    from kb_core.contracts import LayerResult
    from kb_core.writer import Authorization, LocalWriter
    coordinator=Coordinator(data['instance']); evidence=tmp_path/'native-writer-evidence'; evidence.mkdir()
    writer=LocalWriter(coordinator.members,coordinator.bindings,'vault②',
        authorization=Authorization('kb-arch','kb-arch-local','native',True),evidence_root=evidence)
    writer.write(data['card_path'],updated_card,expected_hash=hashlib.sha256(old_card).hexdigest())
    writer.write(new_path,new_bytes)
    writer.write('wiki/index.md',updated_index,expected_hash=hashlib.sha256(old_index).hexdigest())
    evidence_file=evidence/'checks/native-index-validation.md'; evidence_file.parent.mkdir()
    assert b'F-C06-002-new' in updated_index and b'Changed after owner authorization.' in updated_card
    evidence_file.write_text('Isolated native index/card validation passed.\n',encoding='utf-8')
    sources={data['card_path']:hashlib.sha256(updated_card).hexdigest(),
             new_path:hashlib.sha256(new_bytes).hexdigest(),
             'wiki/index.md':hashlib.sha256(updated_index).hexdigest()}
    receipt=writer.complete(domain_result=LayerResult(status='succeeded',evidence_refs=['checks/native-index-validation.md']),
                            domain_sources=sources)
    assert receipt.domain_result.status=='succeeded' and receipt.system_result.status=='succeeded'

    changes=module.pending_authorization_changes(
        instance=data['instance'],policy_root=data['policy_root'],catalog_config=data['catalog_config'],
        authorization_path=data['authorization_path'],vault_id='kb-arch')

    by_path={item['path']:item for item in changes}
    assert set(by_path)=={'wiki/index.md',data['card_path'],new_path}
    assert by_path['wiki/index.md']['native_state']=='native-index'
    assert by_path[new_path]['native_state']=='active'
    assert by_path[new_path]['previous_sha256'] is None
    assert by_path[data['card_path']]['previous_sha256']==hashlib.sha256(data['card_bytes']).hexdigest()
    assert by_path[new_path]['current_sha256']==hashlib.sha256(new_bytes).hexdigest()


def test_exact_reauthorization_refuses_a_file_that_changed_after_review(tmp_path):
    data=fixture(tmp_path)
    module=api()
    target=data['vault']/data['card_path']
    before=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    reviewed=b'# mem0\nReviewed candidate bytes.\n'
    target.write_bytes(reviewed)
    kwargs={'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],
        'authorization_path':data['authorization_path'],'authorization_document':data['authorization_document'],
        'authorization_ref':'owner-request/real-vault-web.md','vault_id':'kb-arch','path':data['card_path']}
    with pytest.raises(module.LocalWebError) as changed:
        module.authorize_current_scope(**kwargs,expected_sha256='0'*64)
    assert changed.value.code=='local_source_changed_review_required'
    after=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    assert after==before
    authorized=module.authorize_current_scope(**kwargs,expected_sha256=hashlib.sha256(reviewed).hexdigest())
    assert authorized['reauthorized_paths']==[data['card_path']]
    after=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    assert after['entries']['kb-arch'][data['card_path']]==hashlib.sha256(reviewed).hexdigest()


def test_new_native_card_stays_hidden_until_its_exact_file_is_reviewed(tmp_path):
    data=fixture(tmp_path)
    module=api()
    new_path='wiki/frameworks/F-C06-002-new.md'
    new_bytes=b'---\nid: F-C06-002\ntitle: isolated owner-approved new card\n---\n# New indexed card\nUnique review phrase.\n'
    index=data['vault']/'wiki/index.md'
    old_index=index.read_bytes()
    updated_index=old_index+b'- [[frameworks/F-C06-002-new|isolated new card]]\n'
    from kb_core.contracts import LayerResult
    from kb_core.writer import Authorization, LocalWriter
    coordinator=Coordinator(data['instance']); evidence=tmp_path/'native-writer-evidence'; evidence.mkdir()
    writer=LocalWriter(coordinator.members,coordinator.bindings,'vault②',
        authorization=Authorization('kb-arch','kb-arch-local','native',True),evidence_root=evidence)
    writer.write(new_path,new_bytes)
    writer.write('wiki/index.md',updated_index,expected_hash=hashlib.sha256(old_index).hexdigest())
    validation=evidence/'checks/native-index-validation.md'; validation.parent.mkdir()
    validation.write_text('Isolated native writer, index and card checks passed.\n',encoding='utf-8')
    receipt=writer.complete(domain_result=LayerResult(status='succeeded',evidence_refs=['checks/native-index-validation.md']),
        domain_sources={new_path:hashlib.sha256(new_bytes).hexdigest(),
                        'wiki/index.md':hashlib.sha256(updated_index).hexdigest()})
    assert receipt.domain_result.status=='succeeded' and receipt.system_result.status=='succeeded'

    kwargs={'instance':data['instance'],'policy_root':data['policy_root'],'catalog_config':data['catalog_config'],
        'authorization_path':data['authorization_path'],'authorization_document':data['authorization_document'],
        'authorization_ref':'owner-request/real-vault-web.md','vault_id':'kb-arch'}
    with running({key:kwargs[key] for key in ('instance','policy_root','catalog_config','authorization_path')}) as port:
        status,_,_=get(port,'/api/catalog?vault_id=kb-arch&offset=0&limit=30')
        assert status==409  # changed index cannot silently replace the reviewed native scope
        module.authorize_current_scope(**kwargs,path='wiki/index.md',
            expected_sha256=hashlib.sha256(updated_index).hexdigest())
        status,_,body=get(port,'/api/catalog?vault_id=kb-arch&offset=0&limit=30')
        catalog=json.loads(body)
        assert status==200
        new_item=next(item for item in catalog['items'] if item['path']==new_path)
        assert new_item['status']=='restricted' and new_item['reason']=='policy_not_allowed'
        status,_,body=get(port,'/api/search?vault_id=kb-arch&q=Unique%20review%20phrase')
        assert status==200 and json.loads(body)['total']==0

        module.authorize_current_scope(**kwargs,path=new_path,
            expected_sha256=hashlib.sha256(new_bytes).hexdigest())
        status,_,body=get(port,'/api/search?vault_id=kb-arch&q=Unique%20review%20phrase')
        result=json.loads(body)
        assert status==200 and result['total']==1 and result['items'][0]['path']==new_path
        status,_,body=get(port,'/api/read?vault_id=kb-arch&path='+new_path)
        read=json.loads(body)
    assert status==200 and read['source_sha256']==hashlib.sha256(new_bytes).hexdigest()
    assert 'Unique review phrase.' in read['text']


def test_native_index_resolves_unique_nested_cards_without_guessing_ambiguous_names(tmp_path):
    module=api()
    root=tmp_path/'vault'; folder=root/'wiki/frameworks/F-C06'; folder.mkdir(parents=True)
    (root/'wiki').mkdir(exist_ok=True)
    (root/'wiki/index.md').write_text('[[F-C06-001-mem0]]\n',encoding='utf-8')
    (folder/'F-C06-001-mem0.md').write_text('# mem0\n',encoding='utf-8')
    config={'index':'wiki/index.md','content_roots':['wiki/frameworks']}
    _,entries=module._wiki_entries(root,config)
    assert entries==['wiki/frameworks/F-C06/F-C06-001-mem0.md']
    duplicate=root/'wiki/frameworks/archive/F-C06-001-mem0.md'; duplicate.parent.mkdir()
    duplicate.write_text('# historical duplicate\n',encoding='utf-8')
    _,entries=module._wiki_entries(root,config)
    assert entries==[]


def test_native_index_includes_unlinked_table_entry_but_not_templates(tmp_path):
    module=api()
    root=tmp_path/'vault'; folder=root/'wiki/matrices'; folder.mkdir(parents=True)
    (root/'wiki/index.md').write_text(
        '| ID | Title |\n|---|---|\n| M-001-memory-map | Memory map |\n'
        '[[M-002-second-matrix\\|Second matrix]]\n',encoding='utf-8')
    (folder/'M-001-memory-map.md').write_text('# matrix\n',encoding='utf-8')
    (folder/'M-002-second-matrix.md').write_text('# second\n',encoding='utf-8')
    (folder/'README.md').write_text('# navigation\n',encoding='utf-8')
    (folder/'_TEMPLATE-matrix.md').write_text('# template\n',encoding='utf-8')
    config={'index':'wiki/index.md','content_roots':['wiki/matrices']}
    _,entries=module._wiki_entries(root,config)
    assert entries==['wiki/matrices/M-002-second-matrix.md','wiki/matrices/M-001-memory-map.md']


def test_video_catalog_uses_native_bullet_index_and_omits_non_active_rows(tmp_path):
    module=api()
    root=tmp_path/'video'; (root/'wiki/cards/str').mkdir(parents=True)
    (root/'wiki/cards/str/STR-ONE.md').write_text('# active\n',encoding='utf-8')
    (root/'wiki/cards/str/STR-TWO.md').write_text('# quarantined\n',encoding='utf-8')
    text='- STR-ONE | active | digest=sha256:'+'a'*64+' | source=SRC-ONE | transaction=tx-one\n'
    text+='- STR-TWO | quarantined | digest=sha256:'+'b'*64+' | source=SRC-TWO | transaction=tx-two\n'
    assert module._video_entries(root,'wiki/index.md',text)==['wiki/cards/str/STR-ONE.md']


def test_video_catalog_shows_reason_when_native_check_support_is_not_authorized(tmp_path,monkeypatch):
    data=fixture(tmp_path); module=api()
    card_path='wiki/cards/str/STR-LOCAL-001.md'
    card='---\ncard_id: STR-LOCAL-001\nstatus: active\nversion: 1.0.0\ntransaction_id: tx-1\nsource_record_id: SRC-1\n---\n# local\n'
    index=data['vault']/'wiki/index.md'; index.write_text(
        '- STR-LOCAL-001 | active | digest=sha256:'+'a'*64+' | source=SRC-1 | transaction=tx-1\n',
        encoding='utf-8',newline='\n')
    target=data['vault']/card_path; target.parent.mkdir(parents=True); target.write_text(card,encoding='utf-8',newline='\n')
    config={'vaults':{'kb-arch':{'kind':'video-active','index':'wiki/index.md','content_roots':['wiki/cards']}}}
    data['catalog_config'].write_text(json.dumps(config),encoding='utf-8')
    policy=PolicyService(data['instance'],data['policy_root']); current=policy.get('kb-arch','web')
    document={'policy_revision':2,'vault_id':'kb-arch','allow':['wiki/index.md',card_path],
        'deny':[],'revoked':[],'channel':'web'}
    policy.save('kb-arch',document,authorized_target=current['metadata_path'],expected_source=current['source'],
        reviewed_proposal_hash=proposal_hash(document,legacy=None),review_ref='owner-request/real-vault-web.md',legacy=None)
    auth=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    auth['entries']['kb-arch'].update({'wiki/index.md':hashlib.sha256(index.read_bytes()).hexdigest(),
        card_path:hashlib.sha256(target.read_bytes()).hexdigest()})
    data['authorization_path'].write_text(json.dumps(auth),encoding='utf-8')
    checked=[]; original=module.NativeCatalog._video_issues
    def count_check(self,*args):
        checked.append(args[-1])
        return original(self,*args)
    monkeypatch.setattr(module.NativeCatalog,'_video_issues',count_check)
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    page=catalog.catalog('kb-arch',0,10)
    assert page['total']==1 and page['items']==[{'path':card_path,'status':'restricted',
        'reason':'native_integrity_support_restricted'}]
    assert checked==[card_path]
    checked.clear()
    result=catalog.search('kb-arch','local',0,10)
    assert checked==[card_path]
    assert result['total']==0
    assert not {'restricted_count','native_entry_count','issues','search_bytes','scanned_count','scan_complete'} & result.keys()


def test_hub_counts_video_index_candidates_without_claiming_integrity_pass(tmp_path,monkeypatch):
    data=fixture(tmp_path); module=api(); card_path='wiki/cards/str/STR-LOCAL-001.md'
    (data['vault']/card_path).parent.mkdir(parents=True)
    (data['vault']/card_path).write_text('# Indexed video card\n',encoding='utf-8')
    index=data['vault']/'wiki/index.md'
    index.write_text('- STR-LOCAL-001 | active | digest=sha256:'+'a'*64+'\n',encoding='utf-8')
    config={'vaults':{'kb-arch':{'kind':'video-active','index':'wiki/index.md','content_roots':['wiki/cards']}}}
    data['catalog_config'].write_text(json.dumps(config),encoding='utf-8')
    authorization=json.loads(data['authorization_path'].read_text(encoding='utf-8'))
    authorization['entries']['kb-arch']['wiki/index.md']=hashlib.sha256(index.read_bytes()).hexdigest()
    data['authorization_path'].write_text(json.dumps(authorization),encoding='utf-8')
    catalog=module.NativeCatalog(data['instance'],data['policy_root'],data['catalog_config'],data['authorization_path'])
    monkeypatch.setattr(catalog,'_video_issues',lambda *_:pytest.fail('Hub overview must defer per-card integrity checks'))
    row=catalog.vaults()['vaults'][0]
    assert row['asset_count'] is None
    assert row['catalog_entry_count']==1 and row['scope_entry_count']==0
    assert 'candidates' in row['count_basis'] and 'integrity' in row['count_basis']
