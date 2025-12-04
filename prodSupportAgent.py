from strands import Agent
from strands.tools.mcp import MCPClient
from strands.models import BedrockModel
from mcp import StdioServerParameters, stdio_client
from strands_tools import use_aws

import os
import sys
import atexit
from typing import Dict

# Import AWS configuration
import awsConfig
from awsConfig import AWS_PROFILE_FOR_TOOLS, AWS_REGION

# Define common production support tasks
PREDEFINED_TASKS = {
    "lambda_invocations": "Check Lambda function invocations in the last hour",
    "lambda_errors": "Check for Lambda function errors and failures",
    "cloudwatch_alarms": "Check current CloudWatch alarms status",
    "recent_logs": "Get recent CloudWatch logs for a specific resource",
    "error_analysis": "Analyze error patterns in the last hour",
    "performance_metrics": "Get performance metrics for Lambda functions",
    "invocation_trends": "Analyze invocation trends over time"
}

# Initialize MCP clients (will be done once in Streamlit session state)
time_mcp_client = None
cloudwatch_mcp_client = None
time_tools = []
cloudwatch_tools = []

def initialize_mcp_clients():
    """Initialize MCP clients once"""
    global time_mcp_client, cloudwatch_mcp_client, time_tools, cloudwatch_tools
    
    is_windows = sys.platform.startswith('win')
    print(f"Detected platform: {'Windows' if is_windows else 'Non-Windows (Linux/macOS)'}")

    try:
        if is_windows:
            # Windows-specific configuration
            print("Using Windows-specific MCP configuration...")
            
            # Set up Time MCP client for Windows
            time_mcp_client = MCPClient(lambda: stdio_client(
                StdioServerParameters(
                    command="uvx",
                    args=["mcp-server-time"]
                )
            ))
            
            # Set up CloudWatch MCP client for Windows
            cloudwatch_mcp_client = MCPClient(lambda: stdio_client(
                StdioServerParameters(
                    command="uvx",
                    args=["--from", "awslabs.cloudwatch-mcp-server@latest", "awslabs.cloudwatch-mcp-server.exe"],
                    env={"FASTMCP_LOG_LEVEL": "ERROR"}
                )
            ))
        else:
            # Non-Windows configuration (Linux/macOS)
            print("Using standard MCP configuration for Linux/macOS...")
            
            # Set up Time MCP client
            time_mcp_client = MCPClient(lambda: stdio_client(
                StdioServerParameters(
                    command="uvx",
                    args=["mcp-server-time"]
                )
            ))
            
            # Set up CloudWatch MCP client (without .exe extension)
            cloudwatch_mcp_client = MCPClient(lambda: stdio_client(
                StdioServerParameters(
                    command="uvx",
                    args=["--from", "awslabs.cloudwatch-mcp-server@latest", "awslabs.cloudwatch-mcp-server"],
                    env={"FASTMCP_LOG_LEVEL": "ERROR"}
                )
            ))

        # Start both MCP clients
        print("Starting Time MCP client...")
        time_mcp_client.start()
        print("Time MCP client started successfully.")
        
        print("Starting CloudWatch MCP client...")
        cloudwatch_mcp_client.start()
        print("CloudWatch MCP client started successfully.")
        
        # Get tools from MCP clients
        time_tools = time_mcp_client.list_tools_sync()
        cloudwatch_tools = cloudwatch_mcp_client.list_tools_sync()

        print(f"Available Time tools: {len(time_tools)} tools loaded")
        print(f"Available CloudWatch tools: {len(cloudwatch_tools)} tools loaded")
        
        return True
        
    except Exception as e:
        print(f"Error initializing MCP clients: {str(e)}")
        raise

def get_bedrock_model():
    """Get or create Bedrock model"""
    # Configure AWS profiles for cross-account access
    wfoprod_profile = os.environ.get("AWS_PROFILE")

    # Temporarily use default profile for Bedrock
    os.environ["AWS_PROFILE"] = "default"

    # Create a BedrockModel - using Claude 3.5 Sonnet
    bedrock_model = BedrockModel(
        model_id=os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0"),
        region_name=AWS_REGION,
        temperature=0.1,
    )

    # Restore wfoprod profile for use_aws tool
    if wfoprod_profile:
        os.environ["AWS_PROFILE"] = wfoprod_profile
    
    return bedrock_model

def get_system_prompt():
    """Get system prompt for the agent"""
    return f"""
You are an expert AWS Production Support Engineer assistant. Your primary role is to help 
monitor, troubleshoot, and analyze production systems, with a focus on:

1. Lambda function monitoring (invocations, errors, duration, throttles)
2. CloudWatch metrics and alarms analysis
3. Error pattern detection and root cause analysis
4. Performance monitoring and optimization
5. Real-time production incident response

CRITICAL AWS CONFIGURATION:
- You are querying AWS Account: {AWS_PROFILE_FOR_TOOLS} (Account ID: 918987959928 - wfoprod)
- Region: {AWS_REGION}
- The use_aws tool is automatically configured to use profile {AWS_PROFILE_FOR_TOOLS}
- You do NOT need to specify --profile in your commands (it's handled automatically)

AVAILABLE TOOLS:
1. Time MCP tools - for getting current time, time calculations, and time-based queries
2. CloudWatch MCP tools - for querying CloudWatch metrics, logs, and alarms
3. AWS CLI (use_aws) - for direct AWS commands when needed

IMPORTANT GUIDELINES:
- When asked about "last hour" or time-based queries, use the Time MCP tools to get accurate timestamps
- For Lambda metrics, query CloudWatch for: Invocations, Errors, Throttles, Duration, ConcurrentExecutions
- Always provide specific numbers and timestamps in your responses
- When analyzing errors, look for patterns and provide actionable insights
- Be concise but thorough in production support scenarios

EXAMPLE QUERY HANDLING:
When asked: "How many invocations were there in the last hour for Lambda production-lambda-hybrid-recording-user-sync and were there any failures"
You should:
1. Use Time tools to get the exact time range (last hour)
2. Query CloudWatch for the Lambda function metrics:
   - Invocations count
   - Errors count
   - Throttles count
3. Present the results clearly with numbers and any error details

When querying specific resources, ONLY query that resource - don't make assumptions about other resources.

IMPORTANT: Never include <thinking> tags or expose your internal thought process in responses.
"""

