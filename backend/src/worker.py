import json
from pathlib import Path
from celery import Celery
from src.config.database import SessionLocal
from src.config.settings import REDIS_URL,ARTIFACT_DIR
from src.models import MonotoneRun
from src.services.analysis import analyze
from src.services.snapshots import verify_snapshot,LEGACY_REFUSAL,FINGERPRINT_MISMATCH
from src.services.audit import record
app=Celery('isotonic_flow',broker=REDIS_URL,backend=REDIS_URL)
app.conf.update(task_track_started=True,worker_prefetch_multiplier=1,task_acks_late=True)
@app.task(name='flow.fit',soft_time_limit=120,time_limit=150)
def fit_run(id):
 with SessionLocal() as db:
  run=db.get(MonotoneRun,id)
  if not run or run.status=='completed':return
  # 历史运行没有留存排队输入：明确拒绝，绝不读取当前底稿补齐。
  if not run.input_snapshot or not run.input_fingerprint:
   run.status='failed';run.error=LEGACY_REFUSAL;db.commit();record(db,'worker','run.refused',{'run_id':id,'reason':'missing_input_snapshot'});return
  # 指纹核验通过后才开始计算；失败重试仍使用同一份原始快照，不混用新版底稿。
  try:
   digest=verify_snapshot(run)
  except Exception as error:
   run.status='failed';run.error=(str(error) or FINGERPRINT_MISMATCH)[:1000];db.commit();record(db,'worker','run.failed',{'run_id':id,'error':run.error});return
  run.status='running';run.error=None;db.commit()
  try:
   study,levels,readings=run.input_snapshot['study'],run.input_snapshot['levels'],run.input_snapshot['readings']
   result=analyze(study,levels,readings,run.config)
   if result['fingerprint']!=digest:raise RuntimeError(FINGERPRINT_MISMATCH)
   Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True);Path(ARTIFACT_DIR,f'flow-{id}.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False))
   run.result=result;run.status='completed';run.error=None;db.commit();record(db,'worker','run.completed',{'run_id':id,'lodo_mse':result['lodo']['mse'],'input_fingerprint':digest})
  except Exception as error:
   db.rollback();run=db.get(MonotoneRun,id);run.status='failed';run.error=str(error)[:1000];db.commit();record(db,'worker','run.failed',{'run_id':id,'error':run.error})
