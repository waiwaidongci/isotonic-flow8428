from sqlalchemy import select
from fastapi import HTTPException
from src.models import MonotoneRun,ValidationNote
from src.utils.serialize import row
from .audit import record

def create_note(db,data,actor):
 run=db.get(MonotoneRun,data.run_id)
 if not run or run.status!='completed':raise HTTPException(422,'仅成功运行可创建复验说明')
 if db.scalar(select(ValidationNote).where(ValidationNote.name==data.name)):raise HTTPException(409,'复验说明名称已存在')
 note=ValidationNote(**data.model_dump(),result_snapshot=run.result,created_by=actor);db.add(note);db.commit();record(db,actor,'note.created',{'note_id':note.id});return row(note)

def approve_note(db,id,data,actor):
 note=db.scalar(select(ValidationNote).where(ValidationNote.id==id).with_for_update())
 if not note:raise HTTPException(404,'说明不存在')
 if note.status!='draft':raise HTTPException(409,'说明已审阅，不可重复审批；请另建新说明')
 note.status=data.status;note.review_note=data.review_note;db.commit();record(db,actor,'note.reviewed',{'note_id':id,'status':note.status});return row(note)
