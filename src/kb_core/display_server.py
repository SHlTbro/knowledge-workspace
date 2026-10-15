"""Independent localhost GET surface; publication and live policy own its data."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import os
import stat
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .bindings import BindingError, BindingStore
from .contracts import relative_path, validate_contract, ContractError
from .display_policy import PolicyError, PolicyService
from .display_description import DescriptionError, DescriptionService
from .display_projection import ProjectionError, load_release, read_resource, read_metadata, assert_resource_source
from .members import MemberStoreError
from .operations import OperationError
from .display_update import DisplayUpdateError, selected_release

_STATIC_DIR = Path(__file__).with_name('display_static')
_STATIC_FILES = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                 '/app.css': ('app.css', 'text/css')}
_STATIC_LIMIT = 1024 * 1024
_STATIC_CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'none'; font-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
_POLICY_SUBJECT = ('vault_id','channel','authority_scope','metadata_scope','binding_id','binding_revision','binding_generation')
_DESCRIPTION_SUBJECT = ('vault_id','authority_scope','metadata_scope','display_ref','binding_id','binding_revision','binding_generation')

def _same_subject(previous,current,keys):
    # Aggregate revision and ordinary content changes are not permission proof.
    return all(key in previous and key in current and type(previous[key]) is type(current[key])
               and previous[key]==current[key] for key in keys)


class DisplayServerError(ValueError):
    def __init__(self, code, status=503):
        self.code, self.status = code, status
        super().__init__('Read-only display refused.')


def _root(value):
    try:
        path = BindingStore(Path(value)).path
        if not path.is_dir(): raise DisplayServerError('display_root_unavailable')
        return path
    except (BindingError, TypeError, ValueError, OSError) as error:
        if isinstance(error, DisplayServerError): raise
        raise DisplayServerError('display_root_invalid') from None


def _metadata_approvals(value, coordinator):
    """Read the explicitly supplied file afresh; never infer or cache a grant."""
    if value is None:return {}
    if isinstance(value,Path):
        def pairs(items):
            result={}
            for key,item in items:
                if key in result:raise ValueError('duplicate approval')
                result[key]=item
            return result
        try:
            path=BindingStore(value).path;before=path.stat()
            if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>65536:raise ValueError()
            with path.open('rb') as stream:
                opened=os.fstat(stream.fileno())
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink!=1:raise ValueError()
                raw=stream.read(65537);after=os.fstat(stream.fileno())
            current=BindingStore(path).path.stat()
            signature=lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_nlink)
            if len(raw)>65536 or signature(before)!=signature(opened) or signature(before)!=signature(after) or signature(after)!=signature(current):raise ValueError()
            value=json.loads(raw,object_pairs_hook=pairs)
        except (OSError,ValueError,BindingError,RecursionError):
            raise DisplayServerError('display_metadata_approval_invalid',400) from None
    if not isinstance(value,dict) or len(value)>64:raise DisplayServerError('display_metadata_approval_invalid',400)
    result={}
    for identity,digest in value.items():
        try:
            if not isinstance(identity,str) or coordinator.members.resolve(identity).vault_id!=identity:
                raise DisplayServerError('display_metadata_approval_invalid',400)
        except MemberStoreError:raise DisplayServerError('display_metadata_approval_invalid',400) from None
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise DisplayServerError('display_metadata_approval_invalid',400)
        result[identity]=digest
    return result


class _Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def setup(self):
        super().setup()
        self.request.settimeout(30)
        self._response_started = False

    def log_message(self, *_):
        pass  # Resource locators and old tokens never enter the default access log.

    def _send(self, status, raw, *, content_type='application/json; charset=utf-8', headers=None):
        self._response_started = True
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        for name, value in (headers or {}).items(): self.send_header(name, value)
        if status == 405: self.send_header('Allow', 'GET')
        self.end_headers()
        if self.command != 'HEAD': self.wfile.write(raw)
        self.wfile.flush()

    def _error(self, code, status):
        if self._response_started: return  # A completed/partial response cannot be rolled back.
        self._send(status, json.dumps({'error': {'code': code}}, separators=(',', ':')).encode('utf-8'))

    def _static(self, route):
        filename, mime = _STATIC_FILES[route]
        try:
            path = BindingStore(_STATIC_DIR / filename).path
            before = path.stat()
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > _STATIC_LIMIT:
                raise DisplayServerError('display_static_unavailable')
            with path.open('rb') as stream:
                opened = os.fstat(stream.fileno())
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                    raise DisplayServerError('display_static_unavailable')
                raw = stream.read(_STATIC_LIMIT + 1); after = os.fstat(stream.fileno())
            current = BindingStore(path).path.stat()
            signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)
            if len(raw) > _STATIC_LIMIT or signature(before) != signature(opened) or signature(before) != signature(after) or signature(after) != signature(current):
                raise DisplayServerError('display_static_unavailable')
        except (BindingError, OSError): raise DisplayServerError('display_static_unavailable') from None
        self._send(200, raw, content_type=mime+'; charset=utf-8', headers={
            'ETag': '"sha256-'+hashlib.sha256(raw).hexdigest()+'"', 'Content-Security-Policy': _STATIC_CSP,
            'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY'})

    def _safe_view(self):
        output=self._release_root()
        released = load_release(output)
        for name in ['instance','metadata_root','policy_root']: _root(self.server.display_roots[name])
        coordinator = self.server.display_policy.coordinator
        members = coordinator.members.snapshot()
        coordinator.bindings.snapshot() # Global corruption cannot be isolated safely.
        if coordinator.operation_issues(): raise DisplayServerError('display_authority_incomplete')
        known = {row['vault_id']:row for row in members['records']}
        evidence = {row['vault_id']:row for row in released['report']['members']}
        authority_scope = hashlib.sha256(os.path.normcase(str(coordinator.instance)).encode('utf-8')).hexdigest()
        for item in evidence.values():
            for name, root_key in [('description_source', 'metadata_root'), ('policy_source', 'policy_root')]:
                metadata_scope = hashlib.sha256(os.path.normcase(str(self.server.display_roots[root_key])).encode('utf-8')).hexdigest()
                if item[name]['authority_scope'] != authority_scope or item[name]['metadata_scope'] != metadata_scope:
                    raise DisplayServerError('display_scope_changed')
        observed = {};rows=[]
        stale = members['collection_revision'] != released['projection']['source_member_revision']
        for original in released['projection']['vaults']:
            identity=original['vault_id'];old=evidence[identity]
            if identity not in known:
                stale=True;continue
            try:
                description=self.server.display_descriptions.read(identity)
                policy=self.server.display_policy.get(identity,'web')
                if policy['policy'] is None or not _same_subject(old['description_source'],description['source'],_DESCRIPTION_SUBJECT) or not _same_subject(old['policy_source'],policy['source'],_POLICY_SUBJECT):
                    stale=True;continue
            except (PolicyError,DescriptionError):
                stale=True;continue # Specific scope failed; never serve its old permission.
            changed = any(description['source'][key] != old['description_source'][key] for key in ['member_revision','description_revision','sha256','bytes'])
            changed = changed or policy['source']['sha256'] != old['policy_source']['sha256']
            state='stale' if changed else original['state'];paths=[];unsafe_subject=False
            if not known[identity]['enabled'] or description['status']=='disabled': state='restricted'
            elif description['source']['binding_status']!='online': state='offline'
            else:
                for entry in released['index']['resources']:
                    if entry['vault_id']!=identity:continue
                    try:
                        with self.server.display_policy.guard(identity,entry['source_resource'],'web',read_authorized=True,exporting=False) as grant:
                            if not _same_subject(entry['policy_source'],grant['source'],_POLICY_SUBJECT):
                                unsafe_subject=True;break
                            assert_resource_source(grant['locator'],entry['source_stamp'])
                            paths.append(entry['source_resource'])
                    except (PolicyError,ProjectionError):state='restricted'
            if unsafe_subject:
                stale=True;continue
            row=dict(original,state=state,resources=paths)
            stale=stale or changed or state!=original['state'] or paths!=original['resources']
            rows.append(row);observed[identity]=description
        coordinator.members.snapshot();coordinator.bindings.snapshot()
        if coordinator.operation_issues():raise DisplayServerError('display_authority_incomplete')
        projection=dict(released['projection'],vaults=rows,freshness='stale' if stale else 'current')
        validate_contract('DisplayProjection',projection)
        return released,projection,observed,output

    def _release_root(self):
        roots=self.server.display_roots
        if 'projection_root' in roots:return _root(roots['projection_root'])
        try:
            choice=selected_release(roots['selection_root'])
            output=_root(Path(choice['output_dir']))
            if output.parent!=roots['selection_root']:raise DisplayServerError('display_selection_scope_invalid')
            return output
        except DisplayUpdateError:raise DisplayServerError('display_selection_unavailable') from None

    def _metadata(self, query):
        approvals = _metadata_approvals(self.server.metadata_approvals,self.server.display_policy.coordinator)
        if not approvals: raise DisplayServerError('display_metadata_unapproved', 403)
        values = parse_qs(query, keep_blank_values=True, encoding='utf-8', errors='strict', max_num_fields=1)
        if set(values) != {'vault_id'} or len(values['vault_id']) != 1 or not values['vault_id'][0]:
            raise DisplayServerError('display_request_invalid', 400)
        identity = values['vault_id'][0]
        released,view,observed,output = self._safe_view()
        entries = [row for row in released['index']['metadata'] if row['vault_id'] == identity]
        if len(entries) != 1: raise DisplayServerError('display_metadata_missing', 404)
        entry = entries[0]
        if identity not in observed:raise DisplayServerError('display_metadata_authority_changed',403)
        if approvals.get(identity) != entry['sha256']:
            raise DisplayServerError('display_metadata_unapproved', 403)
        current = observed[identity]
        evidence = next(row for row in released['report']['members'] if row['vault_id'] == identity)
        try: state = validate_contract('InstanceState', released['report']['state_report']['state'])
        except ContractError: raise DisplayServerError('display_projection_unavailable') from None
        headers = {'X-KB-Binding-Status': current['source']['binding_status'],
                   'X-KB-Description-Status': evidence['status'], 'X-KB-Observed-At': state.generated_at,
                   'X-KB-Projection-Revision': str(released['projection']['projection_revision']),
                   'X-KB-Metadata-SHA256': entry['sha256']}
        if any(not isinstance(value, str) or '\r' in value or '\n' in value for value in headers.values()):
            raise DisplayServerError('display_projection_unavailable')
        payload = read_metadata(output, identity, approvals[identity])
        latest=self.server.display_descriptions.read(identity)
        if not _same_subject(entry['description_source'],latest['source'],_DESCRIPTION_SUBJECT):
            raise DisplayServerError('display_metadata_authority_changed',403)
        raw=json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        if _metadata_approvals(self.server.metadata_approvals,self.server.display_policy.coordinator).get(identity)!=approvals[identity]:
            raise DisplayServerError('display_metadata_unapproved',403)
        self._send(200, raw, headers=headers)

    def send_error(self, code, message=None, explain=None):
        if code == 501: self._error('display_method_not_allowed', 405)
        else: self._error('display_request_invalid', code)

    def do_GET(self):
        try:
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if self.headers.get('Host') not in allowed:
                raise DisplayServerError('display_request_not_local', 403)
            origin = self.headers.get('Origin')
            if origin is not None and origin not in {'http://' + host for host in allowed}:
                raise DisplayServerError('display_request_not_local', 403)
            target = urlsplit(self.path)
            if target.scheme or target.netloc or target.fragment:
                raise DisplayServerError('display_request_invalid', 400)
            if target.path in _STATIC_FILES:
                if target.query: raise DisplayServerError('display_route_unavailable', 404)
                self._static(target.path)
                return
            if target.path not in {'/api/projection', '/api/resources', '/api/descriptions'}:
                raise DisplayServerError('display_route_unavailable', 404)
            if target.path == '/api/projection':
                if target.query: raise DisplayServerError('display_request_invalid', 400)
                _,projection,_,_ = self._safe_view()
                self._send(200, json.dumps(projection, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
                return
            if target.path == '/api/descriptions':
                self._metadata(target.query)
                return
            query = parse_qs(target.query, keep_blank_values=True, encoding='utf-8', errors='strict', max_num_fields=2)
            if set(query) != {'vault_id', 'path'} or any(len(value) != 1 or not value[0] for value in query.values()):
                raise DisplayServerError('display_request_invalid', 400)
            identity, resource = query['vault_id'][0], query['path'][0]
            relative_path(resource)
            with self.server.display_policy.guard(identity, resource, 'web', read_authorized=True, exporting=False) as grant:
                # Live denial precedes publication absence and old snapshot mismatch.
                # Never read a raw Vault locator as an output-root fallback.
                output = self._release_root()
                released = load_release(output)
                entries = [row for row in released['index']['resources']
                           if row['vault_id'] == grant['source']['vault_id'] and row['source_resource'].casefold() == grant['resource'].casefold()]
                if len(entries) != 1: raise DisplayServerError('display_resource_unpublished', 404)
                entry = entries[0]
                current=self.server.display_descriptions.read(entry['vault_id'])
                if not _same_subject(entry['policy_source'],grant['source'],_POLICY_SUBJECT) or not _same_subject(entry['description_source'],current['source'],_DESCRIPTION_SUBJECT):
                    raise DisplayServerError('display_resource_authority_changed',403)
                try:assert_resource_source(grant['locator'],entry['source_stamp'])
                except ProjectionError:raise DisplayServerError('display_resource_source_changed',403) from None
                raw = read_resource(output, entry['vault_id'], entry['source_resource'])
                if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
                    raise DisplayServerError('display_projection_stale')
                try:assert_resource_source(grant['locator'],entry['source_stamp'])
                except ProjectionError:raise DisplayServerError('display_resource_source_changed',403) from None
                self._send(200, raw, content_type='application/octet-stream')
        except DisplayServerError as error:
            self._error(error.code, error.status)
        except PolicyError as error:
            transient = {'policy_busy', 'policy_authority_incomplete', 'policy_revision_conflict',
                         'policy_source_changed', 'policy_authority_invalid', 'policy_lock_changed'}
            self._error(error.code, 503 if error.code in transient else 403)
        except (BrokenPipeError, ConnectionResetError):
            return
        except (ProjectionError, DescriptionError, BindingError, MemberStoreError, OperationError, OSError, KeyError, TypeError):
            self._error('display_projection_unavailable', 503)
        except ValueError:
            self._error('display_request_invalid', 400)


def create_server(*, instance, metadata_root, policy_root, projection_root=None, selection_root=None,
                  read_authorized=False, metadata_approvals=None, host='127.0.0.1', port):
    """Caller supplies actual local read authority; headers/tokens cannot add it.

    ponytail: stdlib threaded server, bounded publications; no shared old web
    application, service discovery, or general plugin/router platform.
    """
    if host != '127.0.0.1': raise DisplayServerError('display_host_not_local', 400)
    if read_authorized is not True: raise DisplayServerError('display_read_unauthorized', 403)
    if type(port) is not int or not 0 <= port <= 65535:
        raise DisplayServerError('display_port_invalid', 400)
    if (projection_root is None)==(selection_root is None):raise DisplayServerError('display_output_mode_invalid',400)
    output_key='projection_root' if projection_root is not None else 'selection_root'
    output_value=projection_root if projection_root is not None else selection_root
    roots = {key: _root(value) for key, value in {'instance': instance, 'metadata_root': metadata_root,
        'policy_root': policy_root, output_key:output_value}.items()}
    output = roots[output_key]
    if any(output == path or output.is_relative_to(path) or path.is_relative_to(output)
           for key, path in roots.items() if key != output_key):
        raise DisplayServerError('display_output_scope_invalid', 400)
    try:
        policy = PolicyService(roots['instance'], roots['policy_root'])
        descriptions = DescriptionService(roots['instance'], roots['metadata_root'])
    except (PolicyError, DescriptionError): raise DisplayServerError('display_authority_unavailable') from None
    if selection_root is not None:
        try:
            for row in policy.coordinator.bindings.snapshot():
                if row['root'] is None:continue
                native=BindingStore(Path(row['root'])).path
                if output==native or output.is_relative_to(native) or native.is_relative_to(output):
                    raise DisplayServerError('display_output_scope_invalid',400)
        except BindingError:raise DisplayServerError('display_authority_unavailable') from None
    approvals = _metadata_approvals(metadata_approvals,policy.coordinator)
    if isinstance(metadata_approvals,Path):approvals=BindingStore(metadata_approvals).path
    try: server = ThreadingHTTPServer((host, port), _Handler)
    except OSError: raise DisplayServerError('display_listener_unavailable') from None
    server.daemon_threads = True
    server.display_roots = roots
    server.display_policy = policy
    server.display_descriptions = descriptions
    server.metadata_approvals = approvals
    return server
