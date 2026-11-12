import json
from pathlib import Path
from celery import Celery
from src.config.database import SessionLocal
from src.config.settings import REDIS_URL,ARTIFACT_DIR
from src.models import MonotoneRun
from src.services.studies import source_data
from src.services.analysis import analyze
from src.services.audit import record
app=Celery('isotonic_flow',broker=REDIS_URL,backend=REDIS_URL)
app.conf.update(task_track_started=True,worker_prefetch_multiplier=1,task_acks_late=True)
@app.task(name='flow.fit',soft_time_limit=120,time_limit=150)
def fit_run(id):
 with SessionLocal() as db:
  run=db.get(MonotoneRun,id)
  if not run or run.status=='completed':return
  run.status='running';db.commit()
  try:
   study,levels,readings=source_data(db,run.study_id);result=analyze(study,levels,readings,run.config)
   Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True);Path(ARTIFACT_DIR,f'flow-{id}.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False));run.result=result;run.status='completed';run.error=None;db.commit();record(db,'worker','run.completed',{'run_id':id,'lodo_mse':result['lodo']['mse']})
  except Exception as error:
   db.rollback();run=db.get(MonotoneRun,id);run.status='failed';run.error=str(error)[:1000];db.commit();record(db,'worker','run.failed',{'run_id':id,'error':run.error})
