
import os


AWS_PROFILE_FOR_TOOLS = os.environ.get("AWS_PROFILE_TOOLS", "wfoprod")
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")

os.environ["AWS_PROFILE"] = AWS_PROFILE_FOR_TOOLS
os.environ["AWS_DEFAULT_REGION"] = AWS_REGION
os.environ["AWS_REGION"] = AWS_REGION

print(f"AWS Tools configured to use profile: {AWS_PROFILE_FOR_TOOLS}, region: {AWS_REGION}")

__all__ = ['AWS_PROFILE_FOR_TOOLS', 'AWS_REGION']

