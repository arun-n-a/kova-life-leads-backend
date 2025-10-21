from typing import List, Dict, Union, Optional, Tuple
from datetime import datetime, timedelta
from flask import g
from sqlalchemy import func


from app.models import (
    SubscriptionOrderSummary as SOS,
    PricingDetail as PD,
    StripeCustomerSubscription  as SCS
    )

def get_revenue_by_plan(start_date: str, end_date: str) -> List[Dict]:
    
    results = SOS.query.join(
        SCS, SOS.subscription_db_id == SCS.id
    ).join(
        PD, SCS.pricing_id == PD.id
    ).with_entities(
        PD.title.label("plan"),
        func.count(SOS.id).label("orders_count"),
        func.coalesce(func.sum(SOS.amount_received), 0.0).label("total_revenue")
    ).filter(
        SOS.created_at.between(datetime.strptime(start_date, "%m-%d-%Y"), datetime.strptime(end_date, "%m-%d-%Y") + timedelta(days=1)),
        SOS.payment_status == "paid"
    ).group_by(
        PD.id
    ).order_by(
        func.sum(SOS.amount_received).desc()
    ).all()

    return [row._asdict() for row in results]
