from django.db import models


class Store(models.Model):
  district = models.CharField(max_length=50)  # 자치구
  small_category = models.CharField(max_length=100)  # 소분류
  # 기타 필요한 필드들...

  def __str__(self):
    return f'{self.district} - {self.small_category}'