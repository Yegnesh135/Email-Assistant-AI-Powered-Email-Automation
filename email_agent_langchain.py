import openai
import smtplib
import json
import os
from typing import Dict, Any, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import AgentAction, AgentFinish

load_dotenv()

# Configuration
SENDER_EMAIL = ""
SENDER_PASSWORD = ""
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

@tool
def generate_email_content(query: str) -> str:
    """
    Generate email components from a natural language query using OpenAI.
    
    Args:
        query: Natural language description of the email to create
        
    Returns:
        JSON string containing email components: subject, body, to, cc, bcc, priority
    """
    try:
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return json.dumps({"error": "OpenAI API key not found in environment variables"})
        
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
        - Extract actual email addresses from the request if provided
        - If no specific recipients mentioned, use placeholder emails
        - Priority can be: low, normal, high
        - Keep cc and bcc empty if not mentioned
        - Use proper email formatting and etiquette
        - End emails with appropriate closing and sender name
        """
        
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates professional emails. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Extract the response content
        email_content = response.choices[0].message.content.strip()
        
        # Parse and validate JSON
        email_data = json.loads(email_content)
        
        # Validate required fields
        required_fields = ['subject', 'body', 'to', 'cc', 'bcc', 'priority']
        for field in required_fields:
            if field not in email_data:
                if field in ['to', 'cc', 'bcc']:
                    email_data[field] = []
                elif field == 'priority':
                    email_data[field] = 'normal'
                else:
                    email_data[field] = ""
        
        # Ensure 'to' field has at least one recipient
        if not email_data['to']:
            email_data['to'] = ['recipient@example.com']
            
        return json.dumps(email_data, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "error": f"Failed to parse JSON response: {str(e)}",
            "raw_response": email_content if 'email_content' in locals() else "No response"
        })
    except Exception as e:
        return json.dumps({"error": f"Email generation failed: {str(e)}"})

@tool  
def send_email_smtp(email_data_json: str) -> str:
    """
    Send an email using SMTP with Gmail configuration.
    
    Args:
        email_data_json: JSON string containing email data with keys: subject, body, to, cc, bcc, priority
        
    Returns:
        Success or error message
    """
    try:
        # Parse email data
        email_data = json.loads(email_data_json)
        
        # Validate required fields
        if not email_data.get('subject'):
            return "Error: Email subject is required"
        if not email_data.get('body'):
            return "Error: Email body is required"
        if not email_data.get('to') or len(email_data['to']) == 0:
            return "Error: At least one recipient is required"
            
        # Create message
        message = MIMEMultipart()
        message["From"] = SENDER_EMAIL
        message["To"] = ", ".join(email_data['to'])
        message["Subject"] = email_data['subject']
        
        # Add CC and BCC if present
        if email_data.get('cc'):
            message["Cc"] = ", ".join(email_data['cc'])
        if email_data.get('bcc'):
            message["Bcc"] = ", ".join(email_data['bcc'])
            
        # Set priority if specified
        priority = email_data.get('priority', 'normal')
        if priority == 'high':
            message["X-Priority"] = "1"
            message["X-MSMail-Priority"] = "High"
        elif priority == 'low':
            message["X-Priority"] = "5"
            message["X-MSMail-Priority"] = "Low"
        
        # Add body to the message
        message.attach(MIMEText(email_data['body'], "plain"))
        
        # Prepare recipient list (to + cc + bcc)
        all_recipients = email_data['to'].copy()
        if email_data.get('cc'):
            all_recipients.extend(email_data['cc'])
        if email_data.get('bcc'):
            all_recipients.extend(email_data['bcc'])
        
        # Connect to SMTP server and send
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        text = message.as_string()
        server.sendmail(SENDER_EMAIL, all_recipients, text)
        server.quit()
        
        return f"Email sent successfully to: {', '.join(all_recipients)}"
        
    except json.JSONDecodeError as e:
        return f"Error: Invalid email data format - {str(e)}"
    except smtplib.SMTPAuthenticationError:
        return "Error: SMTP authentication failed. Please check your email credentials."
    except smtplib.SMTPRecipientsRefused as e:
        return f"Error: Invalid recipient email addresses - {str(e)}"
    except smtplib.SMTPServerDisconnected:
        return "Error: SMTP server connection lost. Please try again."
    except Exception as e:
        return f"Error: Failed to send email - {str(e)}"

# Create the agent prompt
agent_prompt = PromptTemplate.from_template("""
You are an intelligent email assistant that can generate and send emails based on natural language requests.

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

IMPORTANT INSTRUCTIONS:
1. Always generate email content first using generate_email_content tool
2. Before sending any email, show the generated email to the user and ask for confirmation
3. Only send the email after receiving explicit confirmation from the user
4. Handle all errors gracefully and provide helpful error messages
5. If email addresses look like placeholders (example.com), ask the user for real recipient addresses

Begin!

Question: {input}
{agent_scratchpad}
""")

def create_email_agent():
    """Create and return the email agent"""
    # Initialize the language model
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create tools list
    tools = [generate_email_content, send_email_smtp]
    
    # Create the agent
    agent = create_react_agent(llm, tools, agent_prompt)
    
    # Create agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10
    )
    
    return agent_executor

def run_email_agent():
    """Main function to run the email agent interactively"""
    agent_executor = create_email_agent()
    
    print("🤖 Email Agent Started!")
    print("I can help you generate and send emails using natural language.")
    print("Type 'quit' to exit.\n")
    
    while True:
        try:
            user_input = input("👤 What would you like me to do? ")
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
                
            if not user_input.strip():
                continue
                
            print("\n🔄 Processing your request...\n")
            
            # Run the agent
            result = agent_executor.invoke({"input": user_input})
            
            print(f"\n✅ {result['output']}\n")
            print("-" * 50 + "\n")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")

if __name__ == "__main__":
    # Test the tools individually (optional)
    print("Testing email generation...")
    test_result = generate_email_content("Send a thank you email to *******@gmail.com for the great meeting yesterday")
    print("Generated email:", test_result)
    
    print("\n" + "="*50 + "\n")
    
    # Run the interactive agent
    run_email_agent()