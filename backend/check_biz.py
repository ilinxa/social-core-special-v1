import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_core.settings.local_docker")
import django
django.setup()

from apps.organization.business.models import BusinessAccount, BusinessProfile

biz = BusinessAccount.objects.get(slug="e2e-test-business")
print(f"Business: {biz.id}")
print(f"  status={biz.status}")
print(f"  is_active={biz.is_active}")
print(f"  open_member_request={biz.open_member_request}")
print(f"  max_members={biz.max_members}")

try:
    p = biz.profile
    print(f"  Profile: is_public={p.is_public}, display_name={p.display_name}")
except Exception as e:
    print(f"  Profile error: {e}")

# Check RBAC
from apps.rbac.models import Membership
memberships = Membership.objects.filter(
    account_type="business", account_id=biz.id
)
for m in memberships:
    print(f"  Member: user={m.user_id}, role={m.role.name if m.role else 'N/A'}, status={m.status}")
