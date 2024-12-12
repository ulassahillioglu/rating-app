from django.contrib import admin
from django.utils.html import format_html
from .models import Report, UserProfile, Category, Comment, Follow,UserInquiry

from django import forms
from .models import UserProfile, User
from django.utils.html import format_html
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.apps import apps

def create_support_group():
    # Check if the group already exists
    group, created = Group.objects.get_or_create(name='Customer Support')

    # Get content types for the models
    user_inquiry_content_type = ContentType.objects.get_for_model(UserInquiry)
    report_content_type = ContentType.objects.get_for_model(Report)

    # Get permissions for 'view' actions
    view_user_inquiry_permission = Permission.objects.get(
        content_type=user_inquiry_content_type,
        codename='view_userinquiry'
    )
    view_report_permission = Permission.objects.get(
        content_type=report_content_type,
        codename='view_report'
    )
    
    # Add permissions to the group
    group.permissions.add(view_user_inquiry_permission, view_report_permission)
    
    for user in group.user_set.all():
        user.is_staff = True
        user.save()
    print("Customer Support group created with appropriate permissions.")


class UserProfileForm(forms.ModelForm):
    # Display followers as a multiple select field
    followers = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'vSelect2'}),
        label="Followers"
    )
    # Display following as a multiple select field
    following = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'vSelect2'}),
        label="Following"
    )

    class Meta:
        model = UserProfile
        fields = '__all__'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    UserProfile modeli için admin paneli özelleştirmesi.
    """

    # Listede gösterilecek alanlar
    list_display = (
        'id',
        'username',
        'email',
        'phone_number',
        'is_active',
        'profile_picture_preview',
        'created_at',
        'average_score',
    )

    # Arama yapılabilir alanlar
    search_fields = ('username', 'email', 'phone_number', 'first_name', 'last_name')

    # Filtreleme yapılabilir alanlar
    list_filter = ('is_active', 'created_at')

    # Profil resmi önizleme
    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 50%;">',
                obj.profile_picture.url
            )
        return "No Image"

    profile_picture_preview.short_description = "Profile Picture"

    # Ortalama skor hesaplama
    def average_score(self, obj):
        stats = obj.get_user_average_score()
        return stats.get('average_score', 0)

    average_score.short_description = "Average Score"
    readonly_fields = ('average_score', 'created_at')

    # Detay sayfasında gösterilecek alanlar
    fieldsets = (
        ("Basic Information", {
            'fields': ('username', 'email', 'phone_number', 'first_name', 'last_name', 'birth_date', 'bio')
        }),
        ("Profile Picture", {
            'fields': ('profile_picture',)
        }),
        ("OTP Information", {
            'fields': ('otp', 'otp_expiry', 'max_otp_try', 'otp_max_out')
        }),
        ("Status", {
            'fields': ('is_active', 'created_at')
        }),
        ("Unique Identifiers", {
            'fields': ('unique_id',)
        }),
        ("Relationships", {
            'fields': ('followers', 'following')
        })
    )

    form = UserProfileForm

    # İlgili nesnelerin admin panelinde düzenlenmesini sağla
    filter_horizontal = ('followers', 'following')

    # Otomatik güncellemeleri engelleme seçenekleri
    readonly_fields = ('created_at',)

    # İsteğe bağlı aksiyonlar ekle
    actions = ["activate_users", "deactivate_users"]

    def activate_users(self, request, queryset):
        """Seçilen kullanıcıları etkinleştir."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated successfully.")

    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        """Seçilen kullanıcıları devre dışı bırak."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated successfully.")

    deactivate_users.short_description = "Deactivate selected users"

    # Admin panelinde toplam sayılar
    def changelist_view(self, request, extra_context=None):
        """Ekstra bağlam ekle."""
        extra_context = extra_context or {}
        extra_context['total_users'] = UserProfile.objects.count()
        extra_context['active_users'] = UserProfile.objects.filter(is_active=True).count()
        return super().changelist_view(request, extra_context=extra_context)

    # Admin paneli başlıklarını özelleştirme
    admin.site.site_header = "User Management Panel"
    admin.site.site_title = "Admin Portal"
    admin.site.index_title = "Welcome to the User Administration"




@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """
    Follow modeli için admin paneli özelleştirmesi.
    """

    # Listede gösterilecek alanlar
    list_display = ('id', 'follower_username', 'following_username', 'created_at')

    # Arama yapılabilir alanlar
    search_fields = ('follower__username', 'following__username')

    # Filtreleme yapılabilir alanlar
    list_filter = ('created_at',)

    # Detay sayfasında gösterilecek alanlar
    fieldsets = (
        ("Follow Details", {
            'fields': ('follower', 'following', 'created_at')
        }),
    )

    # Sadece okunabilir alanlar
    readonly_fields = ('created_at',)

    

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """
    Comment modeli için admin paneli özelleştirmesi.
    """

    # Listede gösterilecek alanlar
    list_display = (
        'id',
        'user_profile',
        'profile_commented_on',
        'content',
        'category',
        'score',
        'is_positive',
        'is_anonymous',
        'created_at',
    )

    # Arama yapılabilir alanlar
    search_fields = ('user_profile__username', 'profile_commented_on__username', 'content')

    # Filtreleme yapılabilir alanlar
    list_filter = ('category', 'is_positive', 'is_anonymous', 'created_at')

    # İlgili nesnelerin admin panelinde düzenlenmesini sağla
    filter_horizontal = ('likes', 'dislikes')

    # Detay sayfasında gösterilecek alanlar
    fieldsets = (
        ("Comment Details", {
            'fields': (
                'user_profile',
                'profile_commented_on',
                'content',
                'category',
                'score',
                'is_positive',
                'is_anonymous',
                'created_at',
            )
        }),
        ("Reactions", {
            'fields': ('likes', 'dislikes')
        }),
    )

    # Sadece okunabilir alanlar
    readonly_fields = ('created_at',)

    

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']  # Admin panelinde hangi alanların görüneceğini seçin
    search_fields = ['name']  # Arama yapılabilir alanlar

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.order_by('name')  # İsim sırasına göre sıralama
        return queryset

@admin.register(UserInquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'subject', 'content', 'created_at','is_answered']
    search_fields = ['user__username', 'content']
    list_filter = ['created_at']
    fieldsets = (
        ("Inquiry Details", {
            'fields': (
                'user',
                'subject',
                'content'
                
    )}),
    )
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """
    Admin customization for the Report model.
    """
    
    # List of fields to display in the list view
    list_display = (
        'id',
        'user_reporting',
        'report_type',
        'reported_comment_content',
        'reported_comment_profile',
        'commented_on_profile',
        'reported_profile',
        'reason',
        'created_at',
        'is_reviewed',
    )

    # Fields that can be used for searching in the admin panel
    search_fields = (
        'user_reporting__username',
        'reported_comment__content',
        'reported_comment__user_profile__username',  # Search by profile username
        'reported_profile__user__username',
        'reason',
    )

    # Fields that can be used for filtering in the list view
    list_filter = (
        'report_type',
        'is_reviewed',
        'created_at',
    )

    # Fields to show as read-only in the detail view
    readonly_fields = (
        'created_at',
        'reported_comment_content',  # Add this field to the readonly section
        'reported_comment_profile',  # Add this field to the readonly section
        'commented_on_profile'
    )

    # Display the content of the reported comment
    def reported_comment_content(self, obj):
        if obj.reported_comment:
            return f"{obj.reported_comment.content[:50]}..."  # Show the full content of the comment
        return "N/A"

    reported_comment_content.short_description = "Rapor edilen yorum içeriği"

    # Display the profile of the user who made the comment
    def reported_comment_profile(self, obj):
        if obj.reported_comment and obj.reported_comment.user_profile:
            return f"Profile of {obj.reported_comment.user_profile.user.username}"
        return "N/A"

    reported_comment_profile.short_description = "Yorumun sahibi"

    def reported_profile(self, obj):
        if obj.reported_profile:
            return f"Profile of {obj.reported_profile.user.username}"
        return "N/A"

    reported_profile.short_description = "Rapor edilen Profil"
    
    def commented_on_profile(self, obj):
        if obj.reported_comment and obj.reported_comment.profile_commented_on:
            return f"Profile of {obj.reported_comment.profile_commented_on.user.username}"
        return "N/A"

    commented_on_profile.short_description = "Yorumun yapıldığı profil"
    # Customize the detail view to show the comment content and the comment's profile
    def report_type_display(self, obj):
        return obj.get_report_type_display()

    report_type_display.short_description = "Rapor Türü"
    
    fieldsets = (
        ("Rapor Bilgileri", {
            'fields': (
                'user_reporting',
                'report_type',
                'reported_comment_content',  # Add this field to display in the detail view
                'reported_comment_profile',  # Show profile of the user who made the comment
                'reported_profile',
                'reason',
                'created_at',
                'is_reviewed',
            )
        }),
    )

    # Custom actions to mark reports as reviewed
    actions = ['mark_as_reviewed']

    def mark_as_reviewed(self, request, queryset):
        """Mark selected reports as reviewed."""
        updated = queryset.update(is_reviewed=True)
        self.message_user(request, f"{updated} report(s) marked as reviewed.")
    
    mark_as_reviewed.short_description = "İncelendi olarak işaretle"


