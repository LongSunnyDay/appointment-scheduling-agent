import json
import logging
import os

# Initialize logger
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize Boto3 clients if needed outside the handler (e.g., for Secrets Manager)
# secrets_manager = boto3.client('secretsmanager')
# llm_api_key_secret_name = os.environ.get('LLM_API_KEY_SECRET_NAME') # Set via Lambda env var

def lambda_handler(event, context):
    """
    Handles incoming requests for the Langchain AI Agent Lambda.
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract user message from the event body
        # Assumes the event body is a JSON string and contains a 'message' key.
        if 'body' in event and event['body']:
            try:
                body = json.loads(event['body'])
                user_message = body.get('message')
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON body: {e}")
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "Invalid JSON format in request body."
                    })
                }
        else:
            user_message = None

        if not user_message:
            logger.warning("User message not found or empty in the event body.")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Missing 'message' in request body."
                })
            }

        logger.info(f"Extracted user message: {user_message}")

        # TODO: Retrieve LLM API key from AWS Secrets Manager
        # try:
        #     secret_value = secrets_manager.get_secret_value(SecretId=llm_api_key_secret_name)
        #     llm_api_key = secret_value['SecretString']
        # except Exception as e:
        #     logger.error(f"Error retrieving LLM API key from Secrets Manager: {e}")
        #     return {
        #         "statusCode": 500,
        #         "body": json.dumps({
        #             "error": "Could not retrieve LLM API key."
        #         })
        #     }

        # TODO: Initialize Langchain agent (e.g., OpenAI, Anthropic) with the API key
        # Example (conceptual):
        # from langchain.llms import OpenAI # Or other providers
        # from langchain.chains import ConversationChain
        #
        # llm = OpenAI(api_key=llm_api_key)
        # conversation = ConversationChain(llm=llm)
        # logger.info("Langchain agent initialized.")

        # TODO: Pass the user message to the Langchain agent and get a response
        # Example (conceptual):
        # ai_response = conversation.predict(input=user_message)
        # logger.info(f"Response from Langchain agent: {ai_response}")

        # For now, return a dummy success response
        dummy_ai_reply = "Message received. AI Agent is under construction. Your message was: " + user_message
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "reply": dummy_ai_reply
            })
        }

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "An internal server error occurred."
            })
        }

if __name__ == '__main__':
    # Example usage for local testing (optional)
    # Note: For actual Lambda deployment, the handler is 'lambda_function.lambda_handler'
    # and 'boto3' for AWS services will work in the Lambda environment.
    # For local testing without AWS credentials, you might need to mock AWS services or configure local credentials.
    
    # Setup basic logging for local testing
    logging.basicConfig(level=logging.INFO)
    
    test_event_get = {
        "httpMethod": "POST",
        "path": "/chat",
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": "Hello, AI. How are you today?"
        })
    }
    
    test_context = {}
    
    response = lambda_handler(test_event_get, test_context)
    print("\nLambda Response:")
    print(json.dumps(response, indent=2))

    test_event_missing_message = {
        "httpMethod": "POST",
        "path": "/chat",
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({}) # Missing 'message'
    }
    response_missing = lambda_handler(test_event_missing_message, test_context)
    print("\nLambda Response (Missing Message):")
    print(json.dumps(response_missing, indent=2))

    test_event_bad_json = {
        "httpMethod": "POST",
        "path": "/chat",
        "headers": {
            "Content-Type": "application/json"
        },
        "body": "{'message': 'This is not valid JSON'}" # Invalid JSON
    }
    response_bad_json = lambda_handler(test_event_bad_json, test_context)
    print("\nLambda Response (Bad JSON):")
    print(json.dumps(response_bad_json, indent=2))
