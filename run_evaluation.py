import os
from dotenv import load_dotenv
from chatbot import Chatbot
from src.agent.agent import ReActAgent
from src.core.openai_provider import OpenAIProvider
from src.tools.ecommerce_tools import check_stock, get_discount, calc_shipping
from src.telemetry.metrics import tracker
from src.telemetry.logger import logger

# List of scenarios to test
SCENARIOS = [
    {
        "id": "SCENARIO_1_SIMPLE",
        "name": "Simple Fact Q&A",
        "query": "What is the capital of Vietnam?"
    },
    {
        "id": "SCENARIO_2_SINGLE_STEP",
        "name": "Single-Step E-Commerce Stock Check",
        "query": "How many iPhones do we have in stock?"
    },
    {
        "id": "SCENARIO_3_MULTI_STEP",
        "name": "Multi-Step Complex E-Commerce Checkout",
        "query": "I want to buy 2 iPhones using code 'WINNER' and ship to Hanoi. Each iPhone weighs 0.5kg. What is the total price including shipping?"
    }
]

def main():
    load_dotenv()
    print("=" * 80)
    print("                    LAB 3 EVALUATION RUNNER: CHATBOT vs AGENT                    ")
    print("=" * 80)
    
    # 1. Initialize Baseline Chatbot
    print("\n[+] Initializing Baseline Chatbot...")
    chatbot = Chatbot()
    
    # 2. Initialize ReAct Agent
    print("[+] Initializing ReAct Agent...")
    tools = [
        {
            "name": "check_stock",
            "description": "Checks stock levels for a product. Input: item_name (str) - e.g., 'iphone', 'macbook'.",
            "func": check_stock
        },
        {
            "name": "get_discount",
            "description": "Validates a discount coupon and returns the percentage. Input: coupon_code (str) - e.g., 'WINNER'.",
            "func": get_discount
        },
        {
            "name": "calc_shipping",
            "description": "Calculates shipping cost. Input: weight (float) in kg, destination (str) e.g., 'hanoi'.",
            "func": calc_shipping
        }
    ]
    
    # Use default model configured in environment
    provider_name = os.getenv("DEFAULT_PROVIDER", "openai").lower()
    model_name = os.getenv("DEFAULT_MODEL", "gpt-4o")
    api_key = os.getenv("OPENAI_API_KEY") if provider_name == "openai" else os.getenv("GEMINI_API_KEY")
    
    if provider_name == "openai":
        from src.core.openai_provider import OpenAIProvider
        llm = OpenAIProvider(model_name=model_name, api_key=api_key)
    elif provider_name == "google":
        from src.core.gemini_provider import GeminiProvider
        llm = GeminiProvider(model_name=model_name, api_key=api_key)
    elif provider_name == "local":
        from src.core.local_provider import LocalProvider
        llm = LocalProvider(model_path=os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf"))
    else:
        raise ValueError(f"Unknown provider: {provider_name}")

    agent = ReActAgent(llm=llm, tools=tools, max_steps=5)
    
    # Reset session metrics for clean tracking
    tracker.session_metrics = []
    
    chatbot_results = []
    agent_results = []
    
    print("\n" + "=" * 50)
    print("RUNNING CHATBOT EVALUATION")
    print("=" * 50)
    
    for idx, sc in enumerate(SCENARIOS):
        print(f"\n[Scenario {idx+1}] {sc['name']}")
        print(f"Query: '{sc['query']}'")
        
        # Track metric start index
        start_metric_count = len(tracker.session_metrics)
        
        # Run chatbot
        response = chatbot.ask(sc["query"])
        
        # Gather metrics for this run
        run_metrics = tracker.session_metrics[start_metric_count:]
        total_latency = sum(m["latency_ms"] for m in run_metrics)
        total_tokens = sum(m["total_tokens"] for m in run_metrics)
        total_cost = sum(m["cost_estimate"] for m in run_metrics)
        
        print(f"Chatbot Output: {response}")
        print(f"Metrics: Latency: {total_latency}ms | Tokens: {total_tokens} | Cost: ${total_cost:.5f}")
        
        chatbot_results.append({
            "scenario": sc["name"],
            "query": sc["query"],
            "output": response,
            "latency_ms": total_latency,
            "tokens": total_tokens,
            "cost": total_cost,
            "steps": 1
        })
        
    print("\n" + "=" * 50)
    print("RUNNING REACT AGENT EVALUATION")
    print("=" * 50)
    
    for idx, sc in enumerate(SCENARIOS):
        print(f"\n[Scenario {idx+1}] {sc['name']}")
        print(f"Query: '{sc['query']}'")
        
        # Track metric start index
        start_metric_count = len(tracker.session_metrics)
        
        # Run agent
        response = agent.run(sc["query"])
        
        # Gather metrics for this run
        run_metrics = tracker.session_metrics[start_metric_count:]
        total_latency = sum(m["latency_ms"] for m in run_metrics)
        total_tokens = sum(m["total_tokens"] for m in run_metrics)
        total_cost = sum(m["cost_estimate"] for m in run_metrics)
        steps_taken = len(run_metrics)
        
        print(f"Agent Output: {response}")
        print(f"Metrics: Latency: {total_latency}ms | Tokens: {total_tokens} | Cost: ${total_cost:.5f} | Steps: {steps_taken}")
        
        agent_results.append({
            "scenario": sc["name"],
            "query": sc["query"],
            "output": response,
            "latency_ms": total_latency,
            "tokens": total_tokens,
            "cost": total_cost,
            "steps": steps_taken
        })
        
    # 3. Print Comparison Report Dashboard
    print("\n" + "=" * 80)
    print("                         FINAL COMPARISON DASHBOARD                              ")
    print("=" * 80)
    print(f"{'Scenario / Task':<35} | {'System':<10} | {'Latency':<8} | {'Tokens':<6} | {'Cost':<8} | {'Steps':<5}")
    print("-" * 80)
    
    for c_res, a_res in zip(chatbot_results, agent_results):
        sc_name = c_res["scenario"]
        # Chatbot row
        print(f"{sc_name:<35} | {'Chatbot':<10} | {c_res['latency_ms']:>6}ms | {c_res['tokens']:>6} | ${c_res['cost']:>6.5f} | {c_res['steps']:>5}")
        # Agent row
        print(f"{'':<35} | {'ReActAgent':<10} | {a_res['latency_ms']:>6}ms | {a_res['tokens']:>6} | ${a_res['cost']:>6.5f} | {a_res['steps']:>5}")
        print("-" * 80)
        
    # Print Aggregates
    avg_c_lat = sum(r["latency_ms"] for r in chatbot_results) / len(chatbot_results)
    avg_a_lat = sum(r["latency_ms"] for r in agent_results) / len(agent_results)
    tot_c_tok = sum(r["tokens"] for r in chatbot_results)
    tot_a_tok = sum(r["tokens"] for r in agent_results)
    tot_c_cost = sum(r["cost"] for r in chatbot_results)
    tot_a_cost = sum(r["cost"] for r in agent_results)
    
    print("\nAGGREGATE SUMMARY:")
    print(f"Chatbot Baseline  -> Avg Latency: {avg_c_lat:.1f}ms | Total Tokens: {tot_c_tok} | Total Cost: ${tot_c_cost:.5f}")
    print(f"ReAct Agent (v2)  -> Avg Latency: {avg_a_lat:.1f}ms | Total Tokens: {tot_a_tok} | Total Cost: ${tot_a_cost:.5f}")
    print("=" * 80)

if __name__ == "__main__":
    main()
