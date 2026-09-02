"""
Serializers for Mock endpoints.
"""
from rest_framework import serializers

from .models import MockEndpoint


class MockEndpointSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    mock_url = serializers.SerializerMethodField()
    delay_ms = serializers.IntegerField(
        min_value=0, max_value=60_000, required=False
    )

    class Meta:
        model = MockEndpoint
        fields = [
            'id', 'owner', 'owner_name', 'name', 'path', 'method',
            'python_script', 'description', 'enabled', 'delay_ms',
            'mock_url', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'owner', 'owner_name', 'mock_url', 'created_at', 'updated_at']

    def get_mock_url(self, obj) -> str:
        try:
            request = self.context.get('request')
            if request:
                host = request.get_host()
                scheme = 'https' if request.is_secure() else 'http'
                return f'{scheme}://{host}/mock/{obj.path.strip("/")}'
        except Exception:
            pass
        return f'/mock/{obj.path.strip("/")}'
