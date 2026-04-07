from django.contrib import admin
from fee.models import FeeParticular, FeeAmountSlab, FeeDiscount, FeeAmountSlabParticular, StudentFeeDiscount

@admin.register(FeeParticular)
class FeeParticularAdmin(admin.ModelAdmin):
    list_display = ('name', 'frequency', 'is_active', 'created_at')
    list_filter = ('is_active', 'frequency', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)

class FeeAmountSlabParticularInline(admin.TabularInline):
    model = FeeAmountSlabParticular
    extra = 1

@admin.register(FeeAmountSlab)
class FeeAmountSlabAdmin(admin.ModelAdmin):
    list_display = ('class_model', 'academic_month', 'is_active', 'created_at')
    list_filter = ('is_active', 'class_model', 'academic_month')
    search_fields = ('class_model__name',)
    ordering = ('class_model', 'academic_month')
    inlines = [FeeAmountSlabParticularInline]

@admin.register(FeeDiscount)
class FeeDiscountAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_type', 'discount_value', 'is_active', 'created_at')
    list_filter = ('is_active', 'discount_type', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(StudentFeeDiscount)
class StudentFeeDiscountAdmin(admin.ModelAdmin):
    list_display = ('student', 'particular', 'discount_type', 'discount_value', 'discount_amount', 'applied_on')
    list_filter = ('discount_type', 'applied_on', 'student')
    search_fields = ('student__name', 'particular__name')
    ordering = ('-applied_on',)
    readonly_fields = ('applied_on', 'discount_amount', 'final_amount')

