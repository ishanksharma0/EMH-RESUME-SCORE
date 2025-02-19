from fastapi import FastAPI, HTTPException, File, UploadFile, Depends
from io import BytesIO
from typing import List
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from app.services.resume_extraction import ResumeParser
from app.services.jd_extraction_helper import JobDescriptionParser
from app.services.job_description_enhance import JobDescriptionEnhancer
from app.services.resume_scoring import ResumeScoringService
from app.utils.logger import Logger

# Initialize Logger
logger = Logger(__name__).get_logger()

# Initialize FastAPI App
app = FastAPI(
    title="Resume and Job Description Processing API",
    description="API for extracting, enhancing, and scoring resumes and job descriptions",
    version="1.0.0"
)

# Serve static files (HTML UI)
app.mount("/static", StaticFiles(directory="app"), name="static")

@app.get("/")
async def serve_ui():
    return FileResponse(os.path.join("app", "index.html"))

# Initialize Services
resume_parser = ResumeParser()
jd_parser = JobDescriptionParser()
job_description_enhancer = JobDescriptionEnhancer()
resume_scoring_service = ResumeScoringService(job_description_enhancer)

@app.get("/")
async def root():
    return {"message": "Resume and JD Processing API is running!"}

### **Resume Parsing Endpoint**
@app.post("/api/parse-resume/")
async def parse_resume(file: UploadFile = File(...)):
    """
    Endpoint to parse a resume file (PDF, DOCX, DOC, image) and return structured JSON output.
    """
    try:
        # Read the file into a BytesIO buffer
        file_buffer = BytesIO(await file.read())  
        filename = file.filename

        # Call the resume parser service
        result = await resume_parser.parse_resume(file_buffer, filename)
        return result
    except Exception as e:
        logger.error(f"Error parsing resume file '{file.filename}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error parsing resume: {str(e)}")

### **Job Description Parsing Endpoint**
@app.post("/api/parse-job-description/")
async def parse_job_description(file: UploadFile = File(...)):
    """
    Endpoint to parse a job description file (PDF or DOCX) and return structured JSON output.
    """
    try:
        # Read the file into a BytesIO buffer
        file_buffer = BytesIO(await file.read())
        filename = file.filename

        # Call the job description parser service
        result = await jd_parser.parse_job_description(file_buffer, filename)
        return result
    except Exception as e:
        logger.error(f"Error parsing job description file '{file.filename}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error parsing job description: {str(e)}")

### **Job Description Enhancement Endpoint**
@app.post("/api/job-description-enhance/")
async def job_description_enhance(file: UploadFile = File(...)):
    """
    Endpoint to enhance a job description by extracting and structuring details, 
    improving clarity, and generating sample candidate profiles.
    """
    try:
        # Read the file into a BytesIO buffer
        file_buffer = BytesIO(await file.read())
        filename = file.filename

        # Call the JD enhancement service
        result = await job_description_enhancer.enhance_job_description(file_buffer, filename)
        return result
    except Exception as e:
        logger.error(f"Error enhancing job description '{file.filename}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error enhancing job description: {str(e)}")

### **Resume Scoring Endpoint**
@app.post("/api/score-resumes/")
async def score_resumes(files: List[UploadFile] = File(...)):
    """
    Endpoint to score multiple resumes against an enhanced job description and sample candidate profiles.
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No resume files provided.")

        # Read the uploaded files into buffers
        resume_files = [BytesIO(await file.read()) for file in files]
        filenames = [file.filename for file in files]

        # Call the resume scoring service
        result = await resume_scoring_service.process_bulk_resumes(resume_files, filenames)
        return result
    except Exception as e:
        logger.error(f"Error scoring resumes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error scoring resumes: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Resume and JD Processing API")
    uvicorn.run(app, host="0.0.0.0", port=8000)
