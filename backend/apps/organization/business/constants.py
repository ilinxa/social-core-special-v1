# apps/organization/business/constants.py
"""
Business-specific constants.
"""

# Slugs reserved for frontend routing (cconsole static segments + console segments).
# These cannot be used as business account slugs because they would collide with
# Next.js static routes under /cconsole/.
RESERVED_BUSINESS_SLUGS = frozenset(
    {
        # cconsole static route segments
        "sites",
        "templates",
        "media",
        "api-keys",
        "businesses",
        # Common console segments used across bconsole/pconsole/gconsole
        "dashboard",
        "settings",
        "profile",
        "members",
        "audit",
        "catalog",
        "library",
        "chat",
        "transactions",
        # Console prefixes (prevent confusion)
        "bconsole",
        "pconsole",
        "gconsole",
        "cconsole",
        "admin",
    }
)
