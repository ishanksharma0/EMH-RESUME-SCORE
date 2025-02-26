from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


# 📌 **Duration Schema (for Work & Education Duration)**
class DurationDto(BaseModel):
    years: int = Field(..., description="Number of years")
    months: int = Field(..., description="Number of months")


# 📌 **Experience Schema**
class ExperienceDto(BaseModel):
    key: str = Field(..., description="Unique identifier for the experience")
    company: str = Field(..., description="Company name where the experience took place")
    title: Optional[str] = Field(None, description="Job title or position held")
    description: Optional[str] = Field(None, description="Description of responsibilities")
    date_start: Optional[str] = Field(None, description="Start date of the role")
    date_end: Optional[str] = Field(None, description="End date of the role")
    skills: Optional[List[str]] = Field(None, description="Skills gained during the experience")
    tasks: Optional[List[str]] = Field(None, description="Key tasks performed in the role")


# 📌 **Education Schema**
class EducationDto(BaseModel):
    key: Optional[str] = Field(None, description="Unique identifier for education")
    Insitution: str = Field(..., description="Name of the school or university")
    title: Optional[str] = Field(None, description="Degree or qualification")
    description: Optional[str] = Field(None, description="Description of the program or course")
    date_start: Optional[str] = Field(None, description="Start date of the education")
    date_end: Optional[str] = Field(None, description="End date of the education")
    skills: Optional[List[str]] = Field(None, description="Skills learned during the course")
    tasks: Optional[List[str]] = Field(None, description="Tasks or projects undertaken during education")


# 📌 **Social URLs Schema**
class SocialUrlDto(BaseModel):
    type: Optional[str] = Field(None, description="Type of social link (LinkedIn, GitHub, etc.)")
    url: Optional[str] = Field(None, description="URL to the social profile")


# 📌 **Languages Schema**
class LanguageItemDto(BaseModel):
    name: Optional[str] = Field(None, description="Name of the language known")


# 📌 **Skills Schema**
class SkillsDto(BaseModel):
    primary_skills: Optional[List[str]] = Field(None, description="Primary skills of the candidate")
    secondary_skills: Optional[List[str]] = Field(None, description="Secondary skills of the candidate")


# 📌 **Resume Schema (for Extraction & Scoring)**
class ResumeSchema(BaseModel):
    candidate_name: Optional[str] = Field(None, description="Full name of the candidate")
    email_address: Optional[str] = Field(None, description="Email address")
    phone_number: Optional[str] = Field(None, description="Phone number")
    work_experience: Optional[DurationDto] = Field(None, description="Work experience duration")
    educations_duration: Optional[DurationDto] = Field(None, description="Total education duration")
    experiences: Optional[List[ExperienceDto]] = Field(None, description="List of work experiences")
    educations: Optional[List[EducationDto]] = Field(None, description="List of educational qualifications")
    social_urls: Optional[List[SocialUrlDto]] = Field(None, description="List of social media URLs")
    languages: Optional[List[LanguageItemDto]] = Field(None, description="List of languages known")
    certifications: Optional[List[LanguageItemDto]] = Field(None, description="List of any sort of online or offline certification or courses done by the candidate")
    skills: Optional[SkillsDto] = Field(None, description="Skills information")


# 📌 **Job Description Schema (for Extraction)**
class JobDescriptionSchema(BaseModel):
    job_title: str = Field(..., description="Job title for the position")
    job_description: str = Field(..., description="Full job description text without any contextual loss")
    industry_name: str = Field(..., description="Job industry of the job finances, technological, civil, healthcare, etc, without any contextual loss")
    required_skills: Optional[List[str]] = Field(None, description="List of required skills for the job all mentioned no contextual loss")
    min_work_experience: Optional[int] = Field(None, description="Minimum work experience required for the job")


# 📌 **Enhanced Job Description Schema (for Enhancing Job Descriptions)**
class EnhancedJobDescriptionSchema(BaseModel):
    job_title: str = Field(..., description="Enhanced job title for better clarity")
    industry_name: str = Field(..., description="Job industry of the job finances, technological, civil, healthcare, etc, without any contextual loss")
    role_summary: str = Field(..., description="Expanded overview of the role, including its purpose and impact in around 500 words minimum no contextual loss")
    responsibilities: List[str] = Field(..., description="List of responsibilities for the job, clearly defined and specific no contextual loss")
    required_skills: List[str] = Field(..., description="Categorized required skills, both technical and non-technical, no contextual loss")
    min_work_experience: Optional[int] = Field(None, description="Minimum work experience required for the job")
    key_metrics: List[str] = Field(..., description="Quantifiable indicators for performance measurement")


# 📌 **Candidate Profile Schema (for Sample Candidates)**
class CandidateProfileSchema(BaseModel):
    full_name: str = Field(..., description="Generated name of the sample candidate")
    experience: Optional[DurationDto] = Field(None, description="Work experience duration")
    key_skills: Optional[SkillsDto] = Field(None, description="Skills information")
    missing_skills: List[str] = Field(..., description="List of missing skills compared to JD")
    educations: Optional[List[EducationDto]] = Field(None, description="List of educational qualifications")
    work_samples: List[str] = Field(..., description="Relevant work examples or projects")
    score: int = Field(..., description="Candidate's score out of 10")
    scoring_justification: str = Field(..., description="Reasoning for the candidate's score")

class CandidateProfileSchemaList(BaseModel):
    candidate_list: List[CandidateProfileSchema] = Field(..., description="List of candidates")


# 📌 **Resume Scoring Schema**
class ResumeScoringSchema(BaseModel):
    candidate_name: str = Field(..., description="Name of the candidate extracted from resume")
    resume_score: int = Field(..., description="Score assigned to resume (0-10)")
    resume_score_justification: str = Field(..., description="Justification of why this assesment is justified")
    gap_analysis: List[str] = Field(..., description="Details on missing skills, experience gaps")
    candidate_summary: str = Field(..., description="A detailed summary of what the candidate possess")
    recommendations: str = Field(..., description="Improvement recommendations for the candidate")


# 📌 **Resume Scoring Response (for Bulk Processing)**
class ResumeScoringResponse(BaseModel):
    scored_resumes: List[ResumeScoringSchema] = Field(..., description="List of scored resumes with comparison results")

# 📌 **Industry Classification Schema for Resume**
class ResumeIndustrySchema(BaseModel):
    industry: str = Field(..., description="The classified industry of the candidate's resume")

# 📌 **Industry Classification Schema for Job Description**
class JobDescriptionIndustrySchema(BaseModel):
    industry: str = Field(..., description="The classified industry of the job description")
