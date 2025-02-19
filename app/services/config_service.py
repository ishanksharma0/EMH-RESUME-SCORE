import os
from dotenv import load_dotenv
from app.utils.logger import Logger

# Initialize Logger
logger = Logger(__name__).get_logger()

class ConfigService:
    """
    Configuration service to manage environment variables.
    """
    def __init__(self):
        """
        Loads environment variables from .env file.
        """
        load_dotenv()  # Load .env variables into the environment

        # Retrieve necessary environment variables
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        # Validate required configurations
        if not self.openai_api_key:
            logger.error("Missing OpenAI API Key in environment variables.")
            raise ValueError("OPENAI_API_KEY is required in the .env file.")

        logger.info("Configuration loaded successfully.")

    def get_openai_key(self):
        """
        Returns the OpenAI API key.
        """
        return self.openai_api_key
