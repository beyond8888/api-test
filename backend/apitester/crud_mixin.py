"""
Unified CRUD mixin for DRF ViewSets.

Wraps standard ModelViewSet responses with the project's success() response
envelope so every ViewSet doesn't need to repeat the same boilerplate.
"""
from apitester.api_response import success


class UnifiedCRUDMixin:
    """Mixin that wraps list/create/retrieve/update/destroy with success()."""
    model_label: str = 'Resource'

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        return success(resp.data, message=f'{self.model_label} created', status=201)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return success(resp.data)

    def retrieve(self, request, *args, **kwargs):
        resp = super().retrieve(request, *args, **kwargs)
        return success(resp.data)

    def update(self, request, *args, **kwargs):
        resp = super().update(request, *args, **kwargs)
        return success(resp.data, message=f'{self.model_label} updated')

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return success(None, message=f'{self.model_label} deleted')


class OwnerScopedMixin:
    """Scope every queryset to the current user and stamp ``owner`` on create.

    Eliminates the repeated ``get_queryset``/``perform_create`` boilerplate
    that every multi-tenant ViewSet would otherwise duplicate.
    """
    owner_field: str = 'owner'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(**{self.owner_field: self.request.user})

    def perform_create(self, serializer):
        serializer.save(**{self.owner_field: self.request.user})
