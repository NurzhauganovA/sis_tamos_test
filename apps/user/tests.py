from apps.contract.models import StudentMS
from apps.student.models import Student


class UploadStudentDataFromMSSQL:
    @staticmethod
    def clean_null_bytes(value):
        return str(value).replace('\x00', '') if value else value

    def upload_data(self, user, parent_ms):
        if parent_ms is not None:
            students_ms = StudentMS.objects.using('ms_sql').filter(parent_id=parent_ms.id)

            if students_ms is not None:
                for student_ms in students_ms:
                    if Student.objects.filter(id_from_ms=student_ms.id).exists():
                        return False
                    if Student.objects.filter(iin=student_ms.iin).exists():
                        return False
                    if student_ms.id not in Student.objects.all().values_list('id_from_ms', flat=True):
                        Student.objects.create(
                            id_from_ms=student_ms.id,
                            birthday=self.clean_null_bytes(
                                student_ms.birthday) if student_ms.birthday is not None else None,
                            full_name=self.clean_null_bytes(
                                student_ms.full_name) if student_ms.full_name is not None else None,
                            iin=self.clean_null_bytes(student_ms.iin) if student_ms.iin is not None else None,
                            leave=self.clean_null_bytes(student_ms.leave) if student_ms.leave is not None else None,
                            reason_leave=self.clean_null_bytes(
                                student_ms.reason_leave) if student_ms.reason_leave is not None else None,
                            parent=user,
                            sex=1 if self.clean_null_bytes(student_ms.sex) == 1 or self.clean_null_bytes(student_ms.sex) == '1' else False,
                            email=self.clean_null_bytes(student_ms.email) if student_ms.email is not None else None,
                            phone=self.clean_null_bytes(student_ms.phone) if student_ms.phone is not None else None
                        )
                    else:
                        Student.objects.create(
                            id_from_ms=None,
                            birthday=self.clean_null_bytes(student_ms.birthday) if student_ms.birthday is not None else None,
                            full_name=self.clean_null_bytes(student_ms.full_name) if student_ms.full_name is not None else None,
                            iin=self.clean_null_bytes(student_ms.iin) if student_ms.iin is not None else None,
                            leave=self.clean_null_bytes(student_ms.leave) if student_ms.leave is not None else None,
                            reason_leave=self.clean_null_bytes(student_ms.reason_leave) if student_ms.reason_leave is not None else None,
                            parent=user,
                            sex=1 if self.clean_null_bytes(student_ms.sex) == 1 or self.clean_null_bytes(student_ms.sex) == '1' else False,
                            email=self.clean_null_bytes(student_ms.email) if student_ms.email is not None else None,
                            phone=self.clean_null_bytes(student_ms.phone) if student_ms.phone is not None else None
                        )

            return True
