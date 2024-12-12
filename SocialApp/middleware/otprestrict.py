from django.http import JsonResponse

class RestrictOTPEndpointMiddleware:
    """
    Hassas bilgi barındıran OTP endpoint'lerine doğrudan erişimi engeller.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
    # Eğer kullanıcı henüz kimlik doğrulaması yapmamışsa, OTP endpoint'ine erişim izni ver
        if request.path.startswith('/api/otp/') and not request.user.is_authenticated:
            if request.method == 'PATCH':  # Yalnızca OTP doğrulama için izin ver
                return self.get_response(request)
            return JsonResponse({"detail": "Yetkisiz erişim."}, status=403)

        response = self.get_response(request)
        return response

