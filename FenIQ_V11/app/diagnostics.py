from dataclasses import dataclass
from typing import Any

# FenIQ V6 Technical Intelligence Engine
# Thresholds marked "FenIQ working rule" are configurable diagnostic rules,
# not manufacturer specifications. Manufacturer-specific values should only
# be added after document/version verification.

MODULES = {
    "french_door_clearance": {
        "name": "French Door Sash Clearance & Alignment",
        "products": ["French Door"],
        "checks": [
            {"key":"top_clearance","label":"Top clearance","type":"number","unit":"mm","required":True},
            {"key":"bottom_clearance","label":"Bottom clearance","type":"number","unit":"mm","required":True},
            {"key":"meeting_sightline","label":"Master/slave meeting sightline","type":"number","unit":"mm","required":True},
            {"key":"hinge_limit","label":"Hinge adjustment exhausted?","type":"bool","required":True},
            {"key":"frame_geometry","label":"Frame level, square and plumb?","type":"choice","options":["Yes","No","Unknown"],"required":True},
            {"key":"threshold_type","label":"Threshold type","type":"choice","options":["Low aluminium","Standard","Unknown"],"required":False},
            {"key":"sash_dimensions_verified","label":"Sash dimensions independently verified?","type":"bool","required":True},
        ],
        "rules": [
            {"id":"FD01","when":{"bottom_clearance":{"lte":1}},"points":18,"evidence":"Bottom clearance is critically restricted."},
            {"id":"FD02","when":{"top_clearance":{"lte":2}},"points":12,"evidence":"Top clearance is restricted."},
            {"id":"FD03","when":{"meeting_sightline":{"lt":6}},"points":12,"evidence":"Meeting sightline is below the FenIQ working target of 6 mm."},
            {"id":"FD04","when":{"hinge_limit":True},"points":14,"evidence":"Available hinge adjustment has been exhausted."},
            {"id":"FD05","when":{"frame_geometry":"Yes"},"points":10,"evidence":"Frame geometry has been checked and reported acceptable."},
            {"id":"FD06","when":{"threshold_type":"Low aluminium"},"points":4,"evidence":"Low aluminium threshold recorded; clearance sensitivity should be checked."},
            {"id":"FD07","when":{"sash_dimensions_verified":True},"points":10,"evidence":"Sash dimensions have been independently verified."},
        ],
        "diagnoses": [
            {
                "id":"oversized_sash",
                "title":"Oversized sash / insufficient manufacturing clearance",
                "requires":["hinge_limit","sash_dimensions_verified"],
                "min_score":68,
                "recommendation":"Compare verified sash and frame dimensions against the approved manufacturing specification. If geometry is acceptable and adjustment is exhausted, escalate for an engineer-approved remake decision.",
                "repair_steps":["Confirm frame level, square and plumb","Record top and bottom clearances","Record meeting sightline","Confirm hinge adjustment range","Check toe-and-heel / glass packing","Verify sash and frame dimensions","Engineer approves or rejects remake"],
                "commercial_gate":True
            }
        ],
        "fallback":{
            "title":"Sash alignment / installation geometry requires further correction",
            "recommendation":"Correct alignment, frame geometry or glazing support before concluding that the sash requires remanufacture.",
            "repair_steps":["Check frame geometry","Check hinge positions","Check glass packing","Adjust sash","Re-measure all clearances","Re-test master/slave operation"]
        }
    },
    "locking_camb_keep": {
        "name":"Locking Camb & Keep Diagnosis",
        "products":["Window","French Door","Residential Door"],
        "checks":[
            {"key":"camb_catching","label":"Camb/roller catching frame or keep?","type":"bool","required":True},
            {"key":"works_open","label":"Mechanism operates freely with sash/door open?","type":"bool","required":True},
            {"key":"compression_even","label":"Compression even around closing edge?","type":"choice","options":["Yes","No","Unknown"],"required":True},
            {"key":"witness_marks","label":"Visible witness marks at locking point?","type":"bool","required":False},
            {"key":"keep_position_verified","label":"Keep position checked against locking point?","type":"bool","required":True}
        ],
        "rules":[
            {"id":"LK01","when":{"camb_catching":True},"points":22,"evidence":"Locking point is catching."},
            {"id":"LK02","when":{"works_open":True},"points":24,"evidence":"Mechanism operates freely when open, increasing likelihood of alignment/keep interference."},
            {"id":"LK03","when":{"compression_even":"No"},"points":14,"evidence":"Compression is uneven."},
            {"id":"LK04","when":{"witness_marks":True},"points":12,"evidence":"Witness marks support local locking-point interference."},
            {"id":"LK05","when":{"keep_position_verified":True},"points":8,"evidence":"Keep position has been physically checked."}
        ],
        "diagnoses":[
            {"id":"keep_alignment","title":"Locking point / keep alignment issue","requires":["works_open"],"min_score":55,
             "recommendation":"Adjust the locking point or keep only after confirming sash alignment and compression. Re-test without forcing the handle.",
             "repair_steps":["Test mechanism open","Inspect witness marks","Check sash alignment","Check camb eccentric adjustment","Check keep position","Verify gasket compression","Cycle lock repeatedly"],"commercial_gate":False}
        ],
        "fallback":{"title":"Lock mechanism requires further investigation","recommendation":"Inspect gearbox, extensions and locking points before replacing components.","repair_steps":["Test open","Inspect gearbox drive","Inspect extensions","Inspect keeps","Confirm component specification"]}
    },
    "toe_and_heel": {
        "name":"Toe & Heel / Glazing Support",
        "products":["Window","French Door","Residential Door","Bifold"],
        "checks":[
            {"key":"handle_side_drop","label":"Handle side dropped?","type":"bool","required":True},
            {"key":"frame_square","label":"Frame square?","type":"choice","options":["Yes","No","Unknown"],"required":True},
            {"key":"packer_positions_correct","label":"Load-bearing packer positions correct?","type":"choice","options":["Yes","No","Unknown"],"required":True},
            {"key":"glass_secure","label":"Glass unit secure before deglazing?","type":"bool","required":True}
        ],
        "rules":[
            {"id":"TH01","when":{"handle_side_drop":True},"points":28,"evidence":"Handle-side sash drop is present."},
            {"id":"TH02","when":{"packer_positions_correct":"No"},"points":35,"evidence":"Load-bearing packer arrangement requires correction."},
            {"id":"TH03","when":{"frame_square":"Yes"},"points":12,"evidence":"Frame is reported square, increasing likelihood of sash/glazing support issue."}
        ],
        "diagnoses":[
            {"id":"toe_heel_required","title":"Toe-and-heel correction required","requires":["glass_secure"],"min_score":50,
             "recommendation":"Correct the glazing support arrangement to transfer the unit load through the sash, then verify diagonal and operating clearances.",
             "repair_steps":["Secure sash and glass","Remove beads safely","Record existing packer positions","Correct load-bearing packer arrangement","Refit beads","Check sash diagonal","Test operation and locking"],"commercial_gate":False}
        ],
        "fallback":{"title":"Sash drop requires further geometry checks","recommendation":"Check frame square, hinge condition and glazing support before adjustment.","repair_steps":["Check frame","Check hinges","Check glazing support","Measure diagonals"]}
    },
    "multipoint_lock": {
        "name":"Multipoint Lock / Gearbox",
        "products":["Window","French Door","Residential Door"],
        "checks":[
            {"key":"drive_failure","label":"Handle moves but locking points do not drive?","type":"bool","required":True},
            {"key":"works_open","label":"Mechanism works correctly when open?","type":"bool","required":True},
            {"key":"clunky","label":"Grinding/clunky internal operation?","type":"bool","required":False},
            {"key":"extensions_intact","label":"Extensions/shootbolts visually intact?","type":"choice","options":["Yes","No","Unknown"],"required":True}
        ],
        "rules":[
            {"id":"MP01","when":{"drive_failure":True},"points":38,"evidence":"Handle input is not driving the locking points."},
            {"id":"MP02","when":{"works_open":False},"points":26,"evidence":"Fault persists with the sash/door open."},
            {"id":"MP03","when":{"clunky":True},"points":14,"evidence":"Internal operation is clunky/grinding."},
            {"id":"MP04","when":{"extensions_intact":"Yes"},"points":8,"evidence":"Visible extensions appear intact."}
        ],
        "diagnoses":[
            {"id":"gearbox_failure","title":"Likely gearbox / multipoint mechanism failure","requires":["drive_failure"],"min_score":60,
             "recommendation":"Confirm exact mechanism specification and failure point before ordering a replacement.",
             "repair_steps":["Test mechanism open","Inspect spindle/handle drive","Inspect gearbox","Inspect extensions and shootbolts","Check keeps for secondary interference","Confirm exact replacement specification"],"commercial_gate":True}
        ],
        "fallback":{"title":"Alignment / keep loading may be affecting lock operation","recommendation":"Remove frame loading from the mechanism and re-test before replacing the lock.","repair_steps":["Test open","Check keeps","Check compression","Check sash alignment","Re-test"]}
    },
    "gasket_compression": {
        "name":"Gasket, Draught & Compression",
        "products":["Window","French Door","Residential Door","Bifold","Sliding Door"],
        "checks":[
            {"key":"visible_shrinkage","label":"Visible gasket shrinkage?","type":"bool","required":True},
            {"key":"mitre_gaps","label":"Gaps at gasket mitres/corners?","type":"bool","required":True},
            {"key":"compression_even","label":"Compression even?","type":"choice","options":["Yes","No","Unknown"],"required":True},
            {"key":"gasket_damaged","label":"Gasket split/damaged?","type":"bool","required":False}
        ],
        "rules":[
            {"id":"GK01","when":{"visible_shrinkage":True},"points":28,"evidence":"Visible gasket shrinkage recorded."},
            {"id":"GK02","when":{"mitre_gaps":True},"points":24,"evidence":"Gaps are present at gasket joints/corners."},
            {"id":"GK03","when":{"compression_even":"No"},"points":20,"evidence":"Compression is uneven."},
            {"id":"GK04","when":{"gasket_damaged":True},"points":20,"evidence":"Gasket is physically damaged."}
        ],
        "diagnoses":[
            {"id":"gasket_fault","title":"Gasket / compression fault","requires":[],"min_score":45,
             "recommendation":"Correct sash compression and replace/refit damaged or shrunken gasket as appropriate. Use only approved maintenance products.",
             "repair_steps":["Inspect full gasket perimeter","Check corners/mitres","Check locking compression","Refit or replace affected gasket","Apply approved maintenance product if applicable","Re-test operation and seal"],"commercial_gate":False}
        ],
        "fallback":{"title":"No clear gasket fault established","recommendation":"Continue with air/water path and sash-compression investigation.","repair_steps":["Check compression","Check drainage","Check interfaces","Check installation perimeter"]}
    },
    "friction_stay_hinge": {
        "name":"Friction Stay / Window Hinge",
        "products":["Window"],
        "checks":[
            {"key":"sash_catching","label":"Sash catching frame?","type":"bool","required":True},
            {"key":"hinge_damage","label":"Hinge/friction stay visibly bent or damaged?","type":"bool","required":True},
            {"key":"closing_even","label":"Sash closes evenly around frame?","type":"bool","required":True},
            {"key":"fixings_secure","label":"Hinge fixings secure?","type":"choice","options":["Yes","No","Unknown"],"required":True}
        ],
        "rules":[
            {"id":"HG01","when":{"sash_catching":True},"points":22,"evidence":"Sash is catching the frame."},
            {"id":"HG02","when":{"hinge_damage":True},"points":40,"evidence":"Visible hinge/friction-stay damage recorded."},
            {"id":"HG03","when":{"closing_even":False},"points":16,"evidence":"Closing line is uneven."},
            {"id":"HG04","when":{"fixings_secure":"No"},"points":22,"evidence":"Hinge fixings are not secure."}
        ],
        "diagnoses":[
            {"id":"hinge_damage","title":"Damaged / insecure friction stay or hinge","requires":["hinge_damage"],"min_score":55,
             "recommendation":"Replace or correctly secure the hinge/friction stay using the verified hardware specification and fixing method.",
             "repair_steps":["Support sash","Identify hinge type/size","Inspect fixing substrate","Replace/secure hinge","Apply required final fixings","Check sash clearances","Test full opening and locking"],"commercial_gate":True}
        ],
        "fallback":{"title":"Window sash hinge adjustment / alignment required","recommendation":"Correct sash alignment and verify hinge fixing condition before replacing hardware.","repair_steps":["Check fixings","Check clearances","Check sash square","Adjust/reset","Test"]}
    },
    "bifold_alignment": {
        "name":"Bifold Panel Alignment",
        "products":["Bifold"],
        "checks":[
            {"key":"threshold_drag","label":"Panel dragging threshold?","type":"bool","required":True},
            {"key":"meeting_stiles","label":"Meeting stiles aligned?","type":"bool","required":True},
            {"key":"lift_to_lock","label":"Panel must be lifted to lock?","type":"bool","required":True},
            {"key":"track_level","label":"Head/threshold level?","type":"choice","options":["Yes","No","Unknown"],"required":True}
        ],
        "rules":[
            {"id":"BF01","when":{"threshold_drag":True},"points":25,"evidence":"Panel is dragging the threshold."},
            {"id":"BF02","when":{"meeting_stiles":False},"points":20,"evidence":"Meeting stiles are misaligned."},
            {"id":"BF03","when":{"lift_to_lock":True},"points":24,"evidence":"Panel requires lifting to lock."},
            {"id":"BF04","when":{"track_level":"Yes"},"points":10,"evidence":"Head/threshold reported level."}
        ],
        "diagnoses":[
            {"id":"bifold_alignment","title":"Bifold panel alignment / roller-height issue","requires":[],"min_score":45,
             "recommendation":"Check panel support, roller/hinge adjustment and glazing support before altering locking keeps.",
             "repair_steps":["Check head/threshold level","Measure panel clearances","Check rollers and hinges","Check toe-and-heel","Align meeting stiles","Test complete opening sequence and locks"],"commercial_gate":False}
        ],
        "fallback":{"title":"Bifold requires further installation/geometry checks","recommendation":"Check frame/track geometry and panel support.","repair_steps":["Check frame","Check tracks","Check panels","Check hardware"]}
    },
    "sliding_door": {
        "name":"Sliding Door Alignment",
        "products":["Sliding Door"],
        "checks":[
            {"key":"high_resistance","label":"High sliding resistance?","type":"bool","required":True},
            {"key":"heavy_gasket_contact","label":"Heavy sash/gasket contact?","type":"bool","required":True},
            {"key":"lock_smooth","label":"Lock engages smoothly?","type":"bool","required":True},
            {"key":"sash_level","label":"Sliding sash level?","type":"choice","options":["Yes","No","Unknown"],"required":True}
        ],
        "rules":[
            {"id":"SD01","when":{"high_resistance":True},"points":25,"evidence":"High sliding resistance recorded."},
            {"id":"SD02","when":{"heavy_gasket_contact":True},"points":18,"evidence":"Heavy sash/gasket contact recorded."},
            {"id":"SD03","when":{"lock_smooth":False},"points":18,"evidence":"Lock engagement is not smooth."},
            {"id":"SD04","when":{"sash_level":"No"},"points":24,"evidence":"Sliding sash is not level."}
        ],
        "diagnoses":[
            {"id":"slider_alignment","title":"Sliding sash alignment / roller-height issue","requires":[],"min_score":45,
             "recommendation":"Correct roller height/sash level and gasket interference before replacing locking hardware.",
             "repair_steps":["Inspect track","Check roller condition","Measure sash level","Adjust rollers evenly","Check gasket contact","Align lock/keep","Test full travel"],"commercial_gate":False}
        ],
        "fallback":{"title":"Sliding door requires further mechanical investigation","recommendation":"Inspect rollers, track, gaskets and lock independently.","repair_steps":["Inspect track","Inspect rollers","Inspect gaskets","Test lock open/closed"]}
    }
}

