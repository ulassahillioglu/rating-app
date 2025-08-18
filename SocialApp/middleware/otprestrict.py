from django.http import JsonResponse

class RestrictOTPEndpointMiddleware:
    """
    Directly restricts access to OTP endpoints containing sensitive information.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If the user is not authenticated yet, allow access to the OTP endpoint
        if request.path.startswith('/api/otp/') and not request.user.is_authenticated:
            if request.method == 'PATCH':  # Only allow OTP verification
                return self.get_response(request)
            return JsonResponse({"detail": "Unauthorized access."}, status=403)

        response = self.get_response(request)
        return response

