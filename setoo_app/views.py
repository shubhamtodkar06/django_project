# views.py
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from .models import JD, Resume, Results
from django.contrib import messages
from .utils import (
    fetch_file_content_from_drive,
    upload_to_drive,
    delete_file_from_drive,
    get_drive_service,
    clean_and_structure_jd,
    extract_text_from_pdf,
    process_resumes_and_match_cosine ,  # Make sure to choose either process_resumes_and_match_cosine or process_resumes_and_match_agent in utils.py
    visualize_analytics
)
import json
import traceback

def get_api_key(request):
    if request.method == 'POST':
        api_key = request.POST.get('openai_api_key')
        if api_key:
            request.session['openai_api_key'] = api_key
            messages.success(request, "API key saved successfully.")
            return redirect('manage_files')
        else:
            messages.error(request, "API key is required.")
    return render(request, 'setoo_app/api_key_form.html')

def manage_files(request):
    openai_api_key = request.session.get('openai_api_key')

    if not openai_api_key:
        messages.error(request, "No OpenAI API key found in session.")
        return redirect('get_api_key')

    service = get_drive_service()

    if service is None:
        messages.error(request, "Error: Google Drive service not initialized.")
        return render(request, 'setoo_app/manage_files.html', {'jds': JD.objects.all(), 'resumes': Resume.objects.all(), 'openai_api_key': openai_api_key})

    if request.method == 'POST':
        if 'add_jd' in request.POST and request.FILES.get('jd_file'):
            jd_file = request.FILES['jd_file']
            try:
                drive_file_id = upload_to_drive(service, jd_file, settings.JD_DRIVE_FOLDER_ID)
                if drive_file_id:
                    jd = JD(original_filename=jd_file.name, drive_file_id=drive_file_id, drive_folder_id=settings.JD_DRIVE_FOLDER_ID)
                    jd.save()
                    messages.success(request, "JD uploaded successfully.")
                else:
                    messages.error(request, "Error uploading JD to Drive.")
            except IntegrityError:
                messages.error(request, f"A JD with that filename already exists.")
            except Exception as e:
                messages.error(request, f"Error uploading JD: {e}")

        elif 'add_resumes' in request.POST and request.FILES.getlist('resume_files'):
            resume_files = request.FILES.getlist('resume_files')
            for resume_file in resume_files:
                try:
                    drive_file_id = upload_to_drive(service, resume_file, settings.RESUME_DRIVE_FOLDER_ID)
                    if drive_file_id:
                        resume = Resume(original_filename=resume_file.name, drive_file_id=drive_file_id, drive_folder_id=settings.RESUME_DRIVE_FOLDER_ID)
                        resume.save()
                        messages.success(request, f"Resume {resume_file.name} uploaded successfully.") # Success message per file
                    else:
                        messages.error(request, f"Error uploading resume {resume_file.name} to Drive.")
                except IntegrityError:
                    messages.error(request, f"A resume with the filename '{resume_file.name}' already exists.")
                except Exception as e:
                    messages.error(request, f"Error uploading resume {resume_file.name}: {e}")

        elif 'delete_jd' in request.POST:
            jd_id = request.POST.get('jd_to_delete')
            try:
                jd = JD.objects.get(pk=jd_id)
                if delete_file_from_drive(service, jd.drive_file_id):
                    jd.delete()
                    messages.success(request, "JD deleted successfully.")
                else:
                    messages.error(request, "Error deleting JD file from Drive.")
            except JD.DoesNotExist:
                messages.error(request, "JD not found.")
            except Exception as e:
                messages.error(request, f"Error deleting JD: {e}")

        elif 'delete_resume' in request.POST:
            resume_id = request.POST.get('resume_to_delete')
            try:
                resume = Resume.objects.get(pk=resume_id)
                if delete_file_from_drive(service, resume.drive_file_id):
                    resume.delete()
                    messages.success(request, "Resume deleted successfully.")
                else:
                    messages.error(request, "Error deleting resume file from Drive.")
            except Resume.DoesNotExist:
                messages.error(request, "Resume not found.")
            except Exception as e:
                messages.error(request, f"Error deleting resume: {e}")

        elif 'process_and_analyze' in request.POST:
            jds = JD.objects.all()
            structured_data = {}
            for jd in jds:
                jd_content = fetch_file_content_from_drive(service, jd.drive_file_id)
                if jd_content:
                    jd_text = extract_text_from_pdf(jd_content, jd.original_filename)
                    if jd_text:
                        structured_data[jd.original_filename] = clean_and_structure_jd(jd_text, openai_api_key)

            resumes = Resume.objects.all()

            try:
                matched_resumes, unmatched_resumes, analytics = process_resumes_and_match_cosine ( # IMPORTANT: Make sure utils.py has your chosen matching function renamed to process_resumes_and_match
                    structured_data, resumes, service, openai_api_key  # Passed openai_api_key here!
                )

                # Handle "Insufficient information" cases *after* processing all resumes
                insufficient_info_resumes = []
                for role, matches in matched_resumes.items():
                    matches_to_remove = []  # Store indices of matches to remove
                    for i, match in enumerate(matches):
                        explanation = match.get('explanation', '')
                        if explanation.startswith("Insufficient"):  # More robust check
                            insufficient_info_resumes.append(match['resume_filename'])
                            matches_to_remove.append(i)

                    # Remove the matches in reverse order to avoid index issues
                    for i in sorted(matches_to_remove, reverse=True):
                        del matches[i]

                # Clean up empty roles (if any):
                roles_to_remove = []
                for role, matches in matched_resumes.items():
                    if not matches:  # If the list of matches is empty
                        roles_to_remove.append(role)

                for role in roles_to_remove:
                    del matched_resumes[role]


                # Remove empty roles after processing insufficient resumes
                matched_resumes = {k: v for k, v in matched_resumes.items() if v}


                if insufficient_info_resumes:
                    filenames_str = ", ".join(insufficient_info_resumes)
                    messages.error(request, f"The following resumes had insufficient information for a proper match: {filenames_str}. Please check and try again.")
                    # You might optionally log the insufficient_info_resumes for debugging

                results = Results.objects.create(
                    matched_resumes=matched_resumes,
                    unmatched_resumes=unmatched_resumes,
                    analytics=analytics,
                )
                messages.success(request, "Analysis completed successfully.")
                return redirect('analysis_results', results_id=results.id)

            except Exception as e:
                messages.error(request, f"Error during analysis: {e}")
                traceback.print_exc()

            return redirect('manage_files')  # Redirect even if there are errors


        elif 'edit_jd' in request.POST:
            jd_id = request.POST.get('jd_id')
            try:
                jd = JD.objects.get(pk=jd_id)
                # Redirect to JD edit form (not implemented here)
                return redirect('edit_jd_form', jd_id=jd_id)  # Replace 'edit_jd_form' with your URL name
            except JD.DoesNotExist:
                messages.error(request, "JD not found.")

        elif 'edit_resume' in request.POST:
            resume_id = request.POST.get('resume_id')
            try:
                resume = Resume.objects.get(pk=resume_id)
                # Redirect to Resume edit form (not implemented here)
                return redirect('edit_resume_form', resume_id=resume_id)  # Replace 'edit_resume_form' with your URL name
            except Resume.DoesNotExist:
                messages.error(request, "Resume not found.")

        return redirect('manage_files')

    jds = JD.objects.all()
    resumes = Resume.objects.all()
    context = {'jds': jds, 'resumes': resumes, 'openai_api_key': openai_api_key}
    return render(request, 'setoo_app/manage_files.html', context)


