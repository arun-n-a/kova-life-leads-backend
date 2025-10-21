from concurrent.futures import ThreadPoolExecutor
from datetime import (datetime, timedelta)
from typing import (Dict, List)
from uuid import uuid4
import queue


from flask import (g, render_template)
from sqlalchemy import (func, or_)

from app import app, db
from app.models import (
    MailingAssignee as MA,
    MailingLead as ML,
    MailingResponse as MR,
    PricingDetail as PD,
    ShoppingCart as SC,
    SubscriptionOrderSummary as SOS,
    MarketplaceOrderSummary as MOS
)
from app.services.sendgrid_email import SendgridEmailSending
from app.services.crud import CRUD
from app.services.custom_errors import (
    InternalError, NoContent, BadRequest
    )
from app.services.utils import (
    add_redis_ttl_data,
    convert_datetime_to_timezone_date
    )
from app import tasks

from config import Config_is
from constants import PRICING_DETAIL_MONTH



def get_cart_items() -> List:
    """
    Get all active cart items
    """
    cart_items = SC.query.join(PD, PD.id == SC.pricing_id).with_entities(
        SC.id, SC.state, SC.quantity, SC.pricing_id, 
        PD.category, PD.source, PD.description, PD.title, PD.completed, 
        PD.month, PD.unit_price).filter_by(
            user_id=g.user['id'], is_active=True).all()
    data = [item._asdict() for item in cart_items]
    if data:
        return data
    raise NoContent()


def remove_from_cart(id_: str) -> bool:
    """
    Remove an item from the user's shopping cart
    """
    CRUD.delete(SC,{'id': id_, 'user_id': g.user['id'], 'is_active': True})
    return True


def add_to_cart(data: Dict) -> bool:
    existing = SC.query.filter_by(
        user_id=g.user["id"],
        state=data["state"],
        pricing_id=data.get("pricing_id"),
        is_active=True
    ).first()
    if existing:
        existing.quantity = data["quantity"]
        if data['quantity'] <= 0:
            db.session.delete(existing)
        CRUD.db_commit()  
    else:
        pd_obj = PD.query.filter_by(id=data['pricing_id']).with_entities(PD.completed, PD.month).first()
        CRUD.create(SC, {"user_id": g.user["id"], 'month': pd_obj.month, 'completed': pd_obj.completed, **data})
    return True


def get_mailing_leads_stock_availability(user_id: str, data: Dict, today_is: datetime, agent_ids: List, thread_response) -> Dict:
        with app.app_context():
            print('get_mailing_leads_stock_availability main context')
            month_info = PRICING_DETAIL_MONTH.get(data['month'])
            less_than = today_is - timedelta(days=month_info['start_day'])
            greater_than = today_is - timedelta(days=month_info['end_day'])
            print('greater')
            lead_query = (
                ML.query
                .join(MR, ML.mortgage_id == MR.mortgage_id)
                .join(MA, ML.mortgage_id == MA.mortgage_id)
                .filter(
                    MR.call_in_date_time >= greater_than,
                    MR.call_in_date_time < less_than,
                    ML.state == data['state'], 
                    MR.completed== data['completed'],
                    ~ML.lead_assigned_members.any(MA.agent_id.in_(agent_ids)), 
                    or_(
                        ML.last_purchased_date == None,
                        ML.last_purchased_date < (today_is - timedelta(days=30)).date()
                    ),
                    ML.disabled_in_marketplace == False, 
                    ML.can_sale == True,
                    ML.source_id == data['source'],
                    or_(ML.item_reserved_temp_by == user_id, ML.is_in_checkout == False)
                    )
                )
            try:
                with db.session.begin():
                    thread_response.put({data['id']: {'stock': lead_query.distinct(ML.mortgage_id).count()}})
            except Exception as e:
                print(f"exceeded the limited quantity: {e}")
                thread_response.put({data['id']: {'stock': 0}})
                db.session.close()
        return True


