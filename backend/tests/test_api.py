import os
os.environ.setdefault('DATABASE_URL','sqlite+pysqlite:///:memory:')
os.environ.setdefault('REDIS_URL','redis://unused:6379/0')
os.environ.setdefault('JWT_SECRET','test-secret')
os.environ.setdefault('SEED_DEMO','false')
os.environ.setdefault('ARTIFACT_DIR','/tmp/fw-artifacts')

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.config.database import Base,get_db
from src.controllers import dependencies
from src.models import MonotoneRun,FlowStudy,DoseLevel,PressureReading,User
from src.routes import runs as runs_route
from src.services.snapshots import LEGACY_REFUSAL
from src import worker
from src.constants.enums import Role


@pytest.fixture()
def client(monkeypatch):
 engine=create_engine('sqlite+pysqlite:///:memory:',
  connect_args={'check_same_thread':False},poolclass=StaticPool)
 Base.metadata.create_all(engine)
 Session=sessionmaker(engine,expire_on_commit=False)
 monkeypatch.setattr(worker.fit_run,'delay',lambda run_id:None)
 writer=User(id=1,email='a@x',name='试验员',role=Role.ANALYST)
 app=FastAPI();app.include_router(runs_route.router)
 app.dependency_overrides[get_db]=lambda:(yield Session())
 app.dependency_overrides[dependencies.current_user]=lambda:writer
 app.dependency_overrides[dependencies.writers]=lambda:writer
 with TestClient(app) as c:
  yield c,Session


def _seed_study(db):
 study=FlowStudy(name='API研究',filename='a.csv',description='',direction='nondecreasing')
 db.add(study);db.flush()
 for i in range(3):
  level=DoseLevel(study_id=study.id,label=f'L{i+1}',flow=(i+1)*10.);db.add(level);db.flush()
  for j in range(2):
   db.add(PressureReading(study_id=study.id,level_id=level.id,specimen_ref=f'P{i}{j}',pressure=float(i+j+1)))
 db.commit();return study


def _queue_run(db,study_id,name,snapshot=True):
 from tests.test_snapshot import _RunInput
 from src.services.runs import create_run
 if not snapshot:
  run=MonotoneRun(study_id=study_id,name=name,
   config={'target_pressure':6.5,'query_flows':[5.],'direction':'nondecreasing'},
   input_snapshot=None,input_fingerprint=None,status='failed',created_by='old@x')
  db.add(run);db.commit();return run.id
 out=create_run(db,_RunInput(study_id,name),'a@x');return out['id']


def test_input_diff_endpoint_reports_match_then_drift(client):
 c,Session=client
 with Session() as db:
  study=_seed_study(db);run_id=_queue_run(db,study.id,'API冻结运行')
 r=c.get(f'/runs/{run_id}/input-diff')
 assert r.status_code==200
 body=r.json()
 assert body['has_snapshot'] is True and body['matches'] is True
 # 修订底稿后再比对
 reading=db.scalars(select(PressureReading).where(PressureReading.study_id==study.id)).first()
 reading.pressure=9.9;db.commit()
 r=c.get(f'/runs/{run_id}/input-diff')
 body=r.json()
 assert body['matches'] is False
 assert body['current_fingerprint']!=body['snapshot_fingerprint']
 assert any(ch['field']=='pressure' and ch['current']==9.9 for ch in body['readings_changed'])


def test_retry_endpoint_refuses_legacy_run(client):
 c,Session=client
 with Session() as db:
  study=_seed_study(db);run_id=_queue_run(db,study.id,'API历史运行',snapshot=False)
 r=c.post(f'/runs/{run_id}/retry')
 assert r.status_code==422 and r.json()['detail']==LEGACY_REFUSAL
 r=c.get(f'/runs/{run_id}/input-diff')
 assert r.json()=={'has_snapshot':False,'reason':LEGACY_REFUSAL}


def test_retry_endpoint_requeues_failed_frozen_run(client):
 c,Session=client
 with Session() as db:
  study=_seed_study(db);run_id=_queue_run(db,study.id,'API失败重试')
 run=db.get(MonotoneRun,run_id);run.status='failed';run.error='临时故障';db.commit()
 r=c.post(f'/runs/{run_id}/retry')
 assert r.status_code==200 and r.json()['status']=='queued'
 # 重复重试非 failed 运行应 409
 r=c.post(f'/runs/{run_id}/retry')
 assert r.status_code==409


def test_missing_run_returns_404(client):
 c,_=client
 assert c.get('/runs/999/input-diff').status_code==404
 assert c.post('/runs/999/retry').status_code==404


def test_run_listing_contains_frozen_fields(client):
 c,Session=client
 with Session() as db:
  study=_seed_study(db);run_id=_queue_run(db,study.id,'API列表字段')
 r=c.get('/runs')
 assert r.status_code==200
 item=next(x for x in r.json() if x['id']==run_id)
 assert item['input_fingerprint'] and 'input_snapshot' not in item
