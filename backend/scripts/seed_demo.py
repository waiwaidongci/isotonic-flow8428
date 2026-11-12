import json
import numpy as np
from sqlalchemy import select,func
from src.config.database import Base,engine,SessionLocal
from src.models import User,FlowStudy,DoseLevel,PressureReading,MonotoneRun,ValidationNote
from src.utils.security import hash_password
from src.utils.serialize import row
from src.services.analysis import analyze
from src.services.fingerprint import fingerprint
from src.services.snapshots import build_input_snapshot

def seed():
 Base.metadata.create_all(engine)
 with SessionLocal() as db:
  for role,name in [('admin','许澜 · 滤材研究负责人'),('analyst','宋桥 · 压差试验员'),('viewer','叶衡 · 复验观察员')]:
   if not db.scalar(select(User).where(User.email==f'{role}@fangwen.demo')):db.add(User(email=f'{role}@fangwen.demo',name=name,role=role,password_hash=hash_password('Fangwen2026!')))
  db.commit();rng=np.random.default_rng(228);names=['FW-28A 局部逆序滤片','FW-28B 平台响应滤片','FW-28C 恒定对照滤片'];x=np.arange(1,13)*10.;means=[[2,3.5,5,7,6,8,9,10,11,12,14,15],[2,3,4,5,6,6,6,6,8,10,12,14],[6]*12]
  for index,name in enumerate(names):
   study=db.scalar(select(FlowStudy).where(FlowStudy.name==name))
   if study:continue
   study=FlowStudy(name=name,filename=f'fw-pressure-{index+1}-202611.csv',description=['独立滤片，各流速档8片；局部均值逆序用于检验合并','预设物理非降；平台不提供唯一反解','零方差合法；逆集合可以覆盖整个观测域'][index],direction='nondecreasing');db.add(study);db.flush()
   for i,(flow,mean) in enumerate(zip(x,means[index])):
    level=DoseLevel(study_id=study.id,label=f'F{i+1:02d}',flow=float(flow));db.add(level);db.flush();noise=rng.normal(0,.18,8) if index==0 else np.array([-.2,-.1,0,.1,.2,-.1,0,.1]) if index==1 else np.zeros(8)
    for j,value in enumerate(mean+noise):db.add(PressureReading(study_id=study.id,level_id=level.id,specimen_ref=f'FW{index+1}-F{i+1:02d}-P{j+1:02d}',pressure=float(value),measurement_note='独立滤片，非同片重复读数'))
   db.commit()
  run=db.scalar(select(MonotoneRun).where(MonotoneRun.name=='A研究加权非降校对'))
  if not run:
   study=db.scalar(select(FlowStudy).where(FlowStudy.name==names[0]));levels=[row(x) for x in db.scalars(select(DoseLevel).where(DoseLevel.study_id==study.id))];readings=[row(x) for x in db.scalars(select(PressureReading).where(PressureReading.study_id==study.id))];config={'target_pressure':6.5,'query_flows':[5,35,45,80,125],'direction':'nondecreasing'};s_study=row(study);result=analyze(s_study,levels,readings,config);digest=fingerprint(s_study,levels,readings,config);run=MonotoneRun(study_id=study.id,name='A研究加权非降校对',config=config,input_snapshot=build_input_snapshot(s_study,levels,readings),input_fingerprint=digest,status='completed',result=result,created_by='analyst@fangwen.demo');db.add(run);db.commit()
  if not db.scalar(select(ValidationNote).where(ValidationNote.name=='A研究独立新档复验初稿')):db.add(ValidationNote(run_id=run.id,name='A研究独立新档复验初稿',interpretation='局部逆序由加权PAVA合并，不能据此断定材料工艺原因。',next_step='在45mL/min另取独立滤片复验；不把同片重复读数作为独立样本。',proposed_flow=45.,result_snapshot=run.result,created_by='analyst@fangwen.demo'));db.commit()
  counts={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in [User,FlowStudy,DoseLevel,PressureReading,MonotoneRun,ValidationNote]};print(json.dumps(counts));return counts
if __name__=='__main__':seed()
