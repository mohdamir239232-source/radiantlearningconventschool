import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schoolerp.settings')
django.setup()

from students.models import ClassModel, Student
from fee.models import FeeParticular, FeeAmountSlab, FeeAmountSlabParticular

# Clean up test data if exists
FeeAmountSlab.objects.filter(academic_month='test').delete()
ClassModel.objects.filter(name='Test Class').delete()

# Create test data
print("Creating test data...")

class_obj = ClassModel.objects.create(name='Test Class', section='A')
print(f"✓ Created ClassModel: {class_obj}")

particular1 = FeeParticular.objects.create(
    name='Test Particular Add',
    description='Test monthly particular',
    frequency='monthly'
)
print(f"✓ Created FeeParticular: {particular1}")

# Simulate form submission for add
from django.http import QueryDict
from fee.views import fee_amount_slab_add
from django.test import RequestFactory

factory = RequestFactory()

# Create POST data
post_data = {
    'class_model': str(class_obj.id),
    'academic_month': 'jan',
    'particulars[]': [str(particular1.id)],
    'amounts[]': ['5000.00']
}

# Create request
request = factory.post('/fee/amount-slab/add/', post_data)
request.META['CSRF_COOKIE'] = 'test'

# Call view
response = fee_amount_slab_add(request)
print(f"\nAdd Slab Response: {response.content.decode()}")

# Verify slab was created
slabs = FeeAmountSlab.objects.filter(class_model=class_obj, academic_month='jan')
if slabs.exists():
    slab = slabs.first()
    print(f"✓ Fee Slab created: {slab}")
    print(f"  - Particulars: {slab.particulars.count()}")
    for p in slab.particulars.all():
        print(f"    - {p.particular.name}: ₹{p.amount}")
else:
    print("✗ Fee Slab NOT created")
