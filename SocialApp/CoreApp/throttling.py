from rest_framework.throttling import UserRateThrottle, BaseThrottle
from django.core.cache import cache
import time

class CustomRateLimiter(BaseThrottle):
    scope = 'custom'

    def allow_request(self, request, view):
        user_ip = self.get_ident(request)
        return self.is_allowed(user_ip)

    def is_allowed(self, user_ip):
        # Özel bir hız sınırlayıcı tanımla 
        limit = 30
        window = 10  # seconds

        cache_key = f"throttle_{user_ip}"
        request_timestamps = cache.get(cache_key, [])

        # Zaman penceresi içindeki zaman damgalarını filtrele
        current_time = time.time()
        request_timestamps = [
            ts for ts in request_timestamps if current_time - ts < window
        ]

        # İstek sınırını aşıp aşmadığını kontrol et
        if len(request_timestamps) >= limit:
            return False

        # Mevcut istek zaman damgasını ekleyin ve önbelleği güncelleyin
        request_timestamps.append(current_time)
        cache.set(cache_key, request_timestamps, timeout=window)
        return True

    def wait(self):
        # İsteği yeniden denemeden önce beklenecek süreyi isteğe bağlı olarak döndürün
        return 10  
    
class TokenRateLimiter(BaseThrottle):
    scope = 'token'

    def allow_request(self, request, view):
        # Token'i al
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token:
            # Token yoksa izin verme
            return False

        return self.is_allowed(token)

    def is_allowed(self, token):
        # Token için özel bir hız sınırlayıcı tanımla
        limit = 1000
        window = 60  # seconds

        cache_key = f"throttle_token_{hash(token)}"
        request_timestamps = cache.get(cache_key, [])

        # Zaman penceresi içindeki zaman damgalarını filtrele
        current_time = time.time()
        request_timestamps = [
            ts for ts in request_timestamps if current_time - ts < window
        ]

        # İstek sınırını aşıp aşmadığını kontrol et
        if len(request_timestamps) >= limit:
            return False

        # Mevcut istek zaman damgasını ekleyin ve önbelleği güncelle
        request_timestamps.append(current_time)
        cache.set(cache_key, request_timestamps, timeout=window)
        return True

    def wait(self):
        # İsteği yeniden denemeden önce beklenecek süreyi isteğe bağlı olarak döndür
        return 60  