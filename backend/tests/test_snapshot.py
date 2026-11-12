import os
os.environ.setdefault('DATABASE_URL','sqlite+pysqlite:///:memory:')
os.environ.setdefault('REDIS_URL','redis://unused:6379/0')
os.environ.setdefault('JWT_SECRET','test-secret')
os.environ.setdefault('SEED_DEMO','false')
os.environ.setdefault('ARTIFACT_DIR','/tmp/fw-artifacts')

import pytest
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.config import database as db_cfg
from src.models import MonotoneRun,FlowStudy,DoseLevel,PressureReading
from src.utils.serialize import row
from src.services import runs as runs_svc
from src.services.snapshots import (
 ensure_run_columns,input_diff,LEGACY_REFUSAL,build_input_snapshot,
)
from src.services.fingerprint import fingerprint
from src import worker


@pytest.fixture()
def session(monkeypatch):
 engine=create_engine('sqlite+pysqlite:///:memory:',
  connect_args={'check_same_thread':False},poolclass=StaticPool)
 db_cfg.Base.metadata.create_all(engine)
 ensure_run_columns(engine)
 Session=sessionmaker(engine,expire_on_commit=False)
 monkeypatch.setattr(worker,'SessionLocal',Session)
 with Session() as db:
  yield db


def _make_study(db,name='测试研究',pressures=None):
 study=FlowStudy(name=name,filename='t.csv',description='d',direction='nondecreasing')
 db.add(study);db.flush()
 levels=[];readings=[]
 if pressures is None:
  pressures=[[1.0,1.1,1.2],[2.0,2.1,2.2],[3.0,3.1,3.2]]
 for i,vals in enumerate(pressures):
  level=DoseLevel(study_id=study.id,label=f'L{i+1}',flow=float((i+1)*10))
  db.add(level);db.flush();levels.append(level)
  for j,p in enumerate(vals):
   r=PressureReading(study_id=study.id,level_id=level.id,specimen_ref=f'{name}-P{i+1}{j+1}',pressure=float(p),measurement_note='')
   db.add(r);readings.append(r)
 db.commit()
 return study


class _RunInput:
 def __init__(self,study_id,name):
  self.study_id=study_id;self.name=name
  self.target_pressure=6.5;self.query_flows=[5.,35.,125.];self.direction='nondecreasing'
 def model_dump(self,exclude=None):
  data={'study_id':self.study_id,'name':self.name,'target_pressure':self.target_pressure,
        'query_flows':list(self.query_flows),'direction':self.direction}
  return {k:v for k,v in data.items() if k not in (exclude or set())}


def _enqueue_capture(monkeypatch):
 captured=[]
 monkeypatch.setattr(worker.fit_run,'delay',lambda run_id:captured.append(run_id))
 return captured

def _fit(session,run_id):
 # worker 在独立会话提交；让测试会话丢弃身份映射缓存后重新读取。
 worker.fit_run(run_id)
 session.expire_all()


def test_create_run_freezes_snapshot_at_queue_time(session,monkeypatch):
 captured=_enqueue_capture(monkeypatch)
 study=_make_study(session)
 payload=_RunInput(study.id,'排队冻结测试')
 out=runs_svc.create_run(session,payload,'analyst@x')
 run=session.get(MonotoneRun,out['id'])
 assert run.status=='queued'
 assert run.input_snapshot is not None and run.input_fingerprint
 snap=run.input_snapshot
 assert snap['version']=='queued-input-v1'
 assert len(snap['levels'])==3 and len(snap['readings'])==9
 assert snap['readings'][0]['pressure']==1.0
 assert captured==[run.id]
 # 指纹与排队输入一致
 study_r,levels_r,readings_r=runs_svc.source_data(session,study.id)
 assert fingerprint(study_r,levels_r,readings_r,run.config)==run.input_fingerprint


