import time
from typing import Dict, Any, Optional, Generator
from openai import OpenAI
from src.core.llm_provider import LLMProvider

class OpenAIProvider(LLMProvider):
    def __init__(self, model_name: str = "gpt-4o", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        if not self.api_key or "your_openai_api_key" in self.api_key:
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if self.client is None:
            return self._mock_generate(prompt, system_prompt)

        start_time = time.time()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
        )

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Extraction from OpenAI response
        content = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "openai"
        }

    def _mock_generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        time.sleep(0.3)  # Simulate network latency
        content = ""
        is_react = system_prompt and ("Thought:" in system_prompt or "ReAct" in system_prompt)
        prompt_lower = prompt.lower()

        if is_react:
            if "hanoi" in prompt_lower and "winner" in prompt_lower:
                if "observation: shipping to hanoi" in prompt_lower:
                    content = (
                        "Thought: I have all the information now. 2 iPhones are in stock.\n"
                        "The discounted price is $1800 (10% off of $2000 via 'WINNER').\n"
                        "Shipping to Hanoi is 15000 VND. I will now state the final answer.\n"
                        "Final Answer: Yes, we have enough stock (10 units available). The total price for 2 iPhones "
                        "is $1800 (after applying a 10% discount from coupon 'WINNER') and the shipping cost to Hanoi is 15000 VND."
                    )
                elif "observation: coupon winner is valid" in prompt_lower:
                    content = (
                        "Thought: The discount code 'WINNER' is verified as valid and gives 10% off.\n"
                        "The standard price of 2 iPhones is $2000, so with 10% off it is $1800.\n"
                        "Now I need to calculate the shipping cost to Hanoi for a weight of 1.0kg (2 iPhones * 0.5kg).\n"
                        "Action: calc_shipping(weight=1.0, destination=hanoi)"
                    )
                elif "observation: stock for iphone" in prompt_lower:
                    content = (
                        "Thought: We have 10 iPhones in stock, which is enough.\n"
                        "Now I need to check the discount for coupon code 'WINNER'.\n"
                        "Action: get_discount(WINNER)"
                    )
                else:
                    content = (
                        "Thought: I need to check if we have at least 2 iPhones in stock first.\n"
                        "Action: check_stock(iphone)"
                    )
            elif "iphone" in prompt_lower and "stock" in prompt_lower:
                if "observation: stock for iphone" in prompt_lower:
                    content = (
                        "Thought: I have the stock info now. We have 10 iPhones in stock.\n"
                        "Final Answer: We have 10 iPhones in stock."
                    )
                else:
                    content = (
                        "Thought: I need to check the stock of iPhones in the database.\n"
                        "Action: check_stock(iphone)"
                    )
            elif "vietnam" in prompt_lower:
                content = (
                    "Thought: The user is asking for the capital of Vietnam, which is a simple fact.\n"
                    "Final Answer: The capital of Vietnam is Hanoi."
                )
            else:
                content = (
                    "Thought: I should assist the user.\n"
                    "Final Answer: How can I assist you with e-commerce today?"
                )
        else:
            if "hanoi" in prompt_lower and "winner" in prompt_lower:
                content = (
                    "I don't have access to your live inventory or coupon systems directly, "
                    "so I cannot tell you if we have 2 iPhones in stock or calculate the exact "
                    "discounted price with shipping. However, typically we ship to Hanoi."
                )
            elif "iphone" in prompt_lower and "stock" in prompt_lower:
                content = (
                    "As an AI chatbot, I don't have access to your real-time stock database, "
                    "so I cannot tell you how many iPhones are currently in stock."
                )
            elif "vietnam" in prompt_lower:
                content = "The capital of Vietnam is Hanoi."
            else:
                content = "Hello! I am a standard chatbot. How can I help you today?"

        usage = {
            "prompt_tokens": len(prompt) // 4 + 50,
            "completion_tokens": len(content) // 4 + 10,
            "total_tokens": (len(prompt) + len(content)) // 4 + 60
        }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": 300,
            "provider": "openai"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        if self.client is None:
            res = self._mock_generate(prompt, system_prompt)
            for char in res["content"]:
                yield char
                time.sleep(0.01)
            return

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

