import math

def inverse_set(x,fitted,target):
 if not x or len(x)!=len(fitted) or not math.isfinite(target) or any(not math.isfinite(v) for v in [*x,*fitted]) or any(b<=a for a,b in zip(x,x[1:])) or any(b<a for a,b in zip(fitted,fitted[1:])):raise ValueError('逆集合需要有限非降曲线和严格递增节点')
 if target<fitted[0] or target>fitted[-1]:return {'kind':'no_solution','target_pressure':float(target),'lower_flow':None,'upper_flow':None,'reason':'目标不在观测域拟合压差范围内；无外推解'}
 equal=[i for i,v in enumerate(fitted) if v==target]
 if equal:
  lower=x[min(equal)];upper=x[max(equal)];return {'kind':'interval' if lower<upper else 'point','target_pressure':float(target),'lower_flow':float(lower),'upper_flow':float(upper),'reason':'平台的全部观测域解' if lower<upper else '拟合节点的唯一解'}
 for i in range(len(x)-1):
  if fitted[i]<target<fitted[i+1]:
   value=x[i]+(target-fitted[i])/(fitted[i+1]-fitted[i])*(x[i+1]-x[i]);return {'kind':'point','target_pressure':float(target),'lower_flow':float(value),'upper_flow':float(value),'reason':'相邻拟合节点间线性逆解'}
 raise ValueError('未找到逆集合')
