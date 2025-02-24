from neo4j import GraphDatabase
from app.utils.logger import Logger

logger = Logger(__name__).get_logger()

class Neo4jService:
    """
    Service to handle interactions with Neo4j.
    """

    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="Ishu9891"):
        """
        Initializes Neo4j connection.
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info("Neo4j connection initialized.")

    def close(self):
        """
        Closes Neo4j connection.
        """
        self.driver.close()

    def add_industry(self, industry_name: str):
        """
        Adds an industry node.
        """
        with self.driver.session() as session:
            session.run(
                "MERGE (i:Industry {name: $name})",
                name=industry_name
            )
        logger.info(f"Industry '{industry_name}' added to Neo4j.")

    def add_job_role(self, industry_name: str, job_title: str):
        """
        Adds a job role under a specific industry.
        """
        with self.driver.session() as session:
            session.run(
                """
                MATCH (i:Industry {name: $industry_name})
                MERGE (r:JobRole {title: $job_title})
                MERGE (i)-[:HAS_JOB_ROLE]->(r)
                """,
                industry_name=industry_name,
                job_title=job_title
            )
        logger.info(f"Job Role '{job_title}' added under Industry '{industry_name}'.")

    def add_candidate(self, job_title: str, candidate_name: str):
        """
        Adds a candidate to a specific job role and links them.
        """
        with self.driver.session() as session:
            session.run(
                """
                MATCH (r:JobRole {title: $job_title})
                MERGE (c:Candidate {name: $candidate_name})
                MERGE (c)-[:BELONGS_TO_JOB_ROLE]->(r)
                """,
                job_title=job_title,
                candidate_name=candidate_name
            )
        logger.info(f"Candidate '{candidate_name}' added and linked under Job Role '{job_title}'.")

    def add_skill_to_candidate(self, candidate_name: str, skill_name: str):
        """
        Adds a skill to a specific candidate.
        """
        with self.driver.session() as session:
            session.run(
                """
                MATCH (c:Candidate {name: $candidate_name})
                MERGE (s:Skill {name: $skill_name})
                MERGE (c)-[:HAS_SKILL]->(s)
                """,
                candidate_name=candidate_name,
                skill_name=skill_name
            )
        logger.info(f"Skill '{skill_name}' added to Candidate '{candidate_name}'.")

    def add_candidate_resume(self, candidate_name: str, skills: list, experience_years: int, job_title: str):
        """
        Adds a resume for a candidate, including skills and experience years, to Neo4j.
        This method is responsible for adding the uploaded resume data into Neo4j.
        """
        with self.driver.session() as session:
            # Add or update candidate's skills
            for skill in skills:
                session.run(
                    """
                    MATCH (c:Candidate {name: $candidate_name})
                    MERGE (s:Skill {name: $skill_name})
                    MERGE (c)-[:HAS_SKILL]->(s)
                    """,
                    candidate_name=candidate_name,
                    skill_name=skill
                )
            
            # Store the candidate's work experience (in years)
            session.run(
                """
                MATCH (c:Candidate {name: $candidate_name})
                SET c.work_experience = $experience_years
                """,
                candidate_name=candidate_name,
                experience_years=experience_years
            )

            # Add candidate to the job role
            session.run(
                """
                MATCH (r:JobRole {title: $job_title})
                MATCH (c:Candidate {name: $candidate_name})
                MERGE (c)-[:BELONGS_TO_JOB_ROLE]->(r)
                """,
                candidate_name=candidate_name,
                job_title=job_title
            )
        
        logger.info(f"Candidate '{candidate_name}' with skills and experience added to Neo4j.")

    def find_candidates_for_job_role(self, job_title: str):
        """
        Finds all candidates for a specific job role.
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (r:JobRole {title: $job_title})<-[:BELONGS_TO_JOB_ROLE]-(c:Candidate)
                RETURN c.name AS candidate_name
                """,
                job_title=job_title
            )
            candidates = [record["candidate_name"] for record in result]
        logger.info(f"Found {len(candidates)} candidates for Job Role '{job_title}'.")
        return candidates

    def find_skills_for_candidate(self, candidate_name: str):
        """
        Finds all skills for a specific candidate.
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Candidate {name: $candidate_name})-[:HAS_SKILL]->(s:Skill)
                RETURN s.name AS skill_name
                """,
                candidate_name=candidate_name
            )
            skills = [record["skill_name"] for record in result]
        logger.info(f"Found {len(skills)} skills for Candidate '{candidate_name}'.")
        return skills

    def find_job_roles_for_candidate(self, candidate_name: str):
        """
        Finds all job roles associated with a candidate.
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Candidate {name: $candidate_name})-[:BELONGS_TO_JOB_ROLE]->(r:JobRole)
                RETURN r.title AS job_title
                """,
                candidate_name=candidate_name
            )
            job_roles = [record["job_title"] for record in result]
        logger.info(f"Found {len(job_roles)} Job Roles for Candidate '{candidate_name}'.")
        return job_roles
