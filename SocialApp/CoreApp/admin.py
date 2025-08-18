from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, reverse
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

    # Field for searching
    search_fields = ('username', 'email', 'phone_number', 'first_name', 'last_name')

    # Field for filtering
    list_filter = ('is_active', 'created_at')

    # Profile picture preview
    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 50%;">',
                obj.profile_picture.url
            )
        return "No Image"

    profile_picture_preview.short_description = "Profile Picture"

    # Average score calculation
    def average_score(self, obj):
        stats = obj.get_user_average_score()
        return stats.get('average_score', 0)

    average_score.short_description = "Average Score"
    readonly_fields = ('average_score', 'created_at')

    # Fields to be displayed in the detail view
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

    # Allow editing of related objects in the admin panel
    filter_horizontal = ('followers', 'following')

    # Options to prevent automatic updates
    readonly_fields = ('created_at',)

    # Optional actions
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

    # total points in the admin panel
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

    # Fields to be displayed in the list view
    list_display = ('id', 'follower_username', 'following_username', 'created_at')

    # Field for searching
    search_fields = ('follower__username', 'following__username')

    # Field for filtering
    list_filter = ('created_at',)

    # Fields to be displayed in the detail view
    fieldsets = (
        ("Follow Details", {
            'fields': ('follower', 'following', 'created_at')
        }),
    )

    # Read-only fields
    readonly_fields = ('created_at',)

    

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """
    Admin panel customization for the Comment model.
    """

    # Fields to be displayed in the list view
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

    # Field for searching
    search_fields = ('user_profile__username', 'profile_commented_on__username', 'content')

    # Field for filtering
    list_filter = ('category', 'is_positive', 'is_anonymous', 'created_at')

    # Allow editing of related objects in the admin panel
    filter_horizontal = ('likes', 'dislikes')

    # Fields to be displayed in the detail view
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

    # Read-only fields
    readonly_fields = ('created_at',)

    

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']  # Fields to be displayed in the admin panel
    search_fields = ['name']  # Field for searching

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.order_by('name')  # Order by name
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

from django.contrib import admin
from django.db import models

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """
    Admin customization for the Report model.
    """
    
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

    search_fields = (
        'user_reporting__username',
        'reported_comment__content',
        'reported_comment__user_profile__username',
        'reported_profile__user__username',
        'reason',
    )

    list_filter = (
        'report_type',
        'is_reviewed',
        'created_at',
    )

    readonly_fields = (
        'created_at',
        'reported_comment_content',
        'reported_comment_profile',
        'commented_on_profile'
    )

    def reported_comment_content(self, obj):
        if obj.reported_comment:
            return f"{obj.reported_comment.content[:50]}..."
        return "N/A"

    reported_comment_content.short_description = "Reported comment content"

    def reported_comment_profile(self, obj):
        if obj.reported_comment and obj.reported_comment.user_profile:
            return f"Profile of {obj.reported_comment.user_profile.user.username}"
        return "N/A"

    reported_comment_profile.short_description = "Owner of the reported comment"

    def reported_profile(self, obj):
        if obj.reported_profile:
            return f"Profile of {obj.reported_profile.user.username}"
        return "N/A"

    reported_profile.short_description = "Reported profile"

    def commented_on_profile(self, obj):
        if obj.reported_comment and obj.reported_comment.profile_commented_on:
            return f"Profile of {obj.reported_comment.profile_commented_on.user.username}"
        return "N/A"

    commented_on_profile.short_description = "Profile of the commented-on post"

    def report_type_display(self, obj):
        return obj.get_report_type_display()

    report_type_display.short_description = "Report Type"

    fieldsets = (
        ("Report Information", {
            'fields': (
                'user_reporting',
                'report_type',
                'reported_comment_content',
                'reported_comment_profile',
                'reported_profile',
                'reason',
                'created_at',
                'is_reviewed',
            )
        }),
    )

    actions = ['mark_as_reviewed', 'delete_reported_comment']

    def mark_as_reviewed(self, request, queryset):
        updated = queryset.update(is_reviewed=True)
        self.message_user(request, f"{updated} report(s) marked as reviewed.")
    
    mark_as_reviewed.short_description = "İncelendi olarak işaretle"

    def delete_reported_comment(self, request, queryset):
        """Delete the reported comment associated with the selected reports."""
        for report in queryset:
            if report.reported_comment:
                report.reported_comment.delete()
                self.message_user(request, f"Comment from report ID {report.id} deleted.")
        return None

    delete_reported_comment.short_description = "Delete reported comment"

    def delete_reported_comment_action(self, request, object_id):
        """
        Custom admin action to delete the reported comment associated with a report.
        """
        try:
            # Fetch the report object
            report = self.get_object(request, object_id)
            if not report:
                self.message_user(request, "Report not found.", level="error")
                return redirect('admin:%s_%s_changelist' % (self.model._meta.app_label, self.model._meta.model_name))

            # Delete the reported comment if it exists
            if report.reported_comment:
                report.reported_comment.delete()
                self.message_user(request, "Reported comment has been successfully deleted.")
            else:
                self.message_user(request, "No reported comment found to delete.", level="error")

        except Exception as e:
            self.message_user(request, f"An error occurred: {e}", level="error")

        # Redirect back to the change view of the report
        return redirect('admin:%s_%s_change' % (self.model._meta.app_label, self.model._meta.model_name), object_id=object_id)


    def get_urls(self):
        """
        Add a custom URL for deleting a reported comment.
        """
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:object_id>/delete-comment/',
                self.admin_site.admin_view(self.delete_reported_comment_action),
                name='delete_reported_comment',
            ),
        ]
        return custom_urls + urls


    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Override the change view to add a custom delete button for the reported comment.
        """
        extra_context = extra_context or {}
        try:
            # Fetch the report object
            report = self.get_object(request, object_id)

            # If the report and the reported comment exist, add a delete button
            if report and report.reported_comment:
                delete_url = reverse('admin:delete_reported_comment', args=[object_id])
                extra_context['delete_comment_button'] = format_html(
                    '<a class="button" href="{}">Delete Reported Comment</a>', delete_url
                )
            else:
                extra_context['delete_comment_button'] = None

        except Exception as e:
            self.message_user(request, f"An error occurred: {e}", level="error")

        return super().change_view(request, object_id, form_url, extra_context)




