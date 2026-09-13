"""Import a private, searchable PDF library without changing diagnostic rules."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from pypdf import PdfReader

def save_manifest(path, entries):
    """Readers see either the old complete catalogue or the new complete one."""
    pending=path.with_suffix('.json.pending')
    pending.write_text(json.dumps({'schema_version':'1.0','imported_at':datetime.now(timezone.utc).isoformat(),'documents':entries},ensure_ascii=False),encoding='utf-8')
    pending.replace(path)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('destination',type=Path)
    parser.add_argument('--company-id',type=int,required=True)
    parser.add_argument('--manufacturer',default='The Residence Collection')
    parser.add_argument('--pdftotext',default=None)
    args=parser.parse_args()
    if args.pdftotext and not Path(args.pdftotext).is_file(): args.pdftotext=None
    args.destination.mkdir(parents=True,exist_ok=True)
    manifest_path=args.destination/'manifest.json'
    entries=json.loads(manifest_path.read_text(encoding='utf-8'))['documents'] if manifest_path.exists() else []
    hashes={e['sha256']:e for e in entries}
    errors=[]
    for path in sorted(args.source.rglob('*')):
        if path.suffix.lower() not in {'.pdf','.mp4','.mov','.webm'}: continue
        with path.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest in hashes:
            old=hashes[digest]
            old.setdefault('alternate_sources',[])
            reference=str(path.relative_to(args.source))
            if reference!=old['source_reference'] and reference not in old['alternate_sources']: old['alternate_sources'].append(reference)
            if args.company_id not in old['company_ids']: old['company_ids'].append(args.company_id)
            print('Already indexed: '+path.name,flush=True)
            continue
        identifier='doc-'+digest[:16]
        destination=args.destination/(identifier+path.suffix.lower())
        if not destination.exists(): shutil.copyfile(path,destination)
        pages=[]
        if path.suffix.lower()=='.pdf':
            try:
                reader=PdfReader(destination)
                if args.pdftotext:
                    result=subprocess.run([args.pdftotext,'-layout','-enc','UTF-8',str(destination),'-'],capture_output=True,timeout=180)
                    if result.returncode: raise ValueError(result.stderr.decode('utf-8','replace')[:200])
                    chunks=result.stdout.decode('utf-8','replace').split('\f')
                    pages=[{'page':i+1,'text':re.sub(r'\s+',' ',chunks[i] if i<len(chunks) else '').strip()} for i in range(len(reader.pages))]
                else:
                    try:
                        import pypdfium2 as pdfium
                        pdf=pdfium.PdfDocument(destination)
                        for i in range(len(pdf)):
                            page=pdf[i];textpage=page.get_textpage()
                            pages.append({'page':i+1,'text':re.sub(r'\s+',' ',textpage.get_text_range()).strip()})
                            textpage.close();page.close()
                        pdf.close()
                    except ImportError:
                        pages=[{'page':i+1,'text':re.sub(r'\s+',' ',page.extract_text() or '').strip()} for i,page in enumerate(reader.pages)]
            except Exception as error:
                errors.append({'file':path.name,'error':str(error)})
                print('Could not index text: '+path.name+' '+str(error),flush=True)
        title=path.stem.replace('_',' ').strip()
        systems=re.findall(r'\bR[279]\b',title.upper()) if args.manufacturer=='The Residence Collection' else re.findall(r'\b(?:58BD[F]?|58BW(?:ST)?|67CL32|77ID|77IWE?|BSC94|BSF70|C70S|F82|GT55(?:TB)?|S140|SC156|S67|SG52|SL52|PREMILINE|INFINIUM)\b',title.upper())
        revision=re.search(r'Issue\s+(\d+)',title,re.I)
        publication=re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2}',title,re.I)
        entry={'id':identifier,'title':title,'category':path.parent.name,'manufacturer':args.manufacturer,'systems':systems or (['R2','R7','R9'] if args.manufacturer=='The Residence Collection' else []),'revision':'Issue '+revision.group(1) if revision else 'Not stated in filename','publication_date':publication.group(0) if publication else None,'source_filename':path.name,'source_reference':str(path.relative_to(args.source)),'sha256':digest,'filename':destination.name,'page_count':len(pages),'size_bytes':path.stat().st_size,'verification_status':'pending_review','metadata_note':'Category, system and issue are indexed from the supplied filename. Source contents require technical review before rules are changed.','company_ids':[args.company_id],'pages':pages,'media_type':'pdf' if path.suffix.lower()=='.pdf' else 'video','text_indexed':any(p['text'] for p in pages)}
        entries.append(entry);hashes[digest]=entry
        print(f'Indexed {len(pages):3} pages: {title}',flush=True)
        save_manifest(manifest_path,entries)
    save_manifest(manifest_path,entries)
    if errors: (args.destination/'import-errors.json').write_text(json.dumps(errors,indent=2),encoding='utf-8')
    print(f'Library: {len(entries)} files, {sum(e["page_count"] for e in entries)} pages.',flush=True)

if __name__=='__main__': main()
