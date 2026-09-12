from pathlib import Path
import json, re

PATH=Path(__file__).resolve().parent.parent/"KNOWLEDGE_LIBRARY_V8.json"

def load():
    return json.loads(PATH.read_text(encoding="utf-8"))["guides"]

def list_guides(module=None, system=None, product=None):
    out=[]
    for g in load():
        if module and module not in g.get("diagnostic_modules",[]): continue
        if system and system not in g.get("systems",[]): continue
        if product and product not in g.get("products",[]): continue
        out.append(g)
    return out

def get_guide(guide_id):
    return next((g for g in load() if g["id"]==guide_id),None)

def search_guides(query):
    words=[w for w in re.findall(r"[a-z0-9]+",(query or "").lower()) if len(w)>2]
    scored=[]
    for g in load():
        hay=" ".join([
            g["title"],g["summary"]," ".join(g.get("products",[])),
            " ".join(g.get("systems",[]))," ".join(g.get("components",[])),
            " ".join(g.get("diagnostic_modules",[]))
        ]).lower()
        score=sum(1 for w in words if w in hay)
        if score: scored.append((score,g))
    scored.sort(key=lambda x:(-x[0],x[1]["title"]))
    return [g for _,g in scored]

def guides_for_diagnosis(module_id, system_id=None):
    candidates=list_guides(module=module_id)
    if system_id:
        candidates.sort(key=lambda g: system_id not in g.get("systems",[]))
    return candidates
