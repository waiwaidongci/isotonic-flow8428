from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.models import MonotoneRun
from src.controllers.dependencies import current_user,writers
from src.schemas.run import RunInput
from src.services.runs import create_run,retry_run,run_input_diff
from src.utils.serialize import row
router=APIRouter()
def _view(run):
 # 列表与详情不回传完整快照（读数级数据量大）；锁定输入经 /input-diff 端点核对。
 data=row(run);data.pop('input_snapshot',None);return data
@router.get('/runs')
def runs(db:Session=Depends(get_db),user=Depends(current_user)):return [_view(x) for x in db.scalars(select(MonotoneRun).order_by(MonotoneRun.id.desc()))]
@router.get('/runs/{id}')
def one(id:int,db:Session=Depends(get_db),user=Depends(current_user)):
 run=db.get(MonotoneRun,id)
 if not run:raise HTTPException(404,'运行不存在')
 return _view(run)
@router.get('/runs/{id}/input-diff')
def diff(id:int,db:Session=Depends(get_db),user=Depends(current_user)):return run_input_diff(db,id)
@router.post('/runs/{id}/retry')
def retry(id:int,db:Session=Depends(get_db),user=Depends(writers)):return retry_run(db,id,user.email)
@router.post('/runs')
def create(data:RunInput,db:Session=Depends(get_db),user=Depends(writers)):return _view(create_run(db,data,user.email))
