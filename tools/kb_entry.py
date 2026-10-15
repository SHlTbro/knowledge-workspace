"""Candidate native entry protocol; does not activate norms or grant permission."""
import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kb_core.bindings import BindingError
from kb_core.contracts import ContractError, local_root, relative_path, validate_contract
from kb_core.members import MemberStoreError
from kb_core.operations import OperationError, read_request
from kb_core.resources import ResourceError, resolve_reference
from kb_core.state import StateError, StateService

MAX_FILE_BYTES = 8 * 1024 * 1024
PROTOCOL = ['check', 'STATE', 'INVARIANTS', 'member_location', 'AGENTS', 'purpose_navigation_workflow', 'confirmation']

class EntryError(ValueError):
    def __init__(self, code, exit_code=1): self.code, self.exit_code = code, exit_code

class Parser(argparse.ArgumentParser):
    def error(self, message): raise EntryError('entry_arguments_invalid', 2)

def no_links(path):
    for part in [*reversed(path.parents), path]:
        info = part.lstat()
        if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise EntryError('entry_path_unsafe')

def ordinary_single_file(info):
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise EntryError('entry_path_unsafe')

def read_complete(root, reference, role):
    # K01 references are exact relative ordinary-file paths; do not interpret
    # native Workflow/card syntax or follow links on the agent's behalf.
    try:
        local_root(str(root)); relative_path(reference)
        path = root / reference
        no_links(path)
        if not path.is_file(): raise EntryError('entry_file_unavailable', 2)
        before = path.stat()
        ordinary_single_file(before)
        if before.st_size > MAX_FILE_BYTES: raise EntryError('entry_file_limit', 2)
        with path.open('rb') as stream:
            ordinary_single_file(os.fstat(stream.fileno()))
            raw = stream.read(MAX_FILE_BYTES + 1)
            after = os.fstat(stream.fileno())
            ordinary_single_file(after)
        no_links(path)
        current = path.stat()
        ordinary_single_file(current)
        signature = lambda info: (info.st_ino, info.st_size, info.st_mtime_ns)
        if len(raw) > MAX_FILE_BYTES: raise EntryError('entry_file_limit', 2)
        if signature(before) != signature(after) or signature(after) != signature(current):
            raise EntryError('entry_source_changed')
        return {'role': role, 'reference': reference, 'bytes': len(raw),
                'sha256': hashlib.sha256(raw).hexdigest(), 'content': raw.decode('utf-8-sig')}
    except (ContractError, ValueError) as error:
        if isinstance(error, EntryError): raise
        raise EntryError('entry_path_unsafe') from None
    except (OSError, UnicodeError): raise EntryError('entry_file_unavailable', 2) from None

def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        for name in ['instance', 'source-root', 'inputs']:
            parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--member', required=True)
        parser.add_argument('--host-files', action='store_true', help='Caller declaration after an actual bounded public-file probe; not a grant.')
        parser.add_argument('--host-commands', action='store_true', help='Caller declaration after an actual bounded command probe; not a grant.')
        args = parser.parse_args(argv)
        if not args.host_files or not args.host_commands:
            raise EntryError('entry_host_incomplete', 2)
        inputs = read_request(args.inputs)
        service = StateService(args.instance)
        report = service.generate(inputs, scopes=[args.member])
        if report['check_exit_code']: raise EntryError('entry_state_blocked')
        common = read_complete(args.source_root, 'INVARIANTS.md', 'INVARIANTS')
        member = service.coordinator.members.resolve(args.member)
        claim = service.coordinator.bindings.claim(member.location_ref)
        # Existing public guards pin exact member authorization and local binding
        # during these bounded reads. They grant no file/OS or Vault permissions.
        with service.coordinator.bindings.guard(claim), service.coordinator.members.guard(member.model_dump()):
            lock = validate_contract('CapabilityLock', inputs['capabilities'])
            resource = resolve_reference(member.vault_id + '>' + member.agents_ref,
                capabilities=lock, installations={}, member_lookup=lambda identity: [member],
                location_lookup=lambda record: Path(claim['root']))
            files = [common, read_complete(resource.root, member.agents_ref, 'AGENTS'),
                     read_complete(resource.root, member.purpose_ref, 'purpose')]
            files.extend(read_complete(resource.root, reference, 'navigation') for reference in member.navigation_refs)
            current = service.generate(inputs, scopes=[member.vault_id])
            if current['check_exit_code'] or current['state'] != dict(report['state'], generated_at=current['state']['generated_at']):
                raise EntryError('entry_source_changed')
        output = {'status': 'candidate_complete', 'protocol': PROTOCOL, 'state': current['state'],
            'diagnostics': current['diagnostics'], 'loaded_files': files,
            'confirmation': {'control_revision': current['state']['control_revision'], 'vault_id': member.vault_id,
                'member_revision': member.revision, 'location_status': 'online', 'binding_revision': claim['revision'],
                'binding_generation': claim['generation'], 'core_version': member.core_version,
                'profiles': member.model_dump()['profiles']},
            'native_workflow_instruction': 'Follow the complete target AGENTS and its native purpose/index/workflow references; do not replace its domain rules.',
            'permission_grant': False, 'normative_activation': 'verify_effective_cr_and_adopted_versions',
            'agent_gate': 'not_run',
            'host_statement': 'Caller flags are declarations, not actual probe results or READY. Verify bounded public-file/command probes and explicit isolated instance lock-write permission before use; Local/YY is optional.'}
        print(json.dumps(output, ensure_ascii=False))
        return 0
    except EntryError as error:
        print(json.dumps({'error': {'code': error.code, 'message': 'Complete native entry refused; inspect explicit inputs and capabilities.'}}))
        return error.exit_code
    except StateError as error:
        print(json.dumps({'error': {'code': error.code, 'message': error.message}}))
        return error.exit_code
    except (BindingError, MemberStoreError, ResourceError, ContractError):
        print(json.dumps({'error': {'code': 'entry_authority_refused', 'message': 'Native entry authority refused.'}}))
        return 1
    except (OperationError, OSError):
        print(json.dumps({'error': {'code': 'entry_input_unavailable', 'message': 'Explicit entry input unavailable.'}}))
        return 2

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
