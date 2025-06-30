import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(subject, body, sender_email, sender_password, recipient_email):
    """Send an email using SMTP"""

    try:
        # create message
        message = MIMEMultipart()
        message["From"]=sender_email
        message["To"]=recipient_email
        message["Subject"]=subject

        # Add body to the message
        message.attach(MIMEText(body, "plain"))

        # Connect to the SMTP server
        smtp_server= "smtp.gmail.com"
        port= 587

        # Create SMTP session
        server = smtplib.SMTP(smtp_server,port)
        server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
        server.login(sender_email, sender_password)

        # Send the email
        text=message.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()

        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

if __name__ == "__main__":
    sender_email = ""
    sender_password = ""
    receiver=""
    subject="SMTP Test Email"
    body="""
    Hello,

    This is the testing eamil sent using SMTP protocol over python.

    Regards,
    Yegneshwar G.
    """  

    send_email(subject, body, sender_email, sender_password, recipient_email=receiver)
