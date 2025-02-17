from django.db import models

class JD(models.Model):
    """
    Model to store Job Description files and their metadata.
    """
    original_filename = models.CharField(max_length=255, unique=True, help_text="Original name of the uploaded JD file.")
    drive_file_id = models.CharField(max_length=255, help_text="Google Drive File ID of the uploaded JD.")
    drive_folder_id = models.CharField(max_length=255, help_text="Google Drive Folder ID where JDs are stored.")
    uploaded_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp of when the JD was uploaded.")

    def __str__(self):
        return self.original_filename

    class Meta:
        verbose_name = "Job Description"
        verbose_name_plural = "Job Descriptions"

class Resume(models.Model):
    """
    Model to store Resume files and their metadata.
    """
    original_filename = models.CharField(max_length=255, unique=True, help_text="Original name of the uploaded Resume file.")
    drive_file_id = models.CharField(max_length=255, help_text="Google Drive File ID of the uploaded Resume.")
    drive_folder_id = models.CharField(max_length=255, help_text="Google Drive Folder ID where Resumes are stored.")
    uploaded_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp of when the Resume was uploaded.")

    def __str__(self):
        return self.original_filename

    class Meta:
        verbose_name = "Resume"
        verbose_name_plural = "Resumes"

class Results(models.Model):
    """
    Model to store the results of the resume analysis process.
    """
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Timestamp of when the analysis was run.")
    matched_resumes = models.JSONField(null=True, blank=True, help_text="JSON data of matched resumes per job role.")
    unmatched_resumes = models.JSONField(null=True, blank=True, help_text="JSON list of filenames of unmatched resumes.")
    analytics = models.JSONField(null=True, blank=True, help_text="JSON data containing analytics of the analysis.")

    def __str__(self):
        return f"Results - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

    class Meta:
        verbose_name = "Analysis Result"
        verbose_name_plural = "Analysis Results"
        ordering = ['-timestamp'] # Default ordering by timestamp, newest first