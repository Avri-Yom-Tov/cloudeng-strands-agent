from strands import Agent

from strands.tools.mcp import MCPClient

from strands.models import BedrockModel

from mcp import StdioServerParameters, stdio_client




import os

import sys
import atexit

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

def cleanup_mcp_clients():
    """Stop existing MCP clients to free resources"""
    global time_mcp_client, cloudwatch_mcp_client, time_tools, cloudwatch_tools
    
    print("Cleaning up MCP clients...")
    
    if time_mcp_client:
        try:
            print("Stopping Time MCP client...")
            # Check if stop method exists (it should for MCPClient)
            if hasattr(time_mcp_client, 'stop'):
                time_mcp_client.stop(exc_type=None, exc_val=None, exc_tb=None)
            elif hasattr(time_mcp_client, 'close'):
                time_mcp_client.close(exc_type=None, exc_val=None, exc_tb=None)
        except Exception as e:
            print(f"Error stopping Time MCP client: {e}")
        time_mcp_client = None
            
    if cloudwatch_mcp_client:
        try:
            print("Stopping CloudWatch MCP client...")
            if hasattr(cloudwatch_mcp_client, 'stop'):
                cloudwatch_mcp_client.stop(exc_type=None, exc_val=None, exc_tb=None)
            elif hasattr(cloudwatch_mcp_client, 'close'):
                cloudwatch_mcp_client.close(exc_type=None, exc_val=None, exc_tb=None)
        except Exception as e:
            print(f"Error stopping CloudWatch MCP client: {e}")
        cloudwatch_mcp_client = None
            
    time_tools = []
    cloudwatch_tools = []
    print("MCP clients cleanup completed.")

atexit.register(cleanup_mcp_clients)

