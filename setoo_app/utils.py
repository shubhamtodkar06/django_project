import os
import tempfile
from googleapiclient.http import MediaFileUpload
import io
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import time
import PyPDF2
import re
from langchain.llms import OpenAI
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
import json
import matplotlib.pyplot as plt
import uuid  # For generating unique filenames


# Global Drive service variable
service = None

def get_drive_service():
    """Initializes and returns the Google Drive API service."""
    global service
    if service:
        return service  # Return existing service if already initialized

    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_DRIVE_CREDENTIALS_FILE, scopes=settings.GOOGLE_DRIVE_SCOPES)

    try:
        service = build('drive', 'v3', credentials=creds)
        print("Connected to Google Drive!")
        return service
    except Exception as e:
        print(f"Error initializing Google Drive service: {e}")
        return None

def upload_to_drive(service, uploaded_file, drive_folder_id):
    """
    Uploads a file to Google Drive, handling temporary file creation and cleanup,
    with retry logic for deletion on failure.

    Args:
        service: Google Drive service object.
        uploaded_file: Django UploadedFile object.
        drive_folder_id: ID of the Google Drive folder to upload to.

    Returns:
        str: Google Drive file ID of the uploaded file, or None on error.
    """
    if service is None:
        print("Google Drive service not initialized. Cannot upload file.")
        return None

    try:
        file_metadata = {'name': uploaded_file.name, 'parents': [drive_folder_id]}
        temp_file_path = None
        temp_file = None  # Declare temp_file outside the with block

        try: # Start of inner try block for file operations and Drive upload
            print(f"UPLOAD START: Creating temp file for {uploaded_file.name}...")
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") # Create temp file, but don't delete automatically on close yet
            temp_file_path = temp_file.name # Get the temporary file path immediately
            print(f"UPLOAD PROGRESS: Temp file created at {temp_file_path}")

            print(f"UPLOAD PROGRESS: Writing content to temp file {temp_file_path}...")
            for chunk in uploaded_file.chunks(): # Iterate through file chunks from Django upload
                temp_file.write(chunk) # Write each chunk to the temp file

            print(f"UPLOAD PROGRESS: Explicitly closing temp file {temp_file_path} BEFORE upload...")
            temp_file.close() # Important: Explicitly close the temp file object to release file handle

            print(f"UPLOAD PROGRESS: Starting Google Drive upload from {temp_file_path}...")
            media = MediaFileUpload(temp_file_path, mimetype=uploaded_file.content_type) # Prepare media upload from temp file path
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute() # Execute the Drive file creation request
            drive_file_id = file.get('id') # Get the Drive file ID from the response
            print(f"UPLOAD SUCCESS: File ID: {drive_file_id} for {uploaded_file.name}")
            return drive_file_id # Return the Drive file ID on successful upload

        finally:  # Cleanup block - Executes whether upload succeeds or fails (within the inner try block)
            if temp_file_path: # Check if temp_file_path was actually created
                print(f"CLEANUP START: Attempting to remove temp file {temp_file_path} for {uploaded_file.name}...")
                max_retries = 5  # Number of retry attempts for deletion
                retry_delay = 2  # Delay between retry attempts in seconds
                for retry_attempt in range(max_retries): # Retry loop for file deletion
                    try:
                        time.sleep(retry_delay)  # Wait before attempting deletion
                        os.remove(temp_file_path) # Attempt to delete the temporary file
                        print(f"CLEANUP SUCCESS: Temp file {temp_file_path} removed after {retry_attempt+1} attempt(s) for {uploaded_file.name}")
                        break  # If deletion succeeds, exit the retry loop
                    except Exception as e_delete: # Catch any exception during deletion
                        if retry_attempt < max_retries - 1: # If not the last retry attempt
                            print(f"CLEANUP RETRY {retry_attempt+2}/{max_retries}: Error removing temp file {temp_file_path} for {uploaded_file.name}: {e_delete}. Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay) # Wait before retrying
                        else: # Last retry attempt failed
                            print(f"CLEANUP ERROR: Final attempt failed to remove temp file {temp_file_path} for {uploaded_file.name} after {max_retries} retries: {e_delete}")
                            break # Exit retry loop after final failure
                else: # else block of for loop: Executed if loop completes without 'break' (deletion successful in one of the retries)
                    pass # Deletion was successful in one of the retries, no further action needed
                # No need for a nested finally block here - the outer finally already ensures cleanup
                if temp_file and not temp_file.closed: # Ensure temp_file is closed in case of errors before explicit close
                    temp_file.close() # Ensure temp_file is closed in finally block as well

    except Exception as e: # Catch any errors during the entire upload process (outer try block)
        print(f"UPLOAD ERROR: General error during Drive upload for {uploaded_file.name}: {e}")
        return None # Return None to indicate upload failure
    
def delete_file_from_drive(service, file_id):
    if service is None:
        print("Google Drive service not initialized. Cannot delete file.")
        return False

    try:
        service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting file from Drive: {e}")
        return False


def fetch_file_content_from_drive(service, file_id):
    if service is None:
        print("Google Drive service not initialized. Cannot fetch file.")
        return None

    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))
        fh.seek(0)
        return fh.getvalue()
    except Exception as e:
        print(f"Error fetching file from Google Drive: {e}")
        return None

