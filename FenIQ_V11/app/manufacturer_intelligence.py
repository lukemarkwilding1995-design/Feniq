from pathlib import Path
import json

CATALOGUE_PATH=Path(__file__).resolve().parent.parent/"MANUFACTURER_CATALOGUE_V7.json"

def load_catalogue():
    return json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))

def manufacturers():
    c=load_catalogue()
    return [{"id":m["id"],"name":m["name"],"status":m["status"]} for m in c["manufacturers"]]

def systems(manufacturer_id=None):
    c=load_catalogue(); out=[]
    for m in c["manufacturers"]:
        if manufacturer_id and m["id"]!=manufacturer_id: continue
        for s in m["systems"]:
            out.append({
                "manufacturer_id":m["id"],"manufacturer":m["name"],"manufacturer_status":m["status"],**s
            })
    return out

def route(manufacturer_id, system_id, symptom_text=""):
    matches=[x for x in systems(manufacturer_id) if x["id"]==system_id]
    if not matches:
        return {"status":"not_found"}
    s=matches[0]
    text=(symptom_text or "").lower()
    ranked=[]
    keywords={
      "french_door_clearance":["catch","threshold","clearance","oversize","sightline","sag"],
      "locking_camb_keep":["camb","keep","stiff","lock","catch","compression"],
      "toe_and_heel":["drop","dropped","sag","glass","packer"],
      "multipoint_lock":["gearbox","mechanism","handle","shootbolt","lock"],
      "gasket_compression":["gasket","draught","seal","shrink","compression"],
      "friction_stay_hinge":["hinge","friction","stay","sash","catch"],
      "sliding_door":["slide","slider","roller","track","drag"],
      "bifold_alignment":["bifold","panel","roller","threshold","stile"]
    }
    for module in s["recommended_modules"]:
        score=sum(1 for k in keywords.get(module,[]) if k in text)
        ranked.append((score,module))
    ranked.sort(reverse=True)
    return {
      "status":"routed",
      "manufacturer":s["manufacturer"],
      "system":s["name"],
      "verification_status":s["manufacturer_status"],
      "recommended_module":ranked[0][1] if ranked else s["recommended_modules"][0],
      "module_options":s["recommended_modules"],
      "field_patterns":s["field_patterns"],
      "notice":"Manufacturer/system routing is available, but technical limits remain pending source verification unless explicitly marked verified."
    }
