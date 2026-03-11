# Users App

## Domain Rules
- IMPORTANT: This is the custom AUTH_USER_MODEL. Never reference django.contrib.auth.models.User.
- Avatar uploads go through the profile update flow — do not create a standalone upload endpoint.
- User model owns the profile data directly (no separate Profile model).