def initialize_mcp_clients(aws_profile='wfoprod'):

    """Initialize MCP clients once with specified AWS profile"""

    global time_mcp_client, cloudwatch_mcp_client, time_tools, cloudwatch_tools

    # Ensure any existing clients are cleaned up first
    cleanup_mcp_clients()

    is_windows = sys.platform.startswith('win')

    print(f"Detected platform: {'Windows' if is_windows else 'Non-Windows (Linux/macOS)'}")

    print(f"Initializing MCP clients with AWS profile: {aws_profile}")



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

            env_vars = os.environ.copy()
            env_vars.update({
                "FASTMCP_LOG_LEVEL": "ERROR",
                "AWS_PROFILE": aws_profile,
                "AWS_REGION": AWS_REGION
            })

            cloudwatch_mcp_client = MCPClient(lambda: stdio_client(

                StdioServerParameters(

                    command="uv",

                    args=["tool", "run", "--from", "awslabs.cloudwatch-mcp-server@latest", "awslabs.cloudwatch-mcp-server.exe"],

                    env=env_vars

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

            env_vars = os.environ.copy()
            env_vars.update({
                "FASTMCP_LOG_LEVEL": "ERROR",
                "AWS_PROFILE": aws_profile,
                "AWS_REGION": AWS_REGION
            })

            cloudwatch_mcp_client = MCPClient(lambda: stdio_client(

                StdioServerParameters(

                    command="uvx",

                    args=["--from", "awslabs.cloudwatch-mcp-server@latest", "awslabs.cloudwatch-mcp-server"],

                    env=env_vars

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
            with open('dashboard/applink.json', 'r', encoding='utf-8') as f:
                dashboard_content = f.read()
        except FileNotFoundError:
            return "Error: dashboard/applink.json not found.", conversation_history or []

        full_prompt = f"{prompt_content}\n\nHere is the dashboard configuration (applink-prod-dashboard.json):\n```json\n{dashboard_content}\n```"
        
        return execute_custom_task(full_prompt, conversation_history)
    except Exception as e:
        return f"Error generating report: {str(e)}", conversation_history or []

def generate_smartreach_daily_report(conversation_history=None) -> tuple:
    """Generate the SmartReach Daily Report using the prompt and dashboard file"""
    try:
        # Read prompt file
        try:
            with open('prompts/smartReachReport.md', 'r', encoding='utf-8') as f:
                prompt_content = f.read()
        except FileNotFoundError:
            return "Error: prompts/smartReachReport.md not found.", conversation_history or []

        # Read dashboard file
        try:
            with open('dashboard/smartReach.json', 'r', encoding='utf-8') as f:
                dashboard_content = f.read()
        except FileNotFoundError:
            return "Error: dashboard/smartReach.json not found.", conversation_history or []

        full_prompt = f"{prompt_content}\n\nHere is the dashboard configuration (smartReach-prod-dashboard.json):\n```json\n{dashboard_content}\n```"
        
        return execute_custom_task(full_prompt, conversation_history)
    except Exception as e:
        return f"Error generating report: {str(e)}", conversation_history or []

def generate_ticketing_daily_report(conversation_history=None) -> tuple:
    """Generate the Ticketing Daily Report using the prompt and dashboard file"""
    try:
        # Read prompt file
        try:
            with open('prompts/ticketingDailyReport.md', 'r', encoding='utf-8') as f:
                prompt_content = f.read()
        except FileNotFoundError:
            return "Error: prompts/ticketingDailyReport.md not found.", conversation_history or []

        # Read dashboard file
        try:
            with open('dashboard/ticketing.json', 'r', encoding='utf-8') as f:
                dashboard_content = f.read()
        except FileNotFoundError:
            return "Error: dashboard/ticketing.json not found.", conversation_history or []

        full_prompt = f"{prompt_content}\n\nHere is the dashboard configuration (ticketing-prod-dashboard.json):\n```json\n{dashboard_content}\n```"
        
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

    # Custom CSS for modern, soft design
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 0.5rem;
        }
        .sub-header {
            font-size: 1.1rem;
            color: #6b7280;
            margin-bottom: 2rem;
        }
        .report-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 1rem;
            color: white;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .report-card h2 {
            margin: 0;
            font-size: 1.5rem;
            font-weight: 600;
        }
        .report-card p {
            margin: 0.5rem 0 0 0;
            opacity: 0.9;
        }
        .quick-action {
            background: white;
            padding: 1rem;
            border-radius: 0.75rem;
            margin-bottom: 0.75rem;
            border: 1px solid #e5e7eb;
            transition: all 0.2s;
        }
        .quick-action:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            border-color: #667eea;
        }
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.875rem;
            font-weight: 500;
        }
        .status-ready {
            background: #d1fae5;
            color: #065f46;
        }
        .status-working {
            background: #fef3c7;
            color: #92400e;
        }
        </style>
    """, unsafe_allow_html=True)

    # Initialize current AWS profile in session state
    if "current_aws_profile" not in st.session_state:
        # Check query params
        params = st.query_params
        st.session_state.current_aws_profile = params.get("profile", "wfoprod")

    # Initialize MCP clients only once in session state or when profile changes
    if "mcp_initialized" not in st.session_state or st.session_state.get("profile_changed", False):
        with st.spinner(f"🔧 Initializing AWS MCP clients with profile: {st.session_state.current_aws_profile}..."):
            initialize_mcp_clients(st.session_state.current_aws_profile)
            st.session_state.bedrock_model = get_bedrock_model()
            st.session_state.system_prompt = get_system_prompt()
            st.session_state.agent = Agent(
                tools=time_tools + cloudwatch_tools,
                model=st.session_state.bedrock_model,
                system_prompt=st.session_state.system_prompt
            )
            st.session_state.mcp_initialized = True
            st.session_state.profile_changed = False

    # Initialize session state for UI messages (for display)
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Initialize session state for agent conversation history (Bedrock format)
    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []

    # Sidebar with modern design
    with st.sidebar:
        st.markdown("### 🔧 AWS Profile")
        st.markdown("---")
        
        # Profile selector
        current_profile = st.session_state.current_aws_profile
        
        profile_options = ["wfoprod", "production-rec"]
        profile_display = {"wfoprod": "🟢 WFO Prod", "production-rec": "🔵 Production REC"}
        
        selected_profile = st.selectbox(
            "Select AWS Profile",
            options=profile_options,
            index=profile_options.index(current_profile),
            format_func=lambda x: profile_display[x]
        )
        
        if selected_profile != current_profile:
            if st.button("🔄 Switch Profile & Reload", type="primary", use_container_width=True):
                cleanup_mcp_clients()
                st.session_state.clear()
                st.markdown(f'<meta http-equiv="refresh" content="0;url=?profile={selected_profile}">', unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📊 Daily Reports")
        st.markdown("---")
        
        # Report configuration
        report_configs = {
            "applink": {
                "label": "🚀 AppLink Report",
                "required_profile": "wfoprod",
                "report_type": "applink"
            },
            "smartreach": {
                "label": "🌐 SmartReach Report",
                "required_profile": "production-rec",
                "report_type": "smartreach"
            },
            "ticketing": {
                "label": "🎫 Ticketing Report",
                "required_profile": "production-rec",
                "report_type": "ticketing"
            }
        }
        
        for report_key, config in report_configs.items():
            if st.button(config["label"], use_container_width=True):
                if st.session_state.current_aws_profile != config["required_profile"]:
                    st.warning(f"⚠️ You must switch profile to '{config['required_profile']}' to select this option!")
                else:
                    st.session_state.generating_report = config["report_type"]
                    st.session_state.messages.append({"role": "user", "content": f"Generate {config['label']} Daily Report"})
                    st.rerun()
        
        st.markdown("---")
        
        # Quick Actions
        st.markdown("#### ⚡ Quick Actions")
        
        quick_actions = {
            "🔍 Lambda Errors": "Check for Lambda function errors and failures in the last hour",
            "⚠️ CloudWatch Alarms": "Check current CloudWatch alarms status",
            "📈 Performance Metrics": "Get performance metrics for Lambda functions"
        }
        
        for label, task in quick_actions.items():
            if st.button(label, use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": task})
                with st.chat_message("user"):
                    st.markdown(task)
                with st.chat_message("assistant"):
                    with st.spinner("🔍 Analyzing..."):
                        response, updated_agent_messages = execute_custom_task(
                            task,
                            conversation_history=st.session_state.agent_messages
                        )
                        cleaned_response = clean_response(response)
                        st.markdown(cleaned_response)
                st.session_state.messages.append({"role": "assistant", "content": cleaned_response})
                st.session_state.agent_messages = updated_agent_messages
                st.rerun()
        
        st.markdown("---")
        
        # System Status
        st.markdown("#### 💡 System Status")
        st.success("✓ MCP Clients Ready")
        st.info(f"Region: {AWS_REGION}")
        st.info(f"Profile: {st.session_state.current_aws_profile}")
        
        st.markdown("---")
        
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent_messages = []
            st.rerun()

    # Main content
    st.markdown('<div class="main-header">🔧 AWS Production Support</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Monitor, analyze, and manage your AWS production environment</div>', unsafe_allow_html=True)

    # Handle report generation with progress
    if st.session_state.get("generating_report", False):
        report_type = st.session_state.generating_report
        st.session_state.generating_report = False
        
        report_names = {
            "applink": "AppLink Daily Report",
            "smartreach": "SmartReach Daily Report",
            "ticketing": "Ticketing Daily Report"
        }
        
        report_functions = {
            "applink": generate_applink_daily_report,
            "smartreach": generate_smartreach_daily_report,
            "ticketing": generate_ticketing_daily_report
        }
        
        report_name = report_names.get(report_type, "Unknown Report")
        report_function = report_functions.get(report_type)
        
        with st.chat_message("user"):
            st.markdown(f"Generate {report_name}")
        
        with st.chat_message("assistant"):
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            progress_placeholder.progress(0.2)
            status_placeholder.info("📊 Collecting CloudWatch metrics...")
            
            if report_function:
                response, updated_agent_messages = report_function(
                    conversation_history=st.session_state.agent_messages
                )
            else:
                response = f"Error: Unknown report type '{report_type}'"
                updated_agent_messages = st.session_state.agent_messages
            
            progress_placeholder.progress(0.8)
            status_placeholder.info("📝 Generating comprehensive report...")
            
            cleaned_response = clean_response(response)
            
            progress_placeholder.progress(1.0)
            status_placeholder.success("✅ Report generated successfully!")
            
            st.markdown(cleaned_response)
        
        st.session_state.messages.append({"role": "assistant", "content": cleaned_response})
        st.session_state.agent_messages = updated_agent_messages

    # Display welcome message if no messages yet
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            profile_emoji = "🟢" if st.session_state.current_aws_profile == "wfoprod" else "🔵"
            st.markdown(f"""
            👋 **Welcome to AWS Production Support!**
            
            **Current Profile:** {profile_emoji} `{st.session_state.current_aws_profile}`
            
            I can help you with:
            - 📊 Generate comprehensive daily reports (AppLink, SmartReach, Ticketing)
            - 🔍 Analyze Lambda invocations and errors
            - ⚠️ Check CloudWatch alarms
            - 📈 Review performance metrics
            - 🔎 Investigate error patterns
            
            **Available Reports:**
            - 🚀 **AppLink Report** (requires `wfoprod` profile)
            - 🌐 **SmartReach Report** (requires `production-rec` profile)
            - 🎫 **Ticketing Report** (requires `production-rec` profile)
            
            Use the sidebar to switch profiles and generate reports, or ask me anything about your production environment.
            """)

    # Display all previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle new user input
    if prompt := st.chat_input("💬 Ask about production metrics, errors, alarms..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            progress_placeholder.progress(0.3)
            status_placeholder.info("🔍 Analyzing CloudWatch metrics...")
            
            response, updated_agent_messages = execute_custom_task(
                prompt,
                conversation_history=st.session_state.agent_messages
            )
            
            progress_placeholder.progress(0.9)
            status_placeholder.info("📝 Preparing response...")
            
            cleaned_response = clean_response(response)
            
            progress_placeholder.empty()
            status_placeholder.empty()
            
            st.markdown(cleaned_response)
        
        st.session_state.messages.append({"role": "assistant", "content": cleaned_response})
        st.session_state.agent_messages = updated_agent_messages
        
        st.rerun()



