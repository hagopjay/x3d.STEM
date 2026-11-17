#!/usr/bin/env python3
"""Check the four-splat fork output with the existing pinned validator source."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import sys
from dataclasses import asdict

HERE=Path(__file__).resolve().parent
WORK=HERE.parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--study-root',type=Path,default=WORK/'x3d.STEM/studies/research-loom',
    help='Research Loom study containing its pinned validator and tools/validate_x3d.py')
args=parser.parse_args()
STUDY=args.study_root.resolve()
sys.path.insert(0,str(STUDY))
from tools.validate_x3d import instrument_identity,load_vendor

identity=instrument_identity()
validator,semantic=load_vendor(identity)
path=HERE/'results/native-fork-roundtrip.x3d'
xml=path.read_text()
xsd=validator.validate_xml(xml,version='4.1')
diagnostics=[asdict(d) for d in semantic.semantic_diagnostics(xml)]
bad=xml.replace('positions="','unrecognizedPositions="',1)
negative=validator.validate_xml(bad,version='4.1')
ok=xsd.get('valid') is True and not any(d.get('level',d.get('severity'))=='error' for d in diagnostics) and negative.get('valid') is False
report={'schema':'scivis.native53-x3d-check/1','status':'pass' if ok else 'fail',
    'created_utc':datetime.now(timezone.utc).isoformat(),
    'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'candidate_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
    'validator_repository':identity['repository'],'validator_commit':identity['commit'],
    'validator_origin_sha256':identity['origin_sha256'],
    'validator_files_sha256':identity['files_sha256'],
    'actual_invocation':['validation.validate.validate_xml(version="4.1")','validation.semantic.semantic_diagnostics'],
    'xsd_version':'4.1','semantic_vocabulary_version':'4.1',
    'xsd':xsd,'semantic_diagnostics':diagnostics,'invalid_attribute_control':negative,
    'scope':'A four-splat synthetic fork-exported X3D document. No native X_ITE browser, pixel appearance or general exporter-conformance claim.'}
(HERE/'results/x3d-validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'status':report['status'],'xsd':xsd,'diagnostics':diagnostics,'negative_valid':negative.get('valid')}))
raise SystemExit(0 if ok else 1)