def verify_stock_in_cart(cart_items: List) -> Dict:
    result,thread_response = {}, queue.Queue()
    thread_count = 0
    print(cart_items)
    with ThreadPoolExecutor(max_workers=5) as executor: 
        for sc in cart_items:
            print(sc)
            if sc.get('category_id') == 1:
                executor.submit(
                    get_mailing_leads_stock_availability, 
                    g.user['id'], sc, 
                    datetime.utcnow(),
                    g.user['mailing_agent_ids'], 
                    thread_response
                )
                thread_count += 1
    print(f"Thread count {thread_count}")
    for _ in range(thread_count):
        try:
            res = thread_response.get(timeout=10)
            result.update(res)
        except queue.Empty:
            print('empty queue')
    if len(result) == thread_count:
        return result
    print(f"failed {thread_count} {result}")
    raise InternalError()


def reserving_mailing_for_checkout(
    today_is: datetime, user_id: str, 
    agent_ids: List, cart_item: Dict, 
    thread_response: queue) -> bool:
    try:
        print(f"reserving_mailing_for_checkout")
        with app.app_context():
            unique_id = str(uuid4())
            month_info = PRICING_DETAIL_MONTH.get(cart_item['month'])
            less_than = today_is - timedelta(days=month_info['start_day'])
            greater_than = today_is - timedelta(days=month_info['end_day'])
            leads_obj = (
                ML.query
                .join(MR, ML.mortgage_id == MR.mortgage_id)
                .filter(
                    MR.call_in_date_time >= greater_than,
                    MR.call_in_date_time < less_than,
                    ~ML.lead_assigned_members.any(MA.agent_id.in_(agent_ids)),
                    or_(
                        ML.last_purchased_date == None,
                        ML.last_purchased_date < (today_is - timedelta(days=30)).date()
                        ),
                    ML.state == cart_item['state'],
                    MR.completed== cart_item['completed'],
                    ML.disabled_in_marketplace == False,
                    ML.can_sale == True,
                    ML.source_id == cart_item['source'],
                    or_(
                        ML.item_reserved_temp_by == user_id, 
                        ML.is_in_checkout == False
                        )
                    )
                    .with_entities(ML.mortgage_id)
                    .limit(cart_item['quantity'])
            )
            # print(f"Leads count--> {leads_obj.count()}")
            valid_ids = [ld.mortgage_id for ld in leads_obj]
            print(f" reserving_mailing_for_checkout valid_ids {valid_ids}")
            if len(valid_ids) == cart_item['quantity']:
                ML.query.filter(ML.mortgage_id.in_(valid_ids)).update(dict(is_in_checkout = True, shopping_cart_temp_id = unique_id, item_reserved_temp_by = user_id, modified_at = ML.modified_at))
                add_redis_ttl_data(key=f"reserve_cart_{cart_item['pricing_id']}_{unique_id}", hours=0.28, data=str(cart_item['id']))
                CRUD.db_commit()
                thread_response.put((str(cart_item['id']), unique_id))
                print(f'Successfully reserved leads for cart {cart_item["id"]}')
            else:
                print(f'*****failed to reserve enough leads for {cart_item}')
                thread_response.put(False)
    except Exception as e:
        print(f"Exception in reserving_mailing_for_checkout: {e}")
        thread_response.put(False)
    return True


def reserve_the_leads(cart_ids: List[str]) -> List[Dict]:
    print(f"reserve_the_leads cart_ids {cart_ids}")
    result, thread_response = {}, queue.Queue()
    carts_obj = (
        SC.query.join(PD, PD.id == SC.pricing_id)
        .filter(
            SC.user_id == g.user['id'], 
            SC.id.in_(cart_ids)
            )
        .with_entities(
            SC.id, SC.state, PD.month, SC.quantity, 
            PD.completed, PD.source, PD.category,
            SC.pricing_id
            )
        )
    print(f"carts_obj -{carts_obj}")
    thread_count = 0
    with ThreadPoolExecutor(max_workers=5) as executor:
        for cart in carts_obj.all():
            if cart.category == 1 and cart.month != 0:
                result[str(cart.id)] = {'pricing_id': str(cart.pricing_id)}
                executor.submit(
                    reserving_mailing_for_checkout,
                    datetime.utcnow(),
                    g.user['id'], 
                    g.user['mailing_agent_ids'],
                    cart._asdict(),
                    thread_response
                )
                thread_count += 1
    for _ in range(thread_count):
        try:
            temp_cart_info = thread_response.get(timeout=10)
            if temp_cart_info:
                result[temp_cart_info[0]] |= {'id': temp_cart_info[0], 'shopping_cart_temp_id': temp_cart_info[1]}
        except queue.Empty:
            print("reserce leads Queue get timed out in this iteration.")
            continue
    if len(result) != thread_count:
        db.session.rollback()
        ML.query.filter(ML.is_in_checkout == True, ML.shopping_cart_temp_id.in_(list(result.keys())), ML.item_reserved_temp_by == g.user['id']).delete()
        CRUD.db_commit()
        # tasks.clear_expired_reserved_leads.apply_async(args=(list(result.keys()), ))
        raise BadRequest("Sorry leads are unable to reserve now please try again")
    tasks.clear_expired_reserved_leads.apply_async(args=(list(result.keys()), ), countdown=1020)
    print(f"result is {result}")
    return list(result.values())


