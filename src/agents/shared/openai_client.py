"""
OpenAI LLM client with configurable temperature for agent reasoning.

This module provides standardized ChatOpenAI clients for the multi-agent system.
All agents use temperature=0.2 by default for consistent reasoning, but can override
per agent for specific use cases (e.g., Agent 8 uses temperature=0.4 for creative summaries).
"""

from typing import Type, Optional
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


def get_chat_llm(
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
) -> ChatOpenAI:
    """
    Get ChatOpenAI instance with standardized settings.

    Args:
        model: OpenAI model name (default: gpt-4o-mini for cost efficiency)
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            - 0.0: Agents needing pure determinism (rare)
            - 0.2: Default for factual reasoning (Agents 2-5)
            - 0.4: Creative synthesis (Agent 8)
        max_tokens: Maximum tokens in response (None = no limit)

    Returns:
        ChatOpenAI instance configured for agent use

    Example:
        >>> llm = get_chat_llm(temperature=0.2)
        >>> response = llm.invoke("Analyze this patent data...")
    """
    kwargs = {
        "model": model,
        "temperature": temperature,
    }

    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    return ChatOpenAI(**kwargs)


def get_structured_llm(
    output_schema: Type[BaseModel],
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
) -> ChatOpenAI:
    """
    Get ChatOpenAI instance with structured output (Pydantic schema).

    This ensures the LLM returns JSON that validates against the provided
    Pydantic schema, eliminating parsing errors and type mismatches.

    Args:
        output_schema: Pydantic BaseModel class for output validation
        model: OpenAI model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response

    Returns:
        ChatOpenAI instance with .with_structured_output() applied

    Example:
        >>> class ReasoningOutput(BaseModel):
        ...     reasoning: str
        ...     confidence: float
        >>>
        >>> llm = get_structured_llm(ReasoningOutput, temperature=0.2)
        >>> result = llm.invoke("Why is this technology hyped?")
        >>> # result.reasoning is guaranteed to be a string
        >>> # result.confidence is guaranteed to be a float
    """
    llm = get_chat_llm(model=model, temperature=temperature, max_tokens=max_tokens)
    return llm.with_structured_output(output_schema)


def create_prompt_template(
    system_message: str,
    human_message_template: str,
) -> ChatPromptTemplate:
    """
    Create a reusable ChatPromptTemplate for agent prompts.

    Args:
        system_message: System instruction (defines agent role/behavior)
        human_message_template: User message template with placeholders

    Returns:
        ChatPromptTemplate ready for .format_messages()

    Example:
        >>> prompt = create_prompt_template(
        ...     system_message="You are an innovation analyst.",
        ...     human_message_template="Patents: {patent_count}, Trend: {trend}"
        ... )
        >>> messages = prompt.format_messages(patent_count=42, trend="declining")
    """
    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", human_message_template),
    ])
