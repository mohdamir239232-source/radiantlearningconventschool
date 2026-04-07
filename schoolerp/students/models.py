import secrets
import string

from django.conf import settings
from django.db import models
from django.db.models import Max


class AcademicSession(models.Model):
    name = models.CharField(max_length=50, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.name


class ClassModel(models.Model):
    name = models.CharField(max_length=50)
    section = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'section']
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'

    def __str__(self):
        if self.section:
            return f"{self.name} - {self.section}"
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    classes = models.ManyToManyField(ClassModel, related_name='subjects', blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Student(models.Model):
    admission_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    name = models.CharField(max_length=100)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    category = models.CharField(max_length=50, null=True, blank=True)
    fee_category = models.CharField(max_length=50, null=True, blank=True)
    student_status = models.CharField(max_length=10, null=True, blank=True)
    pen_number = models.CharField(max_length=30, unique=True, null=True, blank=True)
    aadhar_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    apaar_id = models.CharField(max_length=30, unique=True, null=True, blank=True)
    parents_detail = models.TextField(null=True, blank=True)
    contact_detail = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    state = models.CharField(max_length=60, null=True, blank=True)
    district = models.CharField(max_length=60, null=True, blank=True)
    pin_code = models.CharField(max_length=10, null=True, blank=True)
    nationality = models.CharField(max_length=40, null=True, blank=True, default='Indian')
    father_name = models.CharField(max_length=100, null=True, blank=True)
    mother_name = models.CharField(max_length=100, null=True, blank=True)
    local_guardian = models.CharField(max_length=100, null=True, blank=True)
    father_occupation = models.CharField(max_length=100, null=True, blank=True)
    mother_occupation = models.CharField(max_length=100, null=True, blank=True)
    father_qualification = models.CharField(max_length=100, null=True, blank=True)
    mother_qualification = models.CharField(max_length=100, null=True, blank=True)
    father_aadhar = models.CharField(max_length=20, null=True, blank=True)
    mother_aadhar = models.CharField(max_length=20, null=True, blank=True)
    father_mobile = models.CharField(max_length=20, null=True, blank=True)
    mother_mobile = models.CharField(max_length=20, null=True, blank=True)
    last_school_name = models.CharField(max_length=150, null=True, blank=True)
    previous_class = models.CharField(max_length=20, null=True, blank=True)
    last_school_address = models.TextField(null=True, blank=True)
    student_class = models.CharField(max_length=20)
    section = models.CharField(max_length=10)
    roll_no = models.IntegerField(null=True, blank=True)
    student_login_id = models.CharField(max_length=30, unique=True, blank=True, null=True)
    student_password = models.CharField(max_length=30, blank=True, null=True)
    photo = models.FileField(upload_to='students/photos/', null=True, blank=True)
    admission_date = models.DateField(null=True, blank=True)
    session = models.ForeignKey(AcademicSession, on_delete=models.SET_NULL, null=True, blank=True)
    transport_required = models.BooleanField(default=False)
    transport_route = models.ForeignKey('transport.VehicleRoute', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    transport_village = models.CharField(max_length=120, null=True, blank=True)
    transport_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    subjects = models.ManyToManyField(Subject, related_name='students', blank=True)

    class Meta:
        ordering = ['name']

    ADMISSION_PREFIX = 'RLCS'

    @classmethod
    def get_next_admission_number(cls):
        latest = cls.objects.filter(admission_number__startswith=cls.ADMISSION_PREFIX).order_by('-id').first()
        if not latest or not latest.admission_number:
            return f'{cls.ADMISSION_PREFIX}001'

        raw = latest.admission_number.replace(cls.ADMISSION_PREFIX, '')
        try:
            next_value = int(raw) + 1
        except ValueError:
            next_value = cls.objects.count() + 1
        return f'{cls.ADMISSION_PREFIX}{next_value:03d}'

    @classmethod
    def get_next_student_login_id(cls):
        seed = cls.objects.count() + 1
        while True:
            candidate = f'STU{seed:05d}'
            if not cls.objects.filter(student_login_id=candidate).exists():
                return candidate
            seed += 1

    @staticmethod
    def generate_password(length=8):
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def get_next_roll_no(self):
        if not self.student_class or not self.section:
            return 1
        max_roll = (
            Student.objects
            .filter(student_class=self.student_class, section=self.section)
            .exclude(pk=self.pk)
            .aggregate(max_roll=Max('roll_no'))
            .get('max_roll')
        )
        return (max_roll or 0) + 1

    def save(self, *args, **kwargs):
        if not self.admission_number:
            self.admission_number = self.get_next_admission_number()

        if not self.roll_no:
            self.roll_no = self.get_next_roll_no()

        if not self.student_login_id:
            self.student_login_id = self.get_next_student_login_id()

        if not self.student_password:
            self.student_password = self.generate_password()

        if self.transport_required and self.transport_route:
            if self.transport_amount in (None, ''):
                self.transport_amount = self.transport_route.fare_amount
        elif not self.transport_required:
            self.transport_amount = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Fee(models.Model):
    MONTH_CHOICES = [
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
        ('dec', 'December'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_records')
    total_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    due_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    previous_due_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Previous unpaid fee balance")
    concession_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Discount/Concession given")
    concession_remarks = models.TextField(blank=True, null=True, help_text="Reason for concession")
    date = models.DateField(null=True, blank=True)
    fee_month = models.CharField(max_length=20, choices=MONTH_CHOICES, null=True, blank=True, help_text="Month for which fee is being paid")
    session = models.ForeignKey(AcademicSession, on_delete=models.SET_NULL, null=True, blank=True)
    payment_mode = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('online', 'Online Transfer'),
        ('card', 'Card'),
        ('other', 'Other')
    ])
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="Check number or transaction reference")
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Fees"
        
    def save(self, *args, **kwargs):
        """Auto-calculate due_fee based on total, paid, concession, and previous balance"""
        # Calculate actual amount to be paid
        amount_after_concession = max(0, (self.total_fee + self.previous_due_balance) - self.concession_amount)
        # Due is what's remaining after payment
        self.due_fee = amount_after_concession - self.paid_fee
        super().save(*args, **kwargs)

    def __str__(self):
        month_display = f" - {self.get_fee_month_display()}" if self.fee_month else ""
        return f"{self.student.name}{month_display} - ₹{self.total_fee}"


class Designation(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class StaffProfile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    EMPLOYEE_PREFIX = 'EMP'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_profile')
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    full_name = models.CharField(max_length=120)
    father_name = models.CharField(max_length=120, blank=True, default='')
    mother_name = models.CharField(max_length=120, blank=True, default='')
    husband_name = models.CharField(max_length=120, blank=True, default='')
    qualification = models.CharField(max_length=120, blank=True, default='')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, default='')
    mobile_number = models.CharField(max_length=20, blank=True, default='')
    photo = models.FileField(upload_to='staff/photos/', null=True, blank=True)
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_profiles')
    email = models.EmailField(blank=True, default='')
    login_password_plain = models.CharField(max_length=128, blank=True, default='')
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pan_number = models.CharField(max_length=20, blank=True, default='')
    experience = models.CharField(max_length=120, blank=True, default='')
    last_school_name = models.CharField(max_length=150, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'

    @classmethod
    def get_next_employee_id(cls):
        latest = cls.objects.filter(employee_id__startswith=cls.EMPLOYEE_PREFIX).order_by('-id').first()
        if not latest or not latest.employee_id:
            return f'{cls.EMPLOYEE_PREFIX}0001'

        raw = latest.employee_id.replace(cls.EMPLOYEE_PREFIX, '')
        try:
            next_value = int(raw) + 1
        except ValueError:
            next_value = cls.objects.count() + 1
        return f'{cls.EMPLOYEE_PREFIX}{next_value:04d}'

    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = self.get_next_employee_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.employee_id} - {self.full_name}'


class AcademicNotice(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    publish_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-publish_date', '-id']

    def __str__(self):
        return self.title


class StudentAttendance(models.Model):
    STATUS_PRESENT = 'Present'
    STATUS_ABSENT = 'Absent'
    STATUS_CHOICES = [
        (STATUS_PRESENT, 'Present'),
        (STATUS_ABSENT, 'Absent'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    attendance_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PRESENT)
    remarks = models.CharField(max_length=255, blank=True, null=True)
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'attendance_date']
        ordering = ['-attendance_date', 'student__name']

    def __str__(self):
        return f'{self.student.name} - {self.attendance_date} - {self.status}'


class SchoolSetting(models.Model):
    school_name = models.CharField(max_length=150, default='RLCS School')
    school_code = models.CharField(max_length=40, blank=True, default='')
    logo = models.FileField(upload_to='settings/logo/', null=True, blank=True)
    principal_name = models.CharField(max_length=100, blank=True, default='')
    contact_number = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    academic_year_label = models.CharField(max_length=50, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'School Setting'
        verbose_name_plural = 'School Settings'

    def __str__(self):
        return self.school_name


class SystemOptionSetting(models.Model):
    admission_open = models.BooleanField(default=True)
    fee_receipt_auto_number = models.BooleanField(default=True)
    sms_notifications_enabled = models.BooleanField(default=False)
    email_notifications_enabled = models.BooleanField(default=False)
    allow_student_portal = models.BooleanField(default=True)
    require_transport_approval = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'System Option Setting'
        verbose_name_plural = 'System Option Settings'

    def __str__(self):
        return 'System Options'


class PaymentOptionSetting(models.Model):
    allow_cash = models.BooleanField(default=True)
    allow_cheque = models.BooleanField(default=True)
    allow_card = models.BooleanField(default=False)
    allow_online_transfer = models.BooleanField(default=False)
    allow_upi = models.BooleanField(default=False)
    late_fee_enabled = models.BooleanField(default=False)
    late_fee_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    payment_terms_note = models.CharField(max_length=250, blank=True, default='')
    receipt_prefix = models.CharField(max_length=30, blank=True, default='RCPT')
    receipt_footer = models.CharField(max_length=250, blank=True, default='Thank you for your payment')
    quarterly_fee_months = models.CharField(max_length=50, blank=True, default='apr,jul,oct,jan')
    half_yearly_fee_months = models.CharField(max_length=30, blank=True, default='apr,oct')
    yearly_fee_month = models.CharField(max_length=10, blank=True, default='apr')
    once_fee_month = models.CharField(max_length=10, blank=True, default='apr')
    show_school_name_on_receipt = models.BooleanField(default=True)
    show_logo_on_receipt = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Option Setting'
        verbose_name_plural = 'Payment Option Settings'

    def __str__(self):
        return 'Payment Options'


class RoleModulePermission(models.Model):
    ROLE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('principal', 'Principal'),
        ('viceprincipal', 'Vice Principal'),
        ('accountant', 'Accountant'),
        ('teacher', 'Teacher'),
        ('reception', 'Reception'),
        ('staff', 'Staff Admin'),
    ]

    role_key = models.CharField(max_length=30, choices=ROLE_CHOICES, unique=True)
    can_access_students = models.BooleanField(default=False)
    can_access_fee = models.BooleanField(default=False)
    can_access_attendance = models.BooleanField(default=False)
    can_access_academic = models.BooleanField(default=False)
    can_access_staff = models.BooleanField(default=False)
    can_access_exam = models.BooleanField(default=False)
    can_access_transport = models.BooleanField(default=False)
    can_access_settings = models.BooleanField(default=False)
    can_access_reports = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Role Module Permission'
        verbose_name_plural = 'Role Module Permissions'

    def __str__(self):
        return self.get_role_key_display()


class WhatsAppApiSetting(models.Model):
    provider_name = models.CharField(max_length=60, blank=True, default='Meta WhatsApp Cloud API')
    api_base_url = models.URLField(blank=True, default='')
    access_token = models.TextField(blank=True, default='')
    phone_number_id = models.CharField(max_length=100, blank=True, default='')
    business_account_id = models.CharField(max_length=100, blank=True, default='')
    webhook_verify_token = models.CharField(max_length=120, blank=True, default='')
    instance_id = models.CharField(max_length=100, blank=True, default='')
    default_country_code = models.CharField(max_length=8, blank=True, default='+91')
    fee_receipt_template = models.CharField(max_length=100, blank=True, default='fee_receipt_notice')
    due_fee_template = models.CharField(max_length=100, blank=True, default='due_fee_alert')
    attendance_template = models.CharField(max_length=100, blank=True, default='attendance_alert')
    enable_admission_alerts = models.BooleanField(default=False)
    enable_fee_receipt_alerts = models.BooleanField(default=False)
    enable_attendance_alerts = models.BooleanField(default=False)
    enable_due_fee_alerts = models.BooleanField(default=False)
    enable_result_alerts = models.BooleanField(default=False)
    enable_general_broadcasts = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'WhatsApp API Setting'
        verbose_name_plural = 'WhatsApp API Settings'

    def __str__(self):
        return self.provider_name or 'WhatsApp API'


class MobileAppControlSetting(models.Model):
    app_name = models.CharField(max_length=120, blank=True, default='RLCS School App')
    android_latest_version = models.CharField(max_length=20, blank=True, default='1.0.0')
    android_min_supported_version = models.CharField(max_length=20, blank=True, default='1.0.0')
    force_update = models.BooleanField(default=False)
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.CharField(max_length=250, blank=True, default='Server maintenance in progress. Please try again later.')
    student_app_enabled = models.BooleanField(default=True)
    parent_app_enabled = models.BooleanField(default=True)
    staff_app_enabled = models.BooleanField(default=True)
    app_notice = models.CharField(max_length=250, blank=True, default='')
    push_notifications_enabled = models.BooleanField(default=True)
    student_home_modules = models.TextField(blank=True, default='dashboard,attendance,fees,results,notices')
    parent_home_modules = models.TextField(blank=True, default='dashboard,attendance,fees,notices')
    staff_home_modules = models.TextField(blank=True, default='dashboard,attendance,academics,notices')
    current_release_version = models.CharField(max_length=30, blank=True, default='')
    config_api_key = models.CharField(max_length=80, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mobile App Control Setting'
        verbose_name_plural = 'Mobile App Control Settings'

    def save(self, *args, **kwargs):
        if not self.config_api_key:
            self.config_api_key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.app_name or 'Mobile App Control'


class MobileAppDevice(models.Model):
    PLATFORM_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='mobile_devices')
    role_key = models.CharField(max_length=30, blank=True, default='')
    device_id = models.CharField(max_length=120, unique=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='android')
    device_name = models.CharField(max_length=120, blank=True, default='')
    fcm_token = models.CharField(max_length=300, blank=True, default='')
    app_version = models.CharField(max_length=30, blank=True, default='')
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_seen']
        verbose_name = 'Mobile App Device'
        verbose_name_plural = 'Mobile App Devices'

    def __str__(self):
        return f'{self.device_id} ({self.platform})'


class MobileAppRelease(models.Model):
    version_name = models.CharField(max_length=30, unique=True)
    version_code = models.PositiveIntegerField(default=1)
    release_notes = models.TextField(blank=True, default='')
    is_mandatory = models.BooleanField(default=False)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Mobile App Release'
        verbose_name_plural = 'Mobile App Releases'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_current:
            MobileAppRelease.objects.exclude(id=self.id).update(is_current=False)

    def __str__(self):
        return self.version_name


class TimeTableEntry(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
    ]

    SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('upload', 'Upload'),
    ]

    class_name = models.CharField(max_length=30)
    section = models.CharField(max_length=10)
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    period_label = models.CharField(max_length=30)
    subject_name = models.CharField(max_length=120)
    teacher_name = models.CharField(max_length=120, blank=True, default='')
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    room_number = models.CharField(max_length=30, blank=True, default='')
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='manual')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['class_name', 'section', 'day_of_week', 'period_label']
        unique_together = ['class_name', 'section', 'day_of_week', 'period_label']

    def __str__(self):
        return f'{self.class_name}-{self.section} {self.get_day_of_week_display()} {self.period_label}'


