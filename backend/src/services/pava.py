import numpy as np

def weighted_pava(means,weights):
 y=np.asarray(means,dtype=np.longdouble);w=np.asarray(weights,dtype=np.longdouble)
 if y.ndim!=1 or w.shape!=y.shape or len(y)<1 or not np.isfinite(y).all() or not np.isfinite(w).all() or (w<=0).any():raise ValueError('PAVA需要有限均值与正权重')
 stack=[]
 for i,(v,weight) in enumerate(zip(y,w)):
  stack.append({'start':i,'end':i+1,'weight':weight,'total':v*weight})
  while len(stack)>1 and stack[-2]['total']/stack[-2]['weight']>stack[-1]['total']/stack[-1]['weight']:
   right=stack.pop();left=stack.pop();stack.append({'start':left['start'],'end':right['end'],'weight':left['weight']+right['weight'],'total':left['total']+right['total']})
 fitted=np.empty(len(y),dtype=float);blocks=[]
 for b in stack:
  value=float(b['total']/b['weight']);fitted[b['start']:b['end']]=value;blocks.append({'start_index':b['start'],'end_index_exclusive':b['end'],'weight':int(b['weight']) if float(b['weight']).is_integer() else float(b['weight']),'fitted_pressure':value})
 return {'fitted':fitted.tolist(),'blocks':blocks,'weighted_objective':float(np.sum(w*(y-fitted)**2))}
