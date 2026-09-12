import json, uuid
from sqlalchemy.orm import Session
from .models import AuditEvent
def log(db:Session, company_id:int, user_id:int|None, action:str, entity_type="", entity_id="", detail=None):
    e=AuditEvent(id=str(uuid.uuid4()),company_id=company_id,user_id=user_id,action=action,
                 entity_type=entity_type,entity_id=str(entity_id or ""),detail_json=json.dumps(detail or {}))
    db.add(e)
    return e
