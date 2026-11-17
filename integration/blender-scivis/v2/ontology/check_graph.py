#!/usr/bin/env python3
"""Check local RDF metadata shapes and one deliberately broken SHA control.

Requires rdflib and pyshacl. No remote contexts or ontologies are downloaded.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--graph', type=Path, default=Path('integration/examples/research-loom-inventory.jsonld'))
    p.add_argument('--receipt', type=Path, default=Path('private/ontology-validation.json'))
    a = p.parse_args()
    import rdflib
    import pyshacl
    from rdflib import Graph, Namespace, Literal
    from rdflib.namespace import RDF
    root = Path(__file__).resolve().parent
    raw = a.graph.read_bytes()
    data = json.loads(raw)
    if not isinstance(data.get('@context'), dict):
        raise ValueError('Only a bundled local context is accepted')
    sys.path.insert(0,str(root.parent/'integration'))
    from inventory import validate
    validate(data)  # Requires the exact local context before RDF processing.
    graph = Graph().parse(data=raw.decode(), format='json-ld')
    shapes = Graph().parse(root/'shapes.ttl', format='turtle')
    vocab = Graph().parse(root/'hooks.ttl', format='turtle')
    ok, report, message = pyshacl.validate(graph, shacl_graph=shapes, inference='none')
    if not ok:
        raise ValueError(message)
    sv = Namespace('urn:x3d-scivis:inventory:')
    bad = Graph()
    for triple in graph:
        bad.add(triple)
    subject = next(bad.subjects(RDF.type, sv.Artifact))
    bad.remove((subject, sv.sha256, None)); bad.add((subject, sv.sha256, Literal('bad-digest')))
    bad_ok, _, _ = pyshacl.validate(bad, shacl_graph=shapes, inference='none')
    if bad_ok:
        raise ValueError('Malformed SHA control escaped the RDF shape')
    query = (root/'queries.rq').read_text()
    matches = list(graph.query(query))
    if not matches:
        raise ValueError('Trace query returned no claim/evidence paths')
    result = {'schema':'scivis.ontology-check/1', 'status':'pass',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'graph_sha256':hashlib.sha256(raw).hexdigest(), 'graph_triples':len(graph),
        'vocabulary_triples':len(vocab), 'shape_triples':len(shapes),
        'query_rows':len(matches), 'bad_digest_control_caught':not bad_ok,
        'rdflib':rdflib.__version__, 'pyshacl':pyshacl.__version__,
        'scope':'Metadata shapes and a trace query; live artifact bytes and scientific support are checked separately.'}
    a.receipt.parent.mkdir(parents=True,exist_ok=True)
    a.receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
