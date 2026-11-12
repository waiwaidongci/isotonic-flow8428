export const fmt=(x:number,d=4)=>Number.isFinite(x)?x.toLocaleString('zh-CN',{maximumFractionDigits:d}):'—';export const clock=(v:string)=>new Date(v).toLocaleString('zh-CN',{hour12:false});
