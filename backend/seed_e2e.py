"""Seed E2E test users and business for manual UI testing."""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_core.settings.local_docker")

import django
django.setup()

from apps.users.models import User, UserProfile

def create_user(email, username, password, first_name, last_name, is_public=True):
    if User.objects.filter(email=email).exists():
        u = User.objects.get(email=email)
        print(f"  EXISTS: {email} ({u.id})")
        return u
    u = User.objects.create_user(
        email=email, username=username, password=password,
        first_name=first_name, last_name=last_name,
    )
    u.is_email_verified = True
    u.save(update_fields=["is_email_verified"])
    UserProfile.objects.get_or_create(user=u, defaults={"is_public": is_public})
    print(f"  CREATED: {email} ({u.id})")
    return u

print("=== Seeding E2E Test Data ===")

print("\n1. Users:")
user_a = create_user("e2e_user_a@test.com", "e2e_user_a", "TestPass123!", "Alice", "Tester", True)
user_b = create_user("e2e_user_b@test.com", "e2e_user_b", "TestPass123!", "Bob", "Tester", True)
user_c = create_user("e2e_user_c@test.com", "e2e_user_c", "TestPass123!", "Carol", "Private", False)

print("\n2. Business:")
from apps.organization.business.models import BusinessAccount, BusinessProfile
slug = "e2e-test-business"
if BusinessAccount.objects.filter(slug=slug).exists():
    biz = BusinessAccount.objects.get(slug=slug)
    print(f"  EXISTS: {slug} ({biz.id})")
else:
    biz = BusinessAccount.objects.create(
        legal_name="E2E Test Business",
        slug=slug,
        country="US",
        created_by=user_b,
    )
    BusinessProfile.objects.get_or_create(
        business=biz,
        defaults={
            "display_name": "E2E Test Business",
            "tagline": "A test business for E2E testing",
            "is_public": True,
        },
    )
    biz.open_member_request = True
    biz.max_members = 10
    biz.save(update_fields=["open_member_request", "max_members"])
    print(f"  CREATED: {slug} ({biz.id})")

    # Initialize RBAC for business
    from apps.rbac.services import RBACService
    RBACService.initialize_business_account(business_id=biz.id, owner=user_b)
    print(f"  RBAC initialized. User B is owner.")

print("\n3. Platform:")
from apps.organization.platform.models import PlatformAccount
if PlatformAccount.objects.exists():
    plat = PlatformAccount.objects.first()
    print(f"  EXISTS: platform ({plat.id})")
else:
    print("  NO PLATFORM (create via admin)")

print("\n=== Done ===")
