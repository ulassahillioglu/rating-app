
from rest_framework import viewsets, permissions,status,serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import AuthenticationFailed,NotFound,PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle,AnonRateThrottle
from rest_framework.generics import GenericAPIView

from django.utils import timezone
from django.shortcuts import render
from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils.timezone import timedelta

from .models import Category, Report, UserProfile, Comment
from .serializers import ReportSerializer, UserProfileSerializer, CommentSerializer

import random, os
import datetime
from CoreApp.utils import send_sms_otp,send_email_notification
from CoreApp.throttling import CustomRateLimiter,TokenRateLimiter


class CommentPagination(PageNumberPagination):
    page_size = 5  # Set the number of comments per page


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [TokenRateLimiter]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Retrieve the currently authenticated user's profile."""
        user_profile = UserProfile.objects.get(user=request.user)
        serializer = self.get_serializer(user_profile)
        return Response(serializer.data)

    from rest_framework.exceptions import NotFound

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def comments(self, request, pk=None):
        """Retrieve paginated comments for a specific user's profile."""
        try:
            user_profile = UserProfile.objects.get(username=pk)
        except UserProfile.DoesNotExist:
            raise NotFound("User profile not found.")
        
        comments = Comment.objects.filter(profile_commented_on=user_profile).order_by('-created_at')
        
        paginator = CommentPagination()
        paginated_comments = paginator.paginate_queryset(comments, request)
        
        comment_serializer = CommentSerializer(paginated_comments, many=True)
        return paginator.get_paginated_response(comment_serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        """Upload a profile picture for the authenticated user."""
        user_profile = UserProfile.objects.get(user=request.user)
        
        if 'profile_picture' not in request.data:
            return Response({'error': 'No profile picture provided.'}, status=status.HTTP_400_BAD_REQUEST)
        
        profile_picture = request.data['profile_picture']
        
        # Validate the file type and size
        try:
            user_profile.profile_picture = profile_picture
            user_profile.save()
            return Response({'message': 'Profile picture uploaded successfully.'}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'Failed to upload profile picture.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """Update the authenticated user's profile information."""
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Deserialize and validate the data
        serializer = self.get_serializer(user_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentCreateView(APIView):
    throttle_classes = [UserRateThrottle]

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise AuthenticationFailed('Kullanıcı giriş yapmadı.')

        try:
            user_profile = request.user.profile  # Ensure the user has a profile
        except AttributeError:
            raise AuthenticationFailed('Böyle bir kullanıcı yok.')

        # Get the profile being commented on
        try:
            profile_commented_on = UserProfile.objects.get(username=request.data['profile_commented_on'])
        except UserProfile.DoesNotExist:
            raise ValidationError('Bu kullanıcıya ait bir profil bulunamadı.')

        content = request.data.get('content', None)
        if not content:
            raise ValidationError('Yorum Girmelisiniz.')

        # Get and validate the category scores
        category_scores = request.data.get('category_scores', {})
        if not isinstance(category_scores, dict):
            raise ValidationError('Category scores must be a dictionary.')

        # Check if all required categories are provided by their IDs
        required_category_ids = [1, 2, 3]  # IDs for Intelligence, Appearance, and Relationship
        for category_id in required_category_ids:
            if str(category_id) not in category_scores:
                raise ValidationError(f'"{category_id}" için puan girmeniz gerekli.')

        # Validate the scores
        for category_id, score in category_scores.items():
            if not isinstance(score, int) or score < 1 or score > 10:
                raise ValidationError(f'Category ID "{category_id}". 1-10 arasında bir puan vermelisiniz.')

        # Update the JSON field for the profile being commented on
        for category_id, score in category_scores.items():
            current_data = profile_commented_on.category_scores.get(
                str(category_id), {"total_score": 0, "comment_count": 0}
            )
            current_data["total_score"] += score
            current_data["comment_count"] += 1
            profile_commented_on.category_scores[str(category_id)] = current_data

        # Save the profile with updated scores
        profile_commented_on.save()

        # Create a single comment record
        comment = Comment.objects.create(
            user_profile=user_profile,
            profile_commented_on=profile_commented_on,
            content=content,
            category_scores=category_scores  # Save the JSON scores in the comment
        )

        # Serialize and return the created comment
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=201)




class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [TokenRateLimiter]

    def perform_create(self, serializer):
        try:
            user_profile = UserProfile.objects.get(id=self.request.data['user_profile'])
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError({"error": "User profile not found."})
        serializer.save(user_profile=user_profile)

    @action(detail=False, methods=['get'])
    def own_comments(self, request):
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)

        comments = Comment.objects.filter(user_profile=user_profile).order_by('-created_at')
        paginator = PageNumberPagination()
        paginator.page_size = 10
        paginated_comments = paginator.paginate_queryset(comments, request)

        comment_serializer = self.get_serializer(paginated_comments, many=True)
        return paginator.get_paginated_response(comment_serializer.data)

    @action(detail=True, methods=['get'])
    def likes_dislikes(self, request, pk=None) :
        
        ##Performansı arttırma ve anlık request sayısını azaltmak için batch request entegrasyonu yapıldı. 
        ##İlerleyen zamanlarda genişleme sağlaması açısından kod esnek bırakıldı.
        if 'ids' in request.query_params:
            comment_ids = [int(id) for id in request.query_params['ids'].split(',')]
            comments = Comment.objects.filter(id__in=comment_ids)
            
            if not comments.exists():
                return Response({"error": "Some comments not found."}, status=status.HTTP_404_NOT_FOUND)
            
            user_profile = request.user.profile
            response_data = []
            
            for comment in comments:
                likes = comment.likes.values('id', 'username')
                dislikes = comment.dislikes.values('id', 'username')
                
                response_data.append({
                    "id": comment.id,
                    "likes": list(likes),
                    "dislikes": list(dislikes),
                    "user_action": {
                        "has_liked": comment.likes.filter(id=user_profile.id).exists(),
                        "has_disliked": comment.dislikes.filter(id=user_profile.id).exists()
                    }
                })
            
            return Response(response_data, status=status.HTTP_200_OK)
        else:
     
            comment = get_object_or_404(
                Comment.objects.prefetch_related('likes', 'dislikes'),
                id=pk
            )
            likes = comment.likes.values('id', 'username')
            dislikes = comment.dislikes.values('id', 'username')
            user_profile = request.user.profile

            return Response({
                "likes": list(likes),
                "dislikes": list(dislikes),
                "user_action": {
                    "has_liked": comment.likes.filter(id=user_profile.id).exists(),
                    "has_disliked": comment.dislikes.filter(id=user_profile.id).exists()
                }
            }, status=status.HTTP_200_OK)

    
##Yorum beğenme işlemleri
class ToggleLikeCommentView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomRateLimiter]

    def post(self, request, comment_id, *args, **kwargs):
        # Yorumu bul
        comment = get_object_or_404(Comment, id=comment_id)
        user_profile = request.user.profile  # Şu anki kullanıcı profili

        # Kendi yorumunu beğenmeye çalışıyorsa hata döndür
        

        # Kullanıcı dislike yapmışsa önce dislike'ı kaldır
        if user_profile in comment.dislikes.all():
            comment.dislikes.remove(user_profile)

        # Like işlemi: toggle (ekle veya çıkar)
        if user_profile in comment.likes.all():
            comment.likes.remove(user_profile)  # Like'ı geri al
            action = "Like removed successfully."
        else:
            comment.likes.add(user_profile)  # Like ekle
            action = "Like added successfully."

        return Response({"detail": action}, status=status.HTTP_200_OK)

    
#Yorum dislike işlemleri
class ToggleDislikeCommentView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomRateLimiter]

    def post(self, request, comment_id, *args, **kwargs):
        # Yorumu bul
        comment = get_object_or_404(Comment, id=comment_id)
        user_profile = request.user.profile  # Şu anki kullanıcı profili

        # Kendi yorumunu dislike yapmaya çalışıyorsa hata döndür
        

        # Kullanıcı like yapmışsa önce like'ı kaldır
        if user_profile in comment.likes.all():
            comment.likes.remove(user_profile)

        # Dislike işlemi: toggle (ekle veya çıkar)
        if user_profile in comment.dislikes.all():
            comment.dislikes.remove(user_profile)  # Dislike'ı geri al
            action = "Dislike removed successfully."
        else:
            comment.dislikes.add(user_profile)  # Dislike ekle
            action = "Dislike added successfully."

        return Response({"detail": action}, status=status.HTTP_200_OK)

##Deprecated
# class CommentLikesDislikesView(APIView):  # Hem beğenenleri hem de beğenmeyenleri döndürür. 
#     permission_classes = [IsAuthenticated]
#     throttle_classes = [TokenRateLimiter]
#     def get(self, request, comment_id, *args, **kwargs):
#         # Yorumu bul
#         comment = get_object_or_404(Comment, id=comment_id)
#         user_profile = request.user.profile  # Şu anki kullanıcı profili

#         # Beğenen ve beğenmeyen kullanıcıları sadece gerekli alanlarla al
#         likes = comment.likes.values('id', 'username', 'first_name', 'last_name')
#         dislikes = comment.dislikes.values('id', 'username', 'first_name', 'last_name')

#         # Kullanıcının mevcut durumu
#         user_has_liked = comment.likes.filter(id=user_profile.id).exists()
#         user_has_disliked = comment.dislikes.filter(id=user_profile.id).exists()

#         return Response({
#             "likes": list(likes),
#             "dislikes": list(dislikes),
#             "user_action": {
#                 "has_liked": user_has_liked,
#                 "has_disliked": user_has_disliked
#             }
#         }, status=status.HTTP_200_OK)
        


##Anasayfaya takip edilen kullanıcılara yapılan son yorumları getir
class LatestCommentsView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [TokenRateLimiter]
    
    def get(self, request):
        # Kullanıcının profilini al
        user_profile = request.user.profile
        
        # Kullanıcının takip ettiği kişilerin yorumlarını al
        followed_profiles = user_profile.following.all()
        
        # Takip edilen kişilerin son yorumlarını al
        comments = Comment.objects.filter(profile_commented_on__in=followed_profiles).order_by('-created_at')
        
        paginator = PageNumberPagination()
        paginator.page_size = 5
        paginated_comments = paginator.paginate_queryset(comments, request)
        
        # Yorumları serileştir
        comment_serializer = CommentSerializer(paginated_comments, many=True)
        return paginator.get_paginated_response(comment_serializer.data)
        

class FollowToggleView(APIView):
    """
    Toggle follow/unfollow for a user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, username, *args, **kwargs):
        # Takip edilecek kullanıcıyı bul
        target_user = get_object_or_404(UserProfile, username=username)
        current_user_profile = request.user.profile

        # Kullanıcının kendisini takip etmesini engelle
        if target_user == current_user_profile:
            return Response({"detail": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        # Kullanıcıyı takip ediyor mu kontrol et
        if target_user in current_user_profile.following.all():
            # Takibi bırak
            current_user_profile.following.remove(target_user)
            target_user.followers.remove(current_user_profile)
            message = "You have unfollowed this user."
        else:
            # Kullanıcıyı takip et
            current_user_profile.following.add(target_user)
            target_user.followers.add(current_user_profile)
            message = "You are now following this user."

        return Response({"detail": message}, status=status.HTTP_200_OK)


class UserProfileSearchView(GenericAPIView):
    """
    Kullanıcı adıyla arama yapar ve sonuçları sayfalayarak döner.
    """
    
    throttle_classes = [UserRateThrottle]
    serializer_class = UserProfileSerializer
    
    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '')  # Arama kelimesi
        if not query:
            return Response({"detail": "Search query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Kullanıcı adında arama yap
        profiles = UserProfile.objects.filter(username__icontains=query).order_by('id')  # 'id' alanına göre sıralama yap

        # Sayfalama
        paginator = PageNumberPagination()
        paginator.page_size = 20  # Her sayfada 20 sonuç
        paginated_profiles = paginator.paginate_queryset(profiles, request)

        # Sonuçları serileştir
        serializer = self.get_serializer(paginated_profiles, many=True)
        
        # Sayfalanmış sonuçları döndür
        return paginator.get_paginated_response(serializer.data)


class UserProfileDetails(viewsets.ModelViewSet):  
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [TokenRateLimiter]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def details(self, request):
        """Retrieve the currently searched user's profile by username."""
        username = request.query_params.get('username', None)
        if username is None:
            return Response({"detail": "Username query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Aranan kullanıcıyı bul
            user_profile = UserProfile.objects.get(username=username)
        except UserProfile.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Kullanıcıyı serileştir ve döndür
        serializer = self.get_serializer(user_profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def followers(self, request):
        username = request.query_params.get('username', None)
        if username is None:
            return Response({"detail": "Username query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        if username != request.user.username:
            return Response({"detail": "You can only view your own followers."}, status=status.HTTP_403_FORBIDDEN)

        try:
            user_profile = UserProfile.objects.get(username=username)
            followers = user_profile.followers.all().order_by('id')
        except UserProfile.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        paginator = PageNumberPagination()
        paginator.page_size = 20  # Her sayfada 20 sonuç
        paginated_followers = paginator.paginate_queryset(followers, request, view=self)

        if paginated_followers is None:
            return Response({"detail": "Pagination did not return any results."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(paginated_followers, many=True)
        total_pages = paginator.page.paginator.num_pages

        # Get the next and previous links
        next_page = paginator.get_next_link()
        previous_page = paginator.get_previous_link()

        # Include `total_pages`, `next`, and `prev` in the paginated response
        response_data = {
            "results": serializer.data,
            "total_pages": total_pages,
            "next": next_page,
            "prev": previous_page,
        }
        return Response(response_data)

    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def following(self,request):
        """İlgili kullanıcının takip ettiklerini getir"""
        username = request.query_params.get('username',None)
        if username is None:
            return Response({"detail": "Username query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Giriş yapan kullanıcı ile sorgulanan kullanıcının aynı olup olmadığını kontrol et
        if username != request.user.username:
            return Response(
                {"detail": "You are not authorized to view other users' followers."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Aranan kullanıcıyı bul
            user_profile = UserProfile.objects.get(username=username)
            followees = user_profile.following.all()
        except UserProfile.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        paginator = PageNumberPagination()
        paginator.page_size = 20  # Her sayfada 20 sonuç
        paginated_followees = paginator.paginate_queryset(followees, request, view=self)
        
        # Kullanıcıyı serileştir ve döndür
        if paginated_followees is None:
            return Response({"detail": "Pagination did not return any results."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(paginated_followees, many=True)
        total_pages = paginator.page.paginator.num_pages

        # Get the next and previous links
        next_page = paginator.get_next_link()
        previous_page = paginator.get_previous_link()

        # Include `total_pages`, `next`, and `prev` in the paginated response
        response_data = {
            "results": serializer.data,
            "total_pages": total_pages,
            "next": next_page,
            "prev": previous_page,
        }
        return Response(response_data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def comment_stats(self, request):
        """Kullanıcı için yorum istatistiklerini ve ortalama puanı getir"""
        username = request.query_params.get('username', None)
        if username is None:
            return Response({"detail": "Username query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Kullanıcıyı getir
            user_profile = UserProfile.objects.get(username=username)
        except UserProfile.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Yorum istatistiklerini hesapla
        comment_stats = user_profile.get_category_comment_stats()
        user_average_score = user_profile.get_user_average_score()  # Calculate average score

        # İstatistikleri döndür
        return Response({
            "comment_stats": comment_stats,
            "average_score": user_average_score['average_score']
        })
        
        
class OTPViewSet(viewsets.ModelViewSet):  
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    throttle_classes = [CustomRateLimiter]
    
    
    @action(detail=True,methods=['PATCH'])
    def verify_otp(self,request,pk=None):
        instance = self.get_object()
        # Kullanıcı doğrulama
        # if instance.user != request.user:
        #     raise PermissionDenied("Bu işlem için yetkiniz yok.")
        if(
            not instance.is_active
            and instance.otp == request.data.get('otp')
            and instance.otp_expiry
            and timezone.now() < instance.otp_expiry
        ):
            # Auth_user tablosunu günceller
            user = instance.user  
            user.is_active = True
            user.save()
            
            # Core_User tablosunu günceller
            instance.is_active = True
            instance.otp_expiry = None
            instance.max_otp_try = settings.MAX_OTP_TRY
            instance.otp_max_out = None
            instance.save()
            return Response({"detail": "Doğrulama başarılı."}, status=status.HTTP_200_OK)
        
        return Response(
            {"detail": "Doğrulama başarısız. Kullanıcı aktif veya kod hatalı. Lütfen tekrar deneyin."}, 
            status=status.HTTP_400_BAD_REQUEST
            )
        
    @action(detail=True, methods=['PATCH'])
    def regenerate_otp(self, request, pk=None):
        instance = self.get_object()
        
        # if instance.user != request.user:
        #     raise PermissionDenied("Bu işlem için yetkiniz yok.")
        
        if int(instance.max_otp_try) == 0 and timezone.now() < instance.otp_max_out:
            return Response({"detail": "Doğrulama hakkınız bitti. 1 saat sonra tekrar deneyin"}, status=status.HTTP_400_BAD_REQUEST)
         
        otp = random.randint(100000,999999)
        otp_expiry = timezone.now() + timedelta(minutes=5)
        max_otp_try = int(instance.max_otp_try)-1
        
        instance.otp = otp
        instance.otp_expiry = otp_expiry
        instance.max_otp_try = max_otp_try
        
        if max_otp_try == 0:
            instance.otp_max_out = timezone.now() + datetime.timedelta(hours=1)
        elif max_otp_try == -1:
            instance.max_otp_try = settings.MAX_OTP_TRY
        else:
            instance.otp_max_out = None
            instance.max_otp_try = max_otp_try
        
        instance.save()
        # send_sms_otp(instance.phone_number, otp)
        send_email_notification("Activate your Account", otp, settings.EMAIL_HOST_USER, instance.email)
        return Response({"detail": "Yeni OTP kodu gönderildi."}, status=status.HTTP_200_OK)
 

class ReportView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomRateLimiter]

    def post(self, request, *args, **kwargs):
        serializer = ReportSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_reporting=request.user.profile)
            return Response({"detail": "Report submitted successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
class DocumentListView(APIView):
    throttle_classes = [CustomRateLimiter]
    
    def get(self, request, *args, **kwargs):
        docs_dir = os.path.join(settings.BASE_DIR, "static/docs/")
        docs = [
            {"name": f, "url": request.build_absolute_uri(f"/static/docs/{f}")}
            for f in os.listdir(docs_dir) if f.endswith(".pdf")
        ]
        return Response(docs)
