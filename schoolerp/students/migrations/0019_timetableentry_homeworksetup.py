from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0018_paymentoptionsetting_fee_schedule_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HomeworkSetup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('class_name', models.CharField(max_length=30)),
                ('section', models.CharField(max_length=10)),
                ('subject_name', models.CharField(max_length=120)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('assigned_date', models.DateField()),
                ('due_date', models.DateField()),
                ('attachment', models.FileField(blank=True, null=True, upload_to='academic/homework/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-due_date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='TimeTableEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('class_name', models.CharField(max_length=30)),
                ('section', models.CharField(max_length=10)),
                ('day_of_week', models.CharField(choices=[('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'), ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday')], max_length=10)),
                ('period_label', models.CharField(max_length=30)),
                ('subject_name', models.CharField(max_length=120)),
                ('teacher_name', models.CharField(blank=True, default='', max_length=120)),
                ('start_time', models.TimeField(blank=True, null=True)),
                ('end_time', models.TimeField(blank=True, null=True)),
                ('room_number', models.CharField(blank=True, default='', max_length=30)),
                ('source', models.CharField(choices=[('manual', 'Manual'), ('upload', 'Upload')], default='manual', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['class_name', 'section', 'day_of_week', 'period_label'],
                'unique_together': {('class_name', 'section', 'day_of_week', 'period_label')},
            },
        ),
    ]
