from typing import Dict, List

from sqlalchemy import or_, func, case, and_
from app.models import (
    PricingDetail as PD, 
    StripePriceId as SPI,
    StripeCustomerSubscription as SCS
    )
from app.services.crud import CRUD
from app.services.stripe_service import StripeService
from app import db
from constants import STRIPE_COMMISSION_FEE


def list_subscription_pricing_plans(page: int, per_page: int) -> List:
    pricing_objs= PD.query.with_entities(
        PD.id, PD.category, PD.source,
        PD.description, PD.month, PD.unit_price, PD.title,
        PD.quantity, PD.stripe_product_id, PD.stripe_price_id,
        PD.net_price).filter(
            PD.is_fresh_leads == True, 
            PD.is_active == True
            ).order_by(
                PD.quantity.desc()
                ).paginate(page=page, per_page=per_page, error_out=False)
    result= [pricing_obj._asdict() for pricing_obj in pricing_objs.items]
    return result, {'total': pricing_objs.total, 'current_page': pricing_objs.page, 'per_page': pricing_objs.per_page,
                        'length': len(result)}


def list_pricing_plans_in_mp() -> List:
    pricing_objs= PD.query.with_entities(
        PD.id, PD.category, PD.source,
        PD.description, PD.month, PD.unit_price, PD.title,
        PD.quantity, PD.completed
        ).filter(PD.is_fresh_leads == False).all()
    return [pricing_obj._asdict() for pricing_obj in pricing_objs]


def update_pricing_detail(pricing_id: str, data: Dict) -> Dict:
    """Update pricing detail in database and Stripe."""
    stripe_obj = StripeService()
    pricing_obj = PD.query.get(pricing_id)
    if data.get('title') or data.get('description'):
            stripe_obj.product_update(
            product_id=pricing_obj.stripe_product_id,
        data={
            "name": data.get("title", pricing_obj.title),
            "description": data.get("description", pricing_obj.description)
            }
        )
    if data.get('unit_price'):
        pricing_obj.unit_price = data.pop('unit_price')
        if pricing_obj.is_fresh_leads:
            # TODO deactive old pricing
            stripe_obj.deactivate_old_pricing(pricing_obj.stripe_price_id)
            pricing_obj.net_price = round(
                 pricing_obj.unit_price + STRIPE_COMMISSION_FEE * pricing_obj.unit_price
                 )
            price_id = stripe_obj.create_pricing(
                  product_id=pricing_obj.stripe_product_id,
                  unit_amount=pricing_obj.net_price,
                  currency=data.pop('currency', 'usd')
                  )
                            #   metadata=data.pop('metadata', {}),
                #   recurring=data.get('is_recurring')
            #)
            SPI.query.filter_by(stripe_price_id=pricing_obj.stripe_price_id).update({'is_active': False})
            spi_obj = SPI(pricing_id=pricing_id, stripe_price_id=price_id)
            db.session.add(spi_obj)
            pricing_obj.stripe_price_id = price_id
    for k, v in data.items():
        setattr(pricing_obj, k, v)
    CRUD.db_commit()
    return True

    
def admin_list_pricing_packages() -> List:
    """
    In admin view active subscriptions of each pricing detail is shown
    """
    pricing_objs = PD.query.outerjoin(
         SCS, 
         and_(
              SCS.pricing_id == PD.id, 
              or_(
                   SCS.status == None, SCS.status == 'active'
                   )
            )
        ).with_entities(
             PD.id, PD.category, PD.source, PD.is_fresh_leads, 
             PD.description, PD.month, PD.unit_price, PD.title,
             PD.quantity, PD.stripe_product_id, PD.stripe_price_id,
             func.count(SCS.id).label("active_subscriptions_count"),
             PD.net_price
             ).filter(
                 PD.is_fresh_leads == True, PD.is_active == True
                 ).order_by(
                     PD.net_price).group_by(PD.id).all()
    return [pricing_obj._asdict() for pricing_obj in pricing_objs]


def creating_product_pricing(data: Dict) -> Dict:
    stripe_obj = StripeService()
    product = stripe_obj.create_product({
        "name": data.get("title"),
        "description": data.get("description", ""),
        "active": True
    })
    stripe_product_id = product
    pricing_obj = PD(
        title=data.get("title"),
        description=data.get("description", ""),
        quantity=data.get("quantity"),
        month=data.get("month"),
        category=data.get("category"),
        source=data.get("source"),
        unit_price=data.get("unit_price"),
        is_fresh_leads=data.get("is_fresh_leads"),
        stripe_product_id=stripe_product_id,
    )
    db.session.add(pricing_obj)
    if data.get("unit_price") and pricing_obj.is_fresh_leads:
        pricing_obj.unit_price = data.pop("unit_price")
        pricing_obj.net_price = round(
            pricing_obj.unit_price + STRIPE_COMMISSION_FEE * pricing_obj.unit_price
        )
        price_id = stripe_obj.create_pricing(
            product_id=pricing_obj.stripe_product_id,
            unit_amount=pricing_obj.net_price,
            currency=data.pop("currency", "usd")
        )
        spi_obj = SPI(pricing_id=pricing_obj.id, stripe_price_id=price_id)  
        db.session.add(spi_obj)
        pricing_obj.stripe_price_id = price_id

    CRUD.db_commit()
    return True

def deactivating_product_pricing(pricing_id: str) -> bool:
    stripe_obj = StripeService()
    pricing_obj = PD.query.get(pricing_id)
    if pricing_obj.stripe_price_id:
        stripe_obj.deactivate_old_pricing(pricing_obj.stripe_price_id)
    if pricing_obj.stripe_product_id:
        stripe_obj.deactivate_product(pricing_obj.stripe_product_id)
    pricing_obj.is_active = False
    SPI.query.filter_by(stripe_price_id=pricing_obj.stripe_price_id).update({"is_active": False})
    CRUD.db_commit()
    return True

