import {useCallback,useEffect,useState} from 'react';
import {researchApi} from '../api/research';
import type {InputDiff,Run} from '../types/domain';
import {Table} from './common/Table';
import {Notice} from './common/Notice';
import {useTask} from '../hooks/useTask';
import {fmt} from '../utils/format';

const short=(v?:string)=>v?v.slice(0,12)+'…':'—';

function ChangeBlock({title,rows,render}:{title:string;rows:any[];render:(x:any)=>JSX.Element}){
 if(!rows?.length)return null;
 return <details className="diff-block" open><summary>{title}（{rows.length}）</summary>
  <Table headers={['对象','字段','排队锁定值','当前底稿值']}>{rows.map((x,i)=><tr key={i}>{render(x)}</tr>)}</Table></details>;
}

export function InputDiffPanel({run,user,reloadResearch}:{run:Run;user:any;reloadResearch:()=>Promise<any>}){
 const [diff,D]=useState<InputDiff|null>(null),[loadError,E]=useState('');
 const task=useTask();
 const load=useCallback(async()=>{
  try{D(await researchApi.inputDiff(run.id));E('')}catch(error:any){D(null);E(error.message)}
 },[run.id]);
 useEffect(()=>{D(null);E('');load()},[load]);
 const canWrite=user.role!=='viewer';
 return <section className="ledger-section input-lock">
  <div className="section-head"><h2>排队输入锁定与当前底稿核对</h2>
   <span>结果只由排队时刻冻结的研究、档位、读数与配置计算</span></div>
  {loadError&&<Notice error={loadError}/>}
  {!diff&&!loadError&&<p>正在核对锁定输入与当前底稿…</p>}
  {diff&&!diff.has_snapshot&&<div className="notice error" role="alert">历史运行缺少留存输入，拒绝重算<small>{diff.reason}</small></div>}
  {diff?.has_snapshot&&<>
   <div className="lock-badges">
    <span className="lock-pill">锁定输入指纹 <code>{short(diff.snapshot_fingerprint)}</code></span>
    {diff.current_available===false
      ?<span className="lock-pill warn">当前底稿研究已删除，无法比对；结果仍以锁定输入为准</span>
      :diff.matches
        ?<span className="lock-pill ok">与当前底稿一致，无修订混用</span>
        :<span className="lock-pill warn">当前底稿已修订，与锁定输入存在差异（本次结果不受影响）</span>}
   </div>
   {diff.current_available&&!diff.matches&&<>
    <p className="diff-fingerprint">当前底稿指纹 <code>{short(diff.current_fingerprint)}</code> ≠ 锁定指纹 <code>{short(diff.snapshot_fingerprint)}</code></p>
    <div className="diff-grid">
     <ChangeBlock title="研究字段修订" rows={diff.study_changes||[]} render={x=><><td>{diff.snapshot_summary?.study_name}</td><td>{x.field}</td><td>{String(x.snapshot)}</td><td>{String(x.current)}</td></>}/>
     <ChangeBlock title="档位修订" rows={diff.levels_changed||[]} render={x=><><td>档位 #{x.level_id}</td><td>{x.field}{x.field==='flow'?' mL/min':''}</td><td>{x.field==='flow'?fmt(x.snapshot):String(x.snapshot)}</td><td>{x.field==='flow'?fmt(x.current):String(x.current)}</td></>}/>
     <ChangeBlock title="新增档位" rows={diff.levels_added||[]} render={x=><><td>档位 #{x.level_id} {x.label}</td><td>整档</td><td>—</td><td>{fmt(x.flow)} mL/min</td></>}/>
     <ChangeBlock title="删除档位" rows={diff.levels_removed||[]} render={x=><><td>档位 #{x.level_id} {x.label}</td><td>整档</td><td>{fmt(x.flow)} mL/min</td><td>—</td></>}/>
     <ChangeBlock title="读数修订" rows={diff.readings_changed||[]} render={x=><><td>{x.specimen_ref}（读数 #{x.reading_id}）</td><td>{x.field==='pressure'?'压差 kPa':x.field}</td><td>{x.field==='pressure'?fmt(x.snapshot,6):String(x.snapshot)}</td><td>{x.field==='pressure'?fmt(x.current,6):String(x.current)}</td></>}/>
     <ChangeBlock title="新增读数" rows={diff.readings_added||[]} render={x=><><td>{x.specimen_ref}（读数 #{x.reading_id}）</td><td>整读数</td><td>—</td><td>{fmt(x.pressure,6)} kPa</td></>}/>
     <ChangeBlock title="删除读数" rows={diff.readings_removed||[]} render={x=><><td>{x.specimen_ref}（读数 #{x.reading_id}）</td><td>整读数</td><td>{fmt(x.pressure,6)} kPa</td><td>—</td></>}/>
    </div>
   </>}
   {diff.current_available&&diff.matches&&<p>排队后底稿未发生修订；如后续修订，本次结果与已批准复验说明、下载 CSV 均保持不变。</p>}
  </>}
  {run.status==='failed'&&canWrite&&diff?.has_snapshot&&<div className="retry-line">
   <button className="text-action" onClick={()=>task.act(async()=>{await researchApi.retryRun(run.id);await reloadResearch();load()},'已按排队时锁定的原始输入重新排队，不读取当前底稿')}>以原始锁定输入重试 ↻</button>
   <small>重试沿用同一快照与指纹，不混用修订后的两版输入</small>
  </div>}
  {run.status==='failed'&&canWrite&&diff&&!diff.has_snapshot&&<p className="error-text">无留存输入，不可重试；请以当前底稿新建运行。</p>}
  <Notice {...task}/>
 </section>;
}
