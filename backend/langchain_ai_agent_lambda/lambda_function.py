import json
import logging
import os
# import boto3 # If needed for other AWS services like Secrets Manager for API key

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent # Using a modern agent type
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool, Tool # For creating custom tools
from langchain_community.chat_message_histories import ChatMessageHistory # In-memory history for demo
from langchain_core.runnables.history import RunnableWithMessageHistory

# Pydantic might be needed for tool argument schemas if you define them formally
from pydantic import BaseModel, Field
from typing import Type # Required for args_schema type hint if using Pydantic v1 style

# Initialize logger
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# --- Define Dummy Tools ---
class GetServiceListTool(BaseTool):
    name = "GetServiceListTool"
    description = "Use this tool to list available detailing services."
    # args_schema: Type[BaseModel] = None # No args for this simple version

    def _run(self, *args, **kwargs):
        logger.info("GetServiceListTool called")
        return "Available services are: Full Detail, Interior Clean, Exterior Wash, Wax & Polish."

class GetLocationListTool(BaseTool):
    name = "GetLocationListTool"
    description = "Use this tool to list detailing center locations."
    def _run(self, *args, **kwargs):
        logger.info("GetLocationListTool called")
        return "Our locations are: Downtown (123 Main St) and Uptown (456 Central Ave)."

class CheckAvailabilityArgs(BaseModel):
    service_name: str = Field(description="The name of the service.")
    location_name: str = Field(description="The name of the location.")
    date_preference: str = Field(description="The user's preferred date or date range.")

class CheckAvailabilityTool(BaseTool):
    name = "CheckAvailabilityTool"
    description = "Use this tool to check for available appointment slots. Input should be the service name, location name, and desired date or date range."
    args_schema: type[BaseModel] = CheckAvailabilityArgs

    def _run(self, service_name: str, location_name: str, date_preference: str):
        logger.info(f"Tool CheckAvailabilityTool called with: service_name='{service_name}', location_name='{location_name}', date_preference='{date_preference}'")
        if "Downtown" in location_name and "Full Detail" in service_name:
            return f"For {service_name} at {location_name} on {date_preference}, available slots are: Tomorrow at 10:00 AM, Next Tuesday at 2:00 PM."
        return f"Sorry, no slots found for {service_name} at {location_name} on {date_preference} with current mock."

class CreateProvisionalBookingArgs(BaseModel):
    service_name: str = Field(description="The specific name of the service being booked.")
    location_name: str = Field(description="The specific name of the location for the booking.")
    date_time: str = Field(description="The confirmed date and time for the appointment in a clear format (e.g., 'Tomorrow at 10:00 AM' or 'August 15th at 2:00 PM').")
    client_name: str = Field(description="The name of the client making the booking.")
    client_contact: str = Field(description="The contact information for the client (e.g., email or phone number).")

class CreateProvisionalBookingTool(BaseTool):
    name = "CreateProvisionalBookingTool"
    description = "Use this tool to make a tentative booking after confirming all details with the user (service, location, date/time, client name, client contact)."
    args_schema: type[BaseModel] = CreateProvisionalBookingArgs

    def _run(self, service_name: str, location_name: str, date_time: str, client_name: str, client_contact: str):
        logger.info(f"Tool CreateProvisionalBookingTool called for {client_name} for {service_name} at {location_name} on {date_time} with contact {client_contact}")
        # This would call the /bookings API endpoint in a real scenario.
        return f"Provisional booking created for {client_name} for {service_name} at {location_name} on {date_time}. Booking ID: MOCK123. Staff will confirm shortly using {client_contact}."

# --- Lambda Handler ---
def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # --- 1. Load System Prompt ---
        try:
            # Assuming system_prompt.txt is in the same directory as lambda_function.py
            # For AWS Lambda, ensure this file is packaged with your deployment.
            with open("system_prompt.txt", "r", encoding="utf-8") as f:
                system_prompt_text = f.read()
            logger.info("System prompt loaded successfully.")
        except FileNotFoundError:
            logger.error("system_prompt.txt not found. Using a default prompt.")
            system_prompt_text = "You are a helpful assistant specialized in booking car detailing appointments. Be polite and guide the user through the process."
        except Exception as e:
            logger.error(f"Error reading system_prompt.txt: {e}")
            system_prompt_text = "You are a helpful assistant. An error occurred loading detailed instructions."


        # --- 2. Initialize LLM and Tools ---
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if not openai_api_key:
            logger.error("OPENAI_API_KEY environment variable not set.")
            return {"statusCode": 500, "body": json.dumps({"error": "OpenAI API key not configured."})}
        
        llm = ChatOpenAI(temperature=0, openai_api_key=openai_api_key)
        tools = [GetServiceListTool(), GetLocationListTool(), CheckAvailabilityTool(), CreateProvisionalBookingTool()]
        logger.info("LLM and Tools initialized.")

        # --- 3. Create Agent Prompt ---
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt_text),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        logger.info("Agent prompt created.")

        # --- 4. Create Agent ---
        agent = create_openai_tools_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True) # verbose=True for CloudWatch logs
        logger.info("Agent and AgentExecutor created.")

        # --- 5. Set up Chat History ---
        # This is a simplified in-memory store for a single session per Lambda invocation.
        # For production, you'd use DynamoDB, Redis, etc., and manage session_id across invocations.
        store = {} 
        def get_session_history(session_id: str) -> ChatMessageHistory:
            if session_id not in store:
                store[session_id] = ChatMessageHistory()
            return store[session_id]

        agent_with_chat_history = RunnableWithMessageHistory(
            agent_executor,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )
        logger.info("Agent with chat history configured.")

        # --- 6. Process Input ---
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in request body.")
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON format in request body."})}

        user_message = body.get('message')
        session_id = body.get('session_id', 'default_session') # Get or create session_id

        if not user_message:
            logger.warning("Missing 'message' in request body.")
            return {"statusCode": 400, "body": json.dumps({"error": "Missing 'message' in request body."})}
        
        logger.info(f"Processing message for session_id '{session_id}': '{user_message}'")

        # --- 7. Invoke Agent ---
        try:
            response = agent_with_chat_history.invoke(
                {"input": user_message},
                config={"configurable": {"session_id": session_id}},
            )
            ai_response = response.get("output", "Sorry, I encountered an issue processing your request.")
            logger.info(f"Agent response for session_id '{session_id}': '{ai_response}'")
        except Exception as e:
            logger.error(f"Error during agent invocation for session_id '{session_id}': {e}", exc_info=True)
            ai_response = "I'm having trouble connecting to my brain right now. Please try again in a moment."
            # Potentially return a 500 error here if the agent fails consistently
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"reply": ai_response, "session_id": session_id, "error": "Agent execution failed."})
            }
        
        # --- 8. Return Response ---
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"reply": ai_response, "session_id": session_id})
        }

    except Exception as e:
        logger.error(f"An unexpected error occurred in lambda_handler: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "An unexpected server error occurred. Please try again later."})
        }
