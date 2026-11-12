import math
from bisect import bisect_left

def predict(x,fitted,query):
 if not x or len(x)!=len(fitted) or any(not math.isfinite(v) for v in [*x,*fitted,query]) or any(b<=a for a,b in zip(x,x[1:])) or any(b<a for a,b in zip(fitted,fitted[1:])):raise ValueError('插值节点须有限，x严格递增且拟合非降')
 if query<x[0]:return {'flow':float(query),'prediction':float(fitted[0]),'clamped':'left','within_observed_domain':False}
 if query>x[-1]:return {'flow':float(query),'prediction':float(fitted[-1]),'clamped':'right','within_observed_domain':False}
 i=bisect_left(x,query)
 value=fitted[i] if x[i]==query else fitted[i-1]+(query-x[i-1])/(x[i]-x[i-1])*(fitted[i]-fitted[i-1])
 return {'flow':float(query),'prediction':float(value),'clamped':None,'within_observed_domain':True}
