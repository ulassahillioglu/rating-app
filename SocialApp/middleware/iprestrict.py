from django.http import HttpResponseForbidden

class BlockExactApiPathMiddleware:
    ALLOWED_IPS = ['31.155.140.45','185.87.253.121']  # Replace with allowed IP(s)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request path is exactly '/api/'
        if request.path == '/api/' and request.META['REMOTE_ADDR'] not in self.ALLOWED_IPS:
            return HttpResponseForbidden("Access to /api/ is restricted.")
        
        # Allow the request to pass through if it's not the restricted path
        response = self.get_response(request)
        return response