def test_editing_source_after_queue_does_not_change_frozen_run(session,monkeypatch):
 _enqueue_capture(monkeypatch)
 study=_make_study(session)
 out=runs_svc.create_run(session,_RunInput(study.id,'底稿修订隔离'),'a@x')
 run=session.get(MonotoneRun,out['id'])
 before_pressure=run.input_snapshot['readings'][0]['pressure']
 # 排队后修订底稿读数与档位
 reading=session.scalars(select(PressureReading).where(PressureReading.study_id==study.id)).first()
 reading.pressure=9.99;session.commit()
 level=session.scalars(select(DoseLevel).where(DoseLevel.study_id==study.id)).first()
 level.flow=99.0;session.commit()
 run=session.get(MonotoneRun,out['id'])
 assert run.input_snapshot['readings'][0]['pressure']==before_pressure
 assert run.input_snapshot['levels'][0]['flow']==10.0
 # worker 执行只使用快照，结果指纹仍是排队时的输入
 _fit(session,run.id)
 run=session.get(MonotoneRun,out['id'])
 assert run.status=='completed'
 assert run.result['fingerprint']==run.input_fingerprint
 # 当前底稿指纹已经不同，确认结果没有偷偷采用现值
 _,cur_levels,cur_readings=runs_svc.source_data(session,study.id)
 cur_study=row(session.get(FlowStudy,study.id))
 assert fingerprint(cur_study,cur_levels,cur_readings,run.config)!=run.input_fingerprint


def test_retry_after_failure_reuses_original_snapshot(session,monkeypatch):
 _enqueue_capture(monkeypatch)
 study=_make_study(session)
 out=runs_svc.create_run(session,_RunInput(study.id,'失败重试输入不变'),'a@x')
 run_id=out['id']
 original_snapshot=session.get(MonotoneRun,run_id).input_snapshot
 # 模拟一次失败（分析前快照损坏检测），再改底稿
 run=session.get(MonotoneRun,run_id);run.status='failed';run.error='boom';session.commit()
 reading=session.scalars(select(PressureReading).where(PressureReading.study_id==study.id)).first()
 reading.pressure=5.55;session.commit()
 retried=runs_svc.retry_run(session,run_id,'a@x')
 assert retried['status']=='queued'
 run=session.get(MonotoneRun,run_id)
 assert run.input_snapshot==original_snapshot
 _fit(session,run_id)
 run=session.get(MonotoneRun,run_id)
 assert run.status=='completed'
 assert run.result['fingerprint']==run.input_fingerprint
 assert run.result['reading_count']==9


def test_legacy_run_without_snapshot_is_refused_by_worker(session):
 study=_make_study(session)
 study_r,levels,readings=runs_svc.source_data(session,study.id)
 legacy=MonotoneRun(study_id=study.id,name='历史无快照运行',
  config={'target_pressure':6.5,'query_flows':[5.],'direction':'nondecreasing'},
  input_snapshot=None,input_fingerprint=None,status='queued',created_by='old@x')
 session.add(legacy);session.commit()
 _fit(session,legacy.id)
 run=session.get(MonotoneRun,legacy.id)
 assert run.status=='failed'
 assert run.error==LEGACY_REFUSAL
 # 即便底稿之后变化，也不会拿现值补齐
 reading=session.scalars(select(PressureReading).where(PressureReading.study_id==study.id)).first()
 reading.pressure=8.8;session.commit()
 _fit(session,legacy.id)
 run=session.get(MonotoneRun,legacy.id)
 assert run.status=='failed' and run.error==LEGACY_REFUSAL
 assert run.result is None


def test_retry_endpoint_refuses_legacy_run(session,monkeypatch):
 _enqueue_capture(monkeypatch)
 study=_make_study(session)
 legacy=MonotoneRun(study_id=study.id,name='历史拒绝重试',
  config={'target_pressure':6.5,'query_flows':[5.],'direction':'nondecreasing'},
  input_snapshot=None,input_fingerprint=None,status='failed',created_by='old@x')
 session.add(legacy);session.commit()
 from fastapi import HTTPException
 with pytest.raises(HTTPException) as exc:
  runs_svc.retry_run(session,legacy.id,'a@x')
 assert exc.value.status_code==422 and exc.value.detail==LEGACY_REFUSAL


