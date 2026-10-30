"""Validate Atlas content against a supplied, unmodified app schema snapshot."""
import argparse, collections, hashlib, json, pathlib, subprocess
import jsonschema
from PIL import Image

parser=argparse.ArgumentParser()
parser.add_argument('--schema',required=True)
parser.add_argument('--report',required=True)
args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parents[1]
schema_path=pathlib.Path(args.schema)
schema=json.loads(schema_path.read_text())
validator=jsonschema.Draft7Validator(schema,format_checker=jsonschema.FormatChecker())
errors=[];counts={};audio=[];images=[]
index=json.loads((root/'data/countries.json').read_text())
codes=[c['code'] for c in index['countries']]
assert len(codes)==len(set(codes))
sections=set(schema['properties']['section']['enum'])
parsed=0
for p in root.rglob('*.json'):
 json.loads(p.read_text());parsed+=1
for c in index['countries']:
 code=c['code']
 if not c.get('sections'):continue
 if set(c['sections'])!=sections:errors.append(f'{code}: missing section')
 n=collections.Counter()
 for section in c['sections']:
  m=c['documents'][section];p=root/m['path'];d=json.loads(p.read_text())
  if m['path']!=f'data/countries/{code}/{section}.json':errors.append(str(p)+': path')
  for e in validator.iter_errors(d):errors.append(f'{p.relative_to(root)}: {list(e.path)}: {e.message}')
  for field in ['revision','updated_at']:
   if d[field]!=m[field]:errors.append(f'{p}: {field}')
  if p.stat().st_size!=m['byte_length']:errors.append(f'{p}: byte_length')
  if d['country_code']!=code or d['section']!=section:errors.append(f'{p}: identity')
  ids=[t['id'] for t in d['topics']]
  if len(ids)!=len(set(ids)):errors.append(f'{p}: duplicate topic')
  for pt in d.get('map_points',[]):
   if pt['topic'] not in ids:errors.append(f'{p}: point topic')
  tables=d.get('key_tables',[])
  table_ids=[t['id'] for t in tables]
  if len(table_ids)!=len(set(table_ids)):errors.append(f'{p}: duplicate key table')
  block_ids=[b['id'] for t in d['topics'] for b in t.get('blocks',[])]
  if len(block_ids)!=len(set(block_ids)):errors.append(f'{p}: duplicate block')
  n['sections']+=1;n['topics']+=len(ids);n['parts']+=sum(len(t['parts']) for t in d['topics'])
  n['key_tables']+=len(tables);n['key_rows']+=sum(len(t['rows']) for t in tables)
  for t in d['topics']:
   for b in t.get('blocks',[]):
    if b['type']=='table':n['topic_tables']+=1;n['topic_rows']+=len(b['rows']);tables.append(b)
  for t in tables:
   if any(len(row)!=len(t['columns']) for row in t['rows']):errors.append(f'{p}: row width {t["id"]}')
  for metric in d.get('metrics',[]):
   v=metric['value']
   if v is not None and metric['unit']=='percent':
    definition=metric['label']+' '+metric['definition']
    if 'رشد' in definition or 'تغییر' in definition:valid=v>=-100
    elif 'GDP' in definition:valid=v>=0
    else:valid=0<=v<=100
    if not valid:errors.append(f'{p}: percent domain {metric["id"]}')
  # App reader imposes a 4 MiB download ceiling.
  if p.stat().st_size>4*1024*1024:errors.append(f'{p}: app download limit')
 counts[code]=dict(n)

# Decode every packaged raster and audio file; preserve SVGs as source assets.
for p in sorted((root/'assets').rglob('*')):
 if p.suffix.lower() in ['.webp','.png','.jpg','.jpeg']:
  try:
   with Image.open(p) as im:im.load();images.append(dict(path=str(p.relative_to(root)),format=im.format,width=im.width,height=im.height,bytes=p.stat().st_size))
  except Exception as e:errors.append(f'{p}: image decode {e}')
 elif p.suffix.lower() in ['.ogg','.mp3','.m4a']:
  r=subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],capture_output=True,text=True)
  if r.returncode:errors.append(f'{p}: audio decode {r.stderr}')
  q=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name','-of','json',str(p)]))
  audio.append(dict(path=str(p.relative_to(root)),duration_seconds=float(q['format']['duration']),streams=q['streams']))

missing=[]
raster_by_path={x['path']:x for x in images}
for photo in json.loads((root/'data/photos.json').read_text()).values():
 path=photo.get('src')
 if path in raster_by_path:
  actual=raster_by_path[path]
  for dimension in ['width','height']:
   if dimension in photo and photo[dimension]!=actual[dimension]:errors.append(f'{path}: manifest {dimension}')
audio_by_path={x['path']:x for x in audio}
def walk(x):
 if isinstance(x,dict):
  asset=x.get('src',x.get('url'))
  if isinstance(asset,str) and asset in raster_by_path:
   for dimension in ['width','height']:
    if dimension in x and x[dimension]!=raster_by_path[asset][dimension]:errors.append(f'{asset}: image {dimension}')
  if isinstance(asset,str) and asset.startswith('assets/') and 'byte_length' in x and (root/asset).is_file():
   if x['byte_length']!=(root/asset).stat().st_size:errors.append(f'{asset}: asset byte_length')
  if x.get('type')=='audio' and x.get('url') in audio_by_path and 'duration_seconds' in x:
   if abs(x['duration_seconds']-audio_by_path[x['url']]['duration_seconds'])>1:errors.append(f'{x["url"]}: duration metadata')
  for k,v in x.items():
   if isinstance(v,str) and v.startswith('assets/') and '<' not in v and not (root/v).is_file():missing.append(v)
   walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
for p in (root/'data').rglob('*.json'):walk(json.loads(p.read_text()))
errors.extend('Missing asset: '+p for p in sorted(set(missing)))

mapdata=json.loads((root/'region-map.json').read_text())
features={f['properties']['code']:f for f in mapdata['features']}
mapchecks={}
def inside(point,ring):
 x,y=point;hit=False;j=len(ring)-1
 for i,(xi,yi) in enumerate(ring):
  xj,yj=ring[j]
  if (yi>y)!=(yj>y) and x<(xj-xi)*(y-yi)/(yj-yi)+xi:hit=not hit
  j=i
 return hit
for code,point in [('IRN',(51.389,35.689)),('ITA',(12.49,41.89)),('JPN',(139.692,35.69))]:
 f=features[code];g=f['geometry'];polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
 hit=any(inside(point,rings[0]) and not any(inside(point,h) for h in rings[1:]) for rings in polys)
 coords=[xy for poly in polys for ring in poly for xy in ring]
 valid=all(-180<=xy[0]<=180 and -90<=xy[1]<=90 for xy in coords)
 closed=all(ring[0]==ring[-1] for poly in polys for ring in poly)
 mapchecks[code]=dict(type=g['type'],polygons=len(polys),capital_inside=hit,valid_coordinate_ranges=valid,closed_rings=closed)
 if not(hit and valid and closed):errors.append(f'{code}: map geometry')
report=dict(checked_at='2026-10-30',schema_sha256=hashlib.sha256(schema_path.read_bytes()).hexdigest(),schema_origin='arash377/atlas:master/app/src/main/assets/data/schemas/country-section-v1.schema.json',parsed_json_files=parsed,counts=counts,decoded_rasters=images,decoded_audio=audio,map_checks=mapchecks,errors=errors,android_build_run=False,device_test_run=False)
pathlib.Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['parsed_json_files','counts','map_checks','errors']},ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
