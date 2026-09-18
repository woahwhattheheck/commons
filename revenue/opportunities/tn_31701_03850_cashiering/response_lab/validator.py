from __future__ import annotations
import csv,hashlib,json,re
from pathlib import Path
SCHEMA='tn-31701-03850-response-lab/v1';POSTURES={'PRIME_PRODUCT_EVIDENCE','SPECIALIST_WORKSHARE','DEMO_SUPPORTED','GAP_QUESTION'}
DOMAINS={'AUDIT_SECURITY','COMPATIBILITY','INTERFACES','DASHBOARDS_REPORTING','DOCUMENT_SOLUTIONS','FUNCTIONAL','FINANCIAL_ACCOUNTING'}
OPTIONAL={20,35,47,58,75,76,77,82};FALSE_AUTH={'buyer_contact':False,'question_submission':False,'response_submission':False,'partner_contact':False,'contract_acceptance':False,'payment':False,'revenue_recognized':False}
class ResponseLabError(ValueError):pass
def _pairs(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ResponseLabError(f'duplicate JSON key: {k}')
  d[k]=v
 return d
def load_json(path):
 return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=_pairs,parse_constant=lambda x:(_ for _ in ()).throw(ResponseLabError(f'nonfinite: {x}')))
def load_rows(path):
 try: rows=list(csv.DictReader(Path(path).read_text(encoding='utf-8').splitlines()))
 except (OSError,csv.Error,UnicodeError) as e:raise ResponseLabError('invalid crosswalk CSV') from e
 if not rows or set(rows[0])!={'id','domain','required','summary','posture'}:raise ResponseLabError('crosswalk header drift')
 return rows
def validate(manifest_path):
 mp=Path(manifest_path);doc=load_json(mp)
 keys={'schema','solicitation','title','buyer','source_url','issued','questions_due_ct','state_answers','response_due_ct','response_page_limit','minimum_font_points','question_submissions_per_vendor','embedded_external_landing_pages_allowed','commercial','authority','crosswalk'}
 if type(doc) is not dict or set(doc)!=keys:raise ResponseLabError('top-level fields drifted')
 if doc['schema']!=SCHEMA or doc['solicitation']!='31701-03850':raise ResponseLabError('wrong solicitation/schema')
 if doc['questions_due_ct']!='2026-09-25T14:00:00-05:00' or doc['response_due_ct']!='2026-10-05T14:00:00-05:00':raise ResponseLabError('deadline drift')
 if (doc['response_page_limit'],doc['minimum_font_points'],doc['question_submissions_per_vendor'],doc['embedded_external_landing_pages_allowed'])!=(20,12,1,False):raise ResponseLabError('submission constraint drift')
 cw=doc['crosswalk']
 if type(cw) is not dict or set(cw)!={'file','sha256','row_count'} or cw['file']!='requirement_crosswalk.csv' or cw['row_count']!=120 or not re.fullmatch(r'[0-9a-f]{64}',str(cw['sha256'])):raise ResponseLabError('crosswalk binding drift')
 cp=mp.with_name(cw['file']);raw=cp.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=cw['sha256']:raise ResponseLabError('crosswalk SHA drift')
 rows=load_rows(cp)
 try: ids=[int(r['id']) for r in rows]
 except (TypeError,ValueError) as e:raise ResponseLabError('invalid requirement id') from e
 if len(rows)!=120 or ids!=list(range(1,121)):raise ResponseLabError('requirements must be exact ordered 1..120')
 for i,r in zip(ids,rows):
  if r['domain'] not in DOMAINS or r['posture'] not in POSTURES or r['required'] not in {'Y','N'} or not r['summary'].strip():raise ResponseLabError('crosswalk vocabulary drift')
  if (r['required']=='Y')!=(i not in OPTIONAL):raise ResponseLabError('optional-marker drift')
 if doc['commercial']!={'model':'partner-first specialist workshare','fixed_price_usd':25000,'state':'PROPOSED_NOT_ACCEPTED'}:raise ResponseLabError('commercial truth drift')
 if doc['authority']!=FALSE_AUTH:raise ResponseLabError('authority must remain false')
 if not re.fullmatch(r'https://www\.tn\.gov/.+',doc['source_url']):raise ResponseLabError('source must remain first-party Tennessee URL')
 return {'requirements':120,'required':112,'optional':8,'postures':{p:sum(r['posture']==p for r in rows) for p in sorted(POSTURES)},'authority':FALSE_AUTH.copy()}
if __name__=='__main__':
 import sys;print(json.dumps(validate(sys.argv[1] if len(sys.argv)>1 else Path(__file__).with_name('response_manifest.json')),sort_keys=True))
