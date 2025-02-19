from openai import OpenAI
from app.utils.logger import Logger
from app.models.schemas import (
    ResumeSchema, 
    JobDescriptionSchema, 
    EnhancedJobDescriptionSchema, 
    CandidateProfileSchema,
    ResumeScoringSchema,
    CandidateProfileSchemaList
)
from app.services.config_service import ConfigService
from typing import Dict, Any, List

# Initialize Logger
logger = Logger(__name__).get_logger()

class GPTService:
    """
    Service for interacting with OpenAI's GPT API to process resume and job description text.
    """
    def __init__(self):
        """
        Initializes the GPT service with the OpenAI API key.
        """
        try:
            config = ConfigService()
            self.openai_client = OpenAI(api_key=config.get_openai_key())
            logger.info("GPT service initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize GPT service: {str(e)}", exc_info=True)
            raise

    async def extract_with_prompts(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Any  # Keep response_schema unchanged
    ) -> Dict[str, Any]:
        """
        Extract structured information using GPT with custom prompts and schema.
        
        Args:
            system_prompt (str): System-level instructions for GPT.
            user_prompt (str): User-specific query for GPT processing.
            response_schema (Any): Expected schema for the response.

        Returns:
            Dict containing extracted structured information.
        """
        try:
            # Construct the messages
            messages = [
                {"role": "system", "content": f"{system_prompt}\n\nEnsure response follows the schema."},
                {"role": "user", "content": f"{user_prompt}"}
            ]

            # Make GPT API call
            response = self.openai_client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=messages,
                response_format=response_schema  # ✅ Keep response_schema unchanged
            )

            # Parse and return the structured response
            result = response.choices[0].message.parsed.dict()
            return result

        except Exception as e:
            logger.error(f"GPT extraction failed: {str(e)}", exc_info=True)
            raise Exception(f"GPT extraction failed: {str(e)}")

    async def get_text_embedding(self, text: str) -> List[float]:
        """
        Generates a vectorized numerical representation of the given text using OpenAI embeddings.
        
        Args:
            text (str): The text to convert into an embedding.

        Returns:
            List[float]: A vector representation of the text.
        """
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )

            # ✅ FIX: Access response as an object, not a dictionary
            embedding_vector = response.data[0].embedding  # 🔥 Correct way to extract embeddings

            return embedding_vector

        except Exception as e:
            logger.error(f"Failed to generate text embedding: {str(e)}", exc_info=True)
            return []