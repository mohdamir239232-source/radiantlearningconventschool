from django.contrib import admin

from .models import (
    CourseSchedule, DateSheet, Fee, HolidayList,
    HomeworkSetup, Student, Syllabus, TimeTableEntry,
)


admin.site.register(Student)
admin.site.register(Fee)
admin.site.register(TimeTableEntry)
admin.site.register(HomeworkSetup)
admin.site.register(CourseSchedule)
admin.site.register(Syllabus)
admin.site.register(DateSheet)
admin.site.register(HolidayList)

