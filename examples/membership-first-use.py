"""Register an isolated sample Vault; this does not run ENTRY or distillation.

Run from the source root: python examples/membership-first-use.py
Real Vaults retain their own rules, purpose, navigation and quality checks.
"""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / 'src'))
from kb_core.members import MemberStore


def main():
    with TemporaryDirectory(prefix='kb-membership-example-') as temporary:
        root = Path(temporary)
        instance, vault = root / 'instance', root / 'sample-vault'
        instance.mkdir()
        vault.mkdir()
        for name, text in {
            'AGENTS.md': '# Sample rules\nUse only this temporary sample.\n',
            'PURPOSE.md': '# Purpose\nDemonstrate membership, not production knowledge.\n',
            'index.md': '# Sample navigation\nNo knowledge has been produced.\n',
        }.items():
            (vault / name).write_text(text, encoding='utf-8')
        # The CLI has no init command; use the public store initializer.
        MemberStore(instance / 'members.json').create()
        request = root / 'register.json'
        request.write_text(json.dumps({
            'member': {
                'schema_version': 'kb-contracts-1.0', 'revision': 1,
                'vault_id': 'sample-notes', 'aliases': ['sample'],
                'name': 'Sample notes', 'purpose_ref': 'PURPOSE.md',
                'agents_ref': 'AGENTS.md', 'navigation_refs': ['index.md'],
                'core_version': 'preview-1', 'profiles': [],
                'location_ref': 'sample-location', 'display_ref': None,
                'enabled': True,
            },
            'root': str(vault), 'expected_collection_revision': 1,
            'expected_binding_revision': 0, 'expected_generation': 0,
        }), encoding='utf-8')

        def cli(*arguments):
            result = subprocess.run([
                sys.executable, '-B', str(SOURCE / 'tools/kb_cli.py'),
                '--instance', str(instance), *arguments,
            ], capture_output=True, text=True, encoding='utf-8', timeout=30)
            if result.returncode:
                raise RuntimeError('Sample CLI failed; check the source environment.')
            return json.loads(result.stdout)

        register = ('register', '--operation-id', 'sample-register',
                    '--request', str(request))
        created = cli(*register)
        resolved = cli('resolve', '--identity', 'SAMPLE')
        replayed = cli(*register)
        receipt = created['receipt']
        if (receipt['system_result']['status'] != 'succeeded'
                or receipt['domain_result']['status'] != 'not_run'
                or resolved['member']['vault_id'] != 'sample-notes'
                or resolved['binding']['status'] != 'online'
                or replayed['replayed'] is not True):
            raise RuntimeError('Sample membership checks failed.')
    # Temporary files are removed before success is reported.
    print('registered: sample-notes / binding: online / replayed: true')


if __name__ == '__main__':
    main()
