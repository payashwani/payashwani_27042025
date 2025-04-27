import os
import uuid
import pandas as pd
from datetime import datetime, timedelta, time
from pytz import timezone, utc
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends, Response
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Time, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
from utils import load_csv_to_db

# Load environment variables
load_dotenv()

# Database setup
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Directory for CSVs
CSV_DATA_DIR = "data"

# Models
class StoreStatus(Base):
    __tablename__ = 'store_status'

    store_id = Column(String(255), primary_key=True)
    timestamp_utc = Column(DateTime, primary_key=True)
    status = Column(String(255))
    local_time = Column(DateTime)
    prev_status = Column(String(255))

class BusinessHours(Base):
    __tablename__ = 'business_hours'

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255))
    dayofweek = Column(Integer)
    start_time_local = Column(Time)
    end_time_local = Column(Time)

class TimezoneData(Base):
    __tablename__ = 'timezone_data'

    store_id = Column(String(255), primary_key=True)
    timezone_str = Column(String(255))

class ReportStatus(Base):
    __tablename__ = 'report_status'

    report_id = Column(String(36), primary_key=True, index=True)
    status = Column(String(50))
    report_data = Column(String)

Base.metadata.create_all(bind=engine)

# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility function to load CSV data
def load_csv_to_db(db: Session, csv_file: str, model):
    df = pd.read_csv(csv_file)
    for index, row in df.iterrows():
        try:
            db_row = model(**row.to_dict())
            db.add(db_row)
        except Exception as e:
            print(f"Error loading row: {row.to_dict()} - {e}")
    db.commit()

# Lifespan event for startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        from utils import load_csv_to_db # Ensure it's imported here as well (redundant but for clarity)
        load_csv_to_db(db, os.path.join(CSV_DATA_DIR, "store_status.csv"), StoreStatus)
        load_csv_to_db(db, os.path.join(CSV_DATA_DIR, "business_hours.csv"), BusinessHours)
        load_csv_to_db(db, os.path.join(CSV_DATA_DIR, "timezone_data.csv"), TimezoneData)
        db.commit()
    except Exception as e:
        print(f"Error during startup: {e}")
        db.rollback()
    finally:
        db.close()

    yield  # App is running


# Create FastAPI app
app = FastAPI(lifespan=lifespan)

