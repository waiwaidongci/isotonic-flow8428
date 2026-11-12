from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.models import FlowStudy,DoseLevel,PressureReading
from src.schemas.study import StudyInput
from src.schemas.level import LevelPatch
from src.schemas.reading import ReadingPatch
from src.controllers.dependencies import current_user,writers
from src.services.studies import create_study,edit_level,edit_reading
from src.utils.serialize import row
router=APIRouter()
@router.get('/studies')
def studies(db:Session=Depends(get_db),user=Depends(current_user)):return [row(x) for x in db.scalars(select(FlowStudy).order_by(FlowStudy.id))]
@router.post('/studies')
def create(data:StudyInput,db:Session=Depends(get_db),user=Depends(writers)):return create_study(db,data,user.email)
@router.get('/levels')
def levels(db:Session=Depends(get_db),user=Depends(current_user)):return [row(x) for x in db.scalars(select(DoseLevel).order_by(DoseLevel.study_id,DoseLevel.flow,DoseLevel.id))]
@router.patch('/levels/{id}')
def change_level(id:int,data:LevelPatch,db:Session=Depends(get_db),user=Depends(writers)):return edit_level(db,id,data,user.email)
@router.get('/readings')
def readings(db:Session=Depends(get_db),user=Depends(current_user)):return [row(x) for x in db.scalars(select(PressureReading).order_by(PressureReading.specimen_ref))]
@router.patch('/readings/{id}')
def change_reading(id:int,data:ReadingPatch,db:Session=Depends(get_db),user=Depends(writers)):return edit_reading(db,id,data,user.email)
