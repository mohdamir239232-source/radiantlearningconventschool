import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schoolerp.settings')
django.setup()

from django.test import Client
from students.models import ClassModel
from fee.models import FeeParticular, FeeAmountSlab

# Clean up
FeeAmountSlab.objects.filter(academic_month='test2').delete()
ClassModel.objects.filter(name='Test Class2').delete()

# Create test data
class_obj = ClassModel.objects.create(name='Test Class2', section='B')
particular = FeeParticular.objects.create(
    name='Test Particular UniqueName',
    frequency='monthly'
)

print("Test data created")
print(f"Class ID: {class_obj.id}, Particular ID: {particular.id}")

# Use Django test client
client = Client()

# Create POST data
post_data = {
    'class_model': str(class_obj.id),
    'academic_month': 'feb',
    'particulars[]': [str(particular.id)],
    'amounts[]': ['3000.00']
}

print(f"\nSending POST request with data: {post_data}")

# Make request
response = client.post('/fee/amount-slab/add/', post_data)

print(f"Status Code: {response.status_code}")
print(f"Response Content: {response.content.decode()}")

# Parse response
try:
    data = json.loads(response.content)
    print(f"\nParsed Response:")
    print(f"  Success: {data.get('success')}")
    print(f"  Message: {data.get('message')}")
    print(f"  Error: {data.get('error')}")
except:
    print("Could not parse JSON response")

# Check if slab was created
slabs = FeeAmountSlab.objects.filter(class_model=class_obj, academic_month='feb')
if slabs.exists():
    slab = slabs.first()
    print(f"\n✓ Slab created successfully: {slab}")
    print(f"  Particulars: {slab.particulars.count()}")
else:
    print("\n✗ Slab NOT created")
