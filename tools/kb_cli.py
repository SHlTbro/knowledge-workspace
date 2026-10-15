"""Explicit local instance operations; no default root, HTTP or model bridge."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kb_core.bindings import BindingError
from kb_core.members import MemberStoreError
from kb_core.operations import Coordinator, OperationError, read_request


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise OperationError('operation_arguments_invalid')


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--instance', required=True, type=Path)
        commands = parser.add_subparsers(dest='command', required=True)
        commands.add_parser('list')
        resolve = commands.add_parser('resolve')
        resolve.add_argument('--identity', required=True)
        for name in ['register', 'bind', 'rebind', 'unbind']:
            operation = commands.add_parser(name)
            operation.add_argument('--operation-id', required=True)
            operation.add_argument('--request', required=True, type=Path)
        args = parser.parse_args(argv)
        coordinator = Coordinator(args.instance)
        if args.command == 'list':
            output = coordinator.list()
        elif args.command == 'resolve':
            output = coordinator.resolve(args.identity)
        else:
            output = coordinator.execute(args.operation_id, args.command, read_request(args.request))
        print(json.dumps(output, ensure_ascii=False))
        return 0
    except (OperationError, MemberStoreError, BindingError) as error:
        output = {'error': {'code': error.code, 'message': error.message}}
        if getattr(error, 'receipt', None) is not None:
            output['receipt'] = error.receipt
        print(json.dumps(output, ensure_ascii=False))
        return 1
    except OSError:
        print(json.dumps({'error': {'code': 'operation_io_error', 'message': 'Local I/O failed.'}}))
        return 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
