from pydantic import BaseModel,Field,ConfigDict
from typing import Literal
class NoteInput(BaseModel):
 model_config=ConfigDict(allow_inf_nan=False)
 run_id:int=Field(gt=0)
 name:str=Field(min_length=2,max_length=180)
 interpretation:str=Field(min_length=5,max_length=4000)
 next_step:str=Field(min_length=5,max_length=4000)
 proposed_flow:float=Field(ge=0,le=1000)
class ApprovalInput(BaseModel):
 status:Literal['approved','rejected']
 review_note:str=Field(min_length=2,max_length=2000)
