"""Explicit pinned legacy sources -> new candidate report, never activation."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kb_core.legacy import LegacyError, _file, _json, extract, write_candidate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, required=True, help='JSON explicit list: path,kind,sha256')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = extract(_json(_file(args.sources)[1]))
        write_candidate(args.output, result)
        print(json.dumps({'candidate_written': True, 'authority_effect': 'none', 'requires_review': True,
                          'conflict_count': len(result['conflicts']), 'missing_count': len(result['missing'])}))
        return 0
    except LegacyError as error:
        print(json.dumps({'error': {'code': str(error), 'message': 'Legacy extraction refused; review explicit sources.'}}))
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
