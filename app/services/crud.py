from sqlalchemy.exc import IntegrityError

from app import db
from app.services.custom_errors import *
from app import logging


class CRUD:
    @classmethod
    def create(cls, model_is, data):
        try:
            record = model_is(**data)
            db.session.add(record)
        except Exception as e:
            print(f"CRUD Create {model_is} {data} {e}")
            logging.error(f"CRUD Create {model_is} {data} {e}")
            raise BadRequest(f"Please provide all fields correctly {e}")
        cls.db_commit()
        return record

    @classmethod
    def update(cls, model_is, condition, data):
        try:
            record = model_is.query.filter_by(**condition).update(data)
        except IntegrityError as e:
            db.session.rollback()
            print(e)
            logging.error(f"CRUD Update {model_is} {condition} {data} {e}")
            if "errors.UniqueViolation" in str(e):
                raise UnProcessable("This data already exists")
            raise UnProcessable()
        if record:
            cls.db_commit()
            return True
        raise NoContent()

    @classmethod
    def create_if_not(cls, model_is, condition, data):
        record = model_is.query.filter_by(**condition).first()
        if not record:
            return cls.create(model_is, data)
        return record

    @classmethod
    def create_or_update(cls, model_is, condition, data):
        record = model_is.query.filter_by(**condition).first()
        if not record:
            return cls.create(model_is, data)
        return cls.update(model_is, condition, data)

    @classmethod
    def bulk_insertion(cls, model_cls, data):
        try:
            objects = [model_cls(**record) for record in data]
            db.session.bulk_save_objects(objects)
            cls.db_commit()
        except Exception as e:
            logging.error(f"CRUD Bulk Insertion {model_cls} {e}")
            db.session.rollback()
            raise InternalError("Bulk insertion failed")

    @classmethod
    def delete(cls, model_is, condition):
        records = model_is.query.filter_by(**condition).all()
        try:
            for record in records:
                db.session.delete(record)
            cls.db_commit()
        except Exception as e:
            print(f"Crud delete exception {e} {condition} {model_is}")
        return True

    @staticmethod
    def db_commit() -> bool:
        try:
            db.session.commit()
            return True
        except IntegrityError as e:
            print(f"CRUD Commit {e}")
            db.session.rollback()
            if "errors.UniqueViolation" in str(e):
                msg = (str(e).split("Key (")[1].split(")")[0].replace("_", " ").title() + " already exists")
            else:
                msg = 'Database failed this operation'
        except Exception as e:
            print(e)
            msg = 'Unexpected Error occurred'
            db.session.rollback()
        print(f"mgs--> {msg}")
        raise InternalError(msg)
    
    @staticmethod
    def transaction_flush() -> bool:
        try:
            db.session.flush()
            return True
        except IntegrityError as e:
            print(f"CRUD Commit {e}")
            db.session.rollback()
            if "errors.UniqueViolation" in str(e):
                msg = (str(e).split("Key (")[1].split(")")[0].replace("_", " ").title() + " already exists")
            else:
                msg = 'Database failed this operation'
        except Exception as e:
            print(e)
            msg = 'Unexpected Error occurred'
        db.session.rollback()
        raise InternalError(msg)