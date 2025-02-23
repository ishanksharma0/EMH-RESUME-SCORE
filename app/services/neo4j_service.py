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

    def add_candidate_resume(self, candidate_name: str, skills: list, experience_years: int):
        """
        Stores a candidate's resume in Neo4j.

        Args:
            candidate_name (str): Name of the candidate.
            skills (list): List of skills.
            experience_years (int): Years of experience.
        """
        query = """
        MERGE (c:Candidate {name: $candidate_name})
        SET c.experience_years = $experience_years
        """
        with self.driver.session() as session:
            session.run(query, candidate_name=candidate_name, experience_years=experience_years)

            for skill in skills:
                skill_query = """
                MERGE (s:Skill {name: $skill})
                MERGE (c:Candidate {name: $candidate_name})
                MERGE (c)-[:HAS_SKILL]->(s)
                """
                session.run(skill_query, skill=skill, candidate_name=candidate_name)

        logger.info(f" Candidate '{candidate_name}' stored in Neo4j.")

    def add_job_role(self, job_title: str, industry: str, required_skills: list):
        """
        Stores a job role in Neo4j.

        Args:
            job_title (str): Title of the job.
            industry (str): Industry name.
            required_skills (list): List of required skills.
        """
        query = """
        MERGE (j:JobRole {title: $job_title})
        MERGE (i:Industry {name: $industry})
        MERGE (j)-[:BELONGS_TO]->(i)
        """
        with self.driver.session() as session:
            session.run(query, job_title=job_title, industry=industry)

            for skill in required_skills:
                skill_query = """
                MERGE (s:Skill {name: $skill})
                MERGE (j:JobRole {title: $job_title})
                MERGE (j)-[:REQUIRES]->(s)
                """
                session.run(skill_query, skill=skill, job_title=job_title)

        logger.info(f" Job '{job_title}' stored in Neo4j.")

    def find_candidates_by_job(self, job_title: str):
        """
        Finds candidates that match a given job role.

        Args:
            job_title (str): The job title to match candidates for.

        Returns:
            list: A list of matching candidates.
        """
        query = """
        MATCH (j:JobRole {title: $job_title})-[:REQUIRES]->(s:Skill)
        MATCH (c:Candidate)-[:HAS_SKILL]->(s)
        RETURN DISTINCT c.name AS candidate_name, c.experience_years AS experience_years
        """
        with self.driver.session() as session:
            result = session.run(query, job_title=job_title)
            candidates = [{"name": record["candidate_name"], "experience_years": record["experience_years"]} for record in result]

        logger.info(f"🔍 Found {len(candidates)} matching candidates for job '{job_title}'.")
        return candidates

    def find_jobs_for_candidate(self, candidate_name: str):
        """
        Finds job roles that match a given candidate.

        Args:
            candidate_name (str): The candidate's name.

        Returns:
            list: A list of matching jobs.
        """
        query = """
        MATCH (c:Candidate {name: $candidate_name})-[:HAS_SKILL]->(s:Skill)
        MATCH (j:JobRole)-[:REQUIRES]->(s)
        RETURN DISTINCT j.title AS job_title
        """
        with self.driver.session() as session:
            result = session.run(query, candidate_name=candidate_name)
            jobs = [record["job_title"] for record in result]

        logger.info(f"🔍 Found {len(jobs)} matching job roles for candidate '{candidate_name}'.")
        return jobs

    def list_all_jobs(self):
        """
        Retrieves all stored job roles from Neo4j.

        Returns:
            list: A list of all job titles.
        """
        query = "MATCH (j:JobRole) RETURN j.title AS job_title"
        with self.driver.session() as session:
            result = session.run(query)
            jobs = [record["job_title"] for record in result]

        logger.info(f" Retrieved {len(jobs)} job roles from Neo4j.")
        return jobs

    def list_all_candidates(self):
        """
        Retrieves all stored candidates from Neo4j.

        Returns:
            list: A list of all candidates with their experience.
        """
        query = "MATCH (c:Candidate) RETURN c.name AS candidate_name, c.experience_years AS experience_years"
        with self.driver.session() as session:
            result = session.run(query)
            candidates = [{"name": record["candidate_name"], "experience_years": record["experience_years"]} for record in result]

        logger.info(f" Retrieved {len(candidates)} candidates from Neo4j.")
        return candidates

    def delete_candidate(self, candidate_name: str):
        """
        Deletes a candidate and their relationships from Neo4j.

        Args:
            candidate_name (str): The name of the candidate to delete.
        """
        query = "MATCH (c:Candidate {name: $candidate_name}) DETACH DELETE c"
        with self.driver.session() as session:
            session.run(query, candidate_name=candidate_name)

        logger.info(f" Deleted candidate '{candidate_name}' from Neo4j.")

    def delete_job(self, job_title: str):
        """
        Deletes a job role and its relationships from Neo4j.

        Args:
            job_title (str): The title of the job to delete.
        """
        query = "MATCH (j:JobRole {title: $job_title}) DETACH DELETE j"
        with self.driver.session() as session:
            session.run(query, job_title=job_title)

        logger.info(f" Deleted job role '{job_title}' from Neo4j.")

# ✅ Initialize Neo4j service for use in the application
neo4j_service = Neo4jService()
