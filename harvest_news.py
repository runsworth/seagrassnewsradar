#!/usr/bin/env python3
from __future__ import annotations

import hashlib, html, json, os, re, time, unicodedata
from collections import Counter
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse, parse_qsl, urlencode, urlunparse

import feedparser
import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'docs' / 'data'
NEWS_FILE = DATA / 'news.json'
STATUS_FILE = DATA / 'status.json'
NOW = datetime.now(timezone.utc)
TODAY = NOW.date()
LOOKBACK_DAYS = int(os.getenv('LOOKBACK_DAYS', '4'))
INITIAL_LOOKBACK_DAYS = int(os.getenv('INITIAL_LOOKBACK_DAYS', '30'))
RETENTION_DAYS = int(os.getenv('RETENTION_DAYS', '180'))
TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
MAX_GDELT = min(int(os.getenv('MAX_GDELT_RECORDS', '250')), 250)
HEADERS = {'User-Agent': os.getenv('NEWS_RADAR_USER_AGENT', 'GlobalSeagrassNewsRadar/1.0')}

STRONG_TERMS = [
    'seagrass','sea grass','seagrasses','eelgrass','eel grass','seagrass meadow','seagrass bed',
    'marine angiosperm','marine phanerogam','pastos marinos','pasto marino','praderas marinas','pradera marina',
    'hierbas marinas','ervas marinhas','pradarias marinhas','herbiers marins','herbier marin','phanérogames marines',
    'seegras','seegraswiesen','zeegras','zeegrasvelden','ålegræs','ålegras','ålgräs','meriajokas',
    'trawy morskie','trawa morska','deniz çayırları','deniz çayırı','θαλάσσια λιβάδια','λιβάδια ποσειδωνίας',
    'морская трава','морские травы','морська трава','морські трави','padang lamun','lamun',
    'thảm cỏ biển','cỏ biển','หญ้าทะเล','アマモ場','アマモ','海草床','海草场','海草場','잘피밭','잘피',
    'समुद्री घास','সামুদ্রিক ঘাস','கடற்புல்','കടൽപ്പുല്ല്','مروج الأعشاب البحرية','nyasi bahari'
]
TAXA = [
    'zostera marina','zostera noltei','zostera japonica','zostera muelleri','zostera capensis',
    'posidonia oceanica','posidonia australis','halophila ovalis','halophila stipulacea','halophila decipiens',
    'halodule uninervis','halodule wrightii','thalassia testudinum','thalassia hemprichii','cymodocea nodosa',
    'cymodocea serrulata','cymodocea rotundata','syringodium filiforme','syringodium isoetifolium','enhalus acoroides',
    'thalassodendron ciliatum','amphibolis antarctica','phyllospadix','ruppia maritima'
]
GENERA = ['zostera','nanozostera','heterozostera','halophila','halodule','thalassia','cymodocea','syringodium','enhalus','thalassodendron','amphibolis','phyllospadix']
MARINE_CONTEXT = ['marine','ocean','coast','sea','lagoon','estuary','restor','habitat','meadow','ecosystem','biodiversity','fish','carbon','climate','water','shore','reef','conservation','marino','marina','marinhas','meer','kust','océan','海','ทะเล','biển','laut','bahari','мор','deniz','θάλασσ']

THEMES = {
 'Restoration':['restor','replant','transplant','nursery','seed','rehabilitat','restaur','restauro','restauración','restauração'],
 'Conservation & policy':['conservation','protect','policy','government','law','management plan','marine protected','conserv','protección','schutz','保護','보호'],
 'Climate & heat':['climate','warming','heatwave','heat wave','temperature','storm','climático','climatique','klima','calor','温暖化','기후'],
 'Blue carbon':['blue carbon','carbon credit','carbon stock','carbon storage','carbono azul','carbone bleu'],
 'Wildlife & biodiversity':['dugong','turtle','seahorse','fish','bird','biodiversity','wildlife','species','fauna'],
 'Fisheries & food':['fisher','fishery','fisheries','fishing','food security','catch','pesca','pêche','perikanan'],
 'Development & infrastructure':['dredg','port','harbour','harbor','development','construction','offshore wind','cable','pipeline','anchor'],
 'Pollution & water quality':['pollution','sewage','wastewater','nutrient','runoff','water quality','plastic','oil spill','contamin','eutroph'],
 'Science & discovery':['scientist','research','study','survey','mapping','satellite','discovery','university'],
 'Community & culture':['community','volunteer','citizen','school','local people','indigenous','traditional','education']
}

