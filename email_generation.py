import openai
import json
from typing import Dict, Any
import os
from dotenv import load_dotenv
load_dotenv()

def generate_email(query: str, model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
    """
    Generate email components from a natural language query using OpenAI.
    
    Args:
        query (str): Natural language description of the email to create
        api_key (str): Your OpenAI API key
        model (str): OpenAI model to use (default: gpt-3.5-turbo)
    
    Returns:
        Dict containing email components: subject, body, to, cc, bcc, priority
    """
    
    # Initialize OpenAI client
    api_key=os.getenv("OPENAI_API_KEY")
    client = openai.OpenAI(api_key=api_key)
    
    # Create the prompt for the LLM
    prompt = f"""
    Based on the following request, generate email components in JSON format:
    
    Request: "{query}"
    
    Please provide a JSON response with the following structure:
    {{
        "subject": "Email subject line",
        "body": "Email body content",
        "to": ["recipient1@example.com"],
        "cc": [],
        "bcc": [],
        "priority": "normal"
    }}
    
    Guidelines:
    - Make the subject clear and concise
    - Write a professional email body
    - For recipients, use placeholder emails if not specified
    - Priority can be: low, normal, high
    - Keep cc and bcc empty if not mentioned
    - Use proper email formatting and etiquette
    """
    
    try:
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates professional emails. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Extract the response content
        email_content = response.choices[0].message.content.strip()
        
        # Parse the JSON response
        email_data = json.loads(email_content)
        
        # Validate required fields
        required_fields = ['subject', 'body', 'to', 'cc', 'bcc', 'priority']
        for field in required_fields:
            if field not in email_data:
                email_data[field] = [] if field in ['to', 'cc', 'bcc'] else ""
        
        return email_data
        
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse JSON response: {e}",
            "raw_response": email_content
        }
    except Exception as e:
        return {
            "error": f"API call failed: {e}"
        }

