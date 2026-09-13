"""Company-scoped access to a separately stored, private technical library."""
import json
import os
import re
import threading
from io import BytesIO
from functools import lru_cache
from pathlib import Path
from fastapi import HTTPException

RENDER_LOCK=threading.RLock()

def root():
    value=os.getenv('FENIQ_DOCUMENT_ROOT')
    return Path(value).resolve() if value else None

@lru_cache(maxsize=4)
def _read(path,modified):
    return json.loads(Path(path).read_text(encoding='utf-8')).get('documents',[])

def records(company_id):
    directory=root()
    if not directory or not (directory/'manifest.json').is_file(): return []
    manifest=directory/'manifest.json'
    return [d for d in _read(str(manifest),manifest.stat().st_mtime_ns) if company_id in d.get('company_ids',[])]

def catalogue(company_id,query='',category='',system='',manufacturer=''):
    words=re.findall(r'\w+',query.lower())
    results=[]
    for doc in records(company_id):
        if manufacturer and doc['manufacturer']!=manufacturer: continue
        if category and doc['category']!=category: continue
        if system and system not in doc.get('systems',[]): continue
        meta=' '.join([doc['title'],doc['category'],doc['manufacturer'],*doc.get('systems',[])]).lower()
        matches=[]
        for page in doc.get('pages',[]):
            text=page['text']
            if words and all(word in text.lower() for word in words):
                start=max(0,min(text.lower().find(w) for w in words)-80)
                matches.append({'page':page['page'],'excerpt':text[start:start+320]})
        if words and not matches and not all(w in meta for w in words): continue
        public={k:v for k,v in doc.items() if k not in {'pages','filename','company_ids'}}
        public['matches']=matches[:5]
        public['matching_pages']=len(matches)
        public['url']='/api/documents/'+doc['id']+'/file'
        results.append(public)
    return results

def document_file(company_id,identifier):
    doc=next((d for d in records(company_id) if d['id']==identifier),None)
    if not doc: raise HTTPException(404,'Document not found')
    path=(root()/doc['filename']).resolve()
    if path.parent!=root() or not path.is_file(): raise HTTPException(404,'Document file not found')
    return path,doc

def page_image(company_id,identifier,page_number):
    path,doc=document_file(company_id,identifier)
    if path.suffix.lower()!='.pdf': raise HTTPException(400,'This document is not a PDF')
    import pypdfium2 as pdfium
    with RENDER_LOCK:
        pdf=pdfium.PdfDocument(path)
        try:
            if page_number<1 or page_number>len(pdf): raise HTTPException(404,'Page not found')
            page=pdf[page_number-1]
            try:
                scale=min(1.8,1800/max(page.get_size()))
                bitmap=page.render(scale=scale)
                try:
                    image=bitmap.to_pil()
                    output=BytesIO();image.save(output,format='PNG');image.close()
                    return output.getvalue()
                finally: bitmap.close()
            finally: page.close()
        finally: pdf.close()
