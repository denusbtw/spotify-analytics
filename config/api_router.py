from allauth.socialaccount.providers.spotify.views import SpotifyOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.urls import path


class CustomOauth2Client(OAuth2Client):
    def __init__(
        self,
        request,
        consumer_key,
        consumer_secret,
        access_token_method,
        access_token_url,
        callback_url,
        _scope,
        scope_delimiter=" ",
        headers=None,
        basic_auth=False,
    ):
        super().__init__(
            request,
            consumer_key,
            consumer_secret,
            access_token_method,
            access_token_url,
            callback_url,
            scope_delimiter,
            headers,
            basic_auth,
        )


class SpotifyLogin(SocialLoginView):
    adapter_class = SpotifyOAuth2Adapter
    client_class = CustomOauth2Client
    callback_url = "http://127.0.0.1:5173/spotify-callback/"


urlpatterns = [
    path("auth/spotify/", SpotifyLogin.as_view(), name="sp_login"),
]