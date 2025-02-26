from neo4j import GraphDatabase
from typing import List, Dict, Any
from app.utils.logger import Logger

logger = Logger(__name__).get_logger()

class Neo4jService:
    """
    Service to handle interactions with Neo4j.
    """
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="Ishu9891"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info("Neo4j connection initialized.")

    def close(self):
        self.driver.close()

    def add_industry(self, industry_name: str):
        with self.driver.session() as session:
            session.run("MERGE (i:Industry {name: $name})", name=industry_name)
        logger.info(f"Industry '{industry_name}' added to Neo4j.")

    def add_job_role(self, industry_name: str, job_title: str):
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

    def create_experience_node(self, experience_bucket: str):
        with self.driver.session() as session:
            session.run(
                """
                MERGE (i:Industry {name: 'Finances'})
                MERGE (j:JobRole {title: 'Risk Advisory & Internal Auditor'})
                MERGE (i)-[:HAS_JOB_ROLE]->(j)
                MERGE (e:Experience {range: $experience_bucket})
                MERGE (j)-[:HAS_EXPERIENCE_RANGE]->(e)
                """,
                experience_bucket=experience_bucket
            )
        logger.info(f"Experience bucket '{experience_bucket}' merged under 'Finances -> Risk Advisory & Internal Auditor'.")

    def add_skill(self, experience_bucket: str, skill_name: str):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (e:Experience {range: $experience_bucket})
                MERGE (s:Skill {name: $skill_name})
                MERGE (e)-[:HAS_SKILL]->(s)
                """,
                experience_bucket=experience_bucket,
                skill_name=skill_name
            )
        logger.info(f"Skill '{skill_name}' merged under experience '{experience_bucket}'.")

    def create_subskill_under_skill(self, experience_bucket: str, skill_name: str, subskill_name: str):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (e:Experience {range: $experience_bucket})
                MATCH (s:Skill {name: $skill_name})
                MERGE (ss:SubSkill {name: $subskill_name})
                MERGE (s)-[:HAS_SUBSKILL]->(ss)
                """,
                experience_bucket=experience_bucket,
                skill_name=skill_name,
                subskill_name=subskill_name
            )
        logger.info(f"SubSkill '{subskill_name}' merged under Skill '{skill_name}' in '{experience_bucket}' experience bucket.")

    def create_candidate(self, candidate_name: str, overall_score: float):
        with self.driver.session() as session:
            session.run(
                """
                MERGE (c:Candidate {name: $candidate_name})
                SET c.score = $overall_score
                """,
                candidate_name=candidate_name,
                overall_score=overall_score
            )
        logger.info(f"Candidate '{candidate_name}' created with overall score '{overall_score}'.")

    def link_candidate_to_subskill(self, candidate_name: str, subskill_name: str):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (c:Candidate {name: $candidate_name})
                MATCH (ss:SubSkill {name: $subskill_name})
                MERGE (c)-[:BELONGS_TO_SUBSKILL]->(ss)
                """,
                candidate_name=candidate_name,
                subskill_name=subskill_name
            )
        logger.info(f"Candidate '{candidate_name}' linked to subskill '{subskill_name}'.")

    def link_candidate_to_skill(self, candidate_name: str, skill_name: str):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (c:Candidate {name: $candidate_name})
                MATCH (s:Skill {name: $skill_name})
                MERGE (c)-[:BELONGS_TO_SKILL]->(s)
                """,
                candidate_name=candidate_name,
                skill_name=skill_name
            )
        logger.info(f"Candidate '{candidate_name}' linked to skill '{skill_name}'.")

    def find_candidates_for_job_role(self, job_title: str) -> List[str]:
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

    def find_candidates_for_same_experience_skill(self, experience_bucket: str, skill_name: str) -> List[Dict[str, Any]]:
        query = """
        MATCH (job:JobRole {title: 'Risk Advisory & Internal Auditor'})
              -[:HAS_EXPERIENCE_RANGE]->(e:Experience {range: $experience_bucket})
              -[:HAS_SKILL]->(s:Skill {name: $skill_name})
              <-[:BELONGS_TO_SKILL]-(c:Candidate)
        OPTIONAL MATCH (c)-[:BELONGS_TO_SKILL]->(otherSkill:Skill)
        RETURN c.name AS candidate_name, c.score AS candidate_score, collect(distinct otherSkill.name) AS candidate_skills
        """
        with self.driver.session() as session:
            result = session.run(
                query,
                experience_bucket=experience_bucket,
                skill_name=skill_name
            )
            candidates = []
            for record in result:
                candidates.append({
                    "candidate_name": record["candidate_name"],
                    "candidate_score": record["candidate_score"],
                    "candidate_skills": record["candidate_skills"] or []
                })
        logger.info(f"Found {len(candidates)} candidate(s) for experience '{experience_bucket}', skill '{skill_name}'.")
        return candidates

    def find_matching_candidates(self, experience_bucket: str, skill_name: str, subskill_name: str) -> List[Dict[str, Any]]:
        """
        Finds all candidates that match the fixed criteria:
        - Industry: 'Finances'
        - Job Role: 'Risk Advisory & Internal Auditor'
        - Experience: given by experience_bucket
        - Skill: given by skill_name
        - SubSkill: given by subskill_name

        Returns a list of dictionaries with candidate names and scores.
        """
        query = """
        MATCH (i:Industry {name: 'Finances'})-[:HAS_JOB_ROLE]->(r:JobRole {title: 'Risk Advisory & Internal Auditor'})
        MATCH (r)-[:HAS_EXPERIENCE_RANGE]->(e:Experience {range: $experience_bucket})
        MATCH (e)-[:HAS_SKILL]->(s:Skill {name: $skill_name})
        MATCH (s)-[:HAS_SUBSKILL]->(ss:SubSkill {name: $subskill_name})
        MATCH (c:Candidate)-[:BELONGS_TO_SUBSKILL]->(ss)
        RETURN c.name AS candidate_name, c.score AS candidate_score
        """
        with self.driver.session() as session:
            result = session.run(query,
                                 experience_bucket=experience_bucket,
                                 skill_name=skill_name,
                                 subskill_name=subskill_name)
            candidates = [{"candidate_name": record["candidate_name"],
                           "candidate_score": record["candidate_score"]} for record in result]
        logger.info(f"Found {len(candidates)} matching candidates for experience '{experience_bucket}', skill '{skill_name}', subskill '{subskill_name}'.")
        return candidates

    def link_candidate_to_job_role(self, candidate_name: str, job_role: str):
        try:
            with self.driver.session() as session:
                session.run(
                    """
                    MATCH (r:JobRole {title: $job_role})
                    MATCH (c:Candidate {name: $candidate_name})
                    MERGE (c)-[:BELONGS_TO_JOB_ROLE]->(r)
                    """,
                    job_role=job_role,
                    candidate_name=candidate_name
                )
            logger.info(f"Candidate '{candidate_name}' linked to Job Role '{job_role}'.")
        except Exception as e:
            logger.error(f"Error linking candidate to job role: {str(e)}", exc_info=True)
            raise
