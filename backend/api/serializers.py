import json
import re

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Collection, Environment, HistoryEntry
from .ssrf import UnsafeUrlError, assert_safe_target

ALLOWED_METHODS = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'}


class CurlParseRequestSerializer(serializers.Serializer):
    curl_command = serializers.CharField(
        max_length=65536,
        help_text="Raw curl command string to parse"
    )


class ProxyRequestSerializer(serializers.Serializer):
    url = serializers.CharField(max_length=8192, allow_blank=False)
    method = serializers.CharField(max_length=10, default='GET')
    headers = serializers.DictField(child=serializers.CharField(), default=dict)
    query_params = serializers.DictField(child=serializers.CharField(), default=dict)
    body = serializers.CharField(max_length=10_485_760, default='', allow_blank=True)
    body_type = serializers.CharField(default='', allow_blank=True)
    form_fields = serializers.DictField(child=serializers.CharField(), default=dict)
    files = serializers.ListField(default=list)
    timeout = serializers.IntegerField(default=30, min_value=1, max_value=60)

    def validate_url(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError('URL is required')
        try:
            safe_url, _, _ = assert_safe_target(value)
            return safe_url
        except UnsafeUrlError as e:
            raise serializers.ValidationError(f'URL blocked by proxy policy: {e.messages[0] if e.messages else e}') from e

    def validate_method(self, value: str) -> str:
        upper = value.upper()
        if upper not in ALLOWED_METHODS:
            raise serializers.ValidationError(
                f'Unsupported method "{value}". Allowed: {", ".join(sorted(ALLOWED_METHODS))}'
            )
        return upper


class KafkaSendSerializer(serializers.Serializer):
    broker = serializers.CharField(max_length=8192, help_text="Kafka bootstrap servers, e.g. localhost:9092")
    topic = serializers.CharField(max_length=8192, help_text="Target topic name")
    key = serializers.CharField(max_length=8192, required=False, default='', allow_blank=True)
    value = serializers.CharField(help_text="Message body (any text)")
    headers = serializers.DictField(child=serializers.CharField(), default=dict)
    timeout = serializers.IntegerField(default=10, min_value=1, max_value=60)

    def validate_broker(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Broker address is required')
        return value

    def validate_topic(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Topic is required')
        return value


class RocketMQSendSerializer(serializers.Serializer):
    """Send a message to an Alibaba Cloud RocketMQ 5.x instance over gRPC."""
    endpoint = serializers.CharField(
        max_length=8192,
        help_text="gRPC access point, e.g. rmq-cn-xxxx.rmq.aliyuncs.com:8080",
    )
    instance_id = serializers.CharField(
        max_length=256,
        help_text="Instance id (used as resource namespace for 5.x)",
    )
    access_key = serializers.CharField(max_length=256, help_text="Alibaba Cloud AccessKeyId")
    secret_key = serializers.CharField(max_length=256, write_only=True, help_text="Alibaba Cloud AccessKeySecret")
    topic = serializers.CharField(max_length=8192, help_text="Target topic name")
    message_group = serializers.CharField(
        max_length=1024, required=False, default='', allow_blank=True,
        help_text="Message group for FIFO (ordered) messages",
    )
    message_type = serializers.ChoiceField(
        choices=['NORMAL', 'FIFO', 'DELAY', 'TRANSACTION'],
        default='NORMAL',
        help_text="RocketMQ 5.x message type",
    )
    delay_time = serializers.IntegerField(
        required=False, default=0, min_value=0, max_value=3600 * 24 * 7,
        help_text="Delay in seconds (only for DELAY messages, max 7 days)",
    )
    tag = serializers.CharField(max_length=1024, required=False, default='', allow_blank=True)
    keys = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
        help_text="Message keys (business identifiers)",
    )
    body = serializers.CharField(help_text="Message body (any text)")

    def validate_endpoint(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Endpoint is required')
        if ':' not in value:
            value = f'{value}:8080'
        return value

    def validate_topic(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Topic is required')
        return value


# ─── Auth Serializers ────────────────────────────────────────────

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=64, min_length=3)
    password = serializers.CharField(max_length=128, min_length=8, write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists')
        return value

    def validate_password(self, value):
        """Enforce a reasonable password complexity policy."""
        if len(value) < 8:
            raise serializers.ValidationError('Password must be at least 8 characters long')
        if not re.search(r'[A-Za-z]', value):
            raise serializers.ValidationError('Password must contain at least one letter')
        if not re.search(r'\d', value):
            raise serializers.ValidationError('Password must contain at least one digit')
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
        )


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)


# ─── Collection Serializers ───────────────────────────────────────

# Cap the stored collection tree to keep the JSON blob bounded (anti-bloat).
MAX_COLLECTION_BYTES = 5_000_000  # 5 MB


class CollectionSerializer(serializers.ModelSerializer):
    """Full serializer including data — used for list/retrieve/update."""

    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'data', 'created_at', 'updated_at']

    def validate_data(self, value):
        """Guard the JSON blob: must be an object, bounded size, known shape.

        The collection tree is stored as a single JSONField (a deliberate
        trade-off vs. normalized sub-resources). This validation prevents
        malformed or pathologically large payloads from bloating the row.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError('data must be a JSON object')
        raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
        if len(raw) > MAX_COLLECTION_BYTES:
            raise serializers.ValidationError(
                f'collection tree exceeds {MAX_COLLECTION_BYTES} bytes'
            )
        if 'folders' in value and not isinstance(value['folders'], list):
            raise serializers.ValidationError('folders must be an array')
        if 'requests' in value and not isinstance(value['requests'], list):
            raise serializers.ValidationError('requests must be an array')
        return value


# ─── Environment Serializers ──────────────────────────────────────

class EnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Environment
        fields = ['id', 'name', 'is_active', 'variables', 'created_at', 'updated_at']


# ─── History Serializers ─────────────────────────────────────────

# Bound the stored response body so a single history entry can't bloat the DB.
MAX_HISTORY_BODY_BYTES = 1_000_000


class HistoryEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoryEntry
        fields = ['id', 'request', 'response', 'timestamp']

    def validate_response(self, value):
        """Truncate an over-sized response body before persisting."""
        if isinstance(value, dict) and isinstance(value.get('body'), str):
            body = value['body']
            if len(body) > MAX_HISTORY_BODY_BYTES:
                value = {**value, 'body': body[:MAX_HISTORY_BODY_BYTES] + '…[truncated]', 'truncated': True}
        return value

    def validate_request(self, value):
        """Strip heavy file payloads and truncate a large request body.

        A request config may embed base64 file data in ``multipartFiles``,
        which would otherwise bloat the DB; keep metadata only.
        """
        if not isinstance(value, dict):
            return value
        files = value.get('multipartFiles')
        if isinstance(files, list):
            cleaned = [
                {k: v for k, v in f.items() if k != 'dataUrl'}
                if isinstance(f, dict) else f
                for f in files
            ]
            value = {**value, 'multipartFiles': cleaned}
        body = value.get('body')
        if isinstance(body, str) and len(body) > MAX_HISTORY_BODY_BYTES:
            value = {**value, 'body': body[:MAX_HISTORY_BODY_BYTES] + '…[truncated]'}
        return value
