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

class UserUpdateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone_number','bio']

class CommentSerializer(serializers.ModelSerializer):
    commenter_username = serializers.CharField(source='user_profile.user.username')  # Username of the commenter
    user_unique_id = serializers.CharField(source='user_profile.unique_id')  # Unique ID of the commenter
    commented_profile_username = serializers.CharField(source='profile_commented_on.user.username')  # Username of the commented profile
    commented_profile_full_name = serializers.SerializerMethodField()
    commented_profile_picture = serializers.ImageField(source='profile_commented_on.profile_picture')  # Profile picture of the commented profile
    commented_profile_unique_id = serializers.CharField(source='profile_commented_on.unique_id')  # Unique ID of the commented profile
    created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')  # Date format
    average_score = serializers.SerializerMethodField()
    class Meta:
        model = Comment
        fields = [
            'id',
            'commenter_username',
            'content',
            'likes',
            'dislikes',
            'created_at',
            'user_unique_id',
            'is_anonymous',
            'commented_profile_full_name',  # New field
            'commented_profile_username',  # New field
            'commented_profile_picture',  # New field
            'commented_profile_unique_id',  # New field
            'category_scores',
            'average_score'
        ]
    
    def get_average_score(self, obj):
        total = 0
        count = 0

        # Calculate total and count
        for category, score in obj.category_scores.items():
            print(category, score)  # Print for debugging
            total += int(score)
            count += 1

        # Return 0 if no scores were found
        if count == 0:
            return 0

        return round(total / count, 2)  # Return the average

    
        
    def get_commented_profile_full_name(self, obj):
        first_name = obj.profile_commented_on.user.first_name
        last_name = obj.profile_commented_on.user.last_name
        return f"{first_name} {last_name}"

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

