# Uploaded files will be having different column names for the same field so match it from the front end

from typing import Dict
from app.models.base import BaseModel
from app import db


class InputFileTemplate(BaseModel):
    __tablename__ = "input_file_template"
    """Table for storing the data from the input CSV file"""
    id = db.Column(db.Integer, primary_key=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    data = db.Column(db.JSON, default=[])
    category = db.Column(db.Integer, index=True, nullable=False)
    source = db.Column(db.Integer, index=True, nullable=False)