def generate_report(report_id: str):
    db = SessionLocal()
    try:
        print(f"Generating report with report_id: {report_id}")

        # Fetch all data
        store_status_data = db.query(StoreStatus).all()
        business_hours_data = db.query(BusinessHours).all()
        timezone_data = db.query(TimezoneData).all()

        # Create timezone mapping
        timezone_map = {tz.store_id: timezone(tz.timezone_str) for tz in timezone_data}

        # Convert timestamps to local time
        for status in store_status_data:
            local_tz = timezone_map.get(status.store_id, timezone("America/Chicago"))
            status.local_time = status.timestamp_utc.replace(tzinfo=utc).astimezone(local_tz)

        def is_within_business_hours(store_id: str, local_time: datetime):
            hours = [h for h in business_hours_data if h.store_id == store_id and h.dayofweek == local_time.weekday()]
            if not hours:  # Assume 24/7 if no business hours
                return True
            for hour in hours:
                start_time = local_time.replace(hour=hour.start_time_local.hour, minute=hour.start_time_local.minute, second=0, microsecond=0)
                end_time = local_time.replace(hour=hour.end_time_local.hour, minute=hour.end_time_local.minute, second=0, microsecond=0)
                if start_time <= local_time <= end_time:
                    return True
            return False

        # Filter status records by business hours
        valid_status_data = [status for status in store_status_data if is_within_business_hours(status.store_id, status.local_time)]

        # Sort status data by local_time
        valid_status_data.sort(key=lambda x: x.local_time)

        # Extrapolate status
        for i in range(1, len(valid_status_data)):
            valid_status_data[i].prev_status = valid_status_data[i - 1].status

        # Determine "current time"
        if not store_status_data:
            db.query(ReportStatus).filter(ReportStatus.report_id == report_id).update({ReportStatus.status: "complete", ReportStatus.report_data: ""})
            db.commit()
            return

        current_time = max(status.local_time for status in store_status_data)
        one_hour_ago = current_time - timedelta(hours=1)
        one_day_ago = current_time - timedelta(days=1)
        one_week_ago = current_time - timedelta(weeks=1)

        # Calculate uptime/downtime
        report_data = []
        for store_id in sorted(list(set(status.store_id for status in valid_status_data))):
            store_statuses = [status for status in valid_status_data if status.store_id == store_id]

            uptime_last_hour = 0
            uptime_last_day = 0
            downtime_last_hour = 0
            downtime_last_day = 0
            downtime_last_week = 0

            for i in range(1, len(store_statuses)):
                time_diff_minutes = (store_statuses[i].local_time - store_statuses[i - 1].local_time).total_seconds() / 60
                time_diff_hours = time_diff_minutes / 60

                # Last Hour - MODIFIED LOGIC
                if store_statuses[i].local_time > one_hour_ago:
                    overlap_start_hour = max(store_statuses[i - 1].local_time, one_hour_ago)
                    overlap_end_hour = min(store_statuses[i].local_time, current_time)
                    overlap_duration_hour = (overlap_end_hour - overlap_start_hour).total_seconds() / 60
                    if overlap_duration_hour > 0:
                        if store_statuses[i - 1].status == "active":
                            uptime_last_hour += overlap_duration_hour
                        else:
                            downtime_last_hour += overlap_duration_hour

                # Last 24 Hours
                overlap_start_day = max(store_statuses[i - 1].local_time, one_day_ago)
                overlap_end_day = min(store_statuses[i].local_time, current_time)
                overlap_duration_day = (overlap_end_day - overlap_start_day).total_seconds() / 3600
                if overlap_duration_day > 0:
                    if store_statuses[i - 1].status == "active":
                        uptime_last_day += overlap_duration_day
                    else:
                        downtime_last_day += overlap_duration_day

                # Last 7 Days
                overlap_start_week = max(store_statuses[i - 1].local_time, one_week_ago)
                overlap_end_week = min(store_statuses[i].local_time, current_time)
                overlap_duration_week = (overlap_end_week - overlap_start_week).total_seconds() / 3600
                if overlap_duration_week > 0:
                    if store_statuses[i - 1].status == "active":
                        # We'll accumulate total active hours within the week
                        pass # Calculation for weekly uptime is more complex and might require a different approach
                    else:
                        downtime_last_week += overlap_duration_week

            # Simplified weekly uptime (can be improved)
            total_active_week = 0
            for i in range(1, len(store_statuses)):
                if store_statuses[i - 1].status == "active" and store_statuses[i].local_time > one_week_ago:
                    overlap_start_week = max(store_statuses[i - 1].local_time, one_week_ago)
                    overlap_end_week = min(store_statuses[i].local_time, current_time)
                    total_active_week += (overlap_end_week - overlap_start_week).total_seconds() / 3600


            report_data.append({
                "store_id": store_id,
                "uptime_last_hour": uptime_last_hour,
                "uptime_last_day": uptime_last_day,
                "downtime_last_hour": downtime_last_hour,
                "downtime_last_day": downtime_last_day,
                "downtime_last_week": downtime_last_week,
            })

        # Create CSV string
        csv_data = pd.DataFrame(report_data).to_csv(index=False)

        # Update report status
        db.query(ReportStatus).filter(ReportStatus.report_id == report_id).update({ReportStatus.status: "complete", ReportStatus.report_data: csv_data})
        db.commit()
    except Exception as e:
        print(f"Error generating report: {e}")
        db.rollback()
    finally:
        db.close()

# POST endpoint to trigger report
@app.post("/trigger_report")
async def trigger_report(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    report_id = str(uuid.uuid4())
    report_status = ReportStatus(report_id=report_id, status="running")
    db.add(report_status)
    db.commit()
    try:
        db.refresh(report_status)
        print(f"Report status record created with ID: {report_id}, Status: {report_status.status}")
    except Exception as e:
        print(f"Error refreshing report status: {e}")

    background_tasks.add_task(generate_report, report_id)

    return {"report_id": report_id}

# GET endpoint to get report
@app.get("/get_report/{report_id}")
async def get_report(report_id: str, db: Session = Depends(get_db)):
    print(f"Attempting to retrieve report with ID: {report_id}")
    report = db.query(ReportStatus).filter(ReportStatus.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status == "running":
        return {"status": "running"}

    return Response(content=report.report_data, media_type="text/csv", headers={"Content-Disposition": f"attachment;filename=report_{report_id}.csv"})