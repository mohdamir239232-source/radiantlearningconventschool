from django.db import models
from students.models import ClassModel

class FeeParticular(models.Model):
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'),
        ('yearly', 'Yearly'),
        ('once', 'Once')
    ]
    
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"

class FeeAmountSlab(models.Model):
    class_model = models.ForeignKey(ClassModel, on_delete=models.CASCADE)
    academic_month = models.CharField(max_length=50, choices=[
        ('jan', 'January'),
        ('feb', 'February'),
        ('mar', 'March'),
        ('apr', 'April'),
        ('may', 'May'),
        ('jun', 'June'),
        ('jul', 'July'),
        ('aug', 'August'),
        ('sep', 'September'),
        ('oct', 'October'),
        ('nov', 'November'),
        ('dec', 'December')
    ])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['class_model']
        unique_together = ('class_model', 'academic_month')
        
    def __str__(self):
        return f"{self.class_model.name} - {self.get_academic_month_display()}"
    
    def get_total_amount(self):
        return sum(item.amount for item in self.particulars.all())

class FeeAmountSlabParticular(models.Model):
    fee_slab = models.ForeignKey(FeeAmountSlab, on_delete=models.CASCADE, related_name='particulars')
    particular = models.ForeignKey(FeeParticular, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        ordering = ['particular__name']
        unique_together = ('fee_slab', 'particular')
    
    def __str__(self):
        return f"{self.fee_slab} - {self.particular.name}"

class FeeDiscount(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount')
    ]
    
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name


class StudentFeeDiscount(models.Model):
    """Track discounts applied to student fees"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount')
    ]
    
    from students.models import Student
    
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='fee_discounts')
    particular = models.ForeignKey(FeeParticular, on_delete=models.CASCADE)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Calculated discount amount
    original_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Fee amount before discount
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Fee amount after discount
    remarks = models.TextField(blank=True, null=True)
    applied_by = models.CharField(max_length=100, blank=True, null=True)
    applied_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-applied_on']
        unique_together = ('student', 'particular')
    
    def __str__(self):
        return f"{self.student.name} - {self.particular.name} - {self.discount_amount}"

