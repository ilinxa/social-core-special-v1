# Views

Read this when creating API views — HTTP orchestration, permission declaration, view flow, OpenAPI documentation, AuditContext usage, and the me/ endpoint pattern.

## Quick Reference — Project Imports

```python
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.core.permissions import IsAuthenticated, IsOwner, AllowAny
from apps.core.pagination import StandardPagination, CursorResultsPagination
from apps.core.serializers import EmptySerializer
```

---

## 1. Role of Views

Views are the **outermost layer**. They translate HTTP requests into domain operations.

Views SHOULD: parse HTTP input, validate with serializers, delegate reads to selectors, delegate writes to services, serialize responses, declare permissions and API docs.

Views SHOULD NOT: contain business logic, mutate models directly, perform database queries, contain validation rules.

> **Views orchestrate — they never decide.**

---

## 2. View Flow (MANDATORY ORDER)

1. Authentication & permissions
2. Fetch resource (selector) if needed
3. Check object permissions if needed
4. Parse request data
5. Validate input (serializer)
6. Call selector or service (pass `request` for audit context)
7. Serialize output
8. Return HTTP response

---

## 3. Full Example

```python
class ProductListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    serializer_class = ProductListSerializer

    def get_queryset(self):
        return ProductSelector.list_by_owner(owner_id=self.request.user.id)

class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    @extend_schema(summary="Get product", responses={200: ProductOutputSerializer}, tags=["Products"])
    def get(self, request, product_id: int):
        product = ProductSelector.get_by_id(product_id=product_id)
        self.check_object_permissions(request, product)
        return Response(ProductOutputSerializer(product, context={'request': request}).data)

    @extend_schema(summary="Update product", request=ProductUpdateInputSerializer, responses={200: ProductOutputSerializer}, tags=["Products"])
    def patch(self, request, product_id: int):
        product = ProductSelector.get_by_id(product_id=product_id)
        self.check_object_permissions(request, product)

        input_serializer = ProductUpdateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        product = ProductService.update_product(
            product=product, updated_by=request.user, request=request,
            **input_serializer.validated_data
        )

        return Response(ProductOutputSerializer(product, context={'request': request}).data)

    @extend_schema(summary="Delete product", responses={204: EmptySerializer}, tags=["Products"])
    def delete(self, request, product_id: int):
        product = ProductSelector.get_by_id(product_id=product_id)
        self.check_object_permissions(request, product)
        ProductService.soft_delete_product(product=product, deleted_by=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

class ProductCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Create product", request=ProductCreateInputSerializer, responses={201: ProductOutputSerializer}, tags=["Products"])
    def post(self, request):
        input_serializer = ProductCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        product = ProductService.create_product(owner=request.user, request=request, **input_serializer.validated_data)
        return Response(ProductOutputSerializer(product, context={'request': request}).data, status=status.HTTP_201_CREATED)
```

---

## 4. OpenAPI Documentation (MANDATORY)

Every public endpoint MUST have `@extend_schema()` with:
- `summary`
- `request=` (for POST/PATCH/PUT)
- `responses=`
- `tags=`

---

## 5. Permissions & Pagination

- **Declare `permission_classes` explicitly** on every view — use `apps.core.permissions`
- **Declare `pagination_class`** on list views — use `apps.core.pagination`
- Always pass `context={'request': request}` to output serializers

---

## 6. HTTP Status Codes

| Action | Status |
|--------|--------|
| GET | 200 OK |
| PATCH | 200 OK |
| POST (create) | 201 Created |
| DELETE (no body) | 204 No Content |

---

## 7. AuditContext Pattern

Instead of passing `HttpRequest` deep into services, create a lightweight DTO at the view layer:

```python
from apps.core.audit import AuditContext

audit = AuditContext.from_request(request)
ProductService.create_product(owner=request.user, audit=audit, **data)
```

See [services.md](services.md) §4 for full AuditContext implementation.

---

## 8. "me" Endpoints

Prefer "me" patterns for user-owned resources:

```
GET    /users/me/
PATCH  /users/me/
GET    /users/me/profile/
```

Benefits: no user_id in URL, simplifies authorization, prevents privilege escalation.

---

## 9. Parsers & File Uploads

Declare `parser_classes` explicitly for multipart endpoints:
```python
parser_classes = [MultiPartParser, FormParser]
```
Views MUST NOT validate file size/type manually — use serializers.

---

## 10. Error Handling

Do NOT catch domain exceptions in views. Let the global exception handler map them to HTTP.

---

## 11. Anti-Patterns

❌ `from rest_framework.permissions import IsAuthenticated` — Use `apps.core.permissions`
❌ Business logic in views
❌ ORM queries in views
❌ Transactions in views
❌ Validation rules in views
❌ `product.delete()` — Use service with `soft_delete()`
❌ `request` objects passed deep into domain layer (use AuditContext)
