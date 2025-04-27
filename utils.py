import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import inspect

def load_csv_to_db(db: Session, csv_file: str, model):
    print(f"Loading data from {csv_file} into {model.__tablename__}") # Added print statement
    df = pd.read_csv(csv_file)
    inspector = inspect(model)
    primary_key_columns = [pk.name for pk in inspector.primary_key]

    for index, row in df.iterrows():
        row_dict = row.to_dict()
        query = db.query(model)
        conditions = []
        for pk_column in primary_key_columns:
            if pk_column in row_dict:
                conditions.append(getattr(model, pk_column) == row_dict[pk_column])

        if conditions:
            existing_record = query.filter(*conditions).first()
            if not existing_record:
                db_row = model(**row_dict)
                db.add(db_row)
        else:
            # If no primary key is defined (shouldn't happen with our models), just add
            db_row = model(**row_dict)
            db.add(db_row)

    db.commit()