import os
import re
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class ReActAgent:
    """
    A robust ReAct-style Agent that follows the Thought-Action-Observation loop.
    Supports robust parsing, dynamic tool execution, and detailed telemetry logging.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        Generates the ReAct system prompt instructing the agent.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""You are an intelligent e-commerce assistant. You have access to the following tools:
{tool_descriptions}

You MUST follow the ReAct reasoning process. Use EXACTLY the format below:

Thought: [your reasoning about the next step]
Action: tool_name(arguments)
Observation: [result of the tool call - this is provided to you, do not write this yourself]

(Repeat Thought/Action/Observation if needed to gather enough facts)

Thought: [final reasoning confirming you have everything]
Final Answer: [your detailed final response solving the query]

CRITICAL RULES:
1. You must write Thought and then Action. Do not skip either.
2. The Action MUST be in the exact format: tool_name(args). Example: check_stock(iphone) or calc_shipping(weight=1.0, destination=hanoi).
3. Do NOT invent new tools. Only call the ones listed above.
4. When you have enough information, write Final Answer. Do not call any more tools.
"""

    def run(self, user_input: str) -> str:
        """
        Executes the ReAct loop:
        1. Prompts LLM for Thought + Action.
        2. Tracks LLM performance metrics.
        3. Parses the Action and dynamically executes the tool.
        4. Appends Observation and loops until Final Answer or max_steps.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        current_scratchpad = ""
        steps = 0
        
        while steps < self.max_steps:
            # Build current prompt
            prompt = f"User Request: {user_input}\n\nScratchpad / Reasoning History:\n{current_scratchpad}"
            
            # Generate LLM response
            response = self.llm.generate(prompt, system_prompt=self.get_system_prompt())
            
            # Log metrics using PerformanceTracker
            from src.telemetry.metrics import tracker
            tracker.track_request(
                provider=response["provider"],
                model=self.llm.model_name,
                usage=response["usage"],
                latency_ms=response["latency_ms"]
            )
            
            content = response["content"].strip()
            logger.log_event("AGENT_LLM_RESPONSE", {"step": steps, "content": content})
            
            # Append model's response to history
            current_scratchpad += f"\n{content}\n"
            
            # 1. Check for Final Answer
            if "Final Answer:" in content:
                final_answer = content.split("Final Answer:")[-1].strip()
                logger.log_event("AGENT_SUCCESS", {"steps": steps + 1, "final_answer": final_answer})
                return final_answer
                
            # 2. Parse Action
            action_match = re.search(r"Action:\s*(\w+)\((.*)\)", content, re.IGNORECASE)
            if action_match:
                tool_name = action_match.group(1).strip()
                tool_args_str = action_match.group(2).strip()
                
                logger.log_event("AGENT_TOOL_CALL", {"tool": tool_name, "args": tool_args_str})
                
                # Execute tool
                observation = self._execute_tool(tool_name, tool_args_str)
                
                logger.log_event("AGENT_OBSERVATION", {"tool": tool_name, "observation": observation})
                
                # Append Observation to the scratchpad
                current_scratchpad += f"Observation: {observation}\n"
            else:
                # Agent v2: self-correction feedback loop
                error_msg = "Error: Invalid response format. You must output 'Thought: [reasoning]' followed by 'Action: tool_name(arguments)' or 'Final Answer: [response]'."
                logger.log_event("AGENT_PARSING_ERROR", {"content": content})
                current_scratchpad += f"Observation: {error_msg}\n"
            
            steps += 1
            
        logger.log_event("AGENT_TIMEOUT", {"steps": steps})
        return f"Timeout: Agent failed to reach a final answer in {self.max_steps} steps. Scratchpad: {current_scratchpad}"

    def _execute_tool(self, tool_name: str, args_str: str) -> str:
        """
        Helper method to execute tools dynamically by name with robust argument parsing.
        """
        tool_name = tool_name.strip()
        matched_tool = None
        for tool in self.tools:
            if tool["name"].lower() == tool_name.lower():
                matched_tool = tool
                break
                
        if not matched_tool:
            available = ", ".join([t["name"] for t in self.tools])
            return f"Error: Tool '{tool_name}' not found. Available tools: {available}."
            
        # Parse arguments robustly
        parsed_args = []
        parsed_kwargs = {}
        
        clean_args_str = args_str.strip()
        if clean_args_str:
            # Case 1: JSON Arguments
            if clean_args_str.startswith("{") and clean_args_str.endswith("}"):
                import json
                try:
                    parsed_kwargs = json.loads(clean_args_str)
                except Exception:
                    pass
            
            # Case 2: Comma-separated positional/keyword arguments
            if not parsed_kwargs:
                parts = re.split(r",(?=(?:[^'\"]*['\"][^'\"]*['\"])*[^'\"]*$)", clean_args_str)
                for part in parts:
                    part = part.strip()
                    if "=" in part:
                        k, v = part.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        try:
                            if "." in v:
                                parsed_kwargs[k] = float(v)
                            else:
                                parsed_kwargs[k] = int(v)
                        except ValueError:
                            parsed_kwargs[k] = v
                    else:
                        v = part.strip().strip("'\"")
                        try:
                            if "." in v:
                                parsed_args.append(float(v))
                            else:
                                parsed_args.append(int(v))
                        except ValueError:
                            parsed_args.append(v)
                            
        try:
            func = matched_tool["func"]
            if parsed_kwargs:
                return str(func(**parsed_kwargs))
            elif parsed_args:
                return str(func(*parsed_args))
            else:
                return str(func())
        except Exception as e:
            return f"Error executing tool '{tool_name}' with args '{args_str}': {str(e)}"

