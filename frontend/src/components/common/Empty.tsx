export function Empty({title,help}:{title:string;help:string}){return <div className="empty"><small>NO RESEARCH RECORD</small><h2>{title}</h2><p>{help}</p><a href="#config">前往拟合配置 →</a></div>}