def test_retry_only_allowed_for_failed_runs(session,monkeypatch):
 _enqueue_capture(monkeypatch)
 study=_make_study(session)
 out=runs_svc.create_run(session,_RunInput(study.id,'非失败不可重试'),'a@x')
 _fit(session,out['id'])
 from fastapi import HTTPException
 with pytest.raises(HTTPException) as exc:
  runs_svc.retry_run(session,out['id'],'a@x')
 assert exc.value.status_code==409


def test_concurrent_edits_cannot_mix_two_versions(session,monkeypatch):
 # 排队冻结后对底稿做两类修订；结果指纹恒等于排队指纹，且 diff 能检出全部差异
 _enqueue_capture(monkeypatch)
 study=_make_study(session)
 out=runs_svc.create_run(session,_RunInput(study.id,'并发版本隔离'),'a@x')
 run_id=out['id']
 fp_queued=session.get(MonotoneRun,run_id).input_fingerprint
 target=session.scalars(select(PressureReading).where(PressureReading.study_id==study.id)).first()
 target.pressure=4.44;target.measurement_note='并发修订'
 another_level=session.scalars(select(DoseLevel).where(DoseLevel.study_id==study.id)).all()[1]
 another_level.flow=77.0
 session.commit()
 _fit(session,run_id)
 run=session.get(MonotoneRun,run_id)
 assert run.result['fingerprint']==fp_queued
 diff=input_diff(session,run)
 assert diff['has_snapshot'] is True and diff['matches'] is False
 assert any(c['field']=='flow' and c['snapshot']==20.0 and c['current']==77.0 for c in diff['levels_changed'])
 pressure_changes=[c for c in diff['readings_changed'] if c['field']=='pressure']
 note_changes=[c for c in diff['readings_changed'] if c['field']=='measurement_note']
 assert pressure_changes and pressure_changes[0]['snapshot']!=4.44
 assert any(c['current']=='并发修订' for c in note_changes)


def test_input_diff_matches_when_unchanged(session,monkeypatch):
 _enqueue_capture(monkeypatch)
 study=_make_study(session)
 out=runs_svc.create_run(session,_RunInput(study.id,'无差异比对'),'a@x')
 _fit(session,out['id'])
 run=session.get(MonotoneRun,out['id'])
 diff=input_diff(session,run)
 assert diff['matches'] is True
 assert diff['snapshot_fingerprint']==diff['current_fingerprint']
 assert not diff['levels_changed'] and not diff['readings_changed']


def test_input_diff_refuses_legacy_run(session):
 study=_make_study(session)
 legacy=MonotoneRun(study_id=study.id,name='历史diff拒绝',
  config={'target_pressure':6.5,'query_flows':[5.],'direction':'nondecreasing'},
  input_snapshot=None,input_fingerprint=None,status='completed',created_by='old@x')
 session.add(legacy);session.commit()
 diff=input_diff(session,legacy)
 assert diff=={'has_snapshot':False,'reason':LEGACY_REFUSAL}


def test_fingerprint_tampering_blocks_execution(session,monkeypatch):
 _enqueue_capture(monkeypatch)
 study=_make_study(session)
 out=runs_svc.create_run(session,_RunInput(study.id,'指纹防篡改'),'a@x')
 run=session.get(MonotoneRun,out['id'])
 run.input_fingerprint='0'*64;session.commit()
 _fit(session,run.id)
 run=session.get(MonotoneRun,out['id'])
 assert run.status=='failed' and run.result is None
 assert '指纹' in run.error


def test_snapshot_is_deep_copied_from_live_rows(session):
 study=_make_study(session)
 study_r,levels,readings=runs_svc.source_data(session,study.id)
 config={'target_pressure':6.5,'query_flows':[5.],'direction':'nondecreasing'}
 snap=build_input_snapshot(study_r,levels,readings)
 readings[0]['pressure']=123.0
 assert snap['readings'][0]['pressure']!=123.0


