"""Isolated read-only K04 generator/checker; current ENTRY/STATE remain unchanged."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kb_core.operations import OperationError, read_request
from kb_core.state import StateError, StateService

class Parser(argparse.ArgumentParser):
    def error(self, message): raise StateError('state_arguments_invalid', 2)

def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--instance', type=Path, required=True)
        commands = parser.add_subparsers(dest='command', required=True)
        for name in ['generate', 'check']:
            command = commands.add_parser(name)
            command.add_argument('--inputs', type=Path, required=True)
            command.add_argument('--scope', action='append', default=[])
            command.add_argument('--require-capability', action='append', default=[])
            if name == 'check': command.add_argument('--state', type=Path, required=True)
        args = parser.parse_args(argv)
        inputs = read_request(args.inputs)
        service = StateService(args.instance)
        kwargs = {'scopes': args.scope, 'required_capabilities': args.require_capability}
        output = service.generate(inputs, **kwargs) if args.command == 'generate' else service.check(read_request(args.state), inputs, **kwargs)
        print(json.dumps(output, ensure_ascii=False))
        return output['check_exit_code']
    except StateError as error:
        print(json.dumps({'error': {'code': error.code, 'message': error.message}}))
        return error.exit_code
    except (OperationError, OSError):
        print(json.dumps({'error': {'code': 'state_input_unavailable', 'message': 'Explicit state input is unavailable.'}}))
        return 2

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
