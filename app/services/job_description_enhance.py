from app.utils.file_parser import parse_pdf_or_docx
from app.services.neo4j_service import Neo4jService
from app.services.gpt_service import GPTService
from app.services.config_service import ConfigService
from typing import List, Dict, Any
from io import BytesIO
from app.utils.logger import Logger
from app.models.schemas import EnhancedJobDescriptionSchema, CandidateProfileSchemaList, JobDescriptionSchema
from datetime import datetime
import numpy as np

logger = Logger(__name__).get_logger()

# Cosine similarity function
def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    if not np.any(vec1) or not np.any(vec2):
        return 0.0
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

class JobDescriptionEnhancer:
    """
    Service for extracting and enhancing job descriptions, followed by generating sample candidate profiles.
    """

    def __init__(self):
        """
        Initializes the Job Description Enhancer with GPT and Neo4j.
        """
        logger.info("JobDescriptionEnhancer initialized successfully.")
        config = ConfigService()
        self.gpt_service = GPTService()
        self.neo4j_service = Neo4jService()
        self.temp_storage = {}  # Temporary storage for enhanced JD and generated candidates

    async def enhance_job_description(self, file_buffer: BytesIO, filename: str):
        """
        Extracts, enhances a job description, generates sample candidate profiles, vectorizes JD, and stores in Neo4j.

        Args:
            file_buffer (BytesIO): The job description file buffer.
            filename (str): Name of the uploaded job description file.

        Returns:
            Dict containing the enhanced job description, generated candidates, and vectorized JD.
        """
        try:
            # Extract the job description
            structured_data = await self.extract_job_description(file_buffer, filename)

            # Enhance the job description
            enhanced_jd = await self.generate_enhanced_jd(structured_data)

            # Generate 6 Sample Candidates based on enhanced JD
            candidates = await self.generate_candidate_profiles(enhanced_jd)

            # Store Job Role & Skills in Neo4j
            job_title = enhanced_jd["job_title"]
            required_skills = enhanced_jd["required_skills"]

            # Vectorize job description for similarity comparison
            vectorized_jd = await self.vectorize_job_description(enhanced_jd)

            # Store the enhanced job description, generated candidates, and vectorized JD
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
            Ensure accurate data extraction and return structured JSON output without any contextual loss of information.
            Today's date is {today_date}. Follow these rules:

            1. **Extract Fields**:
               - job_title: Extract the most relevant job title.
               - job_description: Provide the full job description text without any contextual loss, with a word limit of 400-500 words.
               - required_skills:
                 a. Identify explicitly mentioned skills.
                 b. Infer essential skills based on job context.
               - min_work_experience:
                 a. If a minimum experience requirement is stated, extract it.
                 b. If experience is not explicitly mentioned, infer based on seniority level.

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
            Extract structured job description details from the following text without contextual loss of any information:

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

    async def generate_enhanced_jd(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhances extracted job descriptions.

        Args:
            structured_data (Dict[str, Any]): Extracted job description details.

        Returns:
            Dict containing enhanced job description.
        """
        try:
            system_prompt = f"""
            You are an AI expert at refining and enhancing job descriptions.
            Enhance clarity, structure, and detail of job descriptions.
            ENSURE NO CONTEXTUAL LOSS IS DONE AT ALL.

            **Enhancement Guidelines**:
            - Responsibilities: Expand to **at least 10** clear, specific duties.
            - Required Skills: Identify **at least 15** relevant skills (technical & non-technical).
            - Key Metrics: Define **at least 10** measurable KPIs.
            - Ensure industry standards and structured formatting.

            Format the output in structured JSON format.
            """

            user_prompt = f"""
            Enhance this job description to be more structured and complete.
            ENSURE NO CONTEXTUAL LOSS IS DONE AT ALL:

            {structured_data}
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
        Vectorizes the enhanced job description for similarity comparisons.
        """
        try:
            jd_text = (
                f"{enhanced_jd.get('job_title', '')} "
                f"{enhanced_jd.get('role_summary', '')} "
                f"{' '.join(enhanced_jd.get('responsibilities', []))} "
                f"{' '.join(enhanced_jd.get('required_skills', []))}"
            )

            vectorized_jd = await self.gpt_service.get_text_embedding(jd_text)
            return vectorized_jd

        except Exception as e:
            logger.error(f"Error vectorizing JD: {str(e)}", exc_info=True)
            return []

    async def similarity_between_job_descriptions(self, jd_text1: str, jd_text2: str) -> float:
        """
        Computes cosine similarity between two job descriptions.
        """
        try:
            embedding1 = await self.gpt_service.get_text_embedding(jd_text1)
            embedding2 = await self.gpt_service.get_text_embedding(jd_text2)

            similarity = cosine_similarity(np.array(embedding1), np.array(embedding2))
            return round(similarity, 3)

        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}", exc_info=True)
            return 0.0
