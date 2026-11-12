from sqlalchemy import select
from fastapi import HTTPException
from src.models import MonotoneRun
from src.utils.serialize import row
from .studies import source_data
from .validation import validate_source,validate_config
from .audit import record

def create_run(db,data,actor):
 study,levels,readings=source_data(db,data.study_id);config=data.model_dump(exclude={'study_id','name'})
 try:validate_source(levels,readings);validate_config(config)
 except ValueError as e:raise HTTPException(422,str(e))
 if db.scalar(select(MonotoneRun).where(MonotoneRun.name==data.name)):raise HTTPException(409,'运行名称已存在')
 run=MonotoneRun(study_id=data.study_id,name=data.name,config=config,created_by=actor);db.add(run);db.commit()
 try:
  from src.worker import fit_run
  fit_run.delay(run.id)
 except Exception:
  run.status='failed';run.error='队列不可用，请稍后重新创建';db.commit();raise HTTPException(503,run.error)
 record(db,actor,'run.queued',{'run_id':run.id});return row(run)
