from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentListView, ReportView, UserProfileViewSet,FollowToggleView,UserProfileSearchView,UserProfileDetails,OTPViewSet,GetUserIdView
from .views import CommentCreateView,CommentViewSet,LatestCommentsView,ToggleLikeCommentView,ToggleDislikeCommentView,CommentCreateView


router = DefaultRouter()
router.register(r'user-profiles', UserProfileViewSet, basename='user-profile')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'otp', OTPViewSet,basename='otp')

#CoreApp
urlpatterns = [
    path('', include(router.urls)),
    path('latest-comments/', LatestCommentsView.as_view(), name='latest-comments'),
    path('comments/create', CommentCreateView.as_view(), name='create_comment'),
    path('profiles/<str:username>/follow/', FollowToggleView.as_view(), name='follow-toggle'),
    path('profiles/search/', UserProfileSearchView.as_view(), name='profile-search'),
    path('profiles/details/', UserProfileDetails.as_view({'get': 'details'}), name='profile-details'),
    path('profiles/info/', UserProfileDetails.as_view({'get': 'info'}), name='profile-info'),
    path('profiles/comment_stats/', UserProfileDetails.as_view({'get': 'comment_stats'}), name='profile-stats'),
    path('profiles/followers/', UserProfileDetails.as_view({'get': 'followers'}),name='profile-followers'),
    path('profiles/following/', UserProfileDetails.as_view({'get': 'following'}),name='profile-followers'),
    path('comments/<int:comment_id>/like/', ToggleLikeCommentView.as_view(), name='toggle-like-comment'),
    path('comments/<int:comment_id>/dislike/', ToggleDislikeCommentView.as_view(), name='toggle-dislike-comment'),
    path('user-id/', GetUserIdView.as_view(), name='get-id'),
    
    # path('comments/<int:comment_id>/likes-dislikes/', CommentLikesDislikesView.as_view(), name='comment-likes-dislikes'),
    path('report/', ReportView.as_view(), name='report'),
    path('documents/', DocumentListView.as_view(), name='document-list'),
    


]