class HomeworkSetup(models.Model):
    class_name = models.CharField(max_length=30)
    section = models.CharField(max_length=10)
    subject_name = models.CharField(max_length=120)
    title = models.CharField(max_length=200)
    description = models.TextField()
    assigned_date = models.DateField()
    due_date = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    attachment = models.FileField(upload_to='academic/homework/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-due_date', '-id']

    def __str__(self):
        return f'{self.class_name}-{self.section}: {self.title}'


class CourseSchedule(models.Model):
    TERM_CHOICES = [
        ('term1', 'Term 1'),
        ('term2', 'Term 2'),
        ('term3', 'Term 3'),
        ('full_year', 'Full Year'),
    ]
    class_name = models.CharField(max_length=30)
    section = models.CharField(max_length=10)
    subject_name = models.CharField(max_length=120)
    teacher_name = models.CharField(max_length=100, blank=True)
    term = models.CharField(max_length=20, choices=TERM_CHOICES, default='full_year')
    periods_per_week = models.PositiveSmallIntegerField(default=1)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        unique_together = ['class_name', 'section', 'subject_name', 'term']

    def __str__(self):
        return f'{self.class_name}-{self.section}: {self.subject_name} ({self.term})'


class Syllabus(models.Model):
    class_name = models.CharField(max_length=30)
    subject_name = models.CharField(max_length=120)
    unit_number = models.PositiveSmallIntegerField()
    unit_title = models.CharField(max_length=200)
    topics = models.TextField()
    teaching_hours = models.PositiveSmallIntegerField(default=1)
    academic_year = models.CharField(max_length=20, default='2025-26')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['class_name', 'subject_name', 'unit_number']

    def __str__(self):
        return f'{self.class_name} | {self.subject_name} - Unit {self.unit_number}: {self.unit_title}'


