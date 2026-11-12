from math import fsum
from .pava import weighted_pava
from .interpolate import predict

def leave_one_dose_out(groups):
 if len(groups)<2:raise ValueError('LODO至少需要两个独特流速')
 folds=[];total_sse=0.;total_n=0;inside_sse=0.;inside_n=0
 for omitted,g in enumerate(groups):
  train=[row for i,row in enumerate(groups) if i!=omitted];fit=weighted_pava([row['mean_pressure'] for row in train],[row['count'] for row in train]);x=[row['flow'] for row in train];pred=predict(x,fit['fitted'],g['flow']);residuals=[{'specimen_ref':r['specimen_ref'],'observed_pressure':r['pressure'],'prediction':pred['prediction'],'residual':r['pressure']-pred['prediction'],'squared_error':(r['pressure']-pred['prediction'])**2} for r in g['readings']];sse=fsum(r['squared_error'] for r in residuals);n=len(residuals);total_sse+=sse;total_n+=n
  if pred['within_observed_domain']:inside_sse+=sse;inside_n+=n
  folds.append({'omitted_flow':g['flow'],'omitted_labels':g['labels'],'omitted_count':n,'training_flows':x,'training_reading_count':sum(row['count'] for row in train),'training_fitted':fit['fitted'],'training_blocks':fit['blocks'],**{k:v for k,v in pred.items() if k!='flow'},'sse':sse,'mse':sse/n,'residuals':residuals})
 return {'folds':folds,'fit_count':len(folds),'reading_count':total_n,'sse':total_sse,'mse':total_sse/total_n,'interior_mse':inside_sse/inside_n if inside_n else None,'interior_reading_count':inside_n,'clamped_folds':sum(f['clamped'] is not None for f in folds),'clamped_reading_count':sum(f['omitted_count'] for f in folds if f['clamped'] is not None),'definition':'Remove every raw reading at one flow, refit PAVA independently, and sum errors over original independent readings. Endpoint clamps are included and marked; not extrapolation or a confidence interval.'}
