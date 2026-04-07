import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schoolerp.settings')
django.setup()

from students.models import ClassModel, Student
from fee.models import FeeParticular, FeeAmountSlab, FeeAmountSlabParticular

# Clean up test data if it exists
ClassModel.objects.filter(name='Test Class').delete()
Student.objects.filter(name__startswith='Test Student').delete()
FeeParticular.objects.filter(name__startswith='Test Particular').delete()

# Create test data
print("Creating test data...")

# Create ClassModel
class_obj = ClassModel.objects.create(name='Test Class', section='A')
print(f"✓ Created ClassModel: {class_obj}")

# Create FeeParticular
particular1 = FeeParticular.objects.create(
    name='Test Particular 1',
    description='Test monthly particular',
    frequency='monthly'
)
particular2 = FeeParticular.objects.create(
    name='Test Particular 2',
    description='Test quarterly particular',
    frequency='quarterly'
)
print(f"✓ Created FeeParticular: {particular1}")
print(f"✓ Created FeeParticular: {particular2}")

# Create Student
student = Student.objects.create(
    name='Test Student 1',
    roll_no='001',
    student_class='Test Class',
    section='A'
)
print(f"✓ Created Student: {student}")

# Create FeeAmountSlab
slab = FeeAmountSlab.objects.create(
    class_model=class_obj,
    academic_month='jan'
)
print(f"✓ Created FeeAmountSlab: {slab}")

# Create FeeAmountSlabParticular
slab_particular1 = FeeAmountSlabParticular.objects.create(
    fee_slab=slab,
    particular=particular1,
    amount=5000.00
)
slab_particular2 = FeeAmountSlabParticular.objects.create(
    fee_slab=slab,
    particular=particular2,
    amount=2500.00
)
print(f"✓ Created FeeAmountSlabParticular: {slab_particular1}")
print(f"✓ Created FeeAmountSlabParticular: {slab_particular2}")

print("\n✅ Test data created successfully!")

# Test get_particulars_by_class
print("\n--- Testing get_particulars_by_class ---")
from fee.models import FeeAmountSlab, FeeAmountSlabParticular
slabs = FeeAmountSlab.objects.filter(class_model=class_obj)
for slab in slabs:
    particulars = slab.particulars.all()
    print(f"Slab: {slab.get_academic_month_display()}")
    for p in particulars:
        print(f"  - {p.particular.name}: {p.amount}")

# Test search_students
print("\n--- Testing search_students ---")
students = Student.objects.filter(student_class='Test Class', section='A')
for s in students:
    print(f"Found Student: {s.name} (Roll: {s.roll_no}) - Class: {s.student_class} - Section: {s.section}")

# Test get_student_particulars
print("\n--- Testing get_student_particulars ---")
print(f"Student: {student.name}")
print(f"  - Roll No: {student.roll_no}")
print(f"  - Class: {student.student_class}")
print(f"  - Section: {student.section}")

# Find ClassModel for this student
from students.models import ClassModel as CM
class_models = CM.objects.filter(name=student.student_class)
if class_models.exists():
    slabs = FeeAmountSlab.objects.filter(class_model__in=class_models)
    print(f"  - Particulars:")
    for slab in slabs:
        for particular_item in slab.particulars.all():
            print(f"    - {particular_item.particular.name}: {particular_item.amount}")


print("\n✅ API tests completed!")
