from typing import List, Dict

from app.services.crud import CRUD
from app.models import InputFileTemplate as IFT


def list_file_templates(category: int, source: int) -> List:
    query_obj = IFT.query.filter(
        IFT.category ==category, IFT.source == source
        ).with_entities(
            IFT.category, IFT.source, IFT.id, IFT.data, 
            IFT.name
            ).order_by(
                IFT.modified_at.desc()
                ).all()
    data = [t._asdict() for t in query_obj]
    return data


def add_new_file_template(data: Dict) -> bool:
    CRUD.create(IFT, data)
    return True


def update_file_template(id_: int, data: Dict) -> bool:
    CRUD.update(IFT, {"id": id_}, data)
    return True
