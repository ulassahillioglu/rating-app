# UserAuth/serializers.py
from rest_framework import serializers
from CoreApp.models import UserProfile
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'profile']
        extra_kwargs = {'password': {'write_only': True}}

    def get_profile(self, obj):
        profile = UserProfile.objects.filter(user=obj).first()
        if profile:
            return {
                'bio': profile.bio,
                'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
                'unique_id': profile.unique_id,
            }
        return None

       
