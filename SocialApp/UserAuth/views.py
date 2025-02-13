from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.timezone import timedelta
from django.utils import timezone

import random
from datetime import datetime
from CoreApp.models import UserProfile, generate_random_unique_id,validate_phone_number
from CoreApp.serializers import UserProfileSerializer
from CoreApp.utils import send_sms_otp, send_email_notification
from .serializers import UserSerializer

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view,authentication_classes,permission_classes
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication,TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
def login(request):
    try:
        user = User.objects.get(username=request.data['username'])
        user_profile = UserProfile.objects.get(username=request.data['username'])
    except User.DoesNotExist:
        return Response({"detail": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

    if not user.is_active:
        return Response({"detail": "Kullanıcı aktif değil. Lütfen hesabınızı doğrulayın"}, status=status.HTTP_403_FORBIDDEN)

    if not user.check_password(request.data['password']):
        return Response({"detail": "Hatalı parola girdiniz."}, status=status.HTTP_401_UNAUTHORIZED)

    # JWT token oluşturma
    refresh = RefreshToken.for_user(user)
    serialized_user = UserProfileSerializer(user_profile)

    user.last_login = datetime.now()
    user.save()

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": serialized_user.data,
        "message": "Giriş başarılı"
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
def refresh_token(request):
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({"detail": "Refresh token eksik."}, status=400)
    try:
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        return Response({"access": access_token}, status=200)
    except Exception as e:
        return Response({"detail": "Geçersiz refresh token."}, status=401)
  
@api_view(['GET'])
@login_required
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def is_superuser(request):
    if request.method == 'GET':
        is_superuser = request.user.is_superuser
        return Response({'is_superuser': is_superuser})
    else:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from django.db import transaction

@api_view(['POST'])
def signup(request):
    required_fields = ['username', 'email', 'password', 'first_name', 'last_name','phone_number','birth_date']
    for field in required_fields:
        if not request.data.get(field):
            return Response(
                {"error": f"{field} is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

    username = request.data.get('username')
    email = request.data.get('email')
    try:
        validate_email(email)  # Email doğrulaması
    except ValidationError:
        return Response({"error": "Geçersiz bir email adresi girdiniz."}, status=status.HTTP_400_BAD_REQUEST)
    password = request.data.get('password')
    if len(password) < 8:
        return Response({"error": "Parola en az 8 karakterden oluşmalı"}, status=status.HTTP_400_BAD_REQUEST)
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    bio = request.data.get('bio', '')
    profile_picture = request.data.get('profile_picture', None)
    phone_number = request.data.get('phone_number')
    try:
        validate_phone_number(phone_number)
    except ValidationError:
        return Response({"error": "Geçersiz bir telefon numarası girdiniz."}, status=status.HTTP_400_BAD_REQUEST)
    birth_date_str = request.data.get('birth_date')

    # Doğum tarihini kontrol et 1
    try:
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        if not str(birth_date.year).startswith(('1', '2')):
            return Response({"error": "Geçerli bir tarih girdiniz"}, status=status.HTTP_400_BAD_REQUEST)

        if birth_date.year < 1900 or birth_date.year > datetime.now().year:
            return Response({"error": "Geçerli bir yıl girdiniz"}, status=status.HTTP_400_BAD_REQUEST)

        if birth_date.month < 1 or birth_date.month > 12:
            return Response({"error": "Geçerli bir ay girdiniz"}, status=status.HTTP_400_BAD_REQUEST)

        if birth_date.month == 2 and birth_date.day > 29:
            return Response({"error": "Geçerli bir tarih girdiniz"}, status=status.HTTP_400_BAD_REQUEST)
        elif birth_date.month == 2 and birth_date.day == 29 and not (birth_date.year % 4 == 0 and (birth_date.year % 100 != 0 or birth_date.year % 400 == 0)):
            return Response({"error": "Geçerli bir tarih girdiniz"}, status=status.HTTP_400_BAD_REQUEST)


        today = datetime.today().date()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        if age < 13:
            return Response({"error": "Kayıt olmak için 13 yaşından büyük olmalısınız."}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError:
        return Response({"error": "Invalid birth_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
    
    if User.objects.filter(username=username).exists():
        return Response({"error": "Kullanıcı adı mevcut. Farklı bir kullanıcı adı deneyin."}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(email=email).exists():
        return Response({"error": "Bu e-mail daha önce kullanılmış. Lütfen farklı bir e-mail adresi ile kayıt olun."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            # User kaydı
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=False,
            )

            # UserProfile kaydı
            user_profile = UserProfile.objects.create(
                user=user,
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                bio=bio,
                profile_picture=profile_picture,
                unique_id=generate_random_unique_id(),
                phone_number=phone_number,
                birth_date = birth_date,
                
                
            )
        otp,otp_expiry = user_profile.generate_otp()
        send_email_notification("Activate your Account", otp, settings.EMAIL_HOST_USER, user_profile.email)
        # send_sms_otp(user_profile.phone_number, otp)
        return Response({
            "message": "User and profile created successfully",
            "user_id": user_profile.id,
            
             }, 
            status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def forgot_password(request):
    """Send OTP to user's email for password reset."""
    email = request.data.get('email')
    if not email:
        return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user_profile = UserProfile.objects.get(email=email)
    except UserProfile.DoesNotExist:
        return Response({"detail": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)
    
    otp = random.randint(100000, 999999)
    otp_expiry = timezone.now() + timedelta(minutes=5)
    
    user_profile.otp = otp
    user_profile.otp_expiry = otp_expiry
    user_profile.save()
    
    send_email_notification("Parolanızı sıfırlamanız için güvenlik kodu: ", otp, settings.EMAIL_HOST_USER, email)
    return Response({"detail": "OTP mail adresine gönderildi."}, status=status.HTTP_200_OK)

@api_view(['POST'])
def reset_password(request):
    """Reset password using OTP."""
    email = request.data.get('email')
    otp = request.data.get('otp')
    new_password = request.data.get('password')
    
    if not email or not otp or not new_password:
        return Response({"detail": "Email, OTP, and new password are required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user_profile = UserProfile.objects.get(email=email)
    except UserProfile.DoesNotExist:
        return Response({"detail": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)
    
    if user_profile.otp != otp or timezone.now() > user_profile.otp_expiry:
        return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
    
    user = User.objects.get(email=email)
    user.set_password(new_password)
    user.save()
    
    user_profile.otp_expiry = None
    user_profile.save()
    
    return Response({"detail": "Password reset successfully."}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def test_token(request):
    return Response(request.user.id)
