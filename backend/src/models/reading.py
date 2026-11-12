from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import ForeignKey,String,Float,Text,UniqueConstraint
from src.config.database import Base
class PressureReading(Base):
 __tablename__='pressure_readings'
 __table_args__=(UniqueConstraint('study_id','specimen_ref'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 study_id:Mapped[int]=mapped_column(ForeignKey('flow_studies.id'))
 level_id:Mapped[int]=mapped_column(ForeignKey('dose_levels.id'))
 specimen_ref:Mapped[str]=mapped_column(String(80))
 pressure:Mapped[float]=mapped_column(Float)
 measurement_note:Mapped[str]=mapped_column(Text,default='')
