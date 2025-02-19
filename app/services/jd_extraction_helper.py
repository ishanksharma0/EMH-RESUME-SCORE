from app.utils.file_parser import parse_pdf_or_docx
from app.services.gpt_service import GPTService
from app.services.config_service import ConfigService
from io import BytesIO
from app.utils.logger import Logger
from app.models.schemas import JobDescriptionSchema
from datetime import datetime

logger = Logger(__name__).get_logger()

class JobDescriptionParser:
    """
    Service for extracting structured information from job descriptions.
    """
    def __init__(self):
        """
        Initializes the Job Description Parser with GPT integration.
        """
        logger.info("JobDescriptionParser initialized successfully.")
        config = ConfigService()
        self.gpt_service = GPTService()

    async def parse_job_description(self, file_buffer: BytesIO, filename: str):
        """
        Parses a job description file and extracts structured information.
        Args:
            file_buffer (BytesIO): The job description file buffer.
            filename (str): Name of the uploaded job description file.
        
        Returns:
            Dict containing structured job description data.
        """
        try:
            text = parse_pdf_or_docx(file_buffer, filename)
            today_date = datetime.now().strftime("%Y-%m-%d")

            # System Prompt
            system_prompt = f"""
            You are an AI model specialized in extracting structured job descriptions. 
            Ensure accurate data extraction and return structured JSON output. 
            Today's date is {today_date}. Follow these rules:

            1. **Extract Fields**:
               - job_title: Extract the most relevant job title.
               - job_description: Provide the full job description text.
               - required_skills:
                 a. Identify explicitly mentioned skills.
                 b. Infer essential skills based on job context.
               - min_work_experience:
                 a. If a minimum experience requirement is stated, extract it.
                 b. If experience is not explicitly mentioned, infer based on seniority level (e.g., 'entry-level' = 0-2 years, 'mid-level' = 3-5 years, 'senior-level' = 6+ years).

            2. **Skill Extraction**:
               - Extract both technical and soft skills.
               - Include tools, technologies, and methodologies mentioned.

            3. **Work Experience Calculation**:
               - Ensure the experience field is formatted in numeric terms (e.g., '2 years' or '5+ years').
               - Infer experience if not explicitly stated using industry norms.

            4. **Ensure Accuracy**:
               - Do not leave fields blank. Provide estimates or mark as 'Not mentioned' where needed.
               - Use contextual inference for missing values.

            5. **Formatting**:
               - Ensure structured JSON output with no missing fields.
               - Provide clean, human-readable formatting.
            """

            # User Prompt
            user_prompt = f"""
            Extract structured job description details from the following text:

            {text}

            Ensure structured formatting, extract all key details, and infer missing information where applicable.
            """

            # Call GPT Service
            structured_data = await self.gpt_service.extract_with_prompts(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=JobDescriptionSchema
            )

            return structured_data  

        except Exception as e:
            logger.error(f"Error parsing job description file '{filename}': {str(e)}", exc_info=True)
            raise