def get_agent(messages=None):
    """Get or create the agent with conversation history"""
    global time_tools, cloudwatch_tools
    agent_params = {
        'tools': [use_aws] + time_tools + cloudwatch_tools,
        'model': get_bedrock_model(),
        'system_prompt': get_system_prompt()
    }
    
    if messages:
        agent_params['messages'] = messages
    
    return Agent(**agent_params)

# Register cleanup handler for MCP clients
def cleanup():
    global time_mcp_client, cloudwatch_mcp_client
    try:
        if time_mcp_client:
            time_mcp_client.stop()
            print("Time MCP client stopped")
    except Exception as e:
        print(f"Error stopping Time MCP client: {e}")
    
    try:
        if cloudwatch_mcp_client:
            cloudwatch_mcp_client.stop()
            print("CloudWatch MCP client stopped")
    except Exception as e:
        print(f"Error stopping CloudWatch MCP client: {e}")

atexit.register(cleanup)

# Function to execute a predefined task
def execute_predefined_task(task_key: str, conversation_history=None) -> tuple:
    """Execute a predefined production support task
    
    Args:
        task_key: Key of the predefined task
        conversation_history: Optional list of previous messages in Bedrock format
        
    Returns:
        tuple: (response_text, updated_messages)
    """
    if task_key not in PREDEFINED_TASKS:
        error_msg = f"Error: Task '{task_key}' not found in predefined tasks."
        return error_msg, conversation_history or []
    
    task_description = PREDEFINED_TASKS[task_key]
    return execute_custom_task(task_description, conversation_history)

# Function to execute a custom task
def execute_custom_task(task_description: str, conversation_history=None) -> tuple:
    """Execute a custom production support task based on description
    
    Args:
        task_description: The task to execute
        conversation_history: Optional list of previous messages in Bedrock format
        
    Returns:
        tuple: (response_text, updated_messages)
    """
    try:
        agent = get_agent(messages=conversation_history)
        response = agent(task_description)
        
        # Handle AgentResult object by extracting the message
        response_text = response.message if hasattr(response, 'message') else str(response)
        
        # Return both the response and the updated conversation history
        return response_text, agent.messages
    except Exception as e:
        error_msg = f"Error executing task: {str(e)}"
        return error_msg, conversation_history or []

# Function to get predefined tasks
def get_predefined_tasks() -> Dict[str, str]:
    """Return the dictionary of predefined tasks"""
    return PREDEFINED_TASKS


if __name__ == "__main__":
    import streamlit as st
    import re
    import ast
    
    def clean_response(response):
        if not response:
            return ""
        
        if not isinstance(response, str):
            try:
                response = str(response)
            except:
                return "Error: Could not convert response to string"
        
        cleaned = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL)
        
        if cleaned.find("'role': 'assistant'") >= 0 and cleaned.find("'content'") >= 0 and cleaned.find("'text'") >= 0:
            try:
                data = ast.literal_eval(cleaned)
                if isinstance(data, dict) and 'content' in data and isinstance(data['content'], list):
                    for item in data['content']:
                        if isinstance(item, dict) and 'text' in item:
                            return item['text']
            except:
                match = re.search(r"'text': '(.+?)(?:'}]|})", cleaned, re.DOTALL)
                if match:
                    text = match.group(1)
                    text = text.replace('\\n', '\n')
                    text = text.replace('\\t', '\t')
                    text = text.replace("\\'", "'")
                    text = text.replace('\\"', '"')
                    return text
        
        return cleaned.strip()
    
    st.set_page_config(page_title="Production Support", page_icon="🔧", layout="wide")
    
    st.title("🔧 AWS Production Support")
    
    # Initialize MCP clients only once
    if "mcp_initialized" not in st.session_state:
        with st.spinner("Initializing MCP clients..."):
            initialize_mcp_clients()
            st.session_state.mcp_initialized = True
    
    # Initialize session state for UI messages (for display)
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Initialize session state for agent conversation history (Bedrock format)
    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []
    
    # Display welcome message if no messages yet
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown("👋 Ask me about Lambda invocations, errors, CloudWatch metrics, etc.")
    
    # Display all previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Handle new user input
    if prompt := st.chat_input("Ask about production metrics..."):
        # Add user message to UI history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response from agent with conversation history
        with st.chat_message("assistant"):
            with st.spinner("🔍 Analyzing CloudWatch metrics..."):
                response, updated_agent_messages = execute_custom_task(
                    prompt, 
                    conversation_history=st.session_state.agent_messages
                )
                cleaned_response = clean_response(response)
                st.markdown(cleaned_response)
        
        # Update both histories
        st.session_state.messages.append({"role": "assistant", "content": cleaned_response})
        st.session_state.agent_messages = updated_agent_messages
        
        st.rerun()




