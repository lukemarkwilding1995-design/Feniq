from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .models import Customer, WorkOrder, ApprovalRequest, Notification, User, Job

def dashboard(db:Session, company_id:int):
    def count(model,*conds):
        return db.scalar(select(func.count()).select_from(model).where(model.company_id==company_id,*conds)) or 0
    return {
      "customers":count(Customer),
      "work_orders":count(WorkOrder),
      "scheduled_open":count(WorkOrder,WorkOrder.status.in_(["New","Scheduled","In Progress"])),
      "pending_approvals":count(ApprovalRequest,ApprovalRequest.status=="Pending"),
      "unread_notifications":count(Notification,Notification.read==False),
      "commercial_note":"Billing is scaffolded as plan metadata only; no payment processor is connected in V10."
    }
