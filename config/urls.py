from allauth.account.views import LogoutView
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include("config.api_router")),

    path("accounts/", include("allauth.socialaccount.providers.spotify.urls")),
    path("logout/", LogoutView.as_view(), name="account_logout"),
]
