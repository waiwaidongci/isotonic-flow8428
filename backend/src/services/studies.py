from sqlalchemy import select
from fastapi import HTTPException
from src.models import FlowStudy,DoseLevel,PressureReading
from src.utils.serialize import row
from .validation import validate_source
from .audit import record

def create_study(db,data,actor):
 if db.scalar(select(FlowStudy).where(FlowStudy.name==data.name)):raise HTTPException(409,'研究名称已存在')
 levels=[{'id':i+1,'label':l.label,'flow':l.flow} for i,l in enumerate(data.levels)];readings=[dict(r.model_dump(),level_id=i+1) for i,l in enumerate(data.levels) for r in l.readings]
 try:validate_source(levels,readings)
 except ValueError as e:raise HTTPException(422,str(e))
 study=FlowStudy(**data.model_dump(exclude={'levels'}));db.add(study);db.flush()
 for source in data.levels:
  level=DoseLevel(study_id=study.id,label=source.label,flow=source.flow);db.add(level);db.flush()
  for reading in source.readings:db.add(PressureReading(study_id=study.id,level_id=level.id,**reading.model_dump()))
 db.commit();record(db,actor,'study.imported',{'study_id':study.id,'levels':len(levels),'readings':len(readings)});return row(study)

def source_data(db,id):
 study=db.get(FlowStudy,id)
 if not study:raise HTTPException(404,'研究不存在')
 return row(study),[row(x) for x in db.scalars(select(DoseLevel).where(DoseLevel.study_id==id).order_by(DoseLevel.id))],[row(x) for x in db.scalars(select(PressureReading).where(PressureReading.study_id==id).order_by(PressureReading.specimen_ref))]

def edit_reading(db,id,data,actor):
 item=db.get(PressureReading,id)
 if not item:raise HTTPException(404,'读数不存在')
 item.pressure=data.pressure;item.measurement_note=data.measurement_note;db.commit();record(db,actor,'reading.revised',{'reading_id':id});return row(item)

def edit_level(db,id,data,actor):
 level=db.get(DoseLevel,id)
 if not level:raise HTTPException(404,'档位不存在')
 if db.scalar(select(DoseLevel).where(DoseLevel.study_id==level.study_id,DoseLevel.label==data.label,DoseLevel.id!=id)):raise HTTPException(409,'研究内档名重复')
 old=(level.label,level.flow);level.label=data.label;level.flow=data.flow;db.flush()
 try:
  _,levels,readings=source_data(db,level.study_id);validate_source(levels,readings)
 except ValueError as e:db.rollback();raise HTTPException(422,str(e))
 db.commit();record(db,actor,'level.revised',{'level_id':id,'old_label':old[0],'old_flow':old[1]});return row(level)