def analysis_results(request, results_id):
    results = get_object_or_404(Results, pk=results_id)

    matched_resumes = results.matched_resumes or {}
    unmatched_resumes = results.unmatched_resumes or []

    analytics_display_data = {}
    total_applications = 0
    total_passed = 0

    if results.analytics:
        try:
            analytics_data = json.loads(results.analytics) if isinstance(results.analytics, str) else results.analytics

            for role, data in analytics_data.items():  # Correctly iterate through the dictionary
                if isinstance(data, dict): # Check if it is a dictionary
                    applied_count = data.get('applied_count', 0)  # Safe access with default
                    passed_count = data.get('passed_count', 0)     # Safe access with default
                    analytics_display_data[role] = {
                        "applied_count": applied_count,
                        "passed_count": passed_count,
                    }
                    total_applications += applied_count
                    total_passed += passed_count
                else:
                    print(f"Warning: Unexpected data format for role '{role}': {data}") # Log warning
                    messages.error(request, "Error processing analytics data. Please check logs.")
                    analytics_display_data = {} # Reset to empty to avoid further errors
                    break # Exit the loop to avoid further errors

            # Visualize the analytics data (only if there's data and no errors):
            if analytics_display_data: # Check if there is data after error handling
                plot_filename = visualize_analytics(analytics_display_data)
            else:
                plot_filename = None

        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            print(f"Error processing analytics data: {e}. Raw data: {results.analytics}")
            analytics_display_data = {}  # Reset to empty on error
            messages.error(request, "Error processing analytics data.")
            plot_filename = None # Set to None if plot generation fails
    context = {
        'matched_resumes': matched_resumes,
        'unmatched_resumes': unmatched_resumes,
        'analytics_display_data': analytics_display_data,
        'total_applications': total_applications,
        'total_passed': total_passed,
        'results_id': results_id,
        'plot_filename': plot_filename,  # Add the plot filename to the context
    }

    return render(request, 'setoo_app/analysis_results.html', context)


from django.shortcuts import render, get_object_or_404
from .models import Results  # Import your Results model

def display_top_resumes(request, results_id):
    try:
        results = get_object_or_404(Results, pk=results_id)
        matched_resumes = results.matched_resumes or {}  # Handle cases where matched_resumes is None
        available_roles = list(matched_resumes.keys())

        if request.method == 'POST':
            role_name = request.POST.get('role')
            top_n = int(request.POST.get('count', 5))  # Default to 5 if count is not provided

            top_resumes = matched_resumes.get(role_name, [])

            # Sort by score (if present), otherwise by filename (as a fallback)
            sorted_resumes = sorted(top_resumes, key=lambda x: x.get('score', 0) if isinstance(x, dict) and x.get('score', 0) is not None else (x.get('score', 0) if isinstance(x, dict) else 0), reverse=True)

            top_resumes_to_display = []
            for match in sorted_resumes[:top_n]:
                top_resumes_to_display.append({
                    'resume': match.get('resume', {}),  # Handle cases where 'resume' might be missing or not a dict
                    'similarity_score': match.get('score', 0),
                })


            context = {
                'role_name': role_name,
                'top_resumes': top_resumes_to_display,
                'available_roles': available_roles,
                'results_id': results_id,
            }
            return render(request, 'setoo_app/top_resumes.html', context)

        context = {'available_roles': available_roles, 'results_id': results_id}
        return render(request, 'setoo_app/top_resumes.html', context)

    except Results.DoesNotExist:
        messages.error(request, "Results not found.")  # Use messages framework
        return redirect('manage_files')  # Redirect on error
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")  # Use messages framework
        traceback.print_exc()  # Print traceback for debugging
        return redirect('manage_files')  # Redirect on error