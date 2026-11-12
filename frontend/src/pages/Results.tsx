import {PageHeading} from '../components/common/PageHeading';
import {Table} from '../components/common/Table';
import {Status} from '../components/common/Status';
import {Empty} from '../components/common/Empty';
import {ResponsePlot} from '../components/ResponsePlot';
import {FitDigest} from '../components/FitDigest';
import {InverseSet} from '../components/InverseSet';
import {LodoTable} from '../components/LodoTable';
import {InputDiffPanel} from '../components/InputDiffPanel';
import {fmt} from '../utils/format';

export function ResultsPage({runs,selectedId,open,user,reloadResearch}:any){
 const run=runs.find(r=>r.id===selectedId)||runs[0],result=run?.result;
 return <>
  <PageHeading index="04" title="曲线有平台，反解有集合。" description="PAVA块、观测域插值与整档预测误差，分别保留数值和解释边界；每次分析锁定排队时的研究、档位、读数与配置。"/>
  <label>结果运行<select value={run?.id||''} onChange={e=>open(runs.find(r=>r.id===+e.target.value))}>{runs.map(r=><option key={r.id} value={r.id}>#{r.id} {r.name}</option>)}</select></label>
  {run&&<p><Status value={run.status}/>　{run.error}</p>}
  {run&&<InputDiffPanel run={run} user={user} reloadResearch={reloadResearch}/>}
  {!result
   ?<Empty title={run?.status==='failed'?'本次拟合失败':'等待真实worker计算'} help={run?.error||'任务每2.5秒刷新；请先核对底稿并排队。'}/>
   :<>
    <FitDigest result={result}/>
    <div className="curve-layout"><ResponsePlot knots={result.knots} threshold={result.threshold_set}/><InverseSet result={result}/></div>
    <section className="ledger-section">
     <div className="section-head"><h2>相邻块如何合并</h2><span>目标函数 {fmt(result.weighted_between_level_objective,6)}</span></div>
     <Table headers={['块','流速范围 mL/min','聚合权重','块拟合 kPa']} >{result.pava_blocks.map((b:any,i:number)=><tr key={i}><td>{i+1}</td><td>{fmt(result.knots[b.start_index].flow)} — {fmt(result.knots[b.end_index_exclusive-1].flow)}</td><td>{b.weight}</td><td>{fmt(b.fitted_pressure,6)}</td></tr>)}</Table>
    </section>
    <section className="ledger-section"><h2>查询与端点边界</h2>
     <Table headers={['查询流速','拟合压差 kPa','范围解释']} >{result.predictions.map((p:any,i:number)=><tr key={i}><td>{fmt(p.flow)}</td><td>{fmt(p.prediction,6)}</td><td>{p.clamped==='left'?'左端点夹持 / 非外推':p.clamped==='right'?'右端点夹持 / 非外推':'观测域内单调线性插值'}</td></tr>)}</Table>
    </section>
    <LodoTable result={result}/>
    <details className="provenance" open={!run.input_fingerprint}>
     <summary>冻结输入指纹与完整聚合节点</summary>
     {run.input_fingerprint
       ?<p className="fingerprint">排队锁定输入指纹 {run.input_fingerprint}<br/><small>结果指纹与排队输入一致：{result.fingerprint===run.input_fingerprint?'是，未采用执行时底稿':'否，已拒绝执行'}</small></p>
       :<p className="fingerprint error-text">历史运行未留存排队输入快照，不能重算；下方结果仅作只读存档，不得拿当前底稿现值补齐。</p>}
     <p className="fingerprint">结果内指纹 {result.fingerprint}</p>
     <Table headers={['流速','档名','独立数','原始均值','PAVA拟合']} >{result.knots.map((k:any)=><tr key={k.flow}><td>{fmt(k.flow)}</td><td>{k.labels.join(' / ')}</td><td>{k.count}</td><td>{fmt(k.mean_pressure,7)}</td><td>{fmt(k.fitted_pressure,7)}</td></tr>)}</Table>
     <p>{result.interpretation}</p>
    </details>
    <a className="text-action" href="#notes">制定独立新档复验说明 →</a>
   </>}
 </>;
}
