# """Models for storing the cost of different leads."""
# from app import db
# from app.models.base import BaseModel


# class MarketplacePricing(BaseModel):
#     __tablename__ = "marketplace_pricing"
#     """Table for storing the lead type id name description and cost"""
#     id = db.Column(db.Integer, primary_key=True)
#     description = db.Column(db.Text)
#     category_id = db.Column(db.Integer)
#     is_gold = db.Column(db.Boolean, nullable=False)
#     month = db.Column(db.Integer)  # 1: last 30 to 60 days,  2: last 60 to 90 days 3: Above 90 days
#     cost = db.Column(db.Float)
#     source_id = db.Column(db.Integer, default=0)
#     promo_codes = db.relationship("PromoCode", backref="marketplace_leads_promos")

#     def to_dict(self):
#         data = dict(
#             id=self.id,
#             type_=self.type_,
#             description=self.description,
#             month=self.month,
#             cost=self.cost,
#             category_id=self.category_id,
#             source_id=self.source_id
#         )
#         return data
