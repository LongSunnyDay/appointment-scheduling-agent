import json
import os
import logging
import hmac
import hashlib
import boto3 # For invoking the Langchain agent Lambda

# Initialize logger
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
FB_APP_SECRET = os.environ.get('FB_APP_SECRET')
FB_VERIFY_TOKEN = os.environ.get('FB_VERIFY_TOKEN') # Your predefined verify token
LANGCHAIN_LAMBDA_NAME = os.environ.get('LANGCHAIN_LAMBDA_NAME')

if not FB_APP_SECRET:
    logger.critical("FB_APP_SECRET environment variable not set.")
if not FB_VERIFY_TOKEN:
    logger.critical("FB_VERIFY_TOKEN environment variable not set.")
if not LANGCHAIN_LAMBDA_NAME:
    logger.warning("LANGCHAIN_LAMBDA_NAME environment variable not set. Cannot invoke agent.")

lambda_client = boto3.client('lambda')

def verify_signature(signature, payload_body, app_secret):
    if not signature:
        logger.warning("Signature not provided in request.")
        return False
    if not app_secret:
        logger.error("App secret not configured for verification.")
        return False # Should not happen if FB_APP_SECRET is checked at startup

    expected_signature_parts = signature.split('=', 1)
    if len(expected_signature_parts) != 2 or expected_signature_parts[0] != 'sha256':
        logger.warning(f"Invalid signature format: {signature}")
        return False
    
    expected_hash = expected_signature_parts[1]
    
    calculated_hash = hmac.new(
        app_secret.encode('utf-8'),
        payload_body.encode('utf-8'), # payload_body should be the raw request body string
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(calculated_hash, expected_hash)

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    http_method = event.get('httpMethod', 'GET').upper()

    if http_method == 'GET':
        # Webhook verification
        params = event.get('queryStringParameters', {})
        if params:
            hub_mode = params.get('hub.mode')
            hub_challenge = params.get('hub.challenge')
            hub_verify_token = params.get('hub.verify_token')

            if hub_mode == 'subscribe' and hub_verify_token == FB_VERIFY_TOKEN:
                logger.info(f"Webhook verification successful. Responding with challenge: {hub_challenge}")
                return {
                    'statusCode': 200,
                    'body': hub_challenge # Must be plain text
                }
            else:
                logger.warning("Webhook verification failed. Mode or token mismatch.")
                return {'statusCode': 403, 'body': 'Verification failed'}
        else:
            logger.warning("GET request with no query parameters.")
            return {'statusCode': 400, 'body': 'Missing query parameters for GET'}

    elif http_method == 'POST':
        # Handle incoming messages
        signature = event.get('headers', {}).get('x-hub-signature-256') # Case-insensitive for headers
        if not signature: # Some API Gateways might lowercase all headers
            signature = event.get('headers', {}).get('X-Hub-Signature-256')

        request_body_str = event.get('body', '{}') # Raw string body

        if not verify_signature(signature, request_body_str, FB_APP_SECRET):
            logger.warning("Signature verification failed for POST request.")
            return {'statusCode': 401, 'body': json.dumps({'error': 'Signature verification failed'})}
        
        logger.info("Signature verified for POST request.")
        
        try:
            body_json = json.loads(request_body_str)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in POST request body.")
            return {'statusCode': 400, 'body': json.dumps({'error': 'Invalid JSON format'})}

        if body_json.get('object') == 'page': # Check if it's a page subscription event
            for entry in body_json.get('entry', []):
                for messaging_event in entry.get('messaging', []):
                    if messaging_event.get('message') and not messaging_event['message'].get('is_echo'): # It's a message, not an echo
                        sender_id = messaging_event['sender']['id']
                        message_text = messaging_event['message'].get('text')
                        
                        if sender_id and message_text:
                            logger.info(f"Received message from sender {sender_id}: '{message_text}'")
                            
                            # Placeholder: Invoke Langchain agent Lambda
                            if LANGCHAIN_LAMBDA_NAME:
                                try:
                                    payload = {
                                        "body": json.dumps({ # Langchain Lambda expects a 'body' with 'message'
                                            "message": message_text,
                                            "session_id": f"fb_{sender_id}" # Create a session ID
                                        })
                                    }
                                    logger.info(f"Invoking Langchain agent Lambda '{LANGCHAIN_LAMBDA_NAME}' with payload: {json.dumps(payload)}")
                                    # response = lambda_client.invoke( # This sends to Langchain lambda but doesn't wait and reply here.
                                    #     FunctionName=LANGCHAIN_LAMBDA_NAME,
                                    #     InvocationType='Event', # Asynchronous
                                    #     Payload=json.dumps(payload)
                                    # )
                                    # For a direct reply, you might use 'RequestResponse' and process the response.
                                    # For now, we assume the Langchain Lambda handles outbound messaging or another mechanism does.
                                    # logger.info(f"Langchain agent Lambda invocation response: {response}")
                                    
                                    # If we want to send a reply back via Messenger API directly from here,
                                    # we would need another function call here.
                                    # For this task, just logging the intent.
                                    logger.info("Placeholder: Logic to send AI response back to Messenger user would be here.")

                                except Exception as e:
                                    logger.error(f"Error invoking Langchain Lambda: {e}", exc_info=True)
                            else:
                                logger.warning("LANGCHAIN_LAMBDA_NAME not set, cannot invoke agent.")
                        else:
                            logger.info("Received message without sender_id or text.")
                    else:
                        logger.info(f"Received non-message event or echo: {json.dumps(messaging_event)}")
            
            return {'statusCode': 200, 'body': json.dumps({'status': 'success'})}
        else:
            logger.info("Received POST request that is not a 'page' object event.")
            return {'statusCode': 200, 'body': json.dumps({'status': 'event_received_but_not_page_subscription'})}

    else:
        logger.warning(f"Unsupported HTTP method: {http_method}")
        return {
            'statusCode': 405, # Method Not Allowed
            'body': json.dumps({'error': f'Unsupported method: {http_method}'})
        }
