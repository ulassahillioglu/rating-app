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
from django.utils.timezone import now
from django.db.models import Count, Q, F,Sum

from django.core.exceptions import ValidationError
import re

def validate_phone_number(value):
    """
    Telefon numarasını doğrular.
    - 10 haneli olmalı
    - Sadece sayılardan oluşmalı
    - Başında '0' olmamalı
    """
    regex = r"^\d{10}$"
    if not re.match(regex, value):
        raise ValidationError("Telefon numarası 10 haneli olmalı ve yalnızca sayılardan oluşmalıdır.")
    
    if value.startswith("0"):
        raise ValidationError("Telefon numarası başında '0' olmamalıdır.")


def max_file_size_validator(file):
    limit_bytes = 2 * 1024 * 1024  # 2 MB
    if file.size > limit_bytes:
        limit_mb = limit_bytes // (1024 * 1024)
        raise ValidationError(f"Yüklenebilecek max dosya boyutu {limit_mb} MB. Lütfen daha düşük boyutlu bir dosya yükleyin.")

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
    score = models.PositiveIntegerField(null=True,blank=True) 
    USERNAME_FIELD = "phone_number"

    # objects = UserProfileManager()
    
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    class Meta:
        db_table = 'Core_Users'
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        
    def generate_otp(self):
        """6 haneli rastgele bir OTP üretir."""
        self.otp = ''.join(random.choices('0123456789', k=6))
        self.otp_expiry = now() + timedelta(minutes=5)  # OTP 5 dakika geçerli
        self.save()
        return self.otp,self.otp_expiry
    
    
    def get_category_comment_stats(self):
        # Tüm kategorileri veritabanından alın
        all_categories = Category.objects.all()  # Category modelinin mevcut olduğunu varsayıyoruz

        # Kategorilere göre yorum puanlarının toplamını ve yorum sayısını al
        category_stats = Comment.objects.filter(profile_commented_on=self).values('category') \
            .annotate(
                total_score=Sum('score'),
                comment_count=Count('id')
            )

        # Tüm kategorileri 0 puanla başlat
        stats = {category.id: {'score': 0} for category in all_categories}

        # Yorum istatistiklerine dayalı olarak puanları güncelle
        for stat in category_stats:
            category_id = stat['category']
            total_score = stat['total_score']
            comment_count = stat['comment_count']

            # Yorum sayısı varsa ortalama puan hesapla
            if comment_count > 0:
                score = total_score / comment_count  # Ortalama puan
            else:
                score = 0

            stats[category_id] = {'score': round(score, 2)}  # Puanı yuvarlayarak kaydet

        return stats


    def get_user_average_score(self):
        stats = self.get_category_comment_stats()

        total_score = 0
        category_count = 0

        # Tüm kategorilerin toplam puanını al
        for category_id, category_stats in stats.items():
            total_score += category_stats['score']
            category_count += 1

        # Genel puan (ortalama) hesapla
        if category_count > 0:
            avg_score = round(total_score / category_count, 2)
        else:
            avg_score = 0

        return {
            'average_score': avg_score
        }
    def save(self, *args, **kwargs):
        if not self.profile_picture:
            self.profile_picture = 'images/profile-pics/keyd.jpg'
        super().save(*args, **kwargs)

        
    # def clean(self):
    #     super().clean()
    #     phone_regex(self.phone_number)  # Telefon numarasını doğrula



class Follow(models.Model):
    follower = models.ForeignKey(
        UserProfile,  # Takip eden kullanıcı
        on_delete=models.CASCADE,
        related_name='follower_relationships'
    )
    following = models.ForeignKey(
        UserProfile,  # Takip edilen kullanıcı
        on_delete=models.CASCADE,
        related_name='following_relationships'
    )
    created_at = models.DateTimeField(auto_now_add=True)  # Takip tarihini kaydeder

    # Takip eden kullanıcının adını döndürür
    def follower_username(self):
        return self.follower.username

    # Takip edilen kullanıcının adını döndürür
    def following_username(self):
        return self.following.username
    
    class Meta:
        db_table = 'Core_Follows'
        unique_together = ('follower', 'following')  # Aynı ilişkiyi birden fazla kez eklemeyi engeller

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
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='comments', default=1)  # Yeni kategori alanı
    is_positive = models.BooleanField(default=True)  # Pozitif/negatif yorumu belirle
    score = models.PositiveIntegerField(default=0)
    
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
        return f"{self.user.user.username} tarafından girilen talep"
    
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
        verbose_name='Rapor Eden Kullanıcı'
    )
    reported_comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='reports',
        blank=True,
        null=True,
        verbose_name='Şikayet Edilen Yorum'
    )
    reported_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='profile_reports',
        blank=True,
        null=True,
        verbose_name='Şikayet Edilen Profil'
    )
    report_type = models.CharField(
        max_length=10,
        choices=REPORT_TYPE_CHOICES,
        verbose_name='Şikayet Türü'
    )
    reason = models.TextField(max_length=255, blank=False, null=False, verbose_name='Gerekçe')
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
