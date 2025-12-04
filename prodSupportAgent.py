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
import aws_tools_wrapper
from aws_tools_wrapper import AWS_PROFILE_FOR_TOOLS, AWS_REGION

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

# Set up MCP clients with platform-specific configurations
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
    
    # Set flag to indicate MCP clients are initialized
    mcp_initialized = True
    
except Exception as e:
    mcp_initialized = False
    error_message = str(e)
    print(f"Error initializing MCP clients: {error_message}")
    
    raise

# Get tools from MCP clients
time_tools = time_mcp_client.list_tools_sync()
cloudwatch_tools = cloudwatch_mcp_client.list_tools_sync()

print(f"Available Time tools: {[tool.name for tool in time_tools]}")
print(f"Available CloudWatch tools: {[tool.name for tool in cloudwatch_tools]}")

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

# System prompt for the agent
system_prompt = f"""
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

# Create the agent with all tools and Bedrock model
agent = Agent(
    tools=[use_aws] + time_tools + cloudwatch_tools,
    model=bedrock_model,
    system_prompt=system_prompt
)

# Register cleanup handler for MCP clients
def cleanup():
    try:
        time_mcp_client.stop()
        print("Time MCP client stopped")
    except Exception as e:
        print(f"Error stopping Time MCP client: {e}")
    
    try:
        cloudwatch_mcp_client.stop()
        print("CloudWatch MCP client stopped")
    except Exception as e:
        print(f"Error stopping CloudWatch MCP client: {e}")

atexit.register(cleanup)

# Function to execute a predefined task
def execute_predefined_task(task_key: str) -> str:
    """Execute a predefined production support task"""
    if task_key not in PREDEFINED_TASKS:
        return f"Error: Task '{task_key}' not found in predefined tasks."
    
    task_description = PREDEFINED_TASKS[task_key]
    return execute_custom_task(task_description)

# Function to execute a custom task
def execute_custom_task(task_description: str) -> str:
    """Execute a custom production support task based on description"""
    try:
        response = agent(task_description)
        
        # Handle AgentResult object by extracting the message
        if hasattr(response, 'message'):
            return response.message
        
        # Handle other types of responses
        return str(response)
    except Exception as e:
        return f"Error executing task: {str(e)}"

# Function to get predefined tasks
def get_predefined_tasks() -> Dict[str, str]:
    """Return the dictionary of predefined tasks"""
    return PREDEFINED_TASKS


if __name__ == "__main__":
    # Example usage - check Lambda invocations and errors in the last hour
    result = execute_custom_task(
        "How many invocations were there in the last hour for Lambda production-lambda-hybrid-recording-user-sync and were there any failures"
    )
    print(result)