def test_input_diff_when_current_study_deleted(session,monkeypatch):
 _enqueue_capture(monkeypatch)
 study=_make_study(session,name='待删除研究')
 out=runs_svc.create_run(session,_RunInput(study.id,'研究删除比对'),'a@x')
 run=session.get(MonotoneRun,out['id'])
 session.query(DoseLevel).filter(DoseLevel.study_id==study.id).delete()
 session.query(PressureReading).filter(PressureReading.study_id==study.id).delete()
 session.delete(study);session.commit()
 diff=input_diff(session,run)
 assert diff['has_snapshot'] is True
 assert diff['current_available'] is False and diff['matches'] is False
 assert '删除' in diff['reason']
 # 结果仍可凭快照完成计算
 _fit(session,run.id)
 run=session.get(MonotoneRun,out['id'])
 assert run.status=='completed' and run.result['fingerprint']==run.input_fingerprint


def test_input_diff_detects_added_and_removed_rows(session,monkeypatch):
 _enqueue_capture(monkeypatch)
 study=_make_study(session,name='增删差异研究')
 out=runs_svc.create_run(session,_RunInput(study.id,'增删差异运行'),'a@x')
 run=session.get(MonotoneRun,out['id'])
 # 新增一个档位与读数
 new_level=DoseLevel(study_id=study.id,label='L4',flow=40.0)
 session.add(new_level);session.flush()
 session.add(PressureReading(study_id=study.id,level_id=new_level.id,specimen_ref='新增-P1',pressure=4.4))
 # 删除排队时的一条读数
 victim=session.scalars(select(PressureReading).where(PressureReading.study_id==study.id)).first()
 session.delete(victim);session.commit()
 diff=input_diff(session,run)
 assert diff['matches'] is False
 assert len(diff['levels_added'])==1 and diff['levels_added'][0]['label']=='L4'
 assert len(diff['readings_added'])==1 and diff['readings_added'][0]['specimen_ref']=='新增-P1'
 assert len(diff['readings_removed'])==1 and diff['readings_removed'][0]['specimen_ref']==victim.specimen_ref
 assert diff['snapshot_summary']['reading_count']-diff['current_summary']['reading_count']==0


class _NoteInput:
 def __init__(self,run_id,name='复验说明'):
  self.run_id=run_id;self.name=name
  self.interpretation='解释';self.next_step='下一步';self.proposed_flow=45.0
 def model_dump(self):
  return {'run_id':self.run_id,'name':self.name,'interpretation':self.interpretation,
          'next_step':self.next_step,'proposed_flow':self.proposed_flow}


def test_note_snapshot_and_export_immune_to_later_rerun(session,monkeypatch):
 _enqueue_capture(monkeypatch)
 from src.services.notes import create_note
 from src.models import ValidationNote
 study=_make_study(session,name='说明冻结研究')
 out=runs_svc.create_run(session,_RunInput(study.id,'说明冻结运行'),'a@x')
 run_id=out['id'];_fit(session,run_id)
 run=session.get(MonotoneRun,run_id)
 note=create_note(session,_NoteInput(run_id,'冻结复验说明'),'a@x')
 note_id=note['id']
 frozen=dict(session.get(ValidationNote,note_id).result_snapshot)
 # 强制把运行改回 failed 再重试（模拟重算路径），底稿同时修订
 r=session.get(MonotoneRun,run_id);r.status='failed';r.result=None;session.commit()
 reading=session.scalars(select(PressureReading).where(PressureReading.study_id==study.id)).first()
 reading.pressure=7.77;session.commit()
 runs_svc.retry_run(session,run_id,'a@x');_fit(session,run_id)
 # 说明快照与批准后导出的指纹保持排队/成簿时的原值，不随重算变化
 note_row=session.get(ValidationNote,note_id)
 assert note_row.result_snapshot==frozen
 assert note_row.result_snapshot['fingerprint']==session.get(MonotoneRun,run_id).input_fingerprint
 # 导出内容中的指纹仍来自说明快照
 from src.controllers.export import export_note
 note_row.status='approved';session.commit()
 response=export_note(session,note_id,'viewer@x')
 assert frozen['fingerprint'] in response.body.decode()
