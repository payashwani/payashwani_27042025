from sqlalchemy import create_engine, Column, String, Integer, DateTime, Time, VARCHAR, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import PrimaryKeyConstraint

Base = declarative_base()

class StoreStatus(Base):
    __tablename__ = 'store_status'

    store_id = Column(VARCHAR(255), primary_key=True)
    timestamp_utc = Column(DateTime, primary_key=True)
    status = Column(VARCHAR(255))
    local_time = Column(DateTime)  # For storing local time
    prev_status = Column(VARCHAR(255)) # For storing previous status

class BusinessHours(Base):
    __tablename__ = 'business_hours'

    store_id = Column(VARCHAR(255), primary_key=True)
    dayofweek = Column(Integer, primary_key=True)
    start_time_local = Column(Time)
    end_time_local = Column(Time)
    __table_args__ = (
        PrimaryKeyConstraint('store_id', 'dayofweek'),
    )

class TimezoneData(Base):
    __tablename__ = 'timezone_data'

    store_id = Column(VARCHAR(255), primary_key=True)
    timezone_str = Column(VARCHAR(255))

class ReportStatus(Base):
    __tablename__ = 'report_status'

    report_id = Column(VARCHAR(255), primary_key=True)
    status = Column(VARCHAR(255))
    report_data = Column(String)  # Or consider TEXT for larger reports