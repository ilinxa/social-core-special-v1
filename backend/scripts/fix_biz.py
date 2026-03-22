import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_core.settings.local_docker")
import django

django.setup()

from apps.organization.business.models import BusinessAccount, BusinessProfile

biz = BusinessAccount.objects.get(slug="e2e-test-business")
print(f"Before: status={biz.status}")

# Activate the business
biz.status = "active"
biz.open_member_request = True
biz.max_members = 10
biz.save(update_fields=["status", "open_member_request", "max_members"])
print(
    f"After: status={biz.status}, open_member_request={biz.open_member_request}, max_members={biz.max_members}"
)

# Ensure profile exists and is public
p, created = BusinessProfile.objects.get_or_create(
    business=biz,
    defaults={
        "display_name": "E2E Test Business",
        "tagline": "A test business for E2E testing",
        "is_public": True,
    },
)
if not created:
    p.is_public = True
    p.display_name = p.display_name or "E2E Test Business"
    p.save(update_fields=["is_public", "display_name"])
print(f"Profile: is_public={p.is_public}, display_name={p.display_name}")

# Check memberships
from apps.rbac.models import Membership

for m in Membership.objects.filter(account_type="business", account_id=biz.id):
    print(
        f"Member: user={m.user_id}, role={m.role.name if m.role else 'N/A'}, status={m.status}"
    )
