import json,re,runpy,sys
from collections import Counter,defaultdict
from difflib import SequenceMatcher
from pathlib import Path
root=Path(__file__).resolve().parents[1]
m=runpy.run_path(str(root/'build_bank.py'))
qs=m['QUESTIONS']; formulas=m['FORMULAS']
errors=[]; warnings=[]
req=['id','category','subcategory','topic','difficulty','interviewFrequency','questionType','question','shortAnswer','idealInterviewAnswer','deepExplanation','intuition','spanishExplanation','followUps','relatedConcepts','tags']
if len(qs)<1000: errors.append(f'Question count {len(qs)} < 1000')
ids=[q['id'] for q in qs]
if len(ids)!=len(set(ids)): errors.append('Duplicate IDs found')
for q in qs:
    miss=[k for k in req if k not in q or q[k] is None or (isinstance(q[k],str) and not q[k].strip())]
    if miss: errors.append(f"{q.get('id')}: missing {miss}")
    if q['difficulty'] not in range(1,6): errors.append(f"{q['id']}: invalid difficulty")
    if q['interviewFrequency'] not in range(1,6): errors.append(f"{q['id']}: invalid frequency")
# Exact normalized duplicates.
def norm(s): return re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()
seen={}
for q in qs:
    n=norm(q['question'])
    if n in seen: errors.append(f"Exact normalized duplicate: {seen[n]} / {q['id']}")
    else: seen[n]=q['id']
# Near duplicates only within same topic; catches accidental paraphrase inflation without treating
# common interview templates across different concepts as duplicates.
bytopic=defaultdict(list)
for q in qs: bytopic[q['topic']].append(q)
for topic,items in bytopic.items():
    for i in range(len(items)):
        for j in range(i+1,len(items)):
            a,b=norm(items[i]['question']),norm(items[j]['question'])
            if a==b: continue
            if SequenceMatcher(None,a,b).ratio()>.94:
                warnings.append(f"Near duplicate? {items[i]['id']} / {items[j]['id']}")
# Coverage gates from product spec.
c=Counter(q['category'] for q in qs); d=Counter(q['difficulty'] for q in qs); f=Counter(q['interviewFrequency'] for q in qs)
for cat,min_n in {'M&A':180,'Valuation':130,'Accounting':130,'Global Markets / Macro':110,'Fixed Income / Derivatives':90,'Financial Ratios':65,'Mental Math':35}.items():
    if c[cat]<min_n: errors.append(f'{cat}: {c[cat]} < {min_n}')
if sum(d[x] for x in (3,4,5)) < len(qs)*.55: errors.append('Insufficient Level 3–5 distribution')
if c['M&A'] != max(c.values()): errors.append('M&A is not the largest category')
# Known formula/answer checks.
checks={
'MM-02':'1,600','MM-07':'10%','MM-15':'2.5x','MM-22':'-4,500','MM-28':'14.9%',
'CASE-VAL-03':'1.708','CASE-MA-15':'2.09','CASE-ACC-01':'2.5'
}
lookup={q['id']:q for q in qs}
for k,v in checks.items():
    hay=(lookup[k]['shortAnswer']+' '+lookup[k]['deepExplanation'])
    if v not in hay: errors.append(f'Known-answer check failed {k}: expected {v}')
# Deterministic market-language check: flag simplistic universal statements in questions/answers.
for q in qs:
    txt=(q['idealInterviewAnswer']+' '+q['deepExplanation']).lower()
    if re.search(r'\brates rise[, ]+(therefore|so) stocks fall\b',txt): errors.append(f'Deterministic market rule in {q["id"]}')
# PWA files.
for rel in ['index.html','styles.css','app.js','manifest.webmanifest','service-worker.js','assets/icon-180.png','assets/icon-192.png','assets/icon-512.png','data/core.js']:
    if not (root/rel).exists(): errors.append(f'Missing PWA file {rel}')
report={'questions':len(qs),'formulas':len(formulas),'categories':dict(c),'difficulty':dict(d),'frequency':dict(f),'level_3_5':sum(d[x] for x in (3,4,5)),'near_duplicate_warnings':len(warnings),'errors':errors,'warning_samples':warnings[:20]}
print(json.dumps(report,indent=2,ensure_ascii=False))
(root/'tests'/'audit-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
sys.exit(1 if errors else 0)
