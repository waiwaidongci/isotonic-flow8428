from math import fsum
from .aggregate import aggregate
from .pava import weighted_pava
from .interpolate import predict
from .inverse import inverse_set
from .lodo import leave_one_dose_out
from .validation import validate_config
from .fingerprint import fingerprint

def analyze(study,levels,readings,config):
 validate_config(config)
 if study['direction']!='nondecreasing':raise ValueError('研究未预先声明物理非降方向')
 groups=aggregate(levels,readings);fit=weighted_pava([g['mean_pressure'] for g in groups],[g['count'] for g in groups]);x=[g['flow'] for g in groups];knots=[{'flow':g['flow'],'mean_pressure':g['mean_pressure'],'fitted_pressure':value,'count':g['count'],'labels':g['labels']} for g,value in zip(groups,fit['fitted'])];sse=fsum((r['pressure']-v)**2 for g,v in zip(groups,fit['fitted']) for r in g['readings']);cv=leave_one_dose_out(groups)
 return {'fingerprint':fingerprint(study,levels,readings,config),'source_study':study,'level_count':len(levels),'unique_flows':len(groups),'reading_count':len(readings),'observed_flow_domain':[x[0],x[-1]],'fitted_pressure_range':[fit['fitted'][0],fit['fitted'][-1]],'knots':knots,'pava_blocks':fit['blocks'],'weighted_between_level_objective':fit['weighted_objective'],'training_raw_mse':sse/len(readings),'threshold_set':inverse_set(x,fit['fitted'],config['target_pressure']),'predictions':[predict(x,fit['fitted'],q) for q in config['query_flows']],'lodo':cv,'direction':'nondecreasing fixed before observing data','interpolation':'Linear monotone interpolation within observed x domain; outside requests are endpoint-clamped and explicitly marked. No extrapolation promise.','interpretation':'Raw independent specimens define weights. LODO refits leave out an entire flow, including duplicate-x named levels. Inverse sets and sensitivity are deterministic fit properties, not confidence intervals, material qualification, or causal guarantees.'}
