# coreapp/models.py
from django.conf import settings
from django.db import models
from django.contrib.auth.models import (
    User,AbstractBaseUser,BaseUserManager,PermissionsMixin)
import random, re, string
from django.core.exceptions import ValidationError
from django.core.validators import (
    RegexValidator,
    EmailValidator,
    FileExtensionValidator
)
from datetime import datetime, timedelta
from django.db.models import JSONField
from django.utils.timezone import now
from django.db.models import Count, Q, F,Sum

from django.core.exceptions import ValidationError
import re

def validate_phone_number(value):
    """
    Validate the phone number.
    - Must be 10 digits long
    - Must consist of only numbers
    - Must not start with '0'
    """
    regex = r"^\d{10}$"
    if not re.match(regex, value):
        raise ValidationError("Phone number must be 10 digits long and consist of only numbers.")

    if value.startswith("0"):
        raise ValidationError("Phone number must not start with '0'.")


def max_file_size_validator(file):
    limit_bytes = 2 * 1024 * 1024  # 2 MB
    if file.size > limit_bytes:
        limit_mb = limit_bytes // (1024 * 1024)
        raise ValidationError(f"Maximum file size allowed is {limit_mb} MB. Please upload a smaller file.")

# Function to generate a random string (letters and digits)
def generate_random_unique_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))
      

class UserProfile(models.Model):
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(
        unique=True, max_length=10,null=False,blank=False,validators=[validate_phone_number]
    )
    followers = models.ManyToManyField('self', symmetrical=False, related_name='followed_by', blank=True)
    following = models.ManyToManyField('self', symmetrical=False, related_name='follows', blank=True)
    username = models.CharField(max_length=20, db_index=True, unique=True)
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    birth_date = models.DateField(default=datetime(1994, 1, 1).date())
    unique_id = models.CharField(
        max_length=10,
        unique=True,
        default=generate_random_unique_id,
        blank=True,
        null=False
    )
    email = models.EmailField(max_length=50,unique=True,validators=[EmailValidator()],blank=False,null=False)
    first_name = models.CharField(max_length=50,blank=False,null=False)
    last_name = models.CharField(max_length=50,blank=False,null=False)
    profile_picture = models.ImageField(
        upload_to='images/profile-pics/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']),
            max_file_size_validator,  # Limit file size to 2 MB
        ],
        default='images/profile-pics/default.jpg'
    )
    otp = models.CharField(max_length=6)
    otp_expiry = models.DateTimeField(blank=True,null=True)
    max_otp_try = models.PositiveIntegerField(default=settings.MAX_OTP_TRY)
    otp_max_out = models.DateTimeField(blank=True,null=True)
    is_active = models.BooleanField(default=False)
    category_scores = JSONField(default=dict, blank=True, null=True)
    USERNAME_FIELD = "phone_number"

    # objects = UserProfileManager()
    
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    class Meta:
        db_table = 'Core_Users'
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        
    def generate_otp(self):
        """Generate a random 6-digit OTP."""
        self.otp = ''.join(random.choices('0123456789', k=6))
        self.otp_expiry = now() + timedelta(minutes=5)  # OTP is valid for 5 minutes
        self.save()
        return self.otp, self.otp_expiry


    def get_category_comment_stats(self):
        all_categories = Category.objects.all()
        
        # Initialize stats for all categories
        stats = {category.id: {'score': 0, 'count': 0} for category in all_categories}
        
        # Fetch all comments for the profile being commented on
        comments = Comment.objects.filter(profile_commented_on=self)
        
        for comment in comments:
            if hasattr(comment, 'category_scores') and comment.category_scores:
                # New format: Use the category_scores field (JSON field)
                category_scores = comment.category_scores
            else:
                # Old format: Use the separate category and score fields
                category_scores = {str(comment.category.id): comment.score} if comment.category and comment.score else {}
            
            # Update stats for each category based on category_scores
            for category_id, score in category_scores.items():
                if int(category_id) in stats:
                    stats[int(category_id)]['score'] += score
                    stats[int(category_id)]['count'] += 1

        # Calculate average score for each category
        for category_id, data in stats.items():
            if data['count'] > 0:
                avg_score = data['score'] / data['count']
                stats[category_id]['avg_score'] = round(avg_score, 2)
            else:
                stats[category_id]['avg_score'] = 0  # No comments for this category, so set avg_score to 0

        return stats






    def get_user_average_score(self):
        stats = self.get_category_comment_stats()

        total_score = 0
        category_count = 0

        # Calculate total score and number of categories
        for category_id, category_stats in stats.items():
            total_score += category_stats['avg_score']
            category_count += 1

        # Calculate average score (overall score)
        if category_count > 0:
            avg_score = round(total_score / category_count, 2)
        else:
            avg_score = 0

        return {'average_score': avg_score}


    def save(self, *args, **kwargs):
        if not self.profile_picture:
            self.profile_picture = 'images/profile-pics/keyd.jpg'
        super().save(*args, **kwargs)

        
    # def clean(self):
    #     super().clean()
    #     phone_regex(self.phone_number)  # Telefon numarasını doğrula



