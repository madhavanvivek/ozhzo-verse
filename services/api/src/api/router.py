from fastapi import APIRouter
from src.api.v1.health import router as health_router
from src.api.v1.auth import router as auth_router
from src.api.v1.admin_auth import router as admin_auth_router, admin_alias_router
from src.api.v1.users import router as users_router
from src.api.v1.homes import router as homes_router
from src.api.v1.members import router as members_router
from src.api.v1.inventory import router as inventory_router
from src.api.v1.locations import router as locations_router, types_router as location_types_router
from src.api.v1.templates import router as templates_router
from src.api.v1.units import router as units_router
from src.api.v1.purchase_list import router as purchase_list_router
from src.api.v1.shopping import router as shopping_router
from src.api.v1.tasks import router as tasks_router
from src.api.v1.task_templates import router as task_templates_router
from src.api.v1.bills import router as bills_router
from src.api.v1.bill_templates import router as bill_templates_router
from src.api.v1.calendar import router as calendar_router
from src.api.v1.notifications import router as notifications_router
from src.api.v1.payments import router as payments_router
from src.api.v1.subscriptions import router as subscriptions_router, coupons_router
from src.api.v1.admin_subscriptions import router as admin_subscriptions_router
from src.api.v1.admin_coupons import router as admin_coupons_router
from src.api.v1.admin_users import router as admin_users_router
from src.api.v1.admin_homes import router as admin_homes_router
from src.api.v1.admin_system import router as admin_system_router, dashboard_router as admin_dashboard_router
from src.api.v1.admin_activity import router as admin_activity_router
from src.api.v1.admin_security import router as admin_security_router
from src.api.v1.admin_regions import router as admin_regions_router
from src.api.v1.admin_feature_flags import router as admin_feature_flags_router
from src.api.v1.admin_invitations import router as admin_invitations_router
from src.api.v1.admin_ai_automations import router as admin_ai_automations_router
from src.api.v1.search import router as search_router
from src.api.v1.dashboard import router as dashboard_router
from src.api.v1.today import router as today_router
from src.api.v1.attention import router as attention_router
from src.api.v1.activity import router as activity_router
from src.api.v1.feedback import router as feedback_router
from src.api.v1.ai import router as ai_router
from src.api.v1.automations import router as automations_router
from src.api.v1.intelligence_memory import router as intelligence_memory_router
from src.api.v1.privacy import router as privacy_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(admin_auth_router)
api_v1_router.include_router(admin_alias_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(homes_router)
api_v1_router.include_router(members_router)
api_v1_router.include_router(templates_router)
api_v1_router.include_router(units_router)
api_v1_router.include_router(inventory_router)
api_v1_router.include_router(locations_router)
api_v1_router.include_router(location_types_router)
api_v1_router.include_router(purchase_list_router)
api_v1_router.include_router(shopping_router)
api_v1_router.include_router(tasks_router)
api_v1_router.include_router(task_templates_router)
api_v1_router.include_router(bills_router)
api_v1_router.include_router(bill_templates_router)
api_v1_router.include_router(calendar_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(payments_router, prefix="/payments", tags=["Payments"])
api_v1_router.include_router(subscriptions_router)
api_v1_router.include_router(coupons_router)
api_v1_router.include_router(admin_subscriptions_router)
api_v1_router.include_router(admin_coupons_router)
api_v1_router.include_router(admin_users_router)
api_v1_router.include_router(admin_homes_router)
api_v1_router.include_router(admin_system_router)
api_v1_router.include_router(admin_dashboard_router)
api_v1_router.include_router(admin_activity_router)
api_v1_router.include_router(admin_security_router)
api_v1_router.include_router(admin_regions_router)
api_v1_router.include_router(admin_feature_flags_router)
api_v1_router.include_router(admin_invitations_router)
api_v1_router.include_router(admin_ai_automations_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(today_router)
api_v1_router.include_router(attention_router)
api_v1_router.include_router(activity_router)
api_v1_router.include_router(feedback_router)
api_v1_router.include_router(ai_router)
api_v1_router.include_router(automations_router)
api_v1_router.include_router(intelligence_memory_router)
api_v1_router.include_router(privacy_router)




