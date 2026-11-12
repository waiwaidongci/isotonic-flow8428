from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.models import AuditLog
from src.controllers.dependencies import current_user
from src.utils.serialize import row
router=APIRouter()
@router.get('/audit')
def logs(db:Session=Depends(get_db),user=Depends(current_user)):return [row(x) for x in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(200))]
