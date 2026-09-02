from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CollectionViewSet,
    CurlParseView,
    EnvironmentViewSet,
    HealthView,
    HistoryViewSet,
    KafkaSendView,
    ProxyView,
    RocketMQSendView,
)

router = DefaultRouter()
router.register('collections', CollectionViewSet, basename='collection')
router.register('environments', EnvironmentViewSet, basename='environment')
router.register('history', HistoryViewSet, basename='history')

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    path('parse-curl/', CurlParseView.as_view(), name='parse-curl'),
    path('proxy/', ProxyView.as_view(), name='proxy'),
    path('kafka/send/', KafkaSendView.as_view(), name='kafka-send'),
    path('rocketmq/send/', RocketMQSendView.as_view(), name='rocketmq-send'),
]

urlpatterns += router.urls
