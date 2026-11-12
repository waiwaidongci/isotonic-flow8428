from pydantic import BaseModel,Field,ConfigDict
from typing import Literal
class RunInput(BaseModel):
 model_config=ConfigDict(allow_inf_nan=False)
 study_id:int=Field(gt=0)
 name:str=Field(min_length=2,max_length=180)
 target_pressure:float=Field(ge=0,le=1000000)
 query_flows:list[float]=Field(min_length=1,max_length=30)
 direction:Literal['nondecreasing']='nondecreasing'
