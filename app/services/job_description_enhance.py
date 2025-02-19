from app.utils.file_parser import parse_pdf_or_docx
from app.services.gpt_service import GPTService
from app.services.config_service import ConfigService
from io import BytesIO
from app.utils.logger import Logger
from app.models.schemas import EnhancedJobDescriptionSchema, CandidateProfileSchemaList
from datetime import datetime
from typing import List, Dict, Any

logger = Logger(__name__).get_logger()

class JobDescriptionEnhancer:
    """
    Service for extracting and enhancing job descriptions, followed by generating sample candidate profiles.
    """

    def __init__(self):
        """
        Initializes the Job Description Enhancer with GPT and OpenAI embeddings for vectorization.
        """
        logger.info("JobDescriptionEnhancer initialized successfully.")
        config = ConfigService()
        self.gpt_service = GPTService()
        self.temp_storage = {}  # Temporary storage for enhanced JD, generated candidates, and vectorized JD

    async def enhance_job_description(self, file_buffer: BytesIO, filename: str):
        """
        Extracts, enhances a job description, generates sample candidate profiles, and vectorizes the JD.

        Args:
            file_buffer (BytesIO): The job description file buffer.
            filename (str): Name of the uploaded job description file.

        Returns:
            Dict containing the enhanced job description, generated candidates, and vectorized JD.
        """
        try:
            # Extract the job description
            extracted_jd = await self.extract_job_description(file_buffer, filename)

            # Enhance the job description
            enhanced_jd = await self.generate_enhanced_jd(extracted_jd)

            # Generate 6 Sample Candidates based on enhanced JD
            candidates = await self.generate_candidate_profiles(enhanced_jd)

            # Vectorize the Enhanced JD for similarity comparisons
            vectorized_jd = await self.vectorize_job_description(enhanced_jd)

            # Store results in temp storage
            self.temp_storage["enhanced_job_description"] = enhanced_jd
            self.temp_storage["candidates"] = candidates
            self.temp_storage["vectorized_jd"] = vectorized_jd

            return {
                "enhanced_job_description": enhanced_jd,
                "generated_candidates": candidates,
                "vectorized_jd": vectorized_jd
            }

        except Exception as e:
            logger.error(f"Error enhancing job description '{filename}': {str(e)}", exc_info=True)
            raise

    async def extract_job_description(self, file_buffer: BytesIO, filename: str) -> Dict[str, Any]:
        """
        Extracts structured job description data.

        Args:
            file_buffer (BytesIO): Job description file buffer.
            filename (str): Uploaded job description file name.

        Returns:
            Dict containing extracted job description details.
        """
        try:
            # Extract text from file
            text = parse_pdf_or_docx(file_buffer, filename)
            today_date = datetime.now().strftime("%Y-%m-%d")

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
                 b. If experience is not explicitly mentioned, infer based on seniority level.

            2. **Skill Extraction**:
               - Extract both technical and soft skills.
               - Include tools, technologies, and methodologies mentioned.

            3. **Ensure Accuracy**:
               - Do not leave fields blank. Provide estimates or mark as 'Not mentioned' where needed.
               - Use contextual inference for missing values.
            """

            user_prompt = f"""
            Extract structured job description details from the following text:

            {text}

            Ensure structured formatting, extract all key details, and infer missing information where applicable.
            """

            extracted_jd = await self.gpt_service.extract_with_prompts(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=EnhancedJobDescriptionSchema
            )

            return extracted_jd

        except Exception as e:
            logger.error(f"Error extracting job description '{filename}': {str(e)}", exc_info=True)
            raise

    async def generate_enhanced_jd(self, extracted_jd: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhances extracted job descriptions.

        Args:
            extracted_jd (Dict[str, Any]): Extracted job description details.

        Returns:
            Dict containing enhanced job description.
        """
        try:
            system_prompt = f"""
            You are an AI expert at refining and enhancing job descriptions.
            Enhance clarity, structure, and detail of job descriptions.

            **Enhancement Guidelines**:
            - Responsibilities: Expand to **at least 10** clear, specific duties.
            - Required Skills: Identify **at least 15** relevant skills (technical & non-technical).
            - Key Metrics: Define **at least 10** measurable KPIs.
            - Ensure industry standards and structured formatting.

            Format the output in structured JSON format.
            """

            user_prompt = f"""
            Enhance this job description to be more structured and complete:

            {extracted_jd}
            """

            enhanced_jd = await self.gpt_service.extract_with_prompts(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=EnhancedJobDescriptionSchema
            )

            return enhanced_jd

        except Exception as e:
            logger.error(f"Error generating enhanced job description: {str(e)}", exc_info=True)
            raise

    async def generate_candidate_profiles(self, enhanced_jd: Dict[str, Any]) -> CandidateProfileSchemaList:
        """
        Generates sample candidate profiles based on the enhanced job description.

        Args:
            enhanced_jd (Dict[str, Any]): The enhanced job description.

        Returns:
            CandidateProfileSchemaList: List of sample candidate profiles.
        """
        try:
            system_prompt = f"""
            Generate six candidate profiles with varying qualification levels for the given job description.

            **Candidate Fit Levels**:
            - 10/10: Perfect match
            - 8/10: Strong match
            - 6/10: Moderate match
            - 4/10: Below average
            - 2/10: Weak match
            - 0/10: Not a fit

            Structure output as JSON.
            """

            user_prompt = f"""
            Generate sample candidates for this job description:

            {enhanced_jd}
            """

            candidates = await self.gpt_service.extract_with_prompts(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=CandidateProfileSchemaList
            )

            return candidates

        except Exception as e:
            logger.error(f"Error generating candidate profiles: {str(e)}", exc_info=True)
            raise

    async def vectorize_job_description(self, enhanced_jd: Dict[str, Any]) -> List[float]:
        """
        Converts the enhanced job description into a vectorized representation using OpenAI embeddings.

        Args:
            enhanced_jd (Dict[str, Any]): The enhanced job description.

        Returns:
            List[float]: Vectorized representation of the job description.
        """
        try:
            jd_text = f"""
            Job Title: {enhanced_jd.get('job_title', '')}
            Role Summary: {enhanced_jd.get('role_summary', '')}
            Responsibilities: {', '.join(enhanced_jd.get('responsibilities', []))}
            Required Skills: {', '.join(enhanced_jd.get('required_skills', []))}
            """

            vectorized_jd = await self.gpt_service.get_text_embedding(jd_text)
            return vectorized_jd

        except Exception as e:
            logger.error(f"Error vectorizing job description: {str(e)}", exc_info=True)
            return []
