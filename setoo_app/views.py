from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from .models import JD, Resume
from django.http import HttpResponse
from .utils import upload_to_drive,fetch_file_content_from_drive, delete_file_from_drive, get_drive_service

def get_api_key(request):
    if request.method == 'POST':
        api_key = request.POST.get('openai_api_key')
        if api_key:
            request.session['openai_api_key'] = api_key
            return redirect('manage_files')
        else:
            error_message = "API key is required."
            return render(request, 'setoo_app/api_key_form.html', {'error_message': error_message})
    return render(request, 'setoo_app/api_key_form.html')

def manage_files(request):
    openai_api_key = request.session.get('openai_api_key')
    if not openai_api_key:
        return redirect('get_api_key')

    service = get_drive_service()
    if service is None:
        error_message = "Error: Google Drive service not initialized."
        return render(request, 'setoo_app/manage_files.html', {'error_message': error_message})

    if request.method == 'POST':
        if 'add_jd' in request.POST and request.FILES.get('jd_file'):
            jd_file = request.FILES['jd_file']
            drive_file_id = upload_to_drive(service, jd_file, settings.JD_DRIVE_FOLDER_ID)
            if drive_file_id:
                jd = JD(original_filename=jd_file.name, drive_file_id=drive_file_id, drive_folder_id=settings.JD_DRIVE_FOLDER_ID)
                jd.save()

        elif 'add_resumes' in request.POST and request.FILES.getlist('resume_files'):
            resume_files = request.FILES.getlist('resume_files')
            for resume_file in resume_files:
                drive_file_id = upload_to_drive(service, resume_file, settings.RESUME_DRIVE_FOLDER_ID)
                if drive_file_id:
                    resume = Resume(original_filename=resume_file.name, drive_file_id=drive_file_id, drive_folder_id=settings.RESUME_DRIVE_FOLDER_ID)
                    resume.save()

        elif 'delete_jd' in request.POST:
            jd_id = request.POST.get('jd_to_delete')
            try:
                jd = JD.objects.get(pk=jd_id)
                if delete_file_from_drive(service, jd.drive_file_id):
                    jd.delete()
            except JD.DoesNotExist:
                pass

        elif 'delete_resume' in request.POST:
            resume_id = request.POST.get('resume_to_delete')
            try:
                resume = Resume.objects.get(pk=resume_id)
                if delete_file_from_drive(service, resume.drive_file_id):
                    resume.delete()
            except Resume.DoesNotExist:
                pass

        elif 'edit_jd' in request.POST:  # Handle JD editing
            jd_id = request.POST.get('jd_id')
            try:
                jd = JD.objects.get(pk=jd_id)
                # Implement your JD editing logic here (e.g., redirect to a form)
                # You'll likely need a separate view/template for editing.
            except JD.DoesNotExist:
                pass

        elif 'edit_resume' in request.POST:  # Handle Resume editing
            resume_id = request.POST.get('resume_id')
            try:
                resume = Resume.objects.get(pk=resume_id)
                # Implement your Resume editing logic here
                # You'll likely need a separate view/template for editing.
            except Resume.DoesNotExist:
                pass

        return redirect('manage_files')  # Redirect after POST

    jds = JD.objects.all()
    resumes = Resume.objects.all()

    context = {
        'jds': jds,
        'resumes': resumes,
        'openai_api_key': openai_api_key,
    }
    return render(request, 'setoo_app/manage_files.html', context)


def display_pdf(request, file_id):
    service = get_drive_service()
    if service is None:
        return HttpResponse("Google Drive service not initialized.", status=500)

    try:
        resume = Resume.objects.get(drive_file_id=file_id) # Get by drive_file_id
        file_content = fetch_file_content_from_drive(service, file_id) # Use drive_file_id

        if file_content:
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{resume.original_filename}"'
            response.write(file_content)
            return response
        else:
            return HttpResponse("File not found on Drive.", status=404)

    except Resume.DoesNotExist:
        return HttpResponse("Resume not found.", status=404)
    except Exception as e:
        return HttpResponse(f"Error displaying PDF: {e}", status=500)
