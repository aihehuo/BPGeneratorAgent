import os
import sys
from typing import List, Optional

# Add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.pydantic_v1 import BaseModel, Field

from src.utils.config import load_config

# 1. Define the structure of the output we want
class CompletenessReport(BaseModel):
    """Report on the completeness of a business idea description."""
    is_complete: bool = Field(..., description="Whether the input has enough detail (at least 2 perspectives).")
    technical_score: str = Field(..., description="Assessment of technical perspective: 'complete', 'partial', or 'missing'.")
    market_score: str = Field(..., description="Assessment of market perspective: 'complete', 'partial', or 'missing'.")
    painpoint_score: str = Field(..., description="Assessment of user painpoint perspective: 'complete', 'partial', or 'missing'.")
    missing_info: List[str] = Field(..., description="List of specific missing details.")
    suggestions: List[str] = Field(..., description="Suggestions for improvement.")

# 2. Create a "Tool" that the agent uses to submit its findings
# In an agentic workflow, this acts as the "Final Answer" mechanism for structured data
@tool
def submit_completeness_report(report: CompletenessReport):
    """Submit the final analysis of the business idea completeness."""
    return report

def create_completeness_agent():
    # Load config
    config = load_config()
    
    # Initialize LLM
    # Note: Agent tools require a model capable of function calling (like GPT-3.5/4 or modern DeepSeek/Qwen)
    if config.default_llm_provider == "openai":
        llm = ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.openai_model,
            temperature=0
        )
    elif config.default_llm_provider == "deepseek":
        llm = ChatOpenAI(
            api_key=config.deepseek_api_key,
            base_url="https://api.deepseek.com",
            model=config.deepseek_model,
            temperature=0
        )
    else:
        # Fallback for other providers if they support OpenAI format
        print(f"Using provider {config.default_llm_provider}, assuming OpenAI compatibility...")
        llm = ChatOpenAI(
            api_key=getattr(config, f"{config.default_llm_provider}_api_key"),
            model=getattr(config, f"{config.default_llm_provider}_model"),
            temperature=0
        )

    # Define tools
    tools = [submit_completeness_report]

    # Define Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert Business Consultant Agent. 
Your task is to evaluate the "Completeness" of a user's business idea description.

Criteria for Completeness:
The user must provide a BASIC description from at least TWO of the following perspectives:
1. Technical Perspective: Technology, approach, platform (e.g., "AI", "Mobile App").
2. User Painpoint Perspective: Problem, need, target user (e.g., "students need help").
3. Market Perspective: Industry, opportunity, target audience (e.g., "Education market").

Instructions:
1. Analyze the user's input carefully.
2. Determine the status ('complete', 'partial', 'missing') for each of the 3 perspectives.
3. Check if at least 2 perspectives are 'complete' or 'partial' (sufficiently described).
4. If < 2 perspectives are present, is_complete = False.
5. Generate specific suggestions for what is missing.
6. USE the 'submit_completeness_report' tool to return your final analysis.
"""),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # Create Agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # Create Executor
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    return agent_executor

def main():
    agent_executor = create_completeness_agent()
    
    # Test Case 1: Incomplete Input
    print("\n--- Test Case 1: Vague Input ---")
    idea_1 = "I want to make a lot of money using AI."
    print(f"Input: {idea_1}")
    
    # Note: The agent will output the tool call result. 
    # In a real app, you'd capture the 'output' or intermediate steps.
    result_1 = agent_executor.invoke({"input": idea_1})
    print("Agent Output:", result_1['output'])

    # Test Case 2: Complete Input
    print("\n--- Test Case 2: Good Input ---")
    idea_2 = """
    I want to build a mobile app for elderly people to easily order groceries (User Painpoint).
    It will use large fonts and voice recognition (Technical).
    The target market is the aging population in Tier 1 cities (Market).
    """
    print(f"Input: {idea_2}")
    result_2 = agent_executor.invoke({"input": idea_2})
    # The output usually contains the string representation of the tool result
    # For structured access, you might parse 'intermediate_steps' or design the tool to return a value the agent repeats.
    print("Agent Output:", result_2['output'])

if __name__ == "__main__":
    main()

