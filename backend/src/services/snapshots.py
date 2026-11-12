from sqlalchemy import inspect,text
from sqlalchemy import select
from src.models import FlowStudy,DoseLevel,PressureReading
from src.utils.serialize import row
from .fingerprint import fingerprint

SNAPSHOT_VERSION='queued-input-v1'
LEGACY_REFUSAL='历史运行未留存排队时的研究、档位与读数快照，按规定拒绝重算；请以当前底稿新建运行，不得以现值补齐。'
FINGERPRINT_MISMATCH='排队输入快照指纹与运行记录不一致，拒绝混用其他版本输入。'

def ensure_run_columns(engine):
 # create_all 不会给已存在的表补列；对旧库幂等 ALTER。
 inspector=inspect(engine)
 existing={c['name'] for c in inspector.get_columns('monotone_runs')}
 with engine.begin() as conn:
  if 'input_snapshot' not in existing:
   snapshot_type='JSON' if conn.dialect.name=='postgresql' else 'TEXT'
   conn.execute(text(f'ALTER TABLE monotone_runs ADD COLUMN input_snapshot {snapshot_type}'))
  if 'input_fingerprint' not in existing:
   conn.execute(text('ALTER TABLE monotone_runs ADD COLUMN input_fingerprint VARCHAR(64)'))

def build_input_snapshot(study,levels,readings):
 # 深拷贝已序列化的字典，确保排队事务提交后快照不与会话对象共享引用。
 return {'version':SNAPSHOT_VERSION,'study':dict(study),'levels':[dict(x) for x in levels],'readings':[dict(x) for x in readings]}

def snapshot_inputs(run):
 if not run.input_snapshot:raise ValueError(LEGACY_REFUSAL)
 snap=run.input_snapshot
 return snap['study'],snap['levels'],snap['readings']

def verify_snapshot(run):
 study,levels,readings=snapshot_inputs(run)
 digest=fingerprint(study,levels,readings,run.config)
 if digest!=run.input_fingerprint:raise ValueError(FINGERPRINT_MISMATCH)
 return digest

def _current_source(db,study_id):
 study=db.get(FlowStudy,study_id)
 if not study:return None
 levels=[row(x) for x in db.scalars(select(DoseLevel).where(DoseLevel.study_id==study_id).order_by(DoseLevel.id))]
 readings=[row(x) for x in db.scalars(select(PressureReading).where(PressureReading.study_id==study_id).order_by(PressureReading.specimen_ref))]
 return row(study),levels,readings

_STUDY_FIELDS=('name','filename','description','direction')

def input_diff(db,run):
 if not run.input_snapshot or not run.input_fingerprint:
  return {'has_snapshot':False,'reason':LEGACY_REFUSAL}
 snap=run.input_snapshot
 s_study,s_levels,s_readings=snap['study'],snap['levels'],snap['readings']
 current=_current_source(db,run.study_id)
 payload={'has_snapshot':True,'snapshot_fingerprint':run.input_fingerprint,
  'snapshot_summary':{'study_id':run.study_id,'study_name':s_study.get('name'),'level_count':len(s_levels),'reading_count':len(s_readings)}}
 if current is None:
  payload.update({'current_available':False,'matches':False,
   'reason':'当前底稿研究已删除，无法比对；本次结果仍以排队快照为准。'})
  return payload
 c_study,c_levels,c_readings=current
 current_fp=fingerprint(c_study,c_levels,c_readings,run.config)
 payload['current_available']=True
 payload['current_fingerprint']=current_fp
 payload['matches']=current_fp==run.input_fingerprint
 payload['current_summary']={'study_id':run.study_id,'study_name':c_study.get('name'),'level_count':len(c_levels),'reading_count':len(c_readings)}
 payload['study_changes']=[{'field':f,'snapshot':s_study.get(f),'current':c_study.get(f)} for f in _STUDY_FIELDS if s_study.get(f)!=c_study.get(f)]
 s_level_map={x['id']:x for x in s_levels};c_level_map={x['id']:x for x in c_levels}
 levels_added=[{'level_id':i,'label':x['label'],'flow':x['flow']} for i,x in c_level_map.items() if i not in s_level_map]
 levels_removed=[{'level_id':i,'label':x['label'],'flow':x['flow']} for i,x in s_level_map.items() if i not in c_level_map]
 levels_changed=[]
 for i,x in s_level_map.items():
  other=c_level_map.get(i)
  if other is None:continue
  for f in ('label','flow'):
   if x.get(f)!=other.get(f):levels_changed.append({'level_id':i,'field':f,'snapshot':x.get(f),'current':other.get(f)})
 s_reading_map={x['id']:x for x in s_readings};c_reading_map={x['id']:x for x in c_readings}
 readings_added=[{'reading_id':i,'specimen_ref':x['specimen_ref'],'pressure':x['pressure']} for i,x in c_reading_map.items() if i not in s_reading_map]
 readings_removed=[{'reading_id':i,'specimen_ref':x['specimen_ref'],'pressure':x['pressure']} for i,x in s_reading_map.items() if i not in c_reading_map]
 readings_changed=[]
 for i,x in s_reading_map.items():
  other=c_reading_map.get(i)
  if other is None:continue
  for f in ('level_id','pressure','measurement_note'):
   if x.get(f)!=other.get(f):readings_changed.append({'reading_id':i,'specimen_ref':x['specimen_ref'],'field':f,'snapshot':x.get(f),'current':other.get(f)})
 payload.update({'levels_added':levels_added,'levels_removed':levels_removed,'levels_changed':levels_changed,
  'readings_added':readings_added,'readings_removed':readings_removed,'readings_changed':readings_changed})
 return payload
