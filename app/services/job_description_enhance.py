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

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    if not np.any(vec1) or not np.any(vec2):
        return 0.0
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

class JobDescriptionEnhancer:
    """
    Service for extracting and enhancing job descriptions, generating sample candidate profiles,
    and storing them in Neo4j using the structure:
      Finances → Risk Advisory & Internal Auditor → Skill → Candidate

    Conditional Candidate–Skill Linking:
      - If a candidate’s skill mapping returns a non‑empty subskills list then the candidate is linked to each SubSkill node.
      - Otherwise, the candidate is linked directly to the Skill node.
    """
    def __init__(self):
        logger.info("JobDescriptionEnhancer initialized successfully.")
        config = ConfigService()
        self.gpt_service = GPTService()
        self.neo4j_service = Neo4jService()
        self.temp_storage = {}  # Temporary storage for enhanced JD and generated candidates

    def map_experience_to_bucket(self, years: int) -> str:
        if years < 1:
            return "0-1"
        elif years < 2:
            return "1-2"
        elif years < 4:
            return "2-4"
        elif years < 8:
            return "4-8"
        elif years < 16:
            return "8-16"
        else:
            return "16+"

    def map_unique_skills(self, primary_skills: List[str], secondary_skills: List[str]) -> Dict[str, List[str]]:
        """
        Combines both primary and secondary skills into two disjoint lists:
          - 'skills': unique primary skills
          - 'subskills': unique secondary skills that do not appear in primary.
        Additionally, removes specific duplicate/conflicting entries.
        """
        primary_skills = primary_skills or []
        secondary_skills = secondary_skills or []
        unique_primary = []
        for s in primary_skills:
            if s not in unique_primary:
                unique_primary.append(s)
        unique_secondary = []
        for s in secondary_skills:
            if s not in unique_secondary:
                unique_secondary.append(s)
        # Exclude any secondary that already appears in primary
        filtered_secondary = [s for s in unique_secondary if s not in unique_primary]
        # Remove duplicates/conflicts as identified:
        conflicts = {"Problem Solving", "Communication", "Critical Thinking"}
        filtered_secondary = [s for s in filtered_secondary if s not in conflicts]
        return {"skills": unique_primary, "subskills": filtered_secondary}

    def map_skills_to_conditional(self, primary_skills: List[str], secondary_skills: List[str]) -> List[Dict[str, Any]]:
        """
        Creates a mapping list where each entry is a dictionary with:
            'skill': a primary skill,
            'subskills': a list of secondary skills (filtered so that none appear in primary).
        """
        unique = self.map_unique_skills(primary_skills, secondary_skills)
        mapping = []
        for main_skill in unique["skills"]:
            mapping.append({
                'skill': main_skill,
                # Always include the filtered secondary skills for conditional linking.
                'subskills': [{'subskill': s} for s in unique["subskills"]]
            })
        return mapping

    async def enhance_job_description(self, file_buffer: BytesIO, filename: str):
        """
        Extracts, enhances a job description, generates sample dummy candidate profiles,
        vectorizes the JD, and stores them in Neo4j using the structure:
          Finances → Risk Advisory & Internal Auditor → Skill → Candidate
        (Candidates are linked conditionally.)
        """
        try:
            structured_data = await self.extract_job_description(file_buffer, filename)
            enhanced_jd = await self.generate_enhanced_jd(structured_data)
            enhanced_jd["industry_name"] = "Finances"
            enhanced_jd["job_title"] = "Risk Advisory & Internal Auditor"
            candidates = await self.generate_candidate_profiles(enhanced_jd)
            self.neo4j_service.add_industry("Finances")
            self.neo4j_service.add_job_role("Finances", "Risk Advisory & Internal Auditor")
            for c in candidates.get("candidate_list", []):
                if c is None or not isinstance(c, dict):
                    logger.error(f"Skipping invalid candidate entry: {c}")
                    continue
                # Default experience to 0 if missing
                experience_data = c.get("experience") or {"years": 0, "months": 0}
                if not isinstance(experience_data, dict):
                    experience_data = {"years": 0, "months": 0}
                candidate_name = c.get("full_name", "Unknown Candidate")
                candidate_score = c.get("score", 0)
                experience_years = experience_data.get("years", 0)
                experience_bucket = self.map_experience_to_bucket(experience_years)
                self.neo4j_service.create_experience_node(experience_bucket)
                self.neo4j_service.create_candidate(candidate_name, candidate_score)
                key_skills = c.get("key_skills") or {}
                primary_skills = key_skills.get("primary_skills", [])
                secondary_skills = key_skills.get("secondary_skills", [])
                combined_mapping = self.map_skills_to_conditional(primary_skills, secondary_skills)
                for mapping_entry in combined_mapping:
                    skill_name = mapping_entry['skill']
                    self.neo4j_service.add_skill(experience_bucket, skill_name)
                    if mapping_entry['subskills']:
                        for subskill_entry in mapping_entry['subskills']:
                            subskill_name = subskill_entry['subskill']
                            self.neo4j_service.create_subskill_under_skill(experience_bucket, skill_name, subskill_name)
                        for subskill_entry in mapping_entry['subskills']:
                            subskill_name = subskill_entry['subskill']
                            self.neo4j_service.link_candidate_to_subskill(candidate_name, subskill_name)
                    else:
                        self.neo4j_service.link_candidate_to_skill(candidate_name, skill_name)
            vectorized_jd = await self.vectorize_job_description(enhanced_jd)
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
            raise Exception(f"Error enhancing job description '{filename}': {str(e)}")

    async def extract_job_description(self, file_buffer: BytesIO, filename: str) -> Dict[str, Any]:
        try:
            text = parse_pdf_or_docx(file_buffer, filename)
            today_date = datetime.now().strftime("%Y-%m-%d")
            system_prompt = f"""
            You are an AI model specialized in extracting structured job descriptions. 
            Ensure accurate data extraction and return structured JSON output without any contextual loss of information.
            Today's date is {today_date}. Follow these rules:

            1. **Extract Fields**:
               - **industry_name**: Extract the industry of the job (e.g., "Technology", "Healthcare", "Finance"). If not mentioned, mark as "Not mentioned". 
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
            user_prompt = f"""
            Extract structured job description details from the following text without contextual loss of any information:

            {text}

            Ensure structured formatting, extract all key details, and infer missing information where applicable.
            """
            structured_data = await self.gpt_service.extract_with_prompts(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=JobDescriptionSchema
            )
            return structured_data
        except Exception as e:
            logger.error(f"Error parsing job description '{filename}': {str(e)}", exc_info=True)
            raise

    async def generate_enhanced_jd(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
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
            logger.error(f"Error enhancing job description: {str(e)}", exc_info=True)
            raise

    async def generate_candidate_profiles(self, enhanced_jd: Dict[str, Any]) -> CandidateProfileSchemaList:
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
        try:
            jd_text = (
                f"{enhanced_jd.get('job_title', '')} "
                f"{enhanced_jd.get('role_summary', '')} "
                f"{' '.join(enhanced_jd.get('responsibilities', []))} "
                f"{' '.join(enhanced_jd.get('required_skills', []))} "
            )
            vectorized_jd = await self.gpt_service.get_text_embedding(jd_text)
            return vectorized_jd
        except Exception as e:
            logger.error(f"Error vectorizing JD: {str(e)}", exc_info=True)
            return []