def _match(actual: Any, condition: Any) -> bool:
    if isinstance(condition, dict):
        for op, expected in condition.items():
            try:
                a=float(actual); e=float(expected)
            except Exception:
                return False
            if op=="lte" and not a<=e:return False
            if op=="lt" and not a<e:return False
            if op=="gte" and not a>=e:return False
            if op=="gt" and not a>e:return False
            if op=="eq" and not a==e:return False
        return True
    return actual == condition

def _rule_matches(rule, answers):
    for key, cond in rule.get("when",{}).items():
        if key not in answers or not _match(answers[key],cond):
            return False
    return True

def diagnose(module_id: str, answers: dict):
    module=MODULES.get(module_id)
    if not module:
        raise KeyError("Unknown diagnostic module")

    missing=[c["key"] for c in module["checks"] if c.get("required") and c["key"] not in answers]
    if missing:
        return {"status":"incomplete","missing":missing,"module":module_id}

    score=20
    evidence=[]
    matched_rules=[]
    for rule in module["rules"]:
        if _rule_matches(rule,answers):
            score += rule["points"]
            evidence.append(rule["evidence"])
            matched_rules.append(rule["id"])
    score=min(97,score)

    chosen=None
    for d in module.get("diagnoses",[]):
        if score < d["min_score"]:
            continue
        req_ok=True
        for req in d.get("requires",[]):
            val=answers.get(req)
            if val not in (True,"Yes"):
                req_ok=False
                break
        if req_ok:
            chosen=d
            break

    if chosen:
        result={
            "status":"diagnosed","module":module_id,"module_name":module["name"],
            "diagnosis_id":chosen["id"],"title":chosen["title"],"confidence":score,
            "evidence":evidence,"matched_rules":matched_rules,
            "recommendation":chosen["recommendation"],"repair_steps":chosen["repair_steps"],
            "commercial_gate":chosen.get("commercial_gate",False),
            "engineer_approval_required":chosen.get("commercial_gate",False)
        }
    else:
        fb=module["fallback"]
        result={
            "status":"needs_further_checks","module":module_id,"module_name":module["name"],
            "diagnosis_id":"fallback","title":fb["title"],"confidence":min(score,74),
            "evidence":evidence,"matched_rules":matched_rules,
            "recommendation":fb["recommendation"],"repair_steps":fb["repair_steps"],
            "commercial_gate":False,"engineer_approval_required":False
        }
    result["rule_note"]="FenIQ working rules are decision-support logic and are not manufacturer specifications unless separately verified."
    return result

def catalogue():
    return [{"id":k,"name":v["name"],"products":v["products"],"checks":v["checks"]} for k,v in MODULES.items()]
