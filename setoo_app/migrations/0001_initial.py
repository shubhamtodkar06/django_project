# Generated by Django 5.1.6 on 2025-02-17 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='JD',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_filename', models.CharField(help_text='Original name of the uploaded JD file.', max_length=255, unique=True)),
                ('drive_file_id', models.CharField(help_text='Google Drive File ID of the uploaded JD.', max_length=255)),
                ('drive_folder_id', models.CharField(help_text='Google Drive Folder ID where JDs are stored.', max_length=255)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, help_text='Timestamp of when the JD was uploaded.')),
            ],
            options={
                'verbose_name': 'Job Description',
                'verbose_name_plural': 'Job Descriptions',
            },
        ),
        migrations.CreateModel(
            name='Results',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True, help_text='Timestamp of when the analysis was run.')),
                ('matched_resumes', models.JSONField(blank=True, help_text='JSON data of matched resumes per job role.', null=True)),
                ('unmatched_resumes', models.JSONField(blank=True, help_text='JSON list of filenames of unmatched resumes.', null=True)),
                ('analytics', models.JSONField(blank=True, help_text='JSON data containing analytics of the analysis.', null=True)),
            ],
            options={
                'verbose_name': 'Analysis Result',
                'verbose_name_plural': 'Analysis Results',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='Resume',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_filename', models.CharField(help_text='Original name of the uploaded Resume file.', max_length=255, unique=True)),
                ('drive_file_id', models.CharField(help_text='Google Drive File ID of the uploaded Resume.', max_length=255)),
                ('drive_folder_id', models.CharField(help_text='Google Drive Folder ID where Resumes are stored.', max_length=255)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, help_text='Timestamp of when the Resume was uploaded.')),
            ],
            options={
                'verbose_name': 'Resume',
                'verbose_name_plural': 'Resumes',
            },
        ),
    ]
