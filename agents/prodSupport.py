from strands import Agent

from strands.tools.mcp import MCPClient

from strands.models import BedrockModel

from mcp import StdioServerParameters, stdio_client




import os

import sys

from typing import Dict

import streamlit as st

import boto3



# Import AWS configuration

from config.main import AWS_PROFILE_FOR_TOOLS, AWS_REGION



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

                    command="uv",

                    args=["tool", "run", "mcp-server-time"]

                )

            ))

           

            # Set up CloudWatch MCP client for Windows

            cloudwatch_mcp_client = MCPClient(lambda: stdio_client(

                StdioServerParameters(

                    command="uv",

                    args=["tool", "run", "--from", "awslabs.cloudwatch-mcp-server@latest", "awslabs.cloudwatch-mcp-server.exe"],

                    env={
                        "FASTMCP_LOG_LEVEL": "ERROR",
                        "AWS_PROFILE": AWS_PROFILE_FOR_TOOLS,
                        "AWS_REGION": AWS_REGION
                    }

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

                    env={
                        "FASTMCP_LOG_LEVEL": "ERROR",
                        "AWS_PROFILE": AWS_PROFILE_FOR_TOOLS,
                        "AWS_REGION": AWS_REGION
                    }

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

        if time_tools:

            print(f"DEBUG: First tool attributes: {dir(time_tools[0])}")

        for tool in time_tools:

            # Try multiple ways to get the tool name

            tool_name = (

                getattr(tool, 'name', None) or 

                getattr(tool, '_name', None) or 

                getattr(tool, 'tool_name', None) or

                getattr(getattr(tool, '_tool', None), 'name', None) or

                getattr(getattr(tool, 'tool', None), 'name', None) or

                "Unknown tool"

            )

            print(f"  - Time tool: {tool_name}")

       

        print(f"Available CloudWatch tools: {len(cloudwatch_tools)} tools loaded")

        for tool in cloudwatch_tools:

            tool_name = (

                getattr(tool, 'name', None) or 

                getattr(tool, '_name', None) or 

                getattr(tool, 'tool_name', None) or

                getattr(getattr(tool, '_tool', None), 'name', None) or

                getattr(getattr(tool, 'tool', None), 'name', None) or

                "Unknown tool"

            )

            print(f"  - CloudWatch tool: {tool_name}")

       

        return True

       

    except Exception as e:

        print(f"Error initializing MCP clients: {str(e)}")

        raise



def get_bedrock_model():

    """Get or create Bedrock model with proper boto3 session"""

    # Create a dedicated boto3 session for Bedrock using 'default' profile

    # This is cleaner than modifying environment variables

    bedrock_profile = os.environ.get("BEDROCK_AWS_PROFILE", "default")

    bedrock_region = os.environ.get("BEDROCK_REGION", AWS_REGION)

    

    # Create boto3 session with proper region

    bedrock_session = boto3.Session(

        profile_name=bedrock_profile,

        region_name=bedrock_region

    )

    

    # Create a BedrockModel with proper session - using Claude 3.5 Sonnet v2 (better tool calling)

    # Note: Cannot specify both boto_session and region_name, so region comes from the session

    bedrock_model = BedrockModel(

        boto_session=bedrock_session,

        model_id=os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"),

        temperature=0.1,

    )

    

    return bedrock_model



def get_system_prompt():

    """Get system prompt for the agent"""

    global time_tools, cloudwatch_tools

    

    # Build tool list

    tool_list = "=" * 80 + "\n"

    tool_list += "AVAILABLE TOOLS - USE ONLY THESE!\n"

    tool_list += "=" * 80 + "\n"

    tool_list += "⚠️  DO NOT call tools that are NOT in this list!\n"

    tool_list += "⚠️  DO NOT invent tool names!\n\n"

    

    if time_tools:

        tool_list += f"Time Tools ({len(time_tools)} tools available):\n"

        for tool in time_tools:

            tool_name = (

                getattr(tool, 'name', None) or 

                getattr(tool, '_name', None) or 

                getattr(tool, 'tool_name', None) or

                getattr(getattr(tool, '_tool', None), 'name', None) or

                getattr(getattr(tool, 'tool', None), 'name', None) or

                "Unknown tool"

            )

            tool_desc = (

                getattr(tool, 'description', None) or 

                getattr(tool, '_description', None) or

                getattr(getattr(tool, '_tool', None), 'description', None) or

                getattr(getattr(tool, 'tool', None), 'description', None) or

                "No description"

            )

            tool_list += f"- {tool_name}: {tool_desc}\n"

    

    if cloudwatch_tools:

        tool_list += f"\nCloudWatch Tools ({len(cloudwatch_tools)} tools available):\n"

        for tool in cloudwatch_tools:

            tool_name = (

                getattr(tool, 'name', None) or 

                getattr(tool, '_name', None) or 

                getattr(tool, 'tool_name', None) or

                getattr(getattr(tool, '_tool', None), 'name', None) or

                getattr(getattr(tool, 'tool', None), 'name', None) or

                "Unknown tool"

            )

            tool_desc = (

                getattr(tool, 'description', None) or 

                getattr(tool, '_description', None) or

                getattr(getattr(tool, '_tool', None), 'description', None) or

                getattr(getattr(tool, 'tool', None), 'description', None) or

                "No description"

            )

            tool_list += f"- {tool_name}: {tool_desc}\n"

    

    tool_list += "\n" + "=" * 80 + "\n"

    tool_list += "⚠️  REMEMBER: Call ONLY tools from this list!\n"

    tool_list += "⚠️  DO NOT call: get_time_range, get_metric_statistics (these don't exist!)\n"

    tool_list += "=" * 80 + "\n\n"

    

    return f"""You are an AWS Production Support Engineer for Account {AWS_PROFILE_FOR_TOOLS} (wfoprod) in {AWS_REGION}.

You have tools available to query CloudWatch metrics and logs. Use them to get actual data.

{tool_list}

Answer questions using real data from the tools."""







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

        # Use session state agent (Streamlit context)

        agent_instance = st.session_state.get('agent')

        

        if agent_instance is None:

            return "Error: Agent not initialized. Please refresh the page.", conversation_history or []

        

        response = agent_instance(task_description)

       

        # Handle AgentResult object by extracting the message

        response_text = response.message if hasattr(response, 'message') else str(response)

       

        # Return both the response and the updated conversation history

        return response_text, agent_instance.messages

    except Exception as e:

        error_msg = f"Error executing task: {str(e)}"

        return error_msg, conversation_history or []



# Function to get predefined tasks

def get_predefined_tasks() -> Dict[str, str]:

    """Return the dictionary of predefined tasks"""

    return PREDEFINED_TASKS

def generate_applink_daily_report(conversation_history=None) -> tuple:
    """Generate the AppLink Daily Report using the prompt and dashboard file"""
    try:
        # Read prompt file
        try:
            with open('prompts/appLinkDailyReport.md', 'r', encoding='utf-8') as f:
                prompt_content = f.read()
        except FileNotFoundError:
            return "Error: prompts/appLinkDailyReport.md not found.", conversation_history or []

        # Read dashboard file
        try:
            with open('dashboard/applinkProd.json', 'r', encoding='utf-8') as f:
                dashboard_content = f.read()
        except FileNotFoundError:
            return "Error: dashboard/applinkProd.json not found.", conversation_history or []

        full_prompt = f"{prompt_content}\n\nHere is the dashboard configuration (applink-prod-dashboard.json):\n```json\n{dashboard_content}\n```"
        
        return execute_custom_task(full_prompt, conversation_history)
    except Exception as e:
        return f"Error generating report: {str(e)}", conversation_history or []


if __name__ == "__main__":

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

    with st.sidebar:
        st.header("Reports")
        if st.button("Generate AppLink Daily Report", type="primary"):
            # Add user message to UI history
            st.session_state.messages.append({"role": "user", "content": "Generate AppLink Daily Report"})
            
            # Run the report generation
            with st.spinner("Generating AppLink Daily Report... (This may take a minute)"):
                response, updated_agent_messages = generate_applink_daily_report(
                    conversation_history=st.session_state.agent_messages
                )
                cleaned_response = clean_response(response)
                
                # Update histories
                st.session_state.messages.append({"role": "assistant", "content": cleaned_response})
                st.session_state.agent_messages = updated_agent_messages
                st.rerun()
   

    # Initialize MCP clients only once in session state

    if "mcp_initialized" not in st.session_state:

        with st.spinner("🔧 Initializing AWS MCP clients..."):

            initialize_mcp_clients()

            st.session_state.bedrock_model = get_bedrock_model()

            st.session_state.system_prompt = get_system_prompt()

            st.session_state.agent = Agent(

                tools=time_tools + cloudwatch_tools,

                model=st.session_state.bedrock_model,

                system_prompt=st.session_state.system_prompt

            )

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



