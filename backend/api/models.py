"""
Data models for API tester — Collections, Environments, History.

Uses JSON blob approach: the entire collection tree (folders + requests)
is stored as a single JSONField. This avoids complex tree table joins
and matches the frontend's existing data model.

All models are user-scoped via `owner` FK — each user only sees their own data.
"""
from django.contrib.auth.models import User
from django.db import models


class Collection(models.Model):
    """A request collection — stores the full tree as JSON.

    The `data` field contains: { id, name, description, folders: [...], requests: [...], preRequestScript }
    matching the frontend's Collection type.
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [models.Index(fields=['owner', 'updated_at'])]

    def __str__(self):
        return f'{self.name} ({self.owner.username})'


class Environment(models.Model):
    """An environment with variables — stored as JSON KV array."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='environments')
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=False)
    # Variables stored as: [{"id":"...","key":"...","value":"...","enabled":true}, ...]
    variables = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['owner', 'name']
        indexes = [models.Index(fields=['owner'])]
        constraints = [
            # At most one active environment per owner (partial unique index).
            # Backs the application-level guarantee in save()/activate() with a
            # real DB constraint so a concurrent race cannot leave two active.
            models.UniqueConstraint(
                fields=['owner'],
                condition=models.Q(is_active=True),
                name='uniq_active_env_per_owner',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.owner.username})'

    def save(self, *args, **kwargs):
        """Ensure only one active environment per user."""
        if self.is_active:
            Environment.objects.filter(owner=self.owner).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class HistoryEntry(models.Model):
    """A request execution history entry."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='history_entries')
    # RequestConfig as JSON: {method, url, headers, queryParams, body, ...}
    request = models.JSONField(default=dict)
    # ResponseData as JSON (nullable for failed requests)
    response = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['owner', '-timestamp'])]

    def __str__(self):
        method = self.request.get('method', '?') if isinstance(self.request, dict) else '?'
        url = self.request.get('url', '') if isinstance(self.request, dict) else ''
        return f'{method} {url[:50]} ({self.timestamp})'