GOOGLE_LOCALES = [
 ('English','en-GB','GB','GB:en',['seagrass OR eelgrass','"Zostera marina" OR "Posidonia oceanica"']),
 ('English','en-US','US','US:en',['seagrass OR eelgrass','"Zostera marina" OR "Thalassia testudinum"']),
 ('Spanish','es','ES','ES:es',['pastos marinos OR praderas marinas','"Zostera marina" OR "Posidonia oceanica"']),
 ('Spanish','es-419','MX','MX:es-419',['pastos marinos OR praderas marinas','seagrass OR Zostera OR Halophila']),
 ('Portuguese','pt-PT','PT','PT:pt-150',['ervas marinhas OR pradarias marinhas','"Zostera marina" OR "Cymodocea nodosa"']),
 ('Portuguese','pt-BR','BR','BR:pt-419',['ervas marinhas OR pradarias marinhas','seagrass OR Halodule OR Halophila']),
 ('French','fr','FR','FR:fr',['herbiers marins OR phanérogames marines','"Zostera marina" OR "Posidonia oceanica"']),
 ('German','de','DE','DE:de',['Seegras OR Seegraswiesen','"Zostera marina"']),
 ('Italian','it','IT','IT:it',['praterie marine OR praterie di Posidonia','"Posidonia oceanica" OR "Cymodocea nodosa"']),
 ('Dutch','nl','NL','NL:nl',['zeegras OR zeegrasvelden','"Zostera marina"']),
 ('Danish','da','DK','DK:da',['ålegræs','"Zostera marina"']),('Swedish','sv','SE','SE:sv',['ålgräs','"Zostera marina"']),
 ('Norwegian','no','NO','NO:no',['ålegras','"Zostera marina"']),('Finnish','fi','FI','FI:fi',['meriajokas','"Zostera marina"']),
 ('Polish','pl','PL','PL:pl',['trawy morskie OR trawa morska','Zostera']),('Greek','el','GR','GR:el',['θαλάσσια λιβάδια OR λιβάδια Ποσειδωνίας','"Posidonia oceanica"']),
 ('Turkish','tr','TR','TR:tr',['deniz çayırları OR deniz çayırı','Zostera OR Posidonia']),('Russian','ru','RU','RU:ru',['морская трава OR морские травы OR зостера','Zostera OR Posidonia']),
 ('Arabic','ar','AE','AE:ar',['مروج الأعشاب البحرية','seagrass OR Halophila OR Halodule']),('Hindi','hi','IN','IN:hi',['समुद्री घास','seagrass OR Halophila OR Halodule']),
 ('Indonesian','id','ID','ID:id',['padang lamun OR lamun','seagrass OR Enhalus OR Thalassia']),('Malay','ms','MY','MY:ms',['padang lamun OR lamun','seagrass OR Enhalus OR Halophila']),
 ('Vietnamese','vi','VN','VN:vi',['thảm cỏ biển OR cỏ biển','seagrass OR Halophila']),('Thai','th','TH','TH:th',['หญ้าทะเล','seagrass OR Halophila OR Enhalus']),
 ('Japanese','ja','JP','JP:ja',['アマモ OR アマモ場','"Zostera marina"']),('Korean','ko','KR','KR:ko',['잘피 OR 잘피밭','"Zostera marina"']),
 ('Chinese','zh-CN','CN','CN:zh-Hans',['海草床 OR 海草场','Zostera OR Halophila']),('Chinese','zh-TW','TW','TW:zh-Hant',['海草床 OR 海草場','Zostera OR Halophila']),
 ('Swahili','sw','KE','KE:sw',['nyasi bahari','seagrass OR Thalassia OR Halophila'])
]

GDELT_QUERIES = [
 '("seagrass" OR "seagrass meadow" OR "seagrass bed" OR eelgrass OR "marine angiosperm" OR "marine phanerogam")',
 '("Zostera marina" OR "Zostera noltei" OR "Zostera japonica" OR "Posidonia oceanica" OR "Posidonia australis")',
 '("Halophila ovalis" OR "Halophila stipulacea" OR "Halodule uninervis" OR "Thalassia testudinum" OR "Thalassia hemprichii")',
 '("Cymodocea nodosa" OR "Cymodocea serrulata" OR "Enhalus acoroides" OR "Syringodium filiforme" OR Phyllospadix)'
]

def log(s): print(f'[{datetime.now(timezone.utc).strftime("%H:%M:%S")}] {s}', flush=True)
def clean(v): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',html.unescape(str(v or '')))).strip()
def norm(v): return re.sub(r'\s+',' ',re.sub(r'[^\w\s\-\u00C0-\uFFFF]',' ',unicodedata.normalize('NFKC',v or '').lower())).strip()

def canon(url):
    try:
        p=urlparse(url); q=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid'}]
        return urlunparse((p.scheme.lower() or 'https',p.netloc.lower(),re.sub(r'/+$','',p.path) or '/', '',urlencode(q),''))
    except: return url

