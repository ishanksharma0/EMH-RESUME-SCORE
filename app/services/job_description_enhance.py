from app.utils.file_parser import parse_pdf_or_docx
from app.services.gpt_service import GPTService
from app.services.config_service import ConfigService
from io import BytesIO
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from app.utils.logger import Logger
from app.models.schemas import EnhancedJobDescriptionSchema, CandidateProfileSchemaList, JobDescriptionSchema
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
            structured_data = await self.extract_job_description(file_buffer, filename)

            # Enhance the job description
            enhanced_jd = await self.generate_enhanced_jd(structured_data)

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
            Ensure accurate data extraction and return structured JSON output there should be no contextual loss of information everything statedis to be given. 
            Today's date is {today_date}. Follow these rules:

            1. **Extract Fields**:
               - job_title: Extract the most relevant job title.
               - job_description: Provide the full job description text without any contextual loss at all with a word limit from 400-500 words.
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
            Enhance this job description to be more structured and complete
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
        Converts the enhanced job description into a vectorized representation using both OpenAI embeddings 
        and TF-IDF vectorization for increased accuracy.

        Args:
            enhanced_jd (Dict[str, Any]): The enhanced job description.

        Returns:
            List[float]: Vectorized representation of the job description.
        """
        try:
            # 🚀 **Extract Key Sections from JD**
            jd_title = enhanced_jd.get("job_title", "")
            jd_summary = enhanced_jd.get("role_summary", "")
            jd_responsibilities = ", ".join(enhanced_jd.get("responsibilities", []))
            jd_skills = ", ".join(enhanced_jd.get("required_skills", []))

            jd_text = f"""
            Job Title: {jd_title}
            Role Summary: {jd_summary}
            Responsibilities: {jd_responsibilities}
            Required Skills: {jd_skills}
            """

            # 🚀 **Step 1: Get GPT-based Embeddings (Deep Contextual Meaning)**
            gpt_embedding = await self.gpt_service.get_text_embedding(jd_text)
            if not gpt_embedding:
                logger.warning("GPT embedding failed, falling back to TF-IDF only.")
                return []

            # 🚀 **Step 2: TF-IDF Vectorization (Word-Level Representation)**
            vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
            tfidf_matrix = vectorizer.fit_transform([jd_text])
            tfidf_vector = tfidf_matrix.toarray()[0]  # Convert sparse matrix to dense array

            # 🚀 **Step 3: Combine GPT & TF-IDF Vectors**
            # Normalize both vectors for better scale consistency
            gpt_embedding = np.array(gpt_embedding) / np.linalg.norm(gpt_embedding)  # Normalize GPT vector
            tfidf_vector = tfidf_vector / np.linalg.norm(tfidf_vector)  # Normalize TF-IDF vector

            # Ensure both vectors are of the same length before concatenation
            if len(gpt_embedding) > len(tfidf_vector):
                tfidf_vector = np.pad(tfidf_vector, (0, len(gpt_embedding) - len(tfidf_vector)), 'constant')
            elif len(tfidf_vector) > len(gpt_embedding):
                gpt_embedding = np.pad(gpt_embedding, (0, len(tfidf_vector) - len(gpt_embedding)), 'constant')

            # 🚀 **Final Combined Vector**
            final_vector = np.concatenate((gpt_embedding, tfidf_vector))

            return final_vector.tolist()  # Convert NumPy array to a list

        except Exception as e:
            logger.error(f"Error vectorizing job description: {str(e)}", exc_info=True)
            return []
