import os
import sys

# Inject current directory into sys.path to resolve top-level sub-agent module imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from google.adk.apps import App
from orchestrator_agent.agent import create_orchestrator_agent

# Initialize the root orchestrator agent
root_agent = create_orchestrator_agent()

# Define the ADK App
app = App(
    root_agent=root_agent,
    name="marketmind",
)
