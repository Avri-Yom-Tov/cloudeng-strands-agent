"""
Bedrock Agent Model wrapper for Strands Agent framework
Enables using AWS Bedrock Agents with Memory and other managed features
"""
import asyncio
import json
import logging
import uuid
from typing import Any, AsyncGenerator, Callable, Optional
import boto3
from botocore.config import Config as BotocoreConfig

logger = logging.getLogger(__name__)


class BedrockAgentModel:
    """
    Wrapper for AWS Bedrock Agent that implements the Strands Model interface.
    
    This allows using a managed Bedrock Agent (with Memory, Knowledge Bases, etc.)
    instead of direct model invocation.
    
    Usage:
        agent_model = BedrockAgentModel(
            agent_id="YOUR_AGENT_ID",
            agent_alias_id="YOUR_AGENT_ALIAS_ID",  # or "TSTALIASID" for draft
            session_id="optional-session-id",  # auto-generated if not provided
            boto_session=boto3_session,
            region_name="us-west-2"
        )
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_alias_id: str = "TSTALIASID",  # Draft alias by default
        session_id: Optional[str] = None,
        boto_session: Optional[boto3.Session] = None,
        region_name: Optional[str] = None,
        enable_trace: bool = False,
        **kwargs
    ):
        """
        Initialize Bedrock Agent Model.
        
        Args:
            agent_id: The unique identifier of the agent (from Bedrock Console)
            agent_alias_id: The alias ID (default: TSTALIASID for draft/test)
            session_id: Session ID for memory persistence (auto-generated if None)
            boto_session: Optional boto3 session for authentication
            region_name: AWS region (required if boto_session not provided)
            enable_trace: Enable trace information in responses
        """
        self.agent_id = agent_id
        self.agent_alias_id = agent_alias_id
        self.session_id = session_id or str(uuid.uuid4())
        self.enable_trace = enable_trace
        
        # Create boto3 session
        if boto_session:
            session = boto_session
            resolved_region = region_name or session.region_name
        else:
            session = boto3.Session(region_name=region_name)
            resolved_region = region_name
            
        if not resolved_region:
            raise ValueError("region_name must be specified either in boto_session or as parameter")
        
        # Create bedrock-agent-runtime client
        client_config = BotocoreConfig(
            user_agent_extra="strands-agents",
            read_timeout=300
        )
        
        self.client = session.client(
            service_name="bedrock-agent-runtime",
            config=client_config,
            region_name=resolved_region
        )
        
        logger.info(
            f"Initialized BedrockAgentModel: agent_id={agent_id}, "
            f"alias={agent_alias_id}, session={self.session_id}, region={resolved_region}"
        )
    
    def get_session_id(self) -> str:
        """Get the current session ID (useful for debugging/logging)"""
        return self.session_id
    
    def new_session(self) -> str:
        """Create a new session ID and return it"""
        self.session_id = str(uuid.uuid4())
        logger.info(f"Created new session: {self.session_id}")
        return self.session_id
    
    async def stream(
        self,
        messages: list[dict[str, Any]],
        tool_specs: Optional[list[dict]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream conversation with the Bedrock Agent.
        
        Args:
            messages: List of message objects (only the last user message is used)
            tool_specs: Ignored (agent uses its configured action groups)
            system_prompt: Ignored (agent uses its configured instructions)
            **kwargs: Additional arguments
            
        Yields:
            Stream events compatible with Strands Agent framework
        """
        # Extract the last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", [])
                if content and isinstance(content, list):
                    for block in content:
                        if "text" in block:
                            user_message = block["text"]
                            break
                if user_message:
                    break
        
        if not user_message:
            logger.warning("No user message found in messages list")
            user_message = "Hello"
        
        logger.debug(f"Invoking agent with message: {user_message[:100]}...")
        
        # Call invoke_agent
        try:
            response = self.client.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=self.session_id,
                inputText=user_message,
                enableTrace=self.enable_trace
            )
            
            # Stream the response
            event_stream = response.get("completion", [])
            
            current_text = ""
            
            for event in event_stream:
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        chunk_text = chunk["bytes"].decode("utf-8")
                        current_text += chunk_text
                        
                        # Yield contentBlockDelta event (compatible with Bedrock converse stream)
                        yield {
                            "contentBlockDelta": {
                                "delta": {
                                    "text": chunk_text
                                },
                                "contentBlockIndex": 0
                            }
                        }
                
                elif "trace" in event and self.enable_trace:
                    # Optionally handle trace events
                    logger.debug(f"Trace event: {event['trace']}")
                
                elif "returnControl" in event:
                    # Agent is requesting action group invocation
                    logger.warning("Agent requested return control - not fully supported yet")
            
            # Yield final messageStop event
            yield {
                "messageStop": {
                    "stopReason": "end_turn"
                }
            }
            
            # Yield metadata
            yield {
                "metadata": {
                    "usage": {
                        "inputTokens": 0,  # Not provided by agent API
                        "outputTokens": len(current_text.split()),  # Rough estimate
                        "totalTokens": len(current_text.split())
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error invoking agent: {e}")
            raise
    
    def update_config(self, **kwargs):
        """Update configuration (placeholder for compatibility)"""
        logger.debug(f"update_config called with: {kwargs}")
        # Agent configuration is managed in Bedrock Console
        pass
    
    def get_config(self) -> dict:
        """Get current configuration"""
        return {
            "agent_id": self.agent_id,
            "agent_alias_id": self.agent_alias_id,
            "session_id": self.session_id,
            "enable_trace": self.enable_trace
        }


class BedrockAgentModelWithStrands:
    """
    Alternative approach: Use Bedrock Agent for conversation but Strands for tool execution.
    This hybrid approach gives you Memory from Bedrock Agent but keeps local tool control.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_alias_id: str = "TSTALIASID",
        fallback_model: Optional[Any] = None,
        **kwargs
    ):
        """
        Initialize hybrid model.
        
        Args:
            agent_id: Bedrock Agent ID
            agent_alias_id: Bedrock Agent Alias ID
            fallback_model: Strands BedrockModel for tool execution
        """
        self.bedrock_agent = BedrockAgentModel(
            agent_id=agent_id,
            agent_alias_id=agent_alias_id,
            **kwargs
        )
        self.fallback_model = fallback_model
        
    async def stream(self, messages, tool_specs=None, **kwargs):
        """Route to appropriate model based on context"""
        # Simple routing: use agent if no tools, fallback if tools needed
        if tool_specs:
            logger.info("Using fallback model for tool execution")
            return self.fallback_model.stream(messages, tool_specs, **kwargs)
        else:
            logger.info("Using Bedrock Agent")
            return self.bedrock_agent.stream(messages, tool_specs, **kwargs)