class DateSheet(models.Model):
    EXAM_TYPE_CHOICES = [
        ('unit_test', 'Unit Test'),
        ('mid_term', 'Mid Term'),
        ('final', 'Final Exam'),
        ('pre_board', 'Pre Board'),
        ('other', 'Other'),
    ]
    class_name = models.CharField(max_length=30)
    section = models.CharField(max_length=10, blank=True)
    subject_name = models.CharField(max_length=120)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, default='final')
    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    total_marks = models.PositiveSmallIntegerField(default=100)
    venue = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['exam_date', 'start_time']

    def __str__(self):
        return f'{self.class_name} | {self.subject_name} - {self.exam_date}'


class HolidayList(models.Model):
    HOLIDAY_TYPE_CHOICES = [
        ('national', 'National Holiday'),
        ('state', 'State Holiday'),
        ('school', 'School Holiday'),
        ('examination', 'Examination Break'),
        ('other', 'Other'),
    ]
    holiday_name = models.CharField(max_length=200)
    holiday_date = models.DateField(unique=True)
    holiday_type = models.CharField(max_length=20, choices=HOLIDAY_TYPE_CHOICES, default='school')
    description = models.TextField(blank=True)
    academic_year = models.CharField(max_length=20, default='2025-26')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['holiday_date']

    def __str__(self):
        return f'{self.holiday_name} ({self.holiday_date})'