def aid(url,title): return hashlib.sha1((canon(url) or norm(title)).encode('utf-8','ignore')).hexdigest()[:18]
def tkey(title): return re.sub(r'\s+-\s+[^-]{2,80}$','',norm(title))[:260]

def gdelt_date(v):
    for f in ('%Y%m%dT%H%M%SZ','%Y%m%d%H%M%S'):
        try: return datetime.strptime(v,f).replace(tzinfo=timezone.utc).isoformat()
        except: pass
    return v or NOW.isoformat()

def feed_date(e):
    for k in ('published','updated'):
        if e.get(k):
            try:
                d=parsedate_to_datetime(e[k]); d=d if d.tzinfo else d.replace(tzinfo=timezone.utc); return d.astimezone(timezone.utc).isoformat()
            except: pass
    return NOW.isoformat()

def score(title,desc=''):
    text,title_n=norm(title+' '+desc),norm(title); s=0
    for term in STRONG_TERMS:
        n=norm(term)
        if n in text: s += 6 if n in title_n else 3
    for term in TAXA:
        n=norm(term)
        if n in text: s += 8 if n in title_n else 4
    for g in GENERA:
        if g in text: s += 4 if g in title_n else 2
    if 'posidonia' in text and not any(c in text for c in MARINE_CONTEXT): s -= 7
    return s

def themes(title,desc=''):
    text=norm(title+' '+desc); out=[]
    for theme,terms in THEMES.items():
        if any(norm(x) in text for x in terms): out.append(theme)
    return out[:4] or ['General seagrass news']

def taxa(title,desc=''):
    text=norm(title+' '+desc); out=[x.title() for x in TAXA if norm(x) in text]
    if not out: out=[g.title() for g in GENERA if g in text]
    return out[:5]

def load_existing():
    if not NEWS_FILE.exists(): return {}
    try:
        p=json.loads(NEWS_FILE.read_text(encoding='utf-8')); return {x['id']:x for x in p.get('articles',[]) if x.get('id')}
    except Exception as e: log(f'Existing database unreadable: {e}'); return {}

def harvest_gdelt(days):
    base='https://api.gdeltproject.org/api/v2/doc/doc'; out=[]; seen=set(); meta={'name':'GDELT','ok':True,'fetched':0,'kept':0,'error':''}
    for q in GDELT_QUERIES:
        try:
            r=requests.get(base,params={'query':q,'mode':'artlist','format':'json','maxrecords':MAX_GDELT,'timespan':f'{days}d','sort':'datedesc'},headers=HEADERS,timeout=TIMEOUT); r.raise_for_status(); data=r.json(); arts=data.get('articles',[]) or []; meta['fetched']+=len(arts)
            for a in arts:
                title,url=clean(a.get('title')),canon(a.get('url',''))
                if not title or not url or (url,tkey(title)) in seen: continue
                seen.add((url,tkey(title))); s=score(title)
                out.append({'id':aid(url,title),'title':title,'url':url,'outlet':clean(a.get('domain')) or urlparse(url).netloc,'domain':clean(a.get('domain')) or urlparse(url).netloc,'published_at':gdelt_date(a.get('seendate','')),'language':clean(a.get('language')) or 'Unknown','source_country':clean(a.get('sourcecountry')) or 'Unknown','image':a.get('socialimage') or '','description':'','themes':themes(title),'taxa':taxa(title),'relevance':max(s,5),'discovery_sources':['GDELT'],'search_route':'GDELT translingual'})
            time.sleep(.3)
        except Exception as e: meta['ok']=False; meta['error']=str(e)[:300]; log(f'GDELT query failed: {e}')
    meta['kept']=len(out); return out,meta

def google_source(e):
    src=e.get('source')
    if isinstance(src,dict): return clean(src.get('title')) or 'Google News'
    m=re.search(r'\s+-\s+([^-]{2,80})$',clean(e.get('title'))); return m.group(1).strip() if m else 'Google News'

