import os
from dotenv import load_dotenv
from src.core.openai_provider import OpenAIProvider
from src.core.gemini_provider import GeminiProvider
from src.core.local_provider import LocalProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

class Chatbot:
    """
    Baseline LLM Chatbot that answers questions directly without tool access.
    Implements standard logging and performance tracking.
    """
    def __init__(self):
        load_dotenv()
        provider_name = os.getenv("DEFAULT_PROVIDER", "openai").lower()
        model_name = os.getenv("DEFAULT_MODEL", "gpt-4o")
        
        logger.info(f"Initializing Baseline Chatbot with provider: {provider_name}")
        
        if provider_name == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            self.llm = OpenAIProvider(model_name=model_name, api_key=api_key)
        elif provider_name == "google":
            api_key = os.getenv("GEMINI_API_KEY")
            self.llm = GeminiProvider(model_name=model_name, api_key=api_key)
        elif provider_name == "local":
            model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
            self.llm = LocalProvider(model_path=model_path)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    def ask(self, query: str) -> str:
        """
        Send query directly to LLM and track performance metrics.
        """
        logger.log_event("CHATBOT_START", {"query": query})
        
        system_prompt = "You are a helpful assistant. Answer the user's questions clearly."
        response = self.llm.generate(prompt=query, system_prompt=system_prompt)
        
        # Track metrics
        tracker.track_request(
            provider=response["provider"],
            model=self.llm.model_name,
            usage=response["usage"],
            latency_ms=response["latency_ms"]
        )
        
        logger.log_event("CHATBOT_END", {"latency_ms": response["latency_ms"]})
        return response["content"]

if __name__ == "__main__":
    chatbot = Chatbot()
    print("Baseline Chatbot initialized. Ask anything (Ctrl+C to exit):")
    try:
        while True:
            user_in = input("\nUser: ")
            if not user_in.strip():
                continue
            answer = chatbot.ask(user_in)
            print(f"Chatbot: {answer}")
    except (KeyboardInterrupt, EOFError):
        print("\nExiting chatbot.")
