# django_project/setoo_app/models.py
from django.db import models

class JD(models.Model):
    original_filename = models.CharField(max_length=255, unique=True)
    drive_file_id = models.CharField(max_length=255, unique=True)
    drive_folder_id = models.CharField(max_length=255)

    def __str__(self):
        return self.original_filename

class Resume(models.Model):
    original_filename = models.CharField(max_length=255, unique=True)
    drive_file_id = models.CharField(max_length=255, unique=True)
    drive_folder_id = models.CharField(max_length=255)

    def __str__(self):
        return self.original_filename