def harvest_google(days):
    out=[]; seen=set(); meta={'name':'Google News RSS','ok':True,'fetched':0,'kept':0,'feeds':0,'errors':[]}; cutoff=NOW-timedelta(days=days+1)
    for language,hl,gl,ceid,queries in GOOGLE_LOCALES:
        for q in queries:
            url='https://news.google.com/rss/search?q='+quote_plus(q)+'&hl='+quote_plus(hl)+'&gl='+quote_plus(gl)+'&ceid='+quote_plus(ceid)
            try:
                r=requests.get(url,headers=HEADERS,timeout=TIMEOUT); r.raise_for_status(); feed=feedparser.parse(r.content); meta['feeds']+=1; meta['fetched']+=len(feed.entries)
                for e in feed.entries:
                    title,link,desc=clean(e.get('title')),canon(e.get('link','')),clean(e.get('summary') or e.get('description') or '')
                    if not title or not link: continue
                    pub=feed_date(e)
                    try:
                        if datetime.fromisoformat(pub.replace('Z','+00:00')) < cutoff: continue
                    except: pass
                    if (link,tkey(title)) in seen: continue
                    seen.add((link,tkey(title))); s=score(title,desc)
                    if s<3: continue
                    out.append({'id':aid(link,title),'title':title,'url':link,'outlet':google_source(e),'domain':urlparse(link).netloc,'published_at':pub,'language':language,'source_country':gl,'image':'','description':desc[:500],'themes':themes(title,desc),'taxa':taxa(title,desc),'relevance':s,'discovery_sources':['Google News RSS'],'search_route':f'Google News {language} ({gl})'})
                time.sleep(.12)
            except Exception as e:
                meta['ok']=False
                if len(meta['errors'])<12: meta['errors'].append(f'{language}/{gl}: {str(e)[:120]}')
    meta['kept']=len(out); return out,meta

def merge(existing,incoming,baseline):
    merged=dict(existing); title_index={tkey(v.get('title','')):k for k,v in merged.items() if tkey(v.get('title',''))}
    for item in incoming:
        k=item['id']; tk=tkey(item['title']); target=k if k in merged else title_index.get(tk)
        if target:
            old=merged[target]; old['discovery_sources']=list(dict.fromkeys((old.get('discovery_sources') or [])+(item.get('discovery_sources') or []))); old['last_seen']=TODAY.isoformat(); old['themes']=list(dict.fromkeys((old.get('themes') or [])+(item.get('themes') or [])))[:5]; old['taxa']=list(dict.fromkeys((old.get('taxa') or [])+(item.get('taxa') or [])))[:6]
            for f in ('image','description','outlet','source_country','language'):
                if not old.get(f) and item.get(f): old[f]=item[f]
        else:
            item['first_seen']=TODAY.isoformat(); item['last_seen']=TODAY.isoformat(); item['baseline']=baseline; merged[k]=item; title_index[tk]=k
    return merged

def prune(items):
    cutoff=TODAY-timedelta(days=RETENTION_DAYS); out={}
    for k,x in items.items():
        try:
            if datetime.fromisoformat((x.get('published_at') or '')[:10]).date() < cutoff: continue
        except: pass
        out[k]=x
    return out

def stats(items):
    def mc(seq,n=None): return Counter(seq).most_common(n)
    return {'languages':mc(x.get('language') or 'Unknown' for x in items),'countries':mc(x.get('source_country') or 'Unknown' for x in items),'outlets':mc((x.get('outlet') or 'Unknown' for x in items),50),'themes':mc(t for x in items for t in x.get('themes',[])),'discovery_sources':mc(s for x in items for s in x.get('discovery_sources',[]))}

def main():
    DATA.mkdir(parents=True,exist_ok=True); existing=load_existing(); baseline=len(existing)==0; days=INITIAL_LOOKBACK_DAYS if baseline else LOOKBACK_DAYS
    log(('Initial baseline' if baseline else 'Daily')+f' harvest: {days}-day lookback')
    log('GDELT: searching translingual global news'); g,gm=harvest_gdelt(days); log(f'GDELT: kept {gm["kept"]} records')
    log('Google News RSS: searching native-language feeds'); n,nm=harvest_google(days); log(f'Google News RSS: kept {nm["kept"]} records from {nm["feeds"]} feeds')
    merged=prune(merge(existing,g+n,baseline)); items=sorted(merged.values(),key=lambda x:x.get('published_at') or '',reverse=True)
    if baseline:
        for x in items: x['baseline']=True
    new_today=sum(1 for x in items if x.get('first_seen')==TODAY.isoformat() and not x.get('baseline'))
    NEWS_FILE.write_text(json.dumps({'generated_at':NOW.isoformat(),'baseline_complete':True,'article_count':len(items),'new_today':new_today,'lookback_days_this_run':days,'articles':items,'stats':stats(items)},ensure_ascii=False,indent=2),encoding='utf-8')
    STATUS_FILE.write_text(json.dumps({'generated_at':NOW.isoformat(),'baseline_mode':baseline,'sources':{'gdelt':gm,'google_news_rss':nm},'coverage':{'gdelt_translingual_languages':65,'explicit_google_language_routes':len(set(x[0] for x in GOOGLE_LOCALES)),'explicit_google_locales':len(GOOGLE_LOCALES),'note':'GDELT provides translingual global search; Google News RSS adds explicit native-language searches.'}},ensure_ascii=False,indent=2),encoding='utf-8')
    log(f'Done: {len(items)} retained stories; {new_today} new discoveries today')
    if baseline: log('Initial stories marked as baseline history, not NEW TODAY.')

if __name__=='__main__': main()