def extract_text_from_pdf(file_content, filename="document.pdf"):
    """Extracts text content from a PDF file content."""
    try:
        pdf_file = io.BytesIO(file_content)
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF {filename}: {e}")
        return None

def clean_and_structure_jd(jd_text, openai_api_key):
    """Cleans and structures job description text using OpenAI."""

    parser = StructuredOutputParser.from_response_schemas([
        ResponseSchema(name="job_title", description="Job title as extracted from the job description"),
        ResponseSchema(name="department", description="Department or team for this job"),
        ResponseSchema(name="responsibilities", description="Key responsibilities and tasks"),
        ResponseSchema(name="skills", description="Technical and soft skills required"),
        ResponseSchema(name="experience", description="Years and type of experience needed"),
        ResponseSchema(name="education", description="Educational qualifications required"),
    ])

    format_instructions = parser.get_format_instructions()

    prompt = f"""
    Your task is to parse the text of a job description and extract key information, structuring it in JSON format.
    Ensure that the extracted information is concise and directly answers the categories. If a category is not mentioned, leave it blank.

    Text of Job Description:
    ```text
    {jd_text}
    ```

    Structure your output to match the following format instructions:
    {format_instructions}
     কনসistent formatting in the JSON output, especially with lists and descriptions.
     কাঠামোগত আউটপুট শুধুমাত্র JSON বিন্যাসে প্রদান করুন। অন্য কোনো ফর্ম্যাট গ্রহণযোগ্য নয়।
    """

    llm = OpenAI(openai_api_key=openai_api_key)
    response = llm(prompt)

    try:
        structured_output = parser.parse(response)
        return structured_output
    except Exception as e:
        print(f"Error parsing OpenAI response: {e}, Response was: {response}")
        return {"error": "Failed to parse structured output from OpenAI", "raw_response": response}


def process_resumes_and_match_cosine(roles_data, resumes, service, openai_api_key): # Example Cosine Similarity based function (rename this to process_resumes_and_match to use)
    """Processes resumes, matches them to job descriptions using cosine similarity (example), and generates analytics."""
    # Placeholder for cosine similarity based matching logic.
    # Replace with your actual cosine similarity implementation.
    matched_resumes = {}
    unmatched_resumes = []
    analytics = {}

    print("process_resumes_and_match_cosine function is a placeholder. Implement your cosine similarity matching logic here.")
    messages = [] # Placeholder for messages

    # Example structure for matched_resumes (replace with your actual logic results)
    for role_name in roles_data.keys():
        matched_resumes[role_name] = [] # Initialize empty list for each role

    for resume in resumes:
        # ... (Your cosine similarity matching logic here to compare resume to each JD in roles_data) ...
        # ... (Determine best role match based on cosine similarity score) ...

        best_role_match = None # Replace with your logic to find the best match or None if no match
        similarity_score = 0.0 # Replace with your similarity score

        if best_role_match:
            matched_resumes[best_role_match].append({
                'resume_filename': resume.original_filename,
                'resume': {"id": resume.id, "filename": resume.original_filename}, # Basic resume info
                'role': best_role_match,
                'score': similarity_score, # Example score
                'explanation': f"Matched to {best_role_match} role based on cosine similarity score: {similarity_score:.2f} (Example Explanation - Replace with actual)", # Example explanation
                # ... (Add more details as needed)
            })
        else:
            unmatched_resumes.append(resume.original_filename)


    analytics = generate_analytics(matched_resumes)

    return matched_resumes, unmatched_resumes, analytics


