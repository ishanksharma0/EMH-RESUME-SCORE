from app.utils.file_parser import parse_pdf_or_docx
from app.services.gpt_service import GPTService
from app.services.config_service import ConfigService
from app.services.neo4j_service import Neo4jService
from io import BytesIO
from app.utils.logger import Logger
from app.models.schemas import ResumeSchema, ResumeScoringSchema
from datetime import datetime
from typing import List, Dict, Any
import numpy as np

logger = Logger(__name__).get_logger()

# Cosine similarity function
def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    """
    if not np.any(vec1) or not np.any(vec2):
        return 0.0
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

class ResumeScoringService:
    """
    Service for extracting structured resume details, scoring resumes against the enhanced job description 
    and sample candidates, and returning a structured comparison report.
    """

    def __init__(self, job_description_enhancer):
        """
        Initializes the Resume Scoring Service with GPT integration.
        """
        logger.info("ResumeScoringService initialized successfully.")
        config = ConfigService()
        self.gpt_service = GPTService()
        self.job_description_enhancer = job_description_enhancer  # Reference to Enhanced JD & Candidates
        self.neo4j_service = Neo4jService()  # Initialize Neo4j connection

    async def process_bulk_resumes(self, resume_files: List[BytesIO], filenames: List[str], user_input: str) -> List[Dict[str, Any]]:
        """
        Processes multiple resumes, extracts structured data, stores in Neo4j, and compares them to the enhanced job description.

        Args:
            resume_files (List[BytesIO]): List of resume file buffers.
            filenames (List[str]): Corresponding filenames.
            user_input (str): Additional input provided by the user.

        Returns:
            List of structured resume analysis results with scores and comparisons.
        """
        try:
            if "enhanced_job_description" not in self.job_description_enhancer.temp_storage:
                raise ValueError("Enhanced Job Description not found. Run /api/job-description-enhance first.")

            enhanced_jd = self.job_description_enhancer.temp_storage["enhanced_job_description"]
            generated_candidates = self.job_description_enhancer.temp_storage["candidates"]

            results = []
            for file_buffer, filename in zip(resume_files, filenames):
                logger.info(f"Processing resume file: {filename}")

                # **Extract Resume Data**
                extracted_resume = await self.parse_resume(file_buffer, filename)

                # **Store Candidate Resume in Neo4j**
                candidate_name = extracted_resume.get("candidate_name", "Unknown")
                skills = extracted_resume.get("skills", {}).get("primary_skills", [])
                experience_years = extracted_resume.get("work_experience", {}).get("years", 0)

                self.neo4j_service.add_candidate_resume(candidate_name, skills, experience_years)  # ✅ Store in Neo4j

                # **Retrieve Relevant Candidates from Neo4j for Comparison**
                matching_candidates = self.neo4j_service.find_candidates_by_job(enhanced_jd["job_title"])

                # **Combine user input, enhanced JD, and candidates in priority order**
                combined_criteria = f"{user_input}\n\n{enhanced_jd}\n\n{matching_candidates}"

                # **Compare Resume Against User Input > JD > Neo4j Candidates**
                resume_comparison = await self.score_resume(extracted_resume, combined_criteria, matching_candidates)

                similarity_score = await self.compute_similarity(extracted_resume, enhanced_jd)

                # **Store Results**
                resume_comparison["cosine_similarity"] = similarity_score
                results.append(resume_comparison)

            return results

        except Exception as e:
            logger.error(f"Error processing resumes: {str(e)}", exc_info=True)
            raise

    async def parse_resume(self, file_buffer: BytesIO, filename: str) -> Dict[str, Any]:
        """
        Parses a resume file and extracts structured information.

        Args:
            file_buffer (BytesIO): The resume file buffer.
            filename (str): Name of the uploaded resume file.

        Returns:
            Dict containing structured resume data.
        """
        try:
            text = parse_pdf_or_docx(file_buffer, filename)
            today_date = datetime.now().strftime("%Y-%m-%d")

            system_prompt = f"""
            You are an AI model specializing in extracting structured information from resumes.
            Parse the text and produce a JSON structure with these top-level fields, each of the following keys must be present:
            1) candidate_name (string) — Full name, ensure spaces between first and last names if applicable.
            2) email_address (string) - The email should be a valid email address with a "@" symbol and a domain name (gmail, outlook, etc..).
            3) phone_number (string) - should be a valid phone number with country codes (default is +91 if none given) first, followed by a space and then the number.
            4) work_experience (object containing 'years' (number) and 'months' (number)) - Ensure that overlapping work periods are handled correctly.
            5) educations_duration (object containing 'years' (number) and 'months' (number)) — Calculate the correct total duration for education.
            6) experiences (array of objects):
                Each experience must include:
                - title (string),
                - company (string),
                - description (string),
                - date_start (string),
                - date_end (string),
                - skills (array of strings),
                - tasks (array of strings)
            7) educations (array of objects):
                - institution (string),
                - title (string),
                - date_start (string),
                - date_end (string),
                - skills (string),
                - tasks (string)
            8) social_urls (array of objects, each with:
                - type (string),
                - url (string)
            9) languages (array of objects, each with:
                - name (string)
            10) skills (object containing 'primary_skills' (array of strings) and 'secondary_skills' (array of strings))

            Key instructions for duration calculations:
            - Calculate work_experience and educations_duration based on the start and end dates. Ensure that consecutive periods (without gaps) are treated as distinct and add up the durations without including the gap between roles.
            - If "present," "ongoing," or similar terms like these are mentioned, then use today's date {today_date} as the date_end and calculate the duration accordingly.
            """

            user_prompt = f"""
            Extract structured information from this resume text:
            {text}
            Follow these instructions:
            1. Parse the text and extract structured information according to the keys mentioned above.
            2. Ensure that the total work experience is calculated accurately by accounting for overlaps and distinct periods.
            3. Handle ongoing periods by comparing "present" with today's date and calculating the accurate duration.
            4. For overlapping roles, calculate the total unique time worked without double-counting.
            5. For education durations, calculate accurately.
            6. Ensure no missing fields, and if any information is not provided, use null or empty arrays.
            7. Return a valid JSON output with accurate dates and durations.
            8. If no skills are explicitly or less than 10 are mentioned in the resume, generate a total of 10 relevant skills based on the candidate's experience and education.
            """

            structured_data = await self.gpt_service.extract_with_prompts(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=ResumeSchema
            )

            if structured_data.get('experiences'):
                structured_data['work_experience'] = self.calculate_total_work_experience(
                    [{'date_start': exp['date_start'], 'date_end': exp['date_end']} for exp in structured_data['experiences']]
                )

            return structured_data

        except Exception as e:
            logger.error(f"Error extracting resume details: {str(e)}", exc_info=True)
            raise

    async def vectorize_resume(self, resume: Dict[str, Any]) -> List[float]:
        """
        Vectorizes the resume content for comparison with the job description.
        """
        resume_text = (
            f"{resume.get('candidate_name', '')} "
            f"{' '.join(resume.get('skills', {}).get('primary_skills', []))} "
            f"{' '.join([exp.get('description', '') for exp in resume.get('experiences', [])])}"
        )
        return await self.gpt_service.get_text_embedding(resume_text)

    async def compute_similarity(self, resume: Dict[str, Any], enhanced_jd: Dict[str, Any]) -> float:
        """
        Computes similarity between resume and enhanced job description using cosine similarity.
        """
        resume_embedding = await self.vectorize_resume(resume)
        jd_embedding = self.job_description_enhancer.temp_storage.get("vectorized_jd", [])
        
        return cosine_similarity(np.array(jd_embedding), np.array(resume_embedding))

    async def score_resume(self, resume: Dict[str, Any], combined_criteria: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Scores an extracted resume against user input, enhanced JD, and sample candidates.

        Args:
            resume (Dict[str, any]): Extracted resume details.
            combined_criteria (str): The combined criteria for scoring.
            candidates (List[Dict[str, any]]): List of sample candidates.

        Returns:
            Dict with resume score, analysis, and recommendations.
        """
        system_prompt = f"""
        You are an AI tasked with evaluating resumes in relation to an user input (more priority), enhanced job description (second priority) and a set of sample candidates. The candidate's resume should be analyzed thoroughly, including both technical and non-technical aspects, and compared with the job description as well as the dummy candidates.

        Your task is to perform a deep analysis of the candidate's resume and compare it to both the enhanced job description and the sample candidates. Every detail in the resume should be examined carefully, including skills, experiences, education, certifications, and any other relevant information. You need to assess the alignment of the candidate's profile with the job description and the sample candidates.

        The analysis should include:
        - Identification of any missing skills or experience gaps.
        - A detailed summary of what the candidate possesses in terms of qualifications, expertise, and suitability for the role.
        - A comparison of the candidate to the closest matching sample candidate from the generated set.
        - Recommendations for improvement to help the candidate better match the job description.

        **Scoring Criteria:**
        1. **Skill Match**: Assess both technical and soft skills mentioned in the resume.
        2. **Experience Relevance**: Evaluate how well the candidate's past roles and industry experience align with the job description and sample candidates.
        3. **Education & Certifications**: Check if the candidate's education and certifications match the requirements of the job description.
        4. **Keyword Similarity**: Analyze the ATS (Applicant Tracking System) optimization by checking how well the resume matches keywords in the job description.

        **Output Format:**
        - **candidate_name**: Name of the candidate extracted from the resume.
        - **resume_score**: A score assigned to the resume on a scale from 0 to 10 based on how well it aligns with the job description and sample candidates.
        - **gap_analysis**: A list of missing skills or experience gaps identified in the candidate's resume.
        - **candidate_summary**: A detailed summary of the candidate's qualifications, experience, and suitability for the job.
        - **recommendations**: A set of recommendations for the candidate to improve their alignment with the job description.

        Your task is to analyze the candidate's resume carefully in relation to the enhanced job description and the sample candidates, and generate the report accordingly.
        """

        user_prompt = f"""
        Evaluate the following resume against the **Enhanced Job Description** and **Sample Candidates**.

        You are an AI tasked with evaluating resumes in relation to an enhanced job description and a set of sample candidates. The candidate's resume should be analyzed thoroughly, including both technical and non-technical aspects, and compared with the job description as well as the dummy candidates.

        Your task is to perform a deep analysis of the candidate's resume and compare it to both the enhanced job description and the sample candidates. Every detail in the resume should be examined carefully, including skills, experiences, education, certifications, and any other relevant information. You need to assess the alignment of the candidate's profile with the job description and the sample candidates.

        The analysis should include:
        - Identification of any missing skills or experience gaps.
        - A detailed summary of what the candidate possesses in terms of qualifications, expertise, and suitability for the role.
        - A comparison of the candidate to the closest matching sample candidate from the generated set.
        - Recommendations for improvement to help the candidate better match the job description.

    Resume details: {resume}

    Enhanced Job Description + User Input + Matching Candidates: {combined_criteria}

    Generated Dummy Candidates for comparison: {candidates}
        """

        try:
            # Call GPT service (this will now properly be inside a try block with exception handling)
            scoring_result = await self.gpt_service.extract_with_prompts(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=ResumeScoringSchema
            )
            return scoring_result

        except Exception as e:
            logger.error(f"Error in scoring resume: {str(e)}", exc_info=True)
            raise Exception(f"Error in scoring resume: {str(e)}")

    def calculate_total_work_experience(self, experiences: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Calculate the total work experience by handling overlapping periods and calculating the duration in years and months.

        Args:
        - experiences: A list of dictionaries, each containing 'date_start' and 'date_end'.
        
        Returns:
        - A dictionary with the total years and months of work experience.
        """
        if not experiences:
            print("No experiences provided")
            return {'years': 0, 'months': 0}

        total_months = 0
        parsed_experiences = [
            {'start': self.parse_date(exp['date_start']), 'end': self.parse_date(exp['date_end'])} for exp in experiences
        ]
        parsed_experiences.sort(key=lambda x: x['start'])

        
        current_start = parsed_experiences[0]['start']
        current_end = parsed_experiences[0]['end']

        for i in range(1, len(parsed_experiences)):
            start = parsed_experiences[i]['start']
            end = parsed_experiences[i]['end']
            
            if start <= current_end:
                
                current_end = max(current_end, end)
            else:
                
                total_months += (current_end.year - current_start.year) * 12 + current_end.month - current_start.month
                current_start = start
                current_end = end
        
        
        total_months += (current_end.year - current_start.year) * 12 + current_end.month - current_start.month
        
        
        years = total_months // 12
        months = total_months % 12

        return {'years': years, 'months': months}

    def parse_date(self, date_string: str) -> datetime:
        """
        Parses a date string in the format 'YYYY-MM-DD' and returns a datetime object.
        If the date string is empty or invalid, the current date is returned.
        """
        try:
            return datetime.strptime(date_string, '%Y-%m-%d')
        except ValueError:
            return datetime.now()  # If the date is invalid, return the current date