class Follow(models.Model):
    follower = models.ForeignKey(
        UserProfile,  # Following user
        on_delete=models.CASCADE,
        related_name='follower_relationships'
    )
    following = models.ForeignKey(
        UserProfile,  # Followed user
        on_delete=models.CASCADE,
        related_name='following_relationships'
    )
    created_at = models.DateTimeField(auto_now_add=True)  # Follow date

    # Returns the username of the following user
    def follower_username(self):
        return self.follower.username

    # Returns the username of the followed user
    def following_username(self):
        return self.following.username
    
    class Meta:
        db_table = 'Core_Follows'
        unique_together = ('follower', 'following')  # Prevents adding the same relationship multiple times

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'Core_Categories'
        
class Comment(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='comments')
    profile_commented_on = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='comments_received')
    content = models.TextField(max_length=255, blank=False, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_anonymous = models.BooleanField(default=True)
    likes = models.ManyToManyField(UserProfile, related_name='liked_comments', blank=True)
    dislikes = models.ManyToManyField(UserProfile, related_name='disliked_comments', blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='comments', default=1)  # new category field
    is_positive = models.BooleanField(default=True)  # Determine positive/negative comment
    score = models.PositiveIntegerField(default=0)
    category_scores = JSONField(default=dict)
    
    def __str__(self):
        return f"Comment by {self.user_profile.user.username} on {self.profile_commented_on.user.username}'s profile"
    
    def clean(self):
        if self.likes.filter(id__in=self.dislikes.values_list('id', flat=True)).exists():
            raise ValidationError("A user cannot both like and dislike the same comment.")
    
    class Meta:
        db_table = 'Core_Comments'

class UserInquiry(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='user_inquiries')
    subject = models.CharField(max_length=255, blank=False, null=True)
    content = models.TextField(max_length=255, blank=False, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_answered = models.BooleanField(default=False)
    

    def __str__(self):
        return f"Request submitted by {self.user.user.username}"
    
    def save(self, *args, **kwargs):
        self.subject = self.subject.strip()
        self.content = self.content.strip()
        super().save(*args, **kwargs)
        
    def clean(self):
        if self.subject == "" or self.content == "":
            raise ValidationError("Subject and content fields must not be empty.")
        if len(self.subject) > 255 or len(self.content) > 255:
            raise ValidationError("Subject and content fields must not exceed 255 characters.")
        if self.user.user.is_active is False:
            raise ValidationError("User is not active.")
        # if self.user.max_inquiry_try > 0 and self.user.user_inquiries.filter(created_at__gte=now() - timedelta(minutes=5)).count() >= self.user.max_inquiry_try:
        #     raise ValidationError("User has reached the maximum number of inquiries.")
        if self.user.otp_expiry is not None and self.user.otp_expiry > now():
            raise ValidationError("User has an active OTP.")
    
    class Meta:
        db_table = 'Core_UserInquiries'
        
    


class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ('comment', 'Comment'),
        ('profile', 'Profile'),
    ]

    user_reporting = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='reports_made',
        verbose_name='Reporting User'
    )
    reported_comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='reports',
        blank=True,
        null=True,
        verbose_name='Reported Comment'
    )
    reported_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='profile_reports',
        blank=True,
        null=True,
        verbose_name='Reported Profile'
    )
    report_type = models.CharField(
        max_length=10,
        choices=REPORT_TYPE_CHOICES,
        verbose_name='Report Type'
    )
    reason = models.TextField(max_length=255, blank=False, null=False, verbose_name='Reason')
    created_at = models.DateTimeField(auto_now_add=True)
    is_reviewed = models.BooleanField(default=False, verbose_name='Reviewed Status')

    def clean(self):
        if not self.reported_comment and not self.reported_profile:
            raise ValidationError("A report must be associated with either a comment or a profile.")
        if self.reported_comment and self.reported_profile:
            raise ValidationError("A report can only be associated with either a comment or a profile, not both.")

    def __str__(self):
        if self.reported_comment:
            return f"Report on Comment by {self.reported_comment.user_profile.user.username}"
        elif self.reported_profile:
            return f"Report on Profile of {self.reported_profile.user.username}"
        return "Invalid Report"

    class Meta:
        db_table = 'Core_Reports'
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
