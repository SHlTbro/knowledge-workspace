"""Explicit independent localhost display service; no write or model endpoints."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kb_core.display_server import DisplayServerError, create_server


class Parser(argparse.ArgumentParser):
    def error(self, message): raise DisplayServerError('display_arguments_invalid', 400)


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        for name in ['instance', 'metadata-root', 'policy-root']:
            parser.add_argument('--' + name, type=Path, required=True)
        output=parser.add_mutually_exclusive_group(required=True)
        output.add_argument('--projection-root',type=Path)
        output.add_argument('--selection-root',type=Path)
        parser.add_argument('--port', type=int, required=True)
        parser.add_argument('--read-authorized', action='store_true')
        parser.add_argument('--metadata-approvals', type=Path)
        args = parser.parse_args(argv)
        server = create_server(**vars(args))
        try:
            print(json.dumps({'status': 'read_only_listener', 'host': '127.0.0.1', 'port': server.server_port,
                              'projection_ready': 'unknown_until_request', 'model_export_permission': False}), flush=True)
            server.serve_forever()
        except KeyboardInterrupt:
            return 0
        finally: server.server_close()
    except DisplayServerError as error:
        print(json.dumps({'error': {'code': error.code}}))
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
