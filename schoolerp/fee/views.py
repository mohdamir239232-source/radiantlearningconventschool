from io import BytesIO

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from schoolerp.access import require_module_access


MONTH_ALIAS_TO_CODE = {
    'jan': 'jan', 'january': 'jan',
    'feb': 'feb', 'february': 'feb',
    'mar': 'mar', 'march': 'mar',
    'apr': 'apr', 'april': 'apr',
    'may': 'may',
    'jun': 'jun', 'june': 'jun',
    'jul': 'jul', 'july': 'jul',
    'aug': 'aug', 'august': 'aug',
    'sep': 'sep', 'sept': 'sep', 'september': 'sep',
    'oct': 'oct', 'october': 'oct',
    'nov': 'nov', 'november': 'nov',
    'dec': 'dec', 'december': 'dec',
}

MONTH_CODE_ORDER = ['apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec', 'jan', 'feb', 'mar']


def _normalize_month_code(raw_month):
    return MONTH_ALIAS_TO_CODE.get((raw_month or '').strip().lower(), (raw_month or '').strip().lower())


def _order_month_codes(month_codes):
    month_set = set(month_codes or [])
    return [month for month in MONTH_CODE_ORDER if month in month_set]


def _is_past_due_month(month_code):
    current_month = _normalize_month_code(timezone.localdate().strftime('%b'))
    if month_code not in MONTH_CODE_ORDER or current_month not in MONTH_CODE_ORDER:
        return False
    return MONTH_CODE_ORDER.index(month_code) < MONTH_CODE_ORDER.index(current_month)


def _months_before(month_code):
    if month_code not in MONTH_CODE_ORDER:
        return []
    return MONTH_CODE_ORDER[:MONTH_CODE_ORDER.index(month_code)]


def _get_applicable_fee_slab(student_class_name, fee_month_code):
    from fee.models import FeeAmountSlab

    class_slabs = FeeAmountSlab.objects.filter(
        class_model__name=student_class_name,
        is_active=True,
    )
    exact_slab = class_slabs.filter(academic_month=fee_month_code).first()
    if exact_slab:
        return exact_slab, False

    # Fallback: use any active slab of the class when specific month slab is not configured.
    fallback_slab = class_slabs.order_by('-id').first()
    return fallback_slab, bool(fallback_slab)


def _is_particular_due_for_month(frequency, fee_month, particular_name=''):
    from students.models import PaymentOptionSetting

    month = _normalize_month_code(fee_month)
    freq = (frequency or '').strip().lower()
    payment_setting = PaymentOptionSetting.objects.first()

    quarterly_months = {'apr', 'jul', 'oct', 'jan'}
    half_yearly_months = {'apr', 'oct'}
    yearly_month = 'apr'
    once_month = 'apr'

    if payment_setting:
        quarterly_months = {
            item.strip().lower()
            for item in (payment_setting.quarterly_fee_months or 'apr,jul,oct,jan').split(',')
            if item.strip()
        } or quarterly_months
        half_yearly_months = {
            item.strip().lower()
            for item in (payment_setting.half_yearly_fee_months or 'apr,oct').split(',')
            if item.strip()
        } or half_yearly_months
        yearly_month = (payment_setting.yearly_fee_month or 'apr').strip().lower() or 'apr'
        once_month = (payment_setting.once_fee_month or 'apr').strip().lower() or 'apr'

    name_lower = (particular_name or '').strip().lower()

    # Business rule: Admission and Registration are charged only at session start (April).
    if 'admission' in name_lower or 'registration' in name_lower:
        return month == 'apr'

    # Business rule: Examination Fee is collected in Jul, Nov, and Feb.
    if 'exam' in name_lower:
        return month in {'jul', 'nov', 'feb'}

    if freq == 'monthly':
        return True
    if freq == 'quarterly':
        return month in quarterly_months
    if freq == 'half_yearly':
        return month in half_yearly_months
    if freq == 'yearly':
        return month == yearly_month
    if freq == 'once':
        return month == once_month
    return True

# ===== FEE PARTICULAR =====
def fee_particular_list(request):
    from fee.models import FeeParticular
    particulars = FeeParticular.objects.all()
    return render(request, 'fee/fee_particular_list.html', {'particulars': particulars})

