import tensorflow as tf
import numpy as np
from app.utils.file_parser import parse_pdf_or_docx
from app.services.gpt_service import GPTService
from app.services.config_service import ConfigService
from io import BytesIO
from app.utils.logger import Logger
from app.models.schemas import ResumeSchema, ResumeScoringSchema, JobDescriptionIndustrySchema, ResumeIndustrySchema
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
from typing import List, Dict, Optional, Any

logger = Logger(__name__).get_logger()

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

    async def process_bulk_resumes(self, resume_files: List[BytesIO], filenames: List[str], user_input: str) -> List[Dict[str, any]]:
        """
        Processes multiple resumes, extracts structured data, and compares them to the enhanced job description 
        and sample candidates, while incorporating additional user preferences.

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

                # **Combine user input, enhanced JD, and candidates in priority order**
                combined_criteria = f"{user_input}\n\n{enhanced_jd}\n\n{generated_candidates}"

                # **Compare Resume Against User Input > JD > Sample Candidates**
                resume_comparison = await self.compare_resume_with_criteria(extracted_resume, combined_criteria, generated_candidates)

                # **Store Results**
                results.append(resume_comparison)

            return results

        except Exception as e:
            logger.error(f"Error processing resumes: {str(e)}", exc_info=True)
            raise


    async def parse_resume(self, file_buffer: BytesIO, filename: str) -> Dict[str, any]:
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
                - key (string),
                - title (string),
                - description (string),
                - date_start (string),
                - date_end (string),
                - skills (array of strings),
                - certifications (array of strings),
                - courses (array of strings),
                - tasks (array of strings),
                - languages (array of strings),
                - interests (array of strings),
                - company (string)
            7) educations (array of objects, similar to experiences):
                - key (string),
                - title (string),
                - description (string),
                - date_start (string),
                - date_end (string),
                - school (string)
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
                experiences_array = structured_data['experiences']
                if not isinstance(experiences_array, list):
                    experiences_array = [experiences_array]

                structured_data['work_experience'] = self.calculate_total_work_experience(
                    [{'date_start': exp['date_start'], 'date_end': exp['date_end']} for exp in experiences_array]
                )

            return structured_data

        except Exception as e:
            logger.error(f"Error extracting resume details: {str(e)}", exc_info=True)
            raise

    async def classify_resume_industry(self, resume: Dict[str, any]) -> str:
        """
        Classifies the industry of a resume based on its extracted content.

        Args:
            resume (Dict[str, any]): The extracted resume details.

        Returns:
            str: Industry classification (e.g., "Finance", "Software Engineering").
        """
        try:
            industry_prompt = f"""
            Analyze the candidate's job roles, skills, and experience. Assign a single industry classification.
            **Candidate Resume:**
            {resume}

            Respond with only one industry name.
            """
            return await self.gpt_service.extract_with_prompts(
                system_prompt="You are an expert in job market analysis. Classify the following resume into an industry category.",
                user_prompt=industry_prompt,
                response_schema=ResumeIndustrySchema
            )
        except Exception as e:
            logger.error(f"Error classifying resume industry: {str(e)}", exc_info=True)
            return "Unknown"

    async def classify_jd_industry(self, enhanced_jd: Dict[str, any]) -> str:
        """
        Classifies the industry of the job description.

        Args:
            enhanced_jd (Dict[str, any]): The enhanced job description.

        Returns:
            str: Industry classification (e.g., "Finance", "Software Engineering").
        """
        try:
            industry_prompt = f"""
            Analyze the job description and required skills. Assign a single industry classification.
            **Job Description:**
            {enhanced_jd}

            Respond with only one industry name.
            """
            return await self.gpt_service.extract_with_prompts(
                system_prompt="You are an expert in job market analysis. Classify the following job description into an industry category.",
                user_prompt=industry_prompt,
                response_schema=JobDescriptionIndustrySchema
            )
        except Exception as e:
            logger.error(f"Error classifying job description industry: {str(e)}", exc_info=True)
            return "Unknown"


    async def compare_resume_with_criteria(self, resume: Dict[str, any], combined_criteria: str, candidates: List[Dict[str, any]]) -> Dict[str, any]:
        """
        Compares an extracted resume against the combined job criteria.

        Args:
            resume (Dict[str, any]): Extracted resume details.
            combined_criteria (str): The combined criteria for scoring.
            candidates (List[Dict[str, any]]): List of sample candidates.

        Returns:
            Dict with resume score, analysis, and recommendations.
        """
        try:
            resume_text = f"{resume['skills']} {resume['experiences']} {resume['educations']}"

            # Compute Similarity Using TF-IDF and Cosine Similarity
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([combined_criteria, resume_text])
            similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

            # Call GPT-Based Resume Scoring
            gpt_based_scoring = await self.call_gpt_for_scoring(resume, combined_criteria, candidates)

            # Add Similarity Score
            gpt_based_scoring["similarity_score"] = similarity_score

            return gpt_based_scoring

        except Exception as e:
            logger.error(f"Error comparing resume: {str(e)}", exc_info=True)
            raise

    async def call_gpt_for_scoring(self, resume: Dict[str, Any], combined_criteria: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calls GPT-based scoring system for deeper analysis.
        """
        try:
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
            - **closest_sample_candidate**: The name of the sample candidate whose profile most closely matches the candidate's.
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

            **User Input:**
            {combined_criteria}

            **Candidate Resume:**
            {resume}

            **Sample Candidates:**
            {candidates}
            """

            return await self.gpt_service.extract_with_prompts(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=ResumeScoringSchema
            )

        except Exception as e:
            logger.error(f"Error in GPT-based scoring: {str(e)}", exc_info=True)
            raise

    async def compute_similarity(self, jd_text: str, resume_text: str, industry_match: bool, experience_relevance: float) -> float:
        """
        Computes similarity between a job description and a resume using multiple vectorization techniques.

        Args:
            jd_text (str): Job Description text.
            resume_text (str): Resume text.
            industry_match (bool): Whether the industries match.
            experience_relevance (float): Experience alignment score (0-1).

        Returns:
            float: Weighted similarity score (always between 0 and 1).
        """
        try:
            # 🚀 **Extract Embeddings for GPT-based Semantic Similarity**
            jd_embedding = await self.gpt_service.get_text_embedding(jd_text)
            resume_embedding = await self.gpt_service.get_text_embedding(resume_text)

            if not jd_embedding or not resume_embedding:
                logger.warning("Embedding retrieval failed, returning similarity 0.0")
                return 0.0  # Fallback if embeddings fail

            # Compute **GPT-based** Cosine Similarity
            semantic_similarity = 1 - tf.keras.losses.cosine_similarity(
                tf.convert_to_tensor([jd_embedding], dtype=tf.float32),
                tf.convert_to_tensor([resume_embedding], dtype=tf.float32)
            ).numpy()[0]

            semantic_similarity = max(0.0, min(1.0, float(semantic_similarity)))  # Ensure between 0-1

            # 🚀 **TF-IDF Vectorization for Word-Based Similarity**
            vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
            tfidf_matrix = vectorizer.fit_transform([jd_text, resume_text])
            word_similarity = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]

            word_similarity = max(0.0, min(1.0, float(word_similarity)))  # Ensure between 0-1

            # 🚀 **Category-Specific Similarities**
            categories = ["skills", "experience", "education", "responsibilities"]
            category_similarities = []

            for category in categories:
                jd_category_text = self.extract_category_text(jd_text, category)
                resume_category_text = self.extract_category_text(resume_text, category)

                if jd_category_text and resume_category_text:
                    category_vectorizer = TfidfVectorizer(stop_words='english', max_features=2000)
                    category_tfidf_matrix = category_vectorizer.fit_transform([jd_category_text, resume_category_text])
                    category_similarity = cosine_similarity(category_tfidf_matrix[0], category_tfidf_matrix[1])[0][0]
                    category_similarities.append(category_similarity)
                else:
                    category_similarities.append(0.0)

            # 🚀 **Weighted Similarity Calculation**
            category_weight = 0.25  # Each category contributes 25% weight
            total_category_similarity = sum(category_similarities) / len(categories)

            final_similarity = (
                (0.4 * semantic_similarity) +  # 40% weight to GPT embeddings
                (0.3 * word_similarity) +  # 30% weight to word similarity
                (0.3 * total_category_similarity)  # 30% weight to category-specific similarity
            )

            # 🚀 **Industry and Experience Penalty Adjustment**
            if not industry_match:
                industry_penalty = max(0.2, 1 - experience_relevance)
                final_similarity *= industry_penalty

            # 🚀 **Ensure final similarity remains within 0 and 1**
            final_similarity = max(0.0, min(1.0, final_similarity))

            logger.info(f"Final computed similarity: {final_similarity:.2f} (Industry: {industry_match}, Experience: {experience_relevance})")

            return round(final_similarity, 2)  # Return similarity rounded to 2 decimal places

        except Exception as e:
            logger.error(f"Error computing similarity: {str(e)}", exc_info=True)
            return 0.0

    async def extract_category_text(self, text: str, category: str) -> str:
        """
        Extracts relevant category text (skills, experience, education) from a given document.
        This function uses NLP-based keyword extraction.

        Args:
            text (str): The full text.
            category (str): The category to extract (e.g., "skills", "experience", etc.).

        Returns:
            str: Extracted text related to the category.
        """
        keywords = {
            "skills": ["skills", "technologies", "competencies"],
            "experience": ["work experience", "professional experience", "employment history"],
            "education": ["education", "degree", "academic background"],
            "responsibilities": ["responsibilities", "duties", "tasks"]
        }

        extracted_sentences = []
        for line in text.split("\n"):
            if any(keyword in line.lower() for keyword in keywords.get(category, [])):
                extracted_sentences.append(line)

        return " ".join(extracted_sentences)

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
