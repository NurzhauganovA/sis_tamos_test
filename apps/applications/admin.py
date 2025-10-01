from django.contrib import admin
from .models import (
    ServiceProvider,
    ApplicationType,
    Application,
    ApplicationFile,
    ApplicationComment,
    ApplicationStatusHistory
)


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'bin_or_iin', 'service_type', 'responsible_full_name', 'responsible_phone', 'responsible_email', 'campus', 'subdivision1', 'subdivision2', 'is_active', 'created_at']
    list_filter = ['service_type', 'is_active', 'created_at']
    search_fields = ['name', 'bin_or_iin', 'service_type']
    ordering = ['-created_at']


@admin.register(ApplicationType)
class ApplicationTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'service_provider', 'is_active']
    list_filter = ['service_provider', 'is_active']
    search_fields = ['name', 'description']


class ApplicationFileInline(admin.TabularInline):
    model = ApplicationFile
    extra = 0
    readonly_fields = ['uploaded_at', 'uploaded_by']


class ApplicationCommentInline(admin.TabularInline):
    model = ApplicationComment
    extra = 0
    readonly_fields = ['created_at', 'author']


class ApplicationStatusHistoryInline(admin.TabularInline):
    model = ApplicationStatusHistory
    extra = 0
    readonly_fields = ['changed_at', 'changed_by']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'subject', 'campus', 'subdivision1', 'subdivision2', 'applicant', 'student_id',
        'student_class_num', 'student_class_liter', 'application_type', 'status', 'created_at'
    ]
    list_filter = ['status', 'application_type', 'created_at']
    search_fields = ['subject', 'description', 'applicant__fio']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'processed_at', 'completed_at']

    inlines = [ApplicationFileInline, ApplicationCommentInline, ApplicationStatusHistoryInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('applicant', 'campus', 'subdivision1', 'subdivision2', 'student_id', 'student_class_num', 'student_class_liter', 'application_type', 'subject', 'description')
        }),
        ('Статус и обработка', {
            'fields': ('status', 'assigned_to', 'rejection_reason')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at', 'processed_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ApplicationFile)
class ApplicationFileAdmin(admin.ModelAdmin):
    list_display = ['application', 'original_name', 'uploaded_by', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['original_name', 'application__subject']


@admin.register(ApplicationComment)
class ApplicationCommentAdmin(admin.ModelAdmin):
    list_display = ['application', 'author', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['comment', 'application__subject']


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['application', 'old_status', 'new_status', 'changed_by', 'changed_at']
    list_filter = ['old_status', 'new_status', 'changed_at']
    search_fields = ['application__subject', 'reason']