@require_http_methods(["POST"])
def fee_particular_add(request):
    from fee.models import FeeParticular
    try:
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        frequency = request.POST.get('frequency', '').strip()
        
        if not name or not frequency:
            return JsonResponse({'success': False, 'error': 'Name and Frequency are required'})
        
        if FeeParticular.objects.filter(name=name).exists():
            return JsonResponse({'success': False, 'error': 'This particular already exists'})
        
        FeeParticular.objects.create(
            name=name,
            description=description,
            frequency=frequency,
            is_active=True
        )
        
        return JsonResponse({'success': True, 'message': 'Fee Particular created successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def fee_particular_get_data(request, particular_id):
    from fee.models import FeeParticular
    try:
        particular = FeeParticular.objects.get(id=particular_id)
        return JsonResponse({
            'success': True,
            'particular': {
                'id': particular.id,
                'name': particular.name,
                'description': particular.description or '',
                'frequency': particular.frequency
            }
        })
    except FeeParticular.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Particular not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def fee_particular_edit(request, particular_id):
    from fee.models import FeeParticular
    try:
        particular = FeeParticular.objects.get(id=particular_id)
        
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        frequency = request.POST.get('frequency', '').strip()
        
        if not name or not frequency:
            return JsonResponse({'success': False, 'error': 'Name and Frequency are required'})
        
        if FeeParticular.objects.filter(name=name).exclude(id=particular_id).exists():
            return JsonResponse({'success': False, 'error': 'A particular with this name already exists'})
        
        particular.name = name
        particular.description = description
        particular.frequency = frequency
        particular.save()
        
        return JsonResponse({'success': True, 'message': 'Fee Particular updated successfully'})
    except FeeParticular.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Particular not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def fee_particular_delete(request, particular_id):
    from fee.models import FeeParticular
    try:
        particular = FeeParticular.objects.get(id=particular_id)
        particular.delete()
        return JsonResponse({'success': True, 'message': 'Fee Particular deleted successfully'})
    except FeeParticular.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Particular not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ===== FEE AMOUNT SLAB =====
def fee_amount_slab_list(request):
    from fee.models import FeeAmountSlab, FeeParticular
    from students.models import ClassModel
    slabs = FeeAmountSlab.objects.all().select_related('class_model').prefetch_related('particulars')
    classes = ClassModel.objects.all()
    particulars = FeeParticular.objects.filter(is_active=True)
    return render(request, 'fee/fee_amount_slab_list.html', {
        'slabs': slabs, 
        'classes': classes,
        'particulars': particulars
    })

@require_http_methods(["POST"])
def fee_amount_slab_add(request):
    from fee.models import FeeAmountSlab, FeeAmountSlabParticular, FeeParticular
    from students.models import ClassModel
    try:
        class_id = request.POST.get('class_model', '').strip()
        month = request.POST.get('academic_month', '').strip()
        
        if not class_id or not month:
            return JsonResponse({'success': False, 'error': 'Class and Month are required'})
        
        class_obj = ClassModel.objects.get(id=class_id)
        
        if FeeAmountSlab.objects.filter(class_model=class_obj, academic_month=month).exists():
            return JsonResponse({'success': False, 'error': 'This combination already exists'})
        
        slab = FeeAmountSlab.objects.create(
            class_model=class_obj,
            academic_month=month,
            is_active=True
        )
        
        # Get particulars with amounts
        particulars_data = request.POST.getlist('particulars[]')
        amounts_data = request.POST.getlist('amounts[]')
        
        for particular_id, amount in zip(particulars_data, amounts_data):
            if particular_id and amount:
                particular = FeeParticular.objects.get(id=particular_id)
                FeeAmountSlabParticular.objects.create(
                    fee_slab=slab,
                    particular=particular,
                    amount=amount
                )
        
        return JsonResponse({'success': True, 'message': 'Fee Amount Slab created successfully'})
    except ClassModel.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Class not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def fee_amount_slab_get_data(request, slab_id):
    from fee.models import FeeAmountSlab
    try:
        slab = FeeAmountSlab.objects.get(id=slab_id)
        particulars = list(slab.particulars.all().values('id', 'particular__id', 'particular__name', 'amount'))
        return JsonResponse({
            'success': True,
            'slab': {
                'id': slab.id,
                'class_model': slab.class_model.id,
                'academic_month': slab.academic_month,
                'particulars': particulars
            }
        })
    except FeeAmountSlab.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Slab not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def fee_amount_slab_edit(request, slab_id):
    from fee.models import FeeAmountSlab, FeeAmountSlabParticular, FeeParticular
    from students.models import ClassModel
    try:
        slab = FeeAmountSlab.objects.get(id=slab_id)
        
        class_id = request.POST.get('class_model', '').strip()
        month = request.POST.get('academic_month', '').strip()
        
        if not class_id or not month:
            return JsonResponse({'success': False, 'error': 'All fields are required'})
        
        class_obj = ClassModel.objects.get(id=class_id)
        
        if FeeAmountSlab.objects.filter(class_model=class_obj, academic_month=month).exclude(id=slab_id).exists():
            return JsonResponse({'success': False, 'error': 'This combination already exists'})
        
        slab.class_model = class_obj
        slab.academic_month = month
        slab.save()
        
        # Update particulars
        slab.particulars.all().delete()
        
        particulars_data = request.POST.getlist('particulars[]')
        amounts_data = request.POST.getlist('amounts[]')
        
        for particular_id, amount in zip(particulars_data, amounts_data):
            if particular_id and amount:
                particular = FeeParticular.objects.get(id=particular_id)
                FeeAmountSlabParticular.objects.create(
                    fee_slab=slab,
                    particular=particular,
                    amount=amount
                )
        
        return JsonResponse({'success': True, 'message': 'Fee Amount Slab updated successfully'})
    except FeeAmountSlab.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Slab not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def fee_amount_slab_delete(request, slab_id):
    from fee.models import FeeAmountSlab
    try:
        slab = FeeAmountSlab.objects.get(id=slab_id)
        slab.delete()
        return JsonResponse({'success': True, 'message': 'Fee Amount Slab deleted successfully'})
    except FeeAmountSlab.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Slab not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ===== FEE DISCOUNT =====
def fee_discount_list(request):
    from fee.models import FeeDiscount
    discounts = FeeDiscount.objects.all()
    return render(request, 'fee/fee_discount_list.html', {'discounts': discounts})

def apply_fee_discount(request):
    """Page for applying discounts to students"""
    from students.models import ClassModel
    classes = ClassModel.objects.all()
    return render(request, 'fee/apply_discount.html', {'classes': classes})

@require_http_methods(["POST"])
def save_fee_discount(request):
    """Save discount to database"""
    from fee.models import StudentFeeDiscount, FeeParticular
    from students.models import Student
    from decimal import Decimal
    
    try:
        student_id = request.POST.get('student_id')
        particular_id = request.POST.get('particular_id')
        discount_type = request.POST.get('discount_type')
        discount_value = request.POST.get('discount_value')
        original_amount = request.POST.get('original_amount')
        remarks = request.POST.get('remarks', '')
        
        if not all([student_id, particular_id, discount_type, discount_value, original_amount]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        student = Student.objects.get(id=student_id)
        particular = FeeParticular.objects.get(id=particular_id)
        
        discount_value = Decimal(discount_value)
        original_amount = Decimal(original_amount)
        
        # Calculate discount amount
        if discount_type == 'percentage':
            discount_amount = (original_amount * discount_value) / 100
        else:
            discount_amount = discount_value
        
        final_amount = original_amount - discount_amount
        
        # Delete existing discount if any
        StudentFeeDiscount.objects.filter(
            student=student,
            particular=particular
        ).delete()
        
        # Create new discount record
        discount = StudentFeeDiscount.objects.create(
            student=student,
            particular=particular,
            discount_type=discount_type,
            discount_value=discount_value,
            discount_amount=discount_amount,
            original_amount=original_amount,
            final_amount=final_amount,
            remarks=remarks
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Discount saved successfully',
            'discount': {
                'id': discount.id,
                'student': student.name,
                'particular': particular.name,
                'discount_amount': float(discount_amount),
                'final_amount': float(final_amount)
            }
        })
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found'})
    except FeeParticular.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Particular not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def fee_discount_add(request):
    from fee.models import FeeDiscount
    try:
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        discount_type = request.POST.get('discount_type', '').strip()
        discount_value = request.POST.get('discount_value', '').strip()
        max_discount = request.POST.get('max_discount_amount', '').strip()
        
        if not name or not discount_type or not discount_value:
            return JsonResponse({'success': False, 'error': 'Required fields missing'})
        
        if FeeDiscount.objects.filter(name=name).exists():
            return JsonResponse({'success': False, 'error': 'This discount already exists'})
        
        FeeDiscount.objects.create(
            name=name,
            description=description,
            discount_type=discount_type,
            discount_value=discount_value,
            max_discount_amount=max_discount if max_discount else None,
            is_active=True
        )
        
        return JsonResponse({'success': True, 'message': 'Fee Discount created successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def fee_discount_get_data(request, discount_id):
    from fee.models import FeeDiscount
    try:
        discount = FeeDiscount.objects.get(id=discount_id)
        return JsonResponse({
            'success': True,
            'discount': {
                'id': discount.id,
                'name': discount.name,
                'description': discount.description or '',
                'discount_type': discount.discount_type,
                'discount_value': str(discount.discount_value),
                'max_discount_amount': str(discount.max_discount_amount) if discount.max_discount_amount else ''
            }
        })
    except FeeDiscount.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Discount not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def fee_discount_edit(request, discount_id):
    from fee.models import FeeDiscount
    try:
        discount = FeeDiscount.objects.get(id=discount_id)
        
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        discount_type = request.POST.get('discount_type', '').strip()
        discount_value = request.POST.get('discount_value', '').strip()
        max_discount = request.POST.get('max_discount_amount', '').strip()
        
        if not name or not discount_type or not discount_value:
            return JsonResponse({'success': False, 'error': 'Required fields missing'})
        
        if FeeDiscount.objects.filter(name=name).exclude(id=discount_id).exists():
            return JsonResponse({'success': False, 'error': 'A discount with this name already exists'})
        
        discount.name = name
        discount.description = description
        discount.discount_type = discount_type
        discount.discount_value = discount_value
        discount.max_discount_amount = max_discount if max_discount else None
        discount.save()
        
        return JsonResponse({'success': True, 'message': 'Fee Discount updated successfully'})
    except FeeDiscount.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Discount not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def fee_discount_delete(request, discount_id):
    from fee.models import FeeDiscount
    try:
        discount = FeeDiscount.objects.get(id=discount_id)
        discount.delete()
        return JsonResponse({'success': True, 'message': 'Fee Discount deleted successfully'})
    except FeeDiscount.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Discount not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def fee_deposit(request):
    from students.models import ClassModel
    classes = ClassModel.objects.filter(is_active=True).order_by('name')
    return render(request, 'fee/fee_deposit_final.html', {'classes': classes})

def fee_deposit_final(request):
    """Fee deposit with class-based student search, month, particulars selection, concession and receipt"""
    from students.models import ClassModel
    classes = ClassModel.objects.filter(is_active=True).order_by('name')
    return render(request, 'fee/fee_deposit_final.html', {'classes': classes})


@require_http_methods(["GET"])
def api_students_by_class(request):
    """Return students filtered by class and optional section"""
    from students.models import Student
    class_name = request.GET.get('class_name', '').strip()
    section = request.GET.get('section', '').strip()

    if not class_name:
        return JsonResponse({'success': False, 'error': 'class_name required'})

    qs = Student.objects.filter(student_class=class_name).select_related('transport_route')
    if section:
        qs = qs.filter(section=section)
    qs = qs.order_by('roll_no', 'name')

    data = []
    for s in qs:
        data.append({
            'id': s.id,
            'name': s.name,
            'admission_number': s.admission_number or '',
            'student_class': s.student_class,
            'roll_no': s.roll_no or '',
            'section': s.section,
            'father_name': s.father_name or '',
            'address': s.address or '',
            'session': s.session or '',
            'transport_required': s.transport_required,
            'transport_route': s.transport_route.route_name if s.transport_route else '',
            'transport_fare': float(s.transport_route.fare_amount) if s.transport_route else 0,
        })
    return JsonResponse({'success': True, 'students': data})


@require_http_methods(["GET"])
def api_student_fee_months(request):
    from students.models import Fee, Student

    student_id = request.GET.get('student_id', '').strip()
    if not student_id:
        return JsonResponse({'success': False, 'error': 'student_id required'})

    try:
        student = Student.objects.get(id=student_id)
        paid_months_raw = Fee.objects.filter(student=student, due_fee__lte=0).values_list('fee_month', flat=True)
        paid_months = {
            _normalize_month_code(month)
            for month in paid_months_raw
            if _normalize_month_code(month) in MONTH_CODE_ORDER
        }
        available_months = [month for month in MONTH_CODE_ORDER if month not in paid_months]

        return JsonResponse({
            'success': True,
            'student_id': student.id,
            'paid_months': _order_month_codes(paid_months),
            'available_months': available_months,
        })
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found'})

def _build_receipt_number(fee_id, payment_setting):
    prefix = 'RCPT'
    if payment_setting and payment_setting.receipt_prefix:
        prefix = payment_setting.receipt_prefix.strip() or 'RCPT'
    return f'{prefix}-{fee_id:05d}'


def fee_receipt(request):
    return render(request, 'fee/fee_receipt.html')


@require_http_methods(["GET"])
def fee_receipt_pdf(request, fee_id):
    from students.models import Fee, PaymentOptionSetting, SchoolSetting

    fee_record = Fee.objects.select_related('student').filter(id=fee_id).first()
    if fee_record is None:
        return JsonResponse({'success': False, 'error': 'Receipt not found'}, status=404)

    school_setting = SchoolSetting.objects.first()
    payment_setting = PaymentOptionSetting.objects.first()
    receipt_number = _build_receipt_number(fee_record.id, payment_setting)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50

    if payment_setting and payment_setting.show_logo_on_receipt and school_setting and school_setting.logo:
        try:
            logo_file = school_setting.logo.path
            logo_reader = ImageReader(logo_file)
            pdf.drawImage(logo_reader, 50, y - 60, width=52, height=52, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawString(120, y, 'FEE RECEIPT')

    if payment_setting is None or payment_setting.show_school_name_on_receipt:
        school_name = school_setting.school_name if school_setting and school_setting.school_name else 'School ERP System'
        pdf.setFont('Helvetica', 11)
        pdf.drawString(120, y - 18, school_name)

    pdf.setLineWidth(0.5)
    pdf.line(50, y - 70, width - 50, y - 70)

    y = y - 95
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(50, y, 'Receipt Number:')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(160, y, receipt_number)

    y -= 20
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(50, y, 'Student Name:')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(160, y, fee_record.student.name)

    y -= 20
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(50, y, 'Admission Number:')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(160, y, fee_record.student.admission_number or '-')

    y -= 20
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(50, y, 'Class / Section:')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(160, y, f"{fee_record.student.student_class} / {fee_record.student.section}")

    y -= 20
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(50, y, 'Payment Date:')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(160, y, fee_record.date.strftime('%d/%m/%Y') if fee_record.date else '-')

    y -= 35
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(50, y, 'Total Fee')
    pdf.drawRightString(width - 50, y, f"INR {float(fee_record.total_fee):.2f}")
    y -= 18
    pdf.drawString(50, y, 'Paid Amount')
    pdf.drawRightString(width - 50, y, f"INR {float(fee_record.paid_fee):.2f}")
    y -= 18
    pdf.drawString(50, y, 'Balance Due')
    pdf.drawRightString(width - 50, y, f"INR {float(fee_record.due_fee):.2f}")

    y -= 25
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(50, y, 'Payment Mode:')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(160, y, fee_record.payment_mode or '-')

    y -= 20
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(50, y, 'Reference Number:')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(160, y, fee_record.reference_number or '-')

    y -= 40
    footer_text = 'Thank you for your payment'
    if payment_setting and payment_setting.receipt_footer:
        footer_text = payment_setting.receipt_footer

    pdf.setFont('Helvetica-Oblique', 10)
    pdf.drawString(50, y, footer_text)

    pdf.setFont('Helvetica', 9)
    pdf.drawString(50, 36, f'Generated on {timezone.localtime().strftime("%d/%m/%Y %I:%M %p")}')

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    inline_mode = request.GET.get('inline') == '1' or request.GET.get('print') == '1'
    disposition = 'inline' if inline_mode else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{receipt_number}.pdf"'
    return response

@require_http_methods(["GET"])
def search_fee_receipts(request):
    from students.models import Student, Fee, PaymentOptionSetting
    from fee.models import FeeAmountSlab, StudentFeeDiscount
    from django.db.models import Q

    query = request.GET.get('q', '').strip()
    if query:
        students = Student.objects.filter(
            Q(name__icontains=query) | Q(admission_number__icontains=query)
        )
        if query.isdigit():
            students = students | Student.objects.filter(roll_no=int(query))
        fees = Fee.objects.filter(student__in=students).select_related('student').order_by('-date')[:20]
        response_message = 'Search results'
    else:
        fees = Fee.objects.select_related('student').order_by('-date')[:20]
        response_message = 'Latest receipts'

    payment_setting = PaymentOptionSetting.objects.first()
    receipt_prefix = (payment_setting.receipt_prefix if payment_setting and payment_setting.receipt_prefix else 'RCPT').strip()

    receipts = []
    for fee in fees:
        particulars = []

        fee_month = _normalize_month_code(fee.fee_month)
        if fee_month:
            fee_slab, _ = _get_applicable_fee_slab(fee.student.student_class, fee_month)
            if fee_slab:
                fee_slab = FeeAmountSlab.objects.filter(id=fee_slab.id).prefetch_related('particulars__particular').first()

            if fee_slab:
                for slab_item in fee_slab.particulars.all():
                    if not _is_particular_due_for_month(
                        slab_item.particular.frequency,
                        fee_month,
                        slab_item.particular.name,
                    ):
                        continue
                    discount = StudentFeeDiscount.objects.filter(
                        student=fee.student,
                        particular=slab_item.particular,
                    ).first()
                    final_amount = discount.final_amount if discount else slab_item.amount
                    particulars.append({
                        'name': slab_item.particular.name,
                        'amount': float(final_amount),
                    })

        if fee.student.transport_required and fee.student.transport_amount:
            particulars.append({
                'name': 'Transport Fee',
                'amount': float(fee.student.transport_amount),
            })

        if not particulars:
            particulars = [{'name': 'Fee Amount', 'amount': float(fee.total_fee)}]

        receipts.append({
            'id': fee.id,
            'receipt_number': f'{receipt_prefix}-{fee.id:05d}',
            'student_name': fee.student.name,
            'father_name': fee.student.father_name or '',
            'roll_number': fee.student.roll_no,
            'admission_number': fee.student.admission_number or '',
            'class': fee.student.student_class,
            'section': fee.student.section,
            'fee_month': fee.fee_month or '',
            'date': fee.date.strftime('%d/%m/%Y') if fee.date else '',
            'total_fee': float(fee.total_fee),
            'paid_amount': float(fee.paid_fee),
            'balance': float(fee.due_fee),
            'payment_mode': getattr(fee, 'payment_mode', 'N/A'),
            'reference_no': getattr(fee, 'reference_number', 'N/A') or 'N/A',
            'status': 'paid' if fee.due_fee <= 0 else 'partial',
            'particulars': particulars,
        })

    return JsonResponse({'success': True, 'message': response_message, 'receipts': receipts})


@require_http_methods(["POST"])
def delete_fee_receipt(request, fee_id):
    from students.models import Fee

    fee_record = Fee.objects.select_related('student').filter(id=fee_id).first()
    if fee_record is None:
        return JsonResponse({'success': False, 'error': 'Receipt not found'}, status=404)

    student_name = fee_record.student.name
    month_code = fee_record.fee_month or ''

    # If same reference/date exists for this student, treat it as a grouped submission
    # and remove all those rows so deposited fee becomes due again.
    if fee_record.reference_number:
        grouped_qs = Fee.objects.filter(
            student=fee_record.student,
            reference_number=fee_record.reference_number,
            date=fee_record.date,
        )
        deleted_count = grouped_qs.count()
        grouped_qs.delete()
    else:
        deleted_count = 1
        fee_record.delete()

    return JsonResponse({
        'success': True,
        'message': 'Receipt deleted successfully',
        'deleted_count': deleted_count,
        'student_name': student_name,
        'fee_month': month_code,
    })

@require_http_methods(["POST"])
@require_http_methods(["POST"])
def save_fee_deposit(request):
    from students.models import Student, Fee, PaymentOptionSetting
    from decimal import Decimal
    
    try:
        student_id = request.POST.get('student_id')
        total_fee = request.POST.get('total_fee')
        paid_amount = request.POST.get('paid_amount')
        payment_date = request.POST.get('payment_date')
        fee_month = request.POST.get('fee_month', '')
        fee_months_csv = request.POST.get('fee_months', '').strip()
        selected_month_totals_raw = request.POST.get('selected_month_totals', '{}').strip()
        concession_amount = request.POST.get('concession_amount', '0')
        concession_remarks = request.POST.get('concession_remarks', '')
        payment_mode = request.POST.get('payment_mode', '')
        reference_number = request.POST.get('reference_number', '')
        remarks = request.POST.get('remarks', '')

        if not student_id or not total_fee or not paid_amount or not payment_date:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})

        student = Student.objects.get(id=student_id)
        payment_setting = PaymentOptionSetting.objects.first()
        total_fee = Decimal(str(total_fee))
        paid_amount = Decimal(str(paid_amount))
        concession_amount = Decimal(str(concession_amount)) if concession_amount else Decimal('0')

        if fee_months_csv:
            month_codes = []
            seen = set()
            for token in fee_months_csv.split(','):
                month_code = _normalize_month_code(token)
                if month_code in MONTH_CODE_ORDER and month_code not in seen:
                    month_codes.append(month_code)
                    seen.add(month_code)
            month_codes = _order_month_codes(month_codes)
        else:
            month_codes = [_normalize_month_code(fee_month)] if _normalize_month_code(fee_month) in MONTH_CODE_ORDER else []

        if not month_codes:
            return JsonResponse({'success': False, 'error': 'At least one valid month is required'})

        if len(month_codes) > 1:
            try:
                selected_month_totals_dict = json.loads(selected_month_totals_raw) if selected_month_totals_raw else {}
            except json.JSONDecodeError:
                selected_month_totals_dict = {}

            month_totals = []
            for month_code in month_codes:
                month_total = Decimal(str(selected_month_totals_dict.get(month_code, '0') or '0'))
                if month_total > Decimal('0'):
                    month_totals.append((month_code, month_total))

            if not month_totals:
                return JsonResponse({'success': False, 'error': 'No payable month totals found for submission'})

            gross_total = sum(total for _, total in month_totals)
            if gross_total <= Decimal('0'):
                return JsonResponse({'success': False, 'error': 'Invalid payable total'})

            remaining_paid = paid_amount
            remaining_concession = concession_amount
            month_results = []

            for index, (month_code, month_total) in enumerate(month_totals):
                if index == len(month_totals) - 1:
                    month_concession = max(Decimal('0'), remaining_concession)
                else:
                    month_concession = (concession_amount * month_total / gross_total).quantize(Decimal('0.01'))
                    month_concession = min(month_concession, remaining_concession)
                    remaining_concession -= month_concession

                payable_after_concession = max(Decimal('0'), month_total - month_concession)
                month_paid = min(remaining_paid, payable_after_concession)
                month_due = payable_after_concession - month_paid
                remaining_paid -= month_paid

                month_rows = Fee.objects.filter(student=student, fee_month=month_code).order_by('-id')
                existing_month_fee = month_rows.first()
                open_month_due = sum(Decimal(str(row.due_fee)) for row in month_rows if Decimal(str(row.due_fee)) > Decimal('0'))

                if existing_month_fee and open_month_due > Decimal('0'):
                    prior_due = open_month_due
                    adjusted_paid = min(month_paid, prior_due)
                    new_due = prior_due - adjusted_paid
                    Fee.objects.filter(id=existing_month_fee.id).update(
                        paid_fee=Decimal(str(existing_month_fee.paid_fee)) + adjusted_paid,
                        due_fee=new_due,
                        payment_mode=payment_mode or existing_month_fee.payment_mode,
                        reference_number=reference_number or existing_month_fee.reference_number,
                        remarks=remarks or existing_month_fee.remarks,
                        date=payment_date,
                    )
                    month_results.append({
                        'month': month_code,
                        'total_fee': float(prior_due),
                        'concession': 0.0,
                        'paid': float(adjusted_paid),
                        'due': float(new_due),
                    })
                    continue

                if existing_month_fee and open_month_due <= Decimal('0'):
                    continue

                new_record = Fee.objects.create(
                    student=student,
                    total_fee=month_total,
                    paid_fee=month_paid,
                    due_fee=month_due,
                    previous_due_balance=Decimal('0'),
                    concession_amount=month_concession,
                    concession_remarks=concession_remarks,
                    fee_month=month_code,
                    date=payment_date,
                    payment_mode=payment_mode,
                    reference_number=reference_number,
                    remarks=remarks,
                    session=student.session
                )
                month_results.append({
                    'month': month_code,
                    'fee_id': new_record.id,
                    'total_fee': float(month_total),
                    'concession': float(month_concession),
                    'paid': float(month_paid),
                    'due': float(max(Decimal('0'), month_due)),
                })

            return JsonResponse({
                'success': True,
                'message': 'Multi-month fee deposit saved successfully',
                'receipt_data': {
                    'receipt_number': _build_receipt_number(month_results[0].get('fee_id') if month_results and month_results[0].get('fee_id') else Fee.objects.filter(student=student, fee_month=month_results[0]['month']).order_by('-id').first().id, payment_setting),
                    'student_name': student.name,
                    'father_name': student.father_name or '',
                    'address': student.address or '',
                    'session': student.session or '',
                    'admission_number': student.admission_number,
                    'class': student.student_class,
                    'section': student.section,
                    'roll_no': student.roll_no,
                    'fee_month': ','.join([item['month'] for item in month_results]),
                    'payment_date': payment_date,
                    'payment_mode': payment_mode,
                    'reference_number': reference_number,
                    'total_fee': float(gross_total),
                    'concession': float(concession_amount),
                    'paid_amount': float(paid_amount),
                    'balance': float(sum(Decimal(str(item['due'])) for item in month_results)),
                    'month_breakup': month_results,
                }
            })

        existing_month_fee = Fee.objects.filter(
            student=student,
            fee_month=month_codes[0],
        ).order_by('-id').first()
        month_due_rows = Fee.objects.filter(student=student, fee_month=month_codes[0])
        open_month_due = sum(Decimal(str(row.due_fee)) for row in month_due_rows if Decimal(str(row.due_fee)) > Decimal('0'))

        if existing_month_fee and open_month_due <= Decimal('0'):
            return JsonResponse({'success': False, 'error': 'Is month ki fee already fully submitted hai.'})

        if existing_month_fee and open_month_due > Decimal('0'):
            payable_due = open_month_due
            adjusted_paid = min(paid_amount, payable_due)
            remaining_due = payable_due - adjusted_paid

            # Use direct update to avoid model save recalculation overriding due-only settlement.
            Fee.objects.filter(id=existing_month_fee.id).update(
                paid_fee=Decimal(str(existing_month_fee.paid_fee)) + adjusted_paid,
                due_fee=remaining_due,
                payment_mode=payment_mode or existing_month_fee.payment_mode,
                reference_number=reference_number or existing_month_fee.reference_number,
                remarks=remarks or existing_month_fee.remarks,
                date=payment_date,
            )

            return JsonResponse({
                'success': True,
                'message': 'Due amount payment updated successfully',
                'fee_id': existing_month_fee.id,
                'receipt_data': {
                    'receipt_number': _build_receipt_number(existing_month_fee.id, payment_setting),
                    'student_name': student.name,
                    'father_name': student.father_name or '',
                    'address': student.address or '',
                    'session': student.session or '',
                    'admission_number': student.admission_number,
                    'class': student.student_class,
                    'section': student.section,
                    'roll_no': student.roll_no,
                    'total_fee': float(payable_due),
                    'previous_due': 0.0,
                    'concession': 0.0,
                    'paid_amount': float(adjusted_paid),
                    'balance': float(remaining_due),
                    'fee_month': month_codes[0],
                    'payment_date': payment_date,
                    'payment_mode': payment_mode,
                    'reference_number': reference_number
                }
            })
        
        # Calculate previous due balance only for first-time month deposit
        previous_fees = Fee.objects.filter(
            student=student,
            fee_month__in=_months_before(month_codes[0]),
        )
        previous_due = sum(Decimal(str(f.due_fee)) for f in previous_fees if f.due_fee > 0)

        # Calculate due: (current fee + previous due - concession - paid)
        amount_after_concession = max(Decimal('0'), (total_fee + previous_due) - concession_amount)
        due_fee = amount_after_concession - paid_amount

        fee_record = Fee.objects.create(
            student=student,
            total_fee=total_fee,
            paid_fee=paid_amount,
            due_fee=due_fee,
            previous_due_balance=previous_due,
            concession_amount=concession_amount,
            concession_remarks=concession_remarks,
            fee_month=month_codes[0],
            date=payment_date,
            payment_mode=payment_mode,
            reference_number=reference_number,
            remarks=remarks,
            session=student.session
        )

        return JsonResponse({
            'success': True,
            'message': 'Fee deposit saved successfully',
            'fee_id': fee_record.id,
            'receipt_data': {
                'receipt_number': _build_receipt_number(fee_record.id, payment_setting),
                'student_name': student.name,
                'father_name': student.father_name or '',
                'address': student.address or '',
                'session': student.session or '',
                'admission_number': student.admission_number,
                'class': student.student_class,
                'section': student.section,
                'roll_no': student.roll_no,
                'total_fee': float(total_fee),
                'previous_due': float(previous_due),
                'concession': float(concession_amount),
                'paid_amount': float(paid_amount),
                'balance': float(due_fee),
                'fee_month': month_codes[0],
                'payment_date': payment_date,
                'payment_mode': payment_mode,
                'reference_number': reference_number
            }
        })
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def search_students(request):
    """Search students by admission number or class/section"""
    from students.models import Student, ClassModel
    
    search_type = request.GET.get('search_type', '')
    query = request.GET.get('query', '').strip()
    
    students = []
    
    if search_type == 'admission_no' and query:
        students = Student.objects.filter(admission_number__icontains=query).select_related('transport_route')
    elif search_type == 'class_section':
        class_name = request.GET.get('class_name', '').strip()
        section = request.GET.get('section', '').strip()
        
        if class_name:
            filter_kwargs = {'student_class': class_name}
            if section:
                filter_kwargs['section'] = section
            students = Student.objects.filter(**filter_kwargs).select_related('transport_route')
    
    # Format student data for JSON response
    student_data = []
    for student in students:
        student_data.append({
            'id': student.id,
            'admission_number': student.admission_number or '',
            'name': student.name,
            'student_class': student.student_class,
            'section': student.section,
            'roll_no': student.roll_no,
            'transport_route': {
                'id': student.transport_route.id if student.transport_route else None,
                'route_name': student.transport_route.route_name if student.transport_route else None,
                'fare_amount': float(student.transport_route.fare_amount) if student.transport_route else 0
            } if student.transport_route else None
        })
    
    return JsonResponse({'students': student_data})

@require_http_methods(["GET"])
def calculate_student_fees(request):
    """Calculate fees for a student based on their class, month, and transport"""
    from students.models import Student, Fee, PaymentOptionSetting
    from fee.models import FeeAmountSlab, FeeAmountSlabParticular, StudentFeeDiscount
    from datetime import datetime
    from decimal import Decimal
    
    student_id = request.GET.get('student_id', '').strip()
    fee_months_raw = request.GET.get('fee_months', '').strip()
    single_month_raw = request.GET.get('fee_month', datetime.now().strftime('%b').lower())
    if fee_months_raw:
        selected_months = []
        seen = set()
        for token in fee_months_raw.split(','):
            month_code = _normalize_month_code(token)
            if month_code in MONTH_CODE_ORDER and month_code not in seen:
                selected_months.append(month_code)
                seen.add(month_code)
    else:
        selected_months = [_normalize_month_code(single_month_raw)]
    selected_months = _order_month_codes(selected_months)
    
    if not student_id:
        return JsonResponse({'success': False, 'error': 'Student ID required'})
    if not selected_months:
        return JsonResponse({'success': False, 'error': 'At least one valid month is required'})
    
    try:
        student = Student.objects.get(id=student_id)
        payment_setting = PaymentOptionSetting.objects.first()
        late_fee_enabled = bool(payment_setting and payment_setting.late_fee_enabled and Decimal(str(payment_setting.late_fee_amount or 0)) > Decimal('0'))
        late_fee_amount = Decimal(str(payment_setting.late_fee_amount or 0)) if payment_setting else Decimal('0')

        overall_breakdown = []
        month_wise_totals = []
        fully_paid_months = []
        late_fee_total = Decimal('0.00')

        for fee_month in selected_months:
            month_rows = Fee.objects.filter(student=student, fee_month=fee_month).order_by('-id')
            existing_month_fee = month_rows.first()
            open_month_due = sum(Decimal(str(row.due_fee)) for row in month_rows if Decimal(str(row.due_fee)) > Decimal('0'))

            month_display = dict(FeeAmountSlab._meta.get_field('academic_month').choices).get(fee_month, fee_month)
            month_breakdown = []
            month_total_due = Decimal('0.00')

            if existing_month_fee and open_month_due <= Decimal('0'):
                fully_paid_months.append(fee_month)
                continue

            if existing_month_fee and open_month_due > Decimal('0'):
                due_amount = open_month_due
                month_breakdown.append({
                    'month_code': fee_month,
                    'month_display': month_display,
                    'particular_name': f'Due Amount ({fee_month.upper()})',
                    'original_amount': float(due_amount),
                    'discount_amount': 0.0,
                    'final_amount': float(due_amount),
                    'particular_id': None,
                })
                month_total_due += due_amount
            else:
                fee_slab, slab_fallback_used = _get_applicable_fee_slab(student.student_class, fee_month)

                if fee_slab:
                    particulars = FeeAmountSlabParticular.objects.filter(fee_slab=fee_slab).select_related('particular')

                    for particular in particulars:
                        if not _is_particular_due_for_month(
                            particular.particular.frequency,
                            fee_month,
                            particular.particular.name,
                        ):
                            continue

                        discount = StudentFeeDiscount.objects.filter(
                            student=student,
                            particular=particular.particular
                        ).first()

                        original_amount = Decimal(str(particular.amount))
                        discount_amount = Decimal(str(discount.discount_amount)) if discount else Decimal('0.00')
                        final_amount = original_amount - discount_amount

                        month_breakdown.append({
                            'month_code': fee_month,
                            'month_display': month_display,
                            'particular_name': particular.particular.name,
                            'original_amount': float(original_amount),
                            'discount_amount': float(discount_amount),
                            'final_amount': float(final_amount),
                            'particular_id': particular.particular.id
                        })

                        month_total_due += final_amount

                if student.transport_required and student.transport_route:
                    transport_fee = Decimal(str(student.transport_route.fare_amount))
                    month_breakdown.append({
                        'month_code': fee_month,
                        'month_display': month_display,
                        'particular_name': 'Transport Fee',
                        'original_amount': float(transport_fee),
                        'discount_amount': 0,
                        'final_amount': float(transport_fee),
                        'particular_id': None,
                    })
                    month_total_due += transport_fee

                if late_fee_enabled and month_total_due > Decimal('0') and _is_past_due_month(fee_month):
                    month_breakdown.append({
                        'month_code': fee_month,
                        'month_display': month_display,
                        'particular_name': f'Late Fee ({fee_month.upper()})',
                        'original_amount': float(late_fee_amount),
                        'discount_amount': 0,
                        'final_amount': float(late_fee_amount),
                        'particular_id': None,
                        'is_late_fee': True,
                    })
                    month_total_due += late_fee_amount
                    late_fee_total += late_fee_amount

            if month_total_due > Decimal('0'):
                overall_breakdown.extend(month_breakdown)
                month_wise_totals.append({
                    'month_code': fee_month,
                    'month_display': month_display,
                    'total_due': float(month_total_due),
                })

        if not overall_breakdown and fully_paid_months:
            return JsonResponse({
                'success': True,
                'fully_paid': True,
                'message': 'Selected month(s) ki fee already fully submitted hai.',
                'fee_breakdown': [],
                'current_month_fee': 0.0,
                'previous_due_balance': 0.0,
                'total_amount_due': 0.0,
                'transport_fee': 0.0,
                'selected_months': selected_months,
                'fully_paid_months': fully_paid_months,
                'month_wise_totals': [],
                'late_fee_total': 0.0,
            })

        total_amount_due = sum(Decimal(str(item['total_due'])) for item in month_wise_totals)

        return JsonResponse({
            'success': True,
            'student': {
                'id': student.id,
                'name': student.name,
                'admission_number': student.admission_number,
                'student_class': student.student_class,
                'section': student.section,
                'roll_no': student.roll_no,
                'transport_route': student.transport_route.route_name if student.transport_route else None,
                'transport_village': student.transport_village
            },
            'fee_breakdown': overall_breakdown,
            'current_month_fee': float(total_amount_due),
            'previous_due_balance': 0.0,
            'total_amount_due': float(total_amount_due),
            'transport_fee': 0.0,
            'selected_months': selected_months,
            'fully_paid_months': fully_paid_months,
            'month_wise_totals': month_wise_totals,
            'late_fee_total': float(late_fee_total),
        })
        
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ===== API ENDPOINTS =====

@require_http_methods(["GET"])
def get_particulars_by_class(request):
    """Get all particulars for a class"""
    from fee.models import FeeParticular, FeeAmountSlab
    try:
        class_id = request.GET.get('class_id', '')
        month = request.GET.get('month', '')
        
        if not class_id:
            return JsonResponse({'success': False, 'error': 'Class ID required'})
        
        # Get active particulars
        particulars = FeeParticular.objects.filter(is_active=True)
        
        # Check if slab already exists and get existing amounts
        existing_slab = None
        if month:
            existing_slab = FeeAmountSlab.objects.filter(
                class_model_id=class_id,
                academic_month=month
            ).first()
        
        particulars_list = []
        existing_amounts = {}
        
        if existing_slab:
            existing_amounts = {p.particular_id: float(p.amount) for p in existing_slab.particulars.all()}
        
        for p in particulars:
            particulars_list.append({
                'id': p.id,
                'name': p.name,
                'frequency': p.frequency,
                'frequency_display': p.get_frequency_display(),
                'amount': existing_amounts.get(p.id, '')
            })
        
        return JsonResponse({'success': True, 'particulars': particulars_list})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def search_students(request):
    """Search students by class, section, or name"""
    from students.models import Student
    from django.db.models import Q
    try:
        query = request.GET.get('q', '').strip()
        class_name = request.GET.get('class_id', '')
        section = request.GET.get('section', '')
        
        students_query = Student.objects.all()
        
        if class_name:
            students_query = students_query.filter(student_class=class_name)
        
        if section:
            students_query = students_query.filter(section=section)
        
        if query:
            students_query = students_query.filter(
                Q(name__icontains=query) |
                Q(roll_no__icontains=query) |
                Q(student_class__icontains=query)
            )
        
        students = students_query.values(
            'id', 'name', 'roll_no', 'student_class', 'section'
        )[:20]
        
        students_list = []
        for student in students:
            students_list.append({
                'id': student['id'],
                'name': student['name'],
                'roll_no': student['roll_no'],
                'class_model__id': student['id'],
                'class_model__name': student['student_class'],
                'class_model__section': student['section']
            })
        
        return JsonResponse({'success': True, 'students': students_list})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def get_student_particulars(request):
    """Get all particulars for a student to apply discount"""
    from fee.models import FeeAmountSlab, FeeAmountSlabParticular
    from students.models import Student, ClassModel
    try:
        student_id = request.GET.get('student_id', '')
        
        if not student_id:
            return JsonResponse({'success': False, 'error': 'Student ID required'})
        
        student = Student.objects.get(id=student_id)
        
        # Try to find ClassModel by name
        class_models = ClassModel.objects.filter(name=student.student_class)
        
        if not class_models.exists():
            return JsonResponse({
                'success': True,
                'student': {
                    'id': student.id,
                    'name': student.name,
                    'roll_no': student.roll_no,
                    'class': student.student_class,
                    'section': student.section
                },
                'particulars': []
            })
        
        # Get all slabs for this class
        slabs = FeeAmountSlab.objects.filter(class_model__in=class_models).prefetch_related('particulars')
        
        particulars_list = []
        for slab in slabs:
            for particular_item in slab.particulars.all():
                particulars_list.append({
                    'id': particular_item.id,
                    'slab_id': slab.id,
                    'month': slab.get_academic_month_display(),
                    'particular_name': particular_item.particular.name,
                    'amount': float(particular_item.amount),
                    'frequency': particular_item.particular.get_frequency_display()
                })
        
        return JsonResponse({
            'success': True,
            'student': {
                'id': student.id,
                'name': student.name,
                'roll_no': student.roll_no,
                'class': student.student_class,
                'section': student.section
            },
            'particulars': particulars_list
        })
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


for _fee_view_name in [
    'fee_particular_list',
    'fee_particular_add',
    'fee_particular_get_data',
    'fee_particular_edit',
    'fee_particular_delete',
    'fee_amount_slab_list',
    'fee_amount_slab_add',
    'fee_amount_slab_get_data',
    'fee_amount_slab_edit',
    'fee_amount_slab_delete',
    'fee_discount_list',
    'apply_fee_discount',
    'save_fee_discount',
    'fee_discount_add',
    'fee_discount_get_data',
    'fee_discount_edit',
    'fee_discount_delete',
    'fee_deposit',
    'fee_deposit_final',
    'api_students_by_class',
    'fee_receipt',
    'fee_receipt_pdf',
    'search_fee_receipts',
    'save_fee_deposit',
    'search_students',
    'calculate_student_fees',
    'get_particulars_by_class',
    'get_student_particulars',
]:
    if _fee_view_name in globals():
        globals()[_fee_view_name] = require_module_access('fee')(globals()[_fee_view_name])
