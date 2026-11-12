from pydantic import BaseModel,Field
from typing import Literal
from .level import LevelInput
class StudyInput(BaseModel):
 name:str=Field(min_length=2,max_length=150)
 filename:str=Field(min_length=2,max_length=180)
 description:str=Field(default='',max_length=3000)
 direction:Literal['nondecreasing']='nondecreasing'
 levels:list[LevelInput]=Field(min_length=2,max_length=30)
