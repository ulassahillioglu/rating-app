#userauth
from django.urls import path,re_path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
    re_path('login/',views.login,name="login"),
    re_path('signup/',views.signup,name="sign_up"),
    re_path('reset-password/',views.reset_password,name="reset_password"),
    re_path('forgot-password/',views.forgot_password,name="forgot_password"),
    re_path('test_token/',views.test_token,name="test_token"),
    re_path('is_superuser/', views.is_superuser, name='is_superuser'),
    
    # JWT token endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
