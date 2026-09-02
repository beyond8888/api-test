"""
Mock endpoint models.

Each MockEndpoint defines a custom mock API:
  - path + method identifies the mock
  - python_script is executed in a sandbox to generate the response dynamically
"""
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class MockEndpoint(models.Model):
    """A user-defined mock API endpoint with Python-driven response generation."""

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mock_endpoints')
    name = models.CharField(max_length=200, help_text='Human-readable name for this mock')
    path = models.CharField(
        max_length=500,
        help_text='Mock path, e.g. api/users/&lt;user_id&gt;. Supports &lt;param&gt; placeholders.',
    )
    method = models.CharField(
        max_length=10,
        default='GET',
        choices=[
            ('GET', 'GET'),
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('DELETE', 'DELETE'),
            ('PATCH', 'PATCH'),
            ('HEAD', 'HEAD'),
            ('OPTIONS', 'OPTIONS'),
        ],
    )
    python_script = models.TextField(
        blank=True,
        default='',
        help_text='Python script — must define a handle(request) function that returns a dict '
        'with keys: status_code, headers, body.',
    )
    description = models.TextField(blank=True, default='', help_text='Optional description')
    enabled = models.BooleanField(default=True)
    delay_ms = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(60_000)],
        help_text='Simulated latency in milliseconds (max 60s)',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['owner', '-updated_at']),
            models.Index(fields=['owner', 'enabled']),
        ]
        # Path+method is globally unique (NOT per-owner) so that a single
        # enabled endpoint owns any given path. This prevents a public caller
        # from hijacking another tenant's mock path via the AllowAny serve view.
        unique_together = [['path', 'method']]

    def __str__(self):
        return f'[{self.method}] {self.path} ({self.name})'
