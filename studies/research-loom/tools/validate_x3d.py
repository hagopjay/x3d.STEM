#!/usr/bin/env python3
"""Run actual pinned x3d_mcp checks on generated Research Loom X3D scenes.

This adapter has its own explicit 2 MiB input budget. It verifies the pinned
upstream source without monkeypatching the validator or its file limits.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib
from importlib import metadata
import json
from pathlib import Path
import platform
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'vendor' / 'x3d_mcp'
VENDOR_SRC = VENDOR / 'src'
REPOSITORY = 'https://github.com/hagopjay/x3d_mcp'
COMMIT = 'b5c9956917714747fe1d034c729612e99b0f09c9'
ORIGIN_SHA256 = 'e7587506b4b4e3455f358451e104ad8d8e31514e6f8e687bdb2b9be5b170c349'
MAX_XML_BYTES = 2 * 1024 * 1024
OWN_DOCTYPE = '<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd">'
_DECLARATION = re.compile(r'<!\s*(?:DOCTYPE|ENTITY)\b', re.IGNORECASE)


class InstrumentError(RuntimeError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def instrument_identity() -> dict:
    manifest_path = VENDOR / 'ORIGIN.json'
    try:
        raw = manifest_path.read_bytes()
        if sha(raw) != ORIGIN_SHA256:
            raise InstrumentError('MCP_ORIGIN_DRIFT: the pinned origin manifest changed')
        manifest = json.loads(raw)
        if manifest.get('repository') != REPOSITORY or manifest.get('commit') != COMMIT:
            raise InstrumentError('MCP_ORIGIN_MISMATCH: wrong repository or commit')
        expected = manifest.get('files_sha256')
        if not isinstance(expected, dict) or not expected:
            raise InstrumentError('MCP_ORIGIN_INVALID: missing nonempty file inventory')
        files = {}
        for name, digest in expected.items():
            p = Path(name)
            if p.is_absolute() or '..' in p.parts or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
                raise InstrumentError('MCP_ORIGIN_INVALID: unsafe path or malformed digest')
            files[name] = sha((VENDOR / p).read_bytes())
            if files[name] != digest:
                raise InstrumentError('MCP_FILE_DRIFT: ' + name)
    except (OSError, ValueError) as error:
        raise InstrumentError('MCP_VENDOR_UNAVAILABLE: ' + type(error).__name__) from error
    from lxml import etree
    identity = {
        'repository': REPOSITORY, 'commit': COMMIT, 'origin_sha256': ORIGIN_SHA256,
        'files_sha256': files, 'adapter_sha256': sha(Path(__file__).read_bytes()),
        'invocation': ['validation.validate.validate_xml(version="4.0")', 'validation.semantic.semantic_diagnostics'],
        'xsd_version': '4.0', 'semantic_vocabulary_version': '4.1',
        'runtime': {'python': platform.python_version(), 'lxml': '.'.join(map(str, etree.LXML_VERSION)),
                    'libxml2': '.'.join(map(str, etree.LIBXML_VERSION)), 'jsonschema': metadata.version('jsonschema')},
    }
    identity['identity_sha256'] = sha(canonical(identity))
    return identity


def load_vendor(identity: dict):
    for name, module in tuple(sys.modules.items()):
        if name in ('validation', 'x3d_utils') or name.startswith(('validation.', 'x3d_utils.')):
            origin = getattr(module, '__file__', None)
            if not origin or not Path(origin).resolve().is_relative_to(VENDOR_SRC.resolve()):
                raise InstrumentError('MCP_NAMESPACE_CONFLICT: ' + name)
    sys.path.insert(0, str(VENDOR_SRC)) if str(VENDOR_SRC) not in sys.path else None
    validator = importlib.import_module('validation.validate')
    semantic = importlib.import_module('validation.semantic')
    check_module_origins(identity)
    return validator, semantic


def check_module_origins(identity: dict) -> None:
    for name, module in tuple(sys.modules.items()):
        if name in ('validation', 'x3d_utils') or name.startswith(('validation.', 'x3d_utils.')):
            origin = getattr(module, '__file__', None)
            if not origin:
                raise InstrumentError('MCP_MODULE_ORIGIN: ' + name)
            p = Path(origin).resolve()
            if not p.is_relative_to(VENDOR_SRC.resolve()):
                raise InstrumentError('MCP_MODULE_ORIGIN: ' + name)
            rel = p.relative_to(VENDOR.resolve()).as_posix()
            if identity['files_sha256'].get(rel) != sha(p.read_bytes()):
                raise InstrumentError('MCP_IMPORTED_FILE_DRIFT: ' + name)


def validate_bytes(raw: bytes, instrument: dict | None = None) -> dict:
    row = {'bytes': len(raw), 'candidate_sha256': sha(raw), 'status': 'not_run',
           'xsd': {'status': 'not_run', 'findings': []}, 'semantic': {'status': 'not_run', 'findings': []}}
    if len(raw) > MAX_XML_BYTES:
        row['input_refusal'] = 'The declared per-file 2 MiB input budget was exceeded.'
        return row
    try:
        xml = raw.decode('utf-8')
    except UnicodeDecodeError:
        row.update(status='fail', input_refusal='The candidate is not UTF-8.')
        return row
    # Preserve the writer's standard fixed DOCTYPE bytes while refusing entity
    # declarations, internal subsets and arbitrary DTD resources. Upstream's
    # parsing paths do not need to fetch this declaration for XSD validation.
    without_owned = xml.replace(OWN_DOCTYPE, '', 1)
    if _DECLARATION.search(without_owned) or not xml.strip():
        row.update(status='fail', input_refusal='Only the exact optional writer DOCTYPE is supported; other DTD/entity declarations are refused.')
        return row
    try:
        identity = instrument_identity()
        if instrument is not None and identity != instrument:
            raise InstrumentError('MCP_INSTRUMENT_DRIFT: identity changed during this run')
        validator, semantic = load_vendor(identity)
        row['instrument_sha256'] = identity['identity_sha256']
    except (ModuleNotFoundError, ImportError) as error:
        row['dependency_error'] = str(error)
        return row
    except InstrumentError as error:
        row.update(status='error', instrument_error=str(error))
        return row
    try:
        result = validator.validate_xml(xml, version='4.0')
        status = 'not_run' if result.get('checked') is False else 'pass' if result.get('valid') is True else 'fail'
        row['xsd'] = {'status': status, 'schema_version': result.get('schema_version', '4.0'),
                      'findings': result.get('errors', []), 'notes': result.get('notes', [])}
        if result.get('verdict'):
            row['xsd']['verdict'] = result['verdict']
    except Exception as error:
        row['xsd'] = {'status': 'error', 'findings': [type(error).__name__ + ': ' + str(error)]}
    try:
        findings = [asdict(value) for value in semantic.semantic_diagnostics(xml)]
        row['semantic'] = {'status': 'fail' if any(f['level'] == 'error' for f in findings) else 'pass', 'findings': findings}
    except Exception as error:
        parse_failure = type(error).__name__ in ('XMLSyntaxError', 'NoSceneError', 'ValueError')
        row['semantic'] = {'status': 'fail' if parse_failure else 'error', 'findings': [type(error).__name__ + ': ' + str(error)]}
    try:
        check_module_origins(identity)
        if instrument_identity() != identity:
            raise InstrumentError('MCP_INSTRUMENT_DRIFT: source changed during validation')
    except InstrumentError as error:
        row.update(status='error', instrument_error=str(error))
        return row
    statuses = [row['xsd']['status'], row['semantic']['status']]
    row['status'] = 'error' if 'error' in statuses else 'fail' if 'fail' in statuses else 'pass' if all(s == 'pass' for s in statuses) else 'not_run'
    return row


def control_pair(identity: dict | None) -> list[dict]:
    positive = b'''<X3D profile="Immersive" version="4.0"><Scene><Viewpoint/><Transform DEF="Target"><Shape><Sphere radius="1"/></Shape></Transform><TimeSensor DEF="Clock"/><PositionInterpolator DEF="Slide" key="0 1" keyValue="0 0 0 1 0 0"/><ROUTE fromNode="Clock" fromField="fraction_changed" toNode="Slide" toField="set_fraction"/><ROUTE fromNode="Slide" fromField="value_changed" toNode="Target" toField="set_translation"/></Scene></X3D>'''
    repaired = validate_bytes(positive, identity)
    rows = []
    for name, mutated, stage in [
        ('numeric_radius', positive.replace(b'radius="1"', b'radius="broken"'), 'xsd'),
        ('missing_route_source', positive.replace(b'fromNode="Clock"', b'fromNode="MissingClock"'), 'semantic'),
    ]:
        defective = validate_bytes(mutated, identity)
        rows.append({'id': name, 'expected_stage': stage, 'positive': repaired, 'negative': defective,
                     'caught': repaired['status'] == 'pass' and defective[stage]['status'] == 'fail'})
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='*', type=Path, help='Defaults to every hash-bound saved X3D 4 frame in the bank.')
    parser.add_argument('--output', type=Path, default=ROOT / 'evidence' / 'x3d-validation.json')
    args = parser.parse_args(argv)
    bank = json.loads((ROOT / 'web' / 'bank' / 'index.json').read_text()) if not args.files else None
    paths = args.files or [ROOT / f['file'] for c in bank['cases'] for f in c['frame_exports']]
    rows = []
    identity = None
    instrument_problem = None
    try:
        identity = instrument_identity()
    except (InstrumentError, ImportError, metadata.PackageNotFoundError) as error:
        instrument_problem = type(error).__name__ + ': ' + str(error)
    for path in paths:
        path = path.resolve()
        name = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
        try:
            size = path.stat().st_size
            if size > MAX_XML_BYTES:
                row = {'bytes': size, 'candidate_sha256': None, 'status': 'not_run',
                       'xsd': {'status': 'not_run', 'findings': []}, 'semantic': {'status': 'not_run', 'findings': []},
                       'input_refusal': 'File exceeds the declared 2 MiB input budget; content was not read or hashed.'}
            else:
                row = validate_bytes(path.read_bytes(), identity)
        except OSError as error:
            row = {'status': 'error', 'input_error': type(error).__name__ + ': ' + str(error)}
        rows.append({'path': name, **row})
    controls = control_pair(identity)
    passed = bool(rows) and identity is not None and all(r['status'] == 'pass' for r in rows) and all(r['caught'] for r in controls)
    report = {'schema': 'stemloom.pinned-x3d-validation/1', 'created_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'pass' if passed else 'incomplete_or_failed', 'input_cap_bytes': MAX_XML_BYTES,
              'instrument': identity, 'instrument_problem': instrument_problem, 'files': rows, 'controls': controls,
              'limitations': [
                  'Actual direct calls to pinned x3d_mcp functions; no network MCP transport or model call.',
                  'XSD 4.0 and the upstream default semantic vocabulary 4.1 are deliberately recorded separately.',
                  'The optional fixed X3D DOCTYPE is retained; arbitrary DTD/entity declarations are refused before upstream parsing.',
                  'Per-file XSD/implemented semantic checks do not establish Research Loom mapping fidelity, physical validity, visible rendering or GPU performance.',
                  'Parameterized model fidelity and exported visual semantics require separate application controls.',
                  'This unsigned local report is not a formal Loom acceptance receipt or publisher authentication.',
              ]}
    report['report_sha256'] = sha(canonical(report))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'files': len(rows), 'passed': sum(r['status'] == 'pass' for r in rows),
                      'paired_controls_caught': sum(r['caught'] for r in controls), 'output': str(args.output)}, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
