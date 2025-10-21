import time
from datetime import datetime, timezone
from typing import Dict, List

from flask import g
from sqlalchemy import or_, and_, func

from app import db
from config import Config_is
from app.models import (
    CouponCode as CC, PromotionCode as PC, 
    UserPromotionCodeAssignment as UPCA, 
    CouponAssignedProduct as CAP, 
    UserPromotionCodeHistory as UPCH,
    User
)
from app.services.crud import CRUD
from app.services.custom_errors import *
from app.services.stripe_service import StripeService
from app.services.utils import (
    convert_utc_to_timezone, convert_timezone_to_utc
)


class CouponService:
    @staticmethod 
    def creating_coupon(data : Dict) -> bool:
        """

        - duration:"once", "repeating", "forever".
        - percent_off : Percentage discount (e.g., 25 for 25% off).
        - amount_off: Fixed discount amount (e.g., 500 for $5.00).
        - currency: if `amount_off` is used (e.g., "usd").
        - id : Optional. A custom coupon ID.(eg:nRO9bq9Z)
        - max_redemptions : Max number of times this coupon can be redeemed.
        - redeem_by : A Unix timestamp for expiration.
        - name :  A name for internal or customer-facing use.
        - assigned_pricing_ids : List of pricing IDs to assign this coupon to.
        """
        is_used_in_marketplace = data.pop('is_used_in_marketplace')
        redeem_by_date_time_obj = convert_timezone_to_utc(datetime.strptime(data['redeem_by'], "%m-%d-%Y %H:%M:%S")) if data.get('redeem_by') else None
        data['currency'] = 'usd'
        if data.get('duration') == 'forever':
            # {'name': 'StagingOne1', 'duration': 'forever', 'max_redemptions': 2, 'redeem_by': '06-10-2025 23:59:00', 'percent_off': 50}
            if not data.get('percent_off'):
                raise BadRequest("Forever duration is only allowed with percent off coupons")
        elif data.get('duration') == 'once':
            data['redeem_by'] = int(time.mktime(redeem_by_date_time_obj.timetuple()))
            if (
                data.get('percent_off') is None and  data.get('amount_off') is None
                ) or (data.get('percent_off') and data.get('amount_off')
                      ):
                raise BadRequest("Once duration is only allowed with eitehr percent_off or amount_off")
                # {'name': 'StagingOne2', 'duration': 'once', 'max_redemptions': 2, 'redeem_by': '06-10-2025 23:59:00', 'percent_off': 50,}
                # {'name': 'StagingOne3', 'duration': 'once', 'max_redemptions': 2, 'redeem_by': '06-10-2025 23:59:00', 'amount_off': 25}
        assigned_pricing_ids = data.pop("assigned_pricing_ids", [])
        stripe_coupon_id = StripeService().create_coupon(data)
        coupon_obj = CRUD.create(CC, dict(
            stripe_coupon_id=stripe_coupon_id, name=data['name'], 
            duration=data['duration'], percent_off=data.get('percent_off'),
            amount_off = data.get('amount_off'), created_by=g.user['id'],
            max_redemptions=data.get('max_redemptions'), 
            redeem_by=redeem_by_date_time_obj,
            is_used_in_marketplace=is_used_in_marketplace
            ))
        if assigned_pricing_ids:
            bulk_cap_objs = [
                CAP(
                    pricing_id=pricing_id,
                    coupon_code_id=coupon_obj.id
                )
                for pricing_id in assigned_pricing_ids
            ]
            db.session.bulk_save_objects(bulk_cap_objs)
            CRUD.db_commit()
            
        return True

    @staticmethod
    def updating_coupon(stripe_coupon_id: str, name: str) -> bool:
        StripeService().update_coupon(stripe_coupon_id, {'name': name})
        CRUD.update(CC, {'stripe_coupon_id': stripe_coupon_id}, {'name': name})
        return True
    
    @staticmethod
    def deleting_coupon(stripe_coupon_id: str) -> bool:
        StripeService().delete_coupon(stripe_coupon_id)
        CRUD.update(CC, {'stripe_coupon_id': stripe_coupon_id}, {'is_active': False, 'is_deleted': True})
        return True

    @staticmethod
    def admin_listing_coupons(page: int, per_page: int, time_zone: str) -> tuple[list, dict]:
        result = []
        coupons_obj = (
            CC.query
            .with_entities(
                CC.id, CC.amount_off, CC.duration, CC.percent_off, CC.name, 
                CC.max_redemptions, CC.stripe_coupon_id, CC.redeem_by,
                CC.is_active, CC.is_used_in_marketplace
                )
            .filter(CC.is_deleted == False)
            .order_by(CC.modified_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
            )
        for coupon_obj in coupons_obj:
            coupon_data = coupon_obj._asdict()
            for date_field in ['redeem_by']:
                coupon_data[date_field] = convert_utc_to_timezone(coupon_obj.redeem_by, time_zone)
            result.append(coupon_data)
        if result:
            return result, {"total": coupons_obj.total,"current_page": coupons_obj.page,"length": len(result),"per_page": coupons_obj.per_page}
        raise NoContent()

class PromotionService:
    @staticmethod
    def creating_stripe_promotion(data: Dict, time_zone: str) -> bool:
        """
        Create a Stripe promotion and store it in the database.

        - code: Promotion code (e.g., "SUMMER20").
        - coupon_code_id: Reference to CouponCode table.
        - restrictions_minimum_amount: Minimum amount restriction.
        - restrictions_first_time_transaction: Restrict to first-time transactions.
        - expires_at: Promotion expiry as string "%m-%d-%Y %H:%M:%S".
        - max_redemptions: Maximum number of redemptions allowed.
        - active: Whether the promotion code is active.
        - user_id: ID of the user creating the promotion.
        - time_zone: Time zone for the expires_at field.
        - assigned_users: List of user IDs to assign the promotion code to.
        """
        coupon_obj = CC.query.with_entities(CC.id, CC.redeem_by, CC.max_redemptions, CC.is_used_in_marketplace)\
            .filter_by(id=data.get("coupon_code_id"), is_active=True, is_deleted=False).first()
        if not coupon_obj:
            raise BadRequest("Coupon not found.")
        stripe_data = {
            "code": data.get("code"),
            "coupon": data.get("coupon_code"),
            "active": data.get("active", True),
            "max_redemptions": data.get("max_redemptions"),
            "restrictions": {
                "first_time_transaction": data.get("restrictions_first_time_transaction", False),
                "minimum_amount": data.get("restrictions_minimum_amount"),
                "minimum_amount_currency": "usd"
                }
            }
        if data.get("expires_at"):
            data['expires_at'] = convert_timezone_to_utc(
                datetime.strptime(data.get("expires_at"), "%m-%d-%Y %H:%M:%S"),
                time_zone=time_zone
                )
            if coupon_obj.redeem_by and data['expires_at'] > coupon_obj.redeem_by:
                raise BadRequest("Promotion expiry cannot be after coupon expiry.")
            stripe_data["expires_at"] = int(data['expires_at'].timestamp())
        if data.get("max_redemptions") > coupon_obj.max_redemptions:
            raise BadRequest(f"Promotion max redemptions cannot be greater than coupon max redemptions {coupon_obj.max_redemptions}.")
        if coupon_obj.is_used_in_marketplace == False:
            promotion_response = StripeService().create_stripe_promotion(stripe_data)
            promotion_db = CRUD.create(PC, {
                "stripe_promotion_id": promotion_response["id"],
                "code": data["code"],
                "coupon_code_id": data.get("coupon_code_id"),
                "created_by": g.user["id"],
                "expires_at": data.get('expires_at'),
                "max_redemptions": data.get("max_redemptions"),
                "is_public": data.get("is_public"),
                "restrictions_minimum_amount": data.get("restrictions_minimum_amount"),
                "restrictions_first_time_transaction": data.get("restrictions_first_time_transaction")
                })
        else:
            promotion_db = CRUD.create(PC, {
                "code": data["code"],
                "coupon_code_id": data.get("coupon_code_id"),
                "created_by": g.user["id"],
                "expires_at": data.get('expires_at'),
                "max_redemptions": data.get("max_redemptions"),
                "is_public": data.get("is_public"),
                "restrictions_minimum_amount": data.get("restrictions_minimum_amount"),
                "restrictions_first_time_transaction": data.get("restriction_first_time_transaction")
                })

        if not data.get("is_public", False) and data.get("assigned_users", []):
            bulk_insertion_objs = [
                UPCA(
                    promotion_id=promotion_db.id,
                    coupon_code_id=data.get("coupon_code_id"),
                    user_id=user_id
                )
                for user_id in data.get("assigned_users", [])
            ]
            db.session.bulk_save_objects(bulk_insertion_objs)
            CRUD.db_commit()
        return True

    @staticmethod
    def activating_deactivating_promotion(promo_id: str, data: Dict) -> bool:
        """
        Activate or deactivate a promotion code.
        """
        promo = PC.query.join(CC, CC.id == PC.coupon_code_id).filter(PC.id==promo_id, CC.is_deleted == False).first()
        if not promo:
            raise NoContent("Promotion code not found.")
        if promo.stripe_promotion_id:
            StripeService().update_stripe_promotion(promo.stripe_promotion_id, {'active': data['is_active']})
        promo.is_active = data.get("is_active")
        CRUD.db_commit()
        return True

    @staticmethod
    def deleting_promotion(promo_id: str) -> bool:
        promo = PC.query.join(CC, CC.id == PC.coupon_code_id).filter(
            PC.id==promo_id, CC.is_deleted == False).first()
        if not promo:
            raise NoContent("Promotion code not found.")
        if promo.stripe_promotion_id:
            StripeService().delete_stripe_promotion(promo.stripe_promotion_id)
        promo.is_deleted = True
        db.session.commit()
        return True 


    @staticmethod
    def admin_listing_promotions(page: int, per_page: int, time_zone: str, is_active: str = None, code: str = None, coupon_name: str = None) -> Dict:
        result = []
        query_objs = PC.query.join(CC, CC.id == PC.coupon_code_id).with_entities(
            PC.id, PC.code, PC.stripe_promotion_id, PC.expires_at, PC.max_redemptions, 
            PC.is_public, PC.restrictions_first_time_transaction, PC.created_by, 
            PC.restrictions_minimum_amount,PC.modified_at, PC.coupon_code_id, 
            CC.name, PC.is_active, CC.is_used_in_marketplace).filter(
                CC.is_deleted == False, PC.is_deleted == False)
        if code:
            query_objs = query_objs.filter(PC.code.ilike(f"%{code}%"))
        if is_active is not None:
            query_objs = query_objs.filter(PC.is_active == True if is_active == str(1) else False)
        if coupon_name:
            query_objs = query_objs.filter(CC.name == coupon_name)

        promotion_objs = query_objs.order_by(PC.modified_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
        for promo_obj in promotion_objs.items:
            promotion_data = promo_obj._asdict()
            promotion_data['expires_at'] = convert_utc_to_timezone(promo_obj.expires_at, time_zone)
            promotion_data['modified_at'] = convert_utc_to_timezone(promo_obj.modified_at, time_zone)
            result.append(promotion_data)
        if result:
            return result, {
                "total": promotion_objs.total, "current_page": promotion_objs.page, 
                "length": len(result), "per_page": promotion_objs.per_page
                }
        raise NoContent()
   

    # @staticmethod
    # def getting_active_promotion_codes(pricing_id: str, time_zone: str) -> list[dict]:
    #     user_id = g.user['id']
    #     now_utc = datetime.utcnow()
    #     result = []
    #     promotion_objs = (
    #         PC.query
    #         .join(CC, PC.coupon_code_id == CC.id)
    #         .outerjoin(UPCA, UPCA.promotion_id == PC.id)
    #         .join(CAP, CAP.coupon_code_id == PC.coupon_code_id)
    #         .filter(
    #             PC.is_active == True,
    #             PC.expires_at >= now_utc,
    #             CAP.pricing_id == pricing_id,
    #             or_(
    #                 PC.is_public == True,
    #                 UPCA.user_id == user_id
    #             ),
    #             CC.is_active == True,
    #             or_(
    #                 CC.redeem_by == None,
    #                 CC.redeem_by >= now_utc
    #             )
    #         )
    #         .with_entities(
    #             PC.id, PC.code, PC.restrictions_minimum_amount, PC.is_public,
    #             PC.restrictions_first_time_transaction, PC.max_redemptions,
    #             PC.stripe_promotion_id, PC.is_active, PC.expires_at,
    #             CC.name, CC.amount_off, CC.percent_off, CC.duration, CC.redeem_by,
    #             CC.stripe_coupon_id, PC.coupon_code_id
    #         )
    #         .all()
    #     )
    #     used_promos = set(
    #         db.session.query(UserPromotionCodeHistory.promotion_id)
    #         .filter_by(user_id=user_id, pricing_id=pricing_id)
    #         .all()
    #     )
    #     used_promos = {row[0] for row in used_promos}
    #     redemption_counts = dict(
    #         db.session.query(
    #             UserPromotionCodeHistory.promotion_id,
    #             func.count(UserPromotionCodeHistory.id)
    #         )
    #         .group_by(UserPromotionCodeHistory.promotion_id)
    #         .all()
    #     )
    #     for promo in promotion_objs:
    #         already_used = promo.id in used_promos
    #         redemption_count = redemption_counts.get(promo.id, 0)
    #         if promo.duration == 'once':
    #             if already_used:
    #                 continue  
    #         elif promo.duration == 'forever':
    #             if promo.max_redemptions is not None and redemption_count >= promo.max_redemptions:
    #                 continue 
    #             if already_used:
    #                 continue  

    #         elif promo.duration == 'repeating':
    #             if promo.max_redemptions is not None and redemption_count >= promo.max_redemptions:
    #                 continue  
    #             if already_used:
    #                 continue  

    #         promotion_data = promo._asdict()
    #         promotion_data['expires_at'] = convert_utc_to_timezone(promo.expires_at, time_zone)
    #         result.append(promotion_data)
    #     if result:
    #         return result
    #     raise NoContent()


    @staticmethod
    def getting_active_promotion_codes(pricing_id: str, time_zone: str) -> list[dict]:
        promotion_objs = (
            PC.query
            .join(CC, PC.coupon_code_id == CC.id)
            .outerjoin(UPCA, UPCA.promotion_id == PC.id)  # For private promo access
            .join(CAP, CAP.coupon_code_id == PC.coupon_code_id)
            .filter(
                CC.is_used_in_marketplace == False,
                PC.is_active == True,
                CC.is_deleted == False,
                PC.is_deleted == False,
                PC.expires_at > datetime.utcnow(),
                CAP.pricing_id == pricing_id,
                CC.is_active == True,
                or_(CC.redeem_by == None, CC.redeem_by >= datetime.utcnow()),
                or_(
                    PC.is_public == True,
                    and_(PC.is_public == False, UPCA.user_id == g.user['id'])  # Private access check
                )
            )
            .with_entities(
                PC.id, PC.code, PC.restrictions_minimum_amount, PC.is_public,
                PC.restrictions_first_time_transaction, PC.max_redemptions,
                PC.stripe_promotion_id, PC.is_active, PC.expires_at,
                CC.name, CC.amount_off, CC.percent_off, CC.duration, CC.redeem_by,
                CC.stripe_coupon_id, PC.coupon_code_id
            )
            .all()
        )

        used_promos = {
            row.promotion_id for row in UPCH.query
            .with_entities(UPCH.promotion_id)
            .filter(
                UPCH.user_id == g.user['id'],
                UPCH.pricing_id == pricing_id
            )
            .all()
        }

        redemption_counts = dict(
            db.session.query(
                UPCH.promotion_id,
                func.count(UPCH.id)
            )
            .group_by(UPCH.promotion_id)
            .all()
        )

        result = []
        for promo in promotion_objs:
            already_used = promo.id in used_promos
            redemption_count = redemption_counts.get(promo.id, 0)
            if promo.duration == 'once' and already_used:
                continue
            if promo.duration in {'forever', 'repeating'}:
                if promo.max_redemptions is not None and redemption_count >= promo.max_redemptions:
                    continue
                if already_used:
                    continue
            promo_dict = promo._asdict()
            promo_dict['expires_at'] = convert_utc_to_timezone(promo.expires_at, time_zone)
            result.append(promo_dict)

        if result:
            return result

        raise NoContent()


    @staticmethod
    def validate_promo_code(promo_db_id: str) -> bool:
        promo = (
            PC.query
            .join(CC, PC.coupon_code_id == CC.id)
            .join(CAP, CAP.coupon_code_id == PC.coupon_code_id)
            .filter(
                CC.is_deleted == False,
                PC.is_deleted == False,
                PC.is_active == True,
                PC.id == promo_db_id,
                PC.is_active == True,
                PC.expires_at >= datetime.utcnow(),
                or_(CC.redeem_by == None, CC.redeem_by >= datetime.utcnow()),
                or_(
                    PC.is_public == True,
                    and_(PC.is_public == False,
                         PC.id.in_(db.session.query(UPCH.promotion_id).filter_by(user_id=g.user['id'])))
                )
            )
            .with_entities(
                PC.id.label("promotion_id"),
                PC.code,
                PC.max_redemptions.label("promo_max"),
                PC.is_public,
                CC.duration,
                CC.max_redemptions.label("coupon_max"),
                CC.id.label("coupon_id")
            )
            .first()
        )

        if not promo:
            raise BadRequest("Promotion code is either invalid, expired, or no longer usable.")

        total_redemptions = db.session.query(func.count(UPCH.id)).filter(
            UPCH.promotion_id == promo.promotion_id
        ).scalar()

        if promo.promo_max is not None:
            if total_redemptions >= promo.promo_max:
                raise BadRequest("This promotion code has reached its redemption limit.")
        elif total_redemptions >= promo.coupon_max:
            raise BadRequest("This promotion code has reached its redemption limit.")
        already_used = db.session.query(UPCH.id).filter(
            UPCH.user_id == g.user['id'],
            UPCH.promotion_id == promo.promotion_id
        ).count()

        if promo.duration == 'once' and already_used:
            raise BadRequest("You have already used this promotion code.")

        if promo.duration in ('forever', 'repeating'):
            if promo.coupon_max is not None and total_redemptions >= promo.coupon_max:
                raise BadRequest("This promotion code is no longer available.")
            if already_used:
                raise BadRequest("You have already used this promotion code.")
        return True
    

def list_promotion_assigned_members(
        page: int, per_page: int, promotion_id: str, time_zone: str) -> tuple:
    users_obj = User.query.join(UPCA, User.id == UPCA.user_id).filter(
        UPCA.promotion_id == promotion_id).with_entities(
            User.id, User.name, UPCA.created_at
            ).order_by(
                UPCA.created_at.desc()
                ).paginate(page=page, per_page=per_page, error_out=False)
    result = []
    for u in users_obj.items:
        u = u._asdict()
        u['created_at'] = convert_utc_to_timezone(u['created_at'], time_zone)
        result.append(u)
        if result:
            return result, {
                "total": users_obj.total,
                "current_page": users_obj.page,
                "per_page": users_obj.per_page,
                "length": len(result)
                }
    raise NoContent()


def list_users_for_promo_assign(
        page: int, per_page: int, promotion_id: str, 
        name_search: str = None) -> tuple:
    if promotion_id:
        users_obj = User.query.outerjoin(UPCA, and_(
            User.id == UPCA.user_id,
            UPCA.promotion_id == promotion_id)
        ).filter(UPCA.id.is_(None))
    else:
        users_obj = User.query
    users_obj = users_obj.with_entities(User.id, User.name).filter(
            User.is_active == True, User.registered == True)
    if name_search:
        users_obj = users_obj.filter(User.name.ilike(f'%{name_search}%'))
    users_obj = users_obj.paginate(page=page, per_page=per_page, error_out=False)
    result = [u._asdict() for u in users_obj.items]
    if result:
        return result, {
            "total": users_obj.total,
            "current_page": users_obj.page,
            "per_page": users_obj.per_page,
            "length": len(result)
            }
    raise NoContent()


# def assign_members_to_promotion(usersbulk_insertion_objs = [
#                 UPCA(
#                     promotion_id=promotion_db.id,
#                     coupon_code_id=data.get("coupon_code_id"),
#                     user_id=user_id
#                 )
#                 for user_id in data.get("assigned_users", [])
#             ]
#             db.session.bulk_save_objects(bulk_insertion_objs)
#             CRUD.db_commit())
