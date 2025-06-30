from django.urls import path, include  # Include is imported here
from .views import (login_view, logout_view, refresh_token_view, protected_view,
                    get_users, create_user, update_user, check_username)
from rest_framework.routers import DefaultRouter
from .views import gps_geojson, BoatViewSet, FisherfolkViewSet, FisherfolkBoatViewSet, BirukbilugTrackerViewSet, ActivityLogViewSet, ProvincialAgriculturistViewSet, MunicipalAgriculturistViewSet, gps_data

router = DefaultRouter()
router.register(r'boats', BoatViewSet)
router.register(r'fisherfolk', FisherfolkViewSet, basename='fisherfolk')
router.register(r'fisherfolkboat', FisherfolkBoatViewSet, basename='fisherfolkboat')
router.register(r'tracker', BirukbilugTrackerViewSet, basename='tracker')
router.register(r'provincial-agriculturists', ProvincialAgriculturistViewSet, basename='provincial-agriculturist')
router.register(r'municipal-agriculturists', MunicipalAgriculturistViewSet, basename='municipal-agriculturist')
router.register(r'activitylog', ActivityLogViewSet, basename='activitylog')

urlpatterns = [
    path('users/', get_users, name='get_users'),
    path('users/create/', create_user, name='create_user'),
    path('users/update/<int:pk>/', update_user, name='update_user'),
    path('users/check-username/', check_username, name='check_username'),

    # TOKEN
    path('login/', login_view),
    path('logout/', logout_view),
    path('refresh/', refresh_token_view),
    path('protected/', protected_view),

    path('', include(router.urls)),

    path('gps/', gps_data),

    path("gps/geojson/", gps_geojson),
]
