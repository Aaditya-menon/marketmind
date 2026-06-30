import os
import sys
sys.path.insert(0, os.getcwd())
import asyncio
import json
from agent import root_agent
from google.adk.apps import App
from google.adk.sessions import Session
from google.adk.agents.invocation_context import InvocationContext
from google.adk.services.service_factory import ServiceFactory
from google.genai import types

async def main():
    session = Session(
        id="test_session",
        app_name="marketmind",
        user_id="user",
        state={}
    )
    
    # We will simulate a user message requesting analysis for 'BTC'
    user_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text="BTC")]
    )
    
    # Instantiate services
    service_factory = ServiceFactory(use_local_storage=True)
    session_service = service_factory.get_session_service()
    artifact_service = service_factory.get_artifact_service()
    memory_service = service_factory.get_memory_service()
    credential_service = service_factory.get_credential_service()
    
    await session_service.create_session(session)
    
    ctx = InvocationContext(
        session_service=session_service,
        artifact_service=artifact_service,
        memory_service=memory_service,
        credential_service=credential_service,
        invocation_id="test_inv",
        session=session,
        user_content=user_content
    )
    
    print("Running orchestrator...")
    # First turn - should trigger HITL input request
    events = []
    async for event in root_agent.run_async(ctx):
        events.append(event)
        
    print("\n--- Event 1 State ---")
    print(json.dumps(ctx.session.state, indent=2, default=str))
    
    # Resume with HITL input response 'yes'
    resume_part = types.Part(
        function_response=types.FunctionResponse(
            name="adk_request_input",
            id=f"hitl_confirm_BTC",
            response={"result": "yes"}
        )
    )
    
    resume_event = Event(
        author="user",
        content=types.Content(
            role="user",
            parts=[resume_part]
        )
    )
    ctx.session.events.append(resume_event)
    await session_service.update_session(ctx.session)
    
    ctx.user_content = resume_event.content
    
    print("\nResuming orchestrator after HITL...")
    async for event in root_agent.run_async(ctx):
        events.append(event)
        
    print("\n--- Final Session State ---")
    print(json.dumps(ctx.session.state, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())
