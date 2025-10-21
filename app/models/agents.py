from sqlalchemy import Sequence
from sqlalchemy.dialects.postgresql import UUID

from app.models import BaseModel
from app import db


class Agent(BaseModel):
    __tablename__ = 'agent'
    agent_id_seq = Sequence('agent_id_seq', start=1001)
    id = db.Column('id', db.Integer, agent_id_seq,
                   server_default=agent_id_seq.next_value(), primary_key=True, index=True)
    category = db.Column(db.Integer, nullable=False,
                         index=True)  # LEAD_CATEGORY keys (Mailing | Digital)
    source = db.Column(db.Integer, nullable=False, index=True) # LEAD_CATEGORY sources
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("user.id", ondelete="CASCADE"))

    # Relationship
    # user_info = db.relationship(
    #     "User", viewonly=True, backref="agent_user_info", 
    #     foreign_keys="[User.id]", uselist=False)
    mailing_leads = db.relationship(
        "MailingAssignee", backref="agent_mailing_leads_list", 
        foreign_keys="[MailingAssignee.agent_id]",
        lazy=True)

    def to_dict(self):
        return {'id': self.id, 'category': self.category, 'source': self.source}

    def to_detailed_dict(self):
        return {'id': self.id, 'category': self.category, 'source': self.source, 'user_id': self.user_id,
                'email': self.user_info.email, 'name': self.user_info.name, 'phone': self.user_info.phone}
