"""SQLite에서도 부동소수 변환 없이 원본 좌표의 소수값을 보존합니다."""
from decimal import Decimal, InvalidOperation
from django import forms
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import DecimalValidator

class ExactCoordinateField(models.Field):
    description='정밀 좌표 (문자열 저장, Decimal 검증)'
    max_digits=30
    decimal_places=25
    def db_type(self,connection): return 'text'
    def to_python(self,value):
        if value is None or value=='': return None
        try:
            result=Decimal(str(value))
            if not result.is_finite(): raise InvalidOperation
            return result
        except (InvalidOperation,ValueError,TypeError):
            raise ValidationError('유효한 좌표 숫자를 입력해주세요.')
    def from_db_value(self,value,expression,connection): return self.to_python(value)
    def get_prep_value(self,value):
        value=self.to_python(value)
        return None if value is None else str(value)
    def validate(self,value,model_instance):
        super().validate(value,model_instance)
        if value is not None: DecimalValidator(self.max_digits,self.decimal_places)(value)
    def formfield(self,**kwargs):
        defaults={'form_class':forms.DecimalField,'max_digits':self.max_digits,'decimal_places':self.decimal_places}
        defaults.update(kwargs)
        return super().formfield(**defaults)
