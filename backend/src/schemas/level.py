from pydantic import BaseModel,Field,ConfigDict
from .reading import ReadingInput
class LevelInput(BaseModel):
 model_config=ConfigDict(allow_inf_nan=False)
 label:str=Field(min_length=1,max_length=80)
 flow:float=Field(ge=0,le=1000)
 readings:list[ReadingInput]=Field(min_length=1,max_length=30)
class LevelPatch(BaseModel):
 model_config=ConfigDict(allow_inf_nan=False)
 label:str=Field(min_length=1,max_length=80)
 flow:float=Field(ge=0,le=1000)