def assigning_reserved_mailing_leads(user: Dict, campaign_name: str, cart_item: Dict, cart_id_with_temp_id: str, order_id: str, today_is: datetime, thread_response: queue) -> bool:
    with app.app_context():
        print("assigning_reserved_mailing_leads")
        print(campaign_name, order_id, cart_item, cart_id_with_temp_id, order_id)
        mortgage_ids, assigned_leads = [], []
        with db.session.begin():
            try:
                query = (
                    ML.query
                    .join(MR, MR.mortgage_id == ML.mortgage_id)
                    .filter(
                        ML.shopping_cart_temp_id == cart_id_with_temp_id
                        )
                    .with_entities(ML.mortgage_id)
                    )
                mailing_normal_agent = (
                    user['agents_source'].get(str(cart_item['source']), {}).get(str(cart_item['category'])) or user['mailing_agent_ids'][0]
                    )
                print('quey all')
                for ld in query.all():
                    print(f"ldd -? {ld}")
                    assigned_leads.append(
                        MA(
                            mortgage_id=ld.mortgage_id,
                            agent_id=mailing_normal_agent,
                            purchased_date=today_is,
                            cart_item_id=cart_item['id'],
                            lead_status=1,
                            purchased_user_id=user['id'],
                            campaign_name=campaign_name
                            )
                        )
                    mortgage_ids.append(ld.mortgage_id)
                    print(f"mortgae is {mortgage_ids}")
                ML.query.filter(ML.mortgage_id.in_(mortgage_ids)).update({'last_purchased_date': today_is, 'is_in_checkout': False, 'shopping_cart_temp_id': None, 'item_reserved_temp_by':None})
                print(f"MLL****, {order_id}")
                SC.query.filter(SC.id == cart_item['id']).update({'is_active': False, 'order_id': order_id})
                db.session.bulk_save_objects(assigned_leads)
                CRUD.db_commit()
                thread_response.put(True)
            except Exception as e:
                import traceback
                print("######################")
                print (traceback.format_exc())
                print("**************************")
                SendgridEmailSending(
                    to_emails=Config_is.DEVELOPERS_EMAIL_ADDRESS,
                    html_content=f"<body><p>{cart_item}<br>Error: {str(e)}</p></body>",
                    subject=f"MP Lead assign Failed: {user['id']} {user['name']} {campaign_name}"
                ).send_email_without_logs()
                print(f"assigning_reserved_mailing_leads --> Exception {e} {cart_item}")
                thread_response.put('Sorry an error has occurred. We will resolve this in 24 hours')
    return True


def update_quatity_of_item_in_cart(cart_id: str, quantity: int) -> bool:
    update_obj = SC.query.filter_by(
        id=cart_id,
        user_id=g.user["id"],
        is_active=True
        ).first()
    if update_obj:
        update_obj.quantity = quantity
        if update_obj.quantity <= 0:
            db.session.delete(update_obj)
    CRUD.db_commit()
    return True


def checkout_final_verifier(category_id: int, shopping_cart_temp_id: str, quantity: int) -> False:
    if category_id == 1 and ML.query.filter(ML.shopping_cart_temp_id == shopping_cart_temp_id, ML.item_reserved_temp_by == g.user['id']).count() == quantity:
        return True
    print(f'checkout_final_verifier leads are outofstock shopping_cart_temp_id={shopping_cart_temp_id} category_id={category_id} quantity={quantity}')
    raise NoContent('Sorry, Leads are out of stock')
    # if category_id == 2 and DL.query.filter_by(id_for_duplicate_cart_items=id_for_duplicate_cart_items).count() == quantity:
    #     return True
