import math

def validate_source(levels,readings):
 if not 2<=len(levels)<=30 or not 2<=len(readings)<=600:raise ValueError('需要2..30档、2..600条独立读数')
 if len({l['id'] for l in levels})!=len(levels) or len({l['label'] for l in levels})!=len(levels):raise ValueError('档位标识或名称重复')
 lookup={l['id']:l for l in levels}
 if any(not math.isfinite(l['flow']) or not 0<=l['flow']<=1000 for l in levels):raise ValueError('流速须有限且0..1000')
 if len({l['flow'] for l in levels})<2:raise ValueError('至少两个不同流速；同x档位会合并')
 if len({x['specimen_ref'] for x in readings})!=len(readings):raise ValueError('独立滤片编号必须在研究内唯一，重复读数不当独立重复')
 counts={l['id']:0 for l in levels}
 for reading in readings:
  if reading['level_id'] not in lookup or not math.isfinite(reading['pressure']) or not 0<=reading['pressure']<=1000000:raise ValueError('读数关联或有限非负压差不合法')
  counts[reading['level_id']]+=1
 if any(n<1 or n>30 for n in counts.values()):raise ValueError('各档需1..30条独立读数')

def validate_config(config):
 if config.get('direction')!='nondecreasing':raise ValueError('方向须预先声明为nondecreasing')
 t=config['target_pressure'];q=config['query_flows']
 if not math.isfinite(t) or not 0<=t<=1000000 or not 1<=len(q)<=30 or any(not math.isfinite(x) or not 0<=x<=1000 for x in q):raise ValueError('目标压差或查询流速不合法')
