from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import ForeignKey,String,Float,UniqueConstraint
from src.config.database import Base
class DoseLevel(Base):
 __tablename__='dose_levels'
 __table_args__=(UniqueConstraint('study_id','label'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 study_id:Mapped[int]=mapped_column(ForeignKey('flow_studies.id'))
 label:Mapped[str]=mapped_column(String(80))
 flow:Mapped[float]=mapped_column(Float)