def process_resumes_and_match_agent(roles_data, resumes, service, openai_api_key): # Example Agent-based matching function (rename this to process_resumes_and_match to use)
    """Processes resumes, matches them to job descriptions using an agent-based approach (example), and generates analytics."""
    # Placeholder for agent-based matching logic.
    # Replace with your actual agent-based implementation using Langchain Agents or similar.
    matched_resumes = {}
    unmatched_resumes = []
    analytics = {}

    print("process_resumes_and_match_agent function is a placeholder. Implement your Agent-based matching logic here.")
    messages = [] # Placeholder messages

    # Example structure (replace with your agent-based matching results)
    for role_name in roles_data.keys():
        matched_resumes[role_name] = [] # Initialize empty list for each role

    for resume in resumes:
        # ... (Your agent-based matching logic using LLMs and potentially Langchain Agents) ...
        # ... (Agent should decide on best role match and provide explanation) ...

        best_role_match = None # Replace with agent's role decision
        match_explanation = "Agent determined this is a good match. (Example Explanation - Replace with actual agent's explanation)" # Replace with agent's explanation
        match_score = 0.85 # Example score from agent (if applicable)


        if best_role_match:
            matched_resumes[best_role_match].append({
                'resume_filename': resume.original_filename,
                'resume': {"id": resume.id, "filename": resume.original_filename}, # Basic resume info
                'role': best_role_match,
                'score': match_score, # Example score - agent might provide a score or confidence
                'explanation': match_explanation, # Agent's detailed explanation for the match
                # ... (Add more details from agent output if needed)
            })
        else:
            unmatched_resumes.append(resume.original_filename)

    analytics = generate_analytics(matched_resumes)

    return matched_resumes, unmatched_resumes, analytics


def generate_analytics(matched_resumes):
    """Generates analytics data from matched resumes."""
    analytics_data = {}
    for role, matches in matched_resumes.items():
        analytics_data[role] = {
            "applied_count": len(matches), # In this example, 'applied_count' is same as matched count - adjust as per your logic if needed
            "passed_count": len(matches), # Assuming all matched resumes are considered 'passed' for this basic analytics - adjust as needed
        }
    return analytics_data


def visualize_analytics(analytics_display_data):
    """
    Generates a bar chart visualizing resume application analytics.

    Args:
        analytics_display_data (dict): A dictionary where keys are role names
                                      and values are dictionaries containing
                                      'applied_count' and 'passed_count'.

    Returns:
        str: The filename (relative path under MEDIA_URL) of the generated plot image,
             or None if there's an error.
    """
    try:
        role_names = list(analytics_display_data.keys())
        applied_counts = [data['applied_count'] for data in analytics_display_data.values()]
        passed_counts = [data['passed_count'] for data in analytics_display_data.values()]

        # Set up matplotlib figure and axes
        fig, ax = plt.subplots(figsize=(10, 6))  # Adjust figure size as needed

        # Bar chart parameters
        bar_width = 0.35
        index = range(len(role_names))

        # Create bars for Applied and Passed counts
        bar1 = ax.bar(index, applied_counts, bar_width, label='Applied Resumes', color='#4c72b0') # Example colors
        bar2 = ax.bar([i + bar_width for i in index], passed_counts, bar_width, label='Matched Resumes', color='#dd8452')

        # Customize the plot
        ax.set_xlabel('Job Roles', fontsize=12)
        ax.set_ylabel('Number of Resumes', fontsize=12)
        ax.set_title('Resume Application Analytics', fontsize=14)
        ax.set_xticks([i + bar_width / 2 for i in index])
        ax.set_xticklabels(role_names, rotation=45, ha="right", fontsize=10) # Rotate role names for better readability
        ax.legend(fontsize=10)

        # Add data labels on top of the bars
        def add_labels(bars):
            for bar in bars:
                height = bar.get_height()
                ax.annotate('{}'.format(height),
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=9)

        add_labels(bar1)
        add_labels(bar2)


        # Save the plot to a file in MEDIA_ROOT/analytics_plots
        plot_filename = f"analytics_plot_{uuid.uuid4().hex}.png" # Generate a unique filename
        plot_filepath = os.path.join(settings.MEDIA_ROOT, 'analytics_plots', plot_filename)
        os.makedirs(os.path.dirname(plot_filepath), exist_ok=True) # Ensure directory exists

        plt.tight_layout() # Adjust layout to fit everything nicely
        plt.savefig(plot_filepath, bbox_inches='tight') # bbox_inches='tight' to prevent labels getting cut off
        plt.close(fig)  # Close the figure to free up memory

        return os.path.join('analytics_plots', plot_filename) # Return relative path for template

    except Exception as e:
        print(f"Error generating analytics visualization: {e}")
        return None