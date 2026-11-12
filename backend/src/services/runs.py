from sqlalchemy import select,inspect
from fastapi import HTTPException
from src.models import MonotoneRun
from src.utils.serialize import row
from .studies import source_data
from .validation import validate_source,validate_config
from .fingerprint import fingerprint
from .snapshots import build_input_snapshot,input_diff,LEGACY_REFUSAL
from .audit import record

def create_run(db,data,actor):
 # 排队即冻结：先开启可重复读事务，再在同一事务内快照研究/档位/读数，
 # 避免排队期间并发修订把第二版底稿混入本次输入（SQLite 等不支持的方言跳过）。
 if inspect(db.bind).dialect.name=='postgresql':
  db.connection(execution_options={'postgresql_transaction_isolation':'REPEATABLE READ'})
 study,levels,readings=source_data(db,data.study_id);config=data.model_dump(exclude={'study_id','name'})
 try:validate_source(levels,readings);validate_config(config)
 except ValueError as e:raise HTTPException(422,str(e))
 if db.scalar(select(MonotoneRun).where(MonotoneRun.name==data.name)):raise HTTPException(409,'运行名称已存在')
 digest=fingerprint(study,levels,readings,config)
 snapshot=build_input_snapshot(study,levels,readings)
 run=MonotoneRun(study_id=data.study_id,name=data.name,config=config,input_snapshot=snapshot,input_fingerprint=digest,created_by=actor);db.add(run);db.commit()
 try:
  from src.worker import fit_run
  fit_run.delay(run.id)
 except Exception:
  # 失败保留已冻结输入，重试仍用原始快照；不回退到实时底稿。
  run.status='failed';run.error='队列不可用，请稍后以原始输入重试';db.commit();raise HTTPException(503,run.error)
 record(db,actor,'run.queued',{'run_id':run.id,'input_fingerprint':digest});return row(run)

def retry_run(db,id,actor):
 run=db.get(MonotoneRun,id)
 if not run:raise HTTPException(404,'运行不存在')
 if not run.input_snapshot or not run.input_fingerprint:raise HTTPException(422,LEGACY_REFUSAL)
 if run.status!='failed':raise HTTPException(409,'仅失败运行可重新排队；已成簿结果与冻结说明不可重算')
 run.status='queued';run.error=None;run.result=None;db.commit()
 try:
  from src.worker import fit_run
  fit_run.delay(run.id)
 except Exception:
  run.status='failed';run.error='队列不可用，请稍后以原始输入重试';db.commit();raise HTTPException(503,run.error)
 record(db,actor,'run.retried',{'run_id':run.id,'input_fingerprint':run.input_fingerprint});return row(run)

def run_input_diff(db,id):
 run=db.get(MonotoneRun,id)
 if not run:raise HTTPException(404,'运行不存在')
 return input_diff(db,run)
