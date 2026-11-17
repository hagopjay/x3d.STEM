#!/usr/bin/env python3
"""Explicit scientific data and geometry transfers for the Research Loom subset."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stemloom.exchange import from_x3d,to_x3d,to_vtp,to_obj,to_ply,points_csv,dataset_to_vti


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('import-csv');c.add_argument('input',type=Path);c.add_argument('output',type=Path);c.add_argument('--units',default='unspecified coordinate unit');c.add_argument('--label',default='Imported research cloud')
    c=sub.add_parser('inspect-x3d');c.add_argument('input',type=Path);c.add_argument('output',type=Path)
    c=sub.add_parser('export');c.add_argument('packet',type=Path);c.add_argument('output',type=Path);c.add_argument('--frame',type=int,default=0);c.add_argument('--format',choices=['x3d4','x3d33','vtp','ply','obj','csv','vti'],required=True)
    args=p.parse_args()
    if args.command=='import-csv':
        from stemloom.tensor import build_from_points
        from stemloom.core import canonical,validate_case,source_hashes
        if args.input.stat().st_size>2*1024*1024:raise ValueError('CSV exceeds 2 MiB input budget.')
        with args.input.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            if not reader.fieldnames or not {'x','y','z'}.issubset(reader.fieldnames):raise ValueError('CSV requires x,y,z columns.')
            points=[]
            for row in reader:
                if len(points)>=5000:raise ValueError('At most 5,000 observations.')
                points.append([float(row[k]) for k in ('x','y','z')])
        case=build_from_points(points,label=args.label)
        case.update(schema='stemloom.case/1',source_sha256=source_hashes(),input_sha256=hashlib.sha256(args.input.read_bytes()).hexdigest())
        case['units']['positions']=args.units
        case['axes']+=' Coordinate unit label: '+args.units+'. No numeric rescaling was applied.'
        text=validate_case(case).decode('utf-8')
    elif args.command=='inspect-x3d':
        frame=from_x3d(args.input.read_text(encoding='utf-8'))
        text=json.dumps({'schema':'stemloom.geometry-inspection/1','frame':frame,
                         'scope':'Geometry decoded; scientific fields and witnesses not reconstructed.'},indent=2,ensure_ascii=False,allow_nan=False)
    else:
        if args.packet.stat().st_size>64*1024*1024:raise ValueError('Packet exceeds 64 MiB budget.')
        case=json.loads(args.packet.read_text(encoding='utf-8'))
        f=args.format
        if f in ('x3d4','x3d33'):text=to_x3d(case,args.frame,version='4.0' if f=='x3d4' else '3.3')
        elif f=='vti':text=dataset_to_vti(case['datasets']['velocity_grid'])
        else:text={'vtp':to_vtp,'ply':to_ply,'obj':to_obj,'csv':points_csv}[f](case,args.frame)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text,encoding='utf-8')
    print(json.dumps({'file':str(args.output),'bytes':args.output.stat().st_size,'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__=='__main__':main()
