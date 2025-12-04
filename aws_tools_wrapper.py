"""
AWS Configuration for Cross-Account Access
This module sets up the environment for using wfoprod profile
"""

import os

# Profile to use for all AWS operations
AWS_PROFILE_FOR_TOOLS = os.environ.get("AWS_PROFILE_TOOLS", "wfoprod")
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")

# Set AWS environment variables for boto3 to use wfoprod profile
# This will be used by use_aws tool
os.environ["AWS_PROFILE"] = AWS_PROFILE_FOR_TOOLS
os.environ["AWS_DEFAULT_REGION"] = AWS_REGION
os.environ["AWS_REGION"] = AWS_REGION

print(f"AWS Tools configured to use profile: {AWS_PROFILE_FOR_TOOLS}, region: {AWS_REGION}")

# Export for use in agent
__all__ = ['AWS_PROFILE_FOR_TOOLS', 'AWS_REGION']

