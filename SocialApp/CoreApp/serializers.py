# coreapp/serializers.py
from rest_framework import serializers
from .models import Report, UserProfile, Comment

class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        fields = ['id', 'username','bio', 'profile_picture', 'email', 'first_name', 'last_name', 'unique_id','followers', 'following','phone_number']
        read_only_fields = ['user']  # The 'user' field will be automatically assigned

    def get_profile_picture(self, obj):
        if obj.profile_picture:
            return f'http://localhost:8000{obj.profile_picture.url}'
        return None
        

class CommentSerializer(serializers.ModelSerializer):
    commenter_username = serializers.CharField(source='user_profile.user.username')  # Yorumu yapan kullanıcının username'i
    user_unique_id = serializers.CharField(source='user_profile.unique_id')  # Yorumu yapan kullanıcının unique_id'si
    commented_profile_username = serializers.CharField(source='profile_commented_on.user.username')  # Yorum yapılan profilin username'i
    commented_profile_unique_id = serializers.CharField(source='profile_commented_on.unique_id')  # Yorum yapılan profilin unique_id'si
    created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')  # Tarih formatı
    category = serializers.CharField(source='category.name') # Kategorinin adı
    category_id = serializers.IntegerField(source='category.id')  
    
    class Meta:
        model = Comment
        fields = [
            'id',
            'commenter_username',
            'content',
            'created_at',
            'user_unique_id',
            'is_anonymous',
            'commented_profile_username',  # Yeni alan
            'commented_profile_unique_id',  # Yeni alan
            'category',
            'category_id' 
        ]


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['report_type', 'reported_comment', 'reported_profile', 'reason']

    def validate(self, data):
        if data['report_type'] == 'comment' and not data.get('reported_comment'):
            raise serializers.ValidationError("Comment ID is required for comment reports.")
        if data['report_type'] == 'profile' and not data.get('reported_profile'):
            raise serializers.ValidationError("Profile ID is required for profile reports.")
        return data

