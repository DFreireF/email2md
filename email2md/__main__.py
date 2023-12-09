import imaplib
import email
from bs4 import BeautifulSoup
import markdown
import markdown2pdf
import toml

# Email configuration
IMAP_SERVER = "email.gsi.de"
IMAP_PORT = 993

def load_config(config_path):
    try:
        with open(config_path, 'r') as config_file:
            config = toml.load(config_file)
        return config
    except FileNotFoundError:
        print(f"Error: Config file '{config_path}' not found.")
        return None

def controller(tomlpath, subject_filter, sender_filter):

    if tomlpath:
        config = load_config(tomlpath)

        if config:
            # Use the values from the config
            EMAIL_USER = config.get('EMAIL_USER', '')
            EMAIL_PASSWORD = config.get('EMAIL_PASSWORD', '')

    else:
        print("Error: Please provide a path to the TOML configuration file using --tomlpath.")
    
    # Connect to the email server
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(EMAIL_USER, EMAIL_PASSWORD)
    mail.select("inbox")

    # Build search criteria based on user input
    search_criteria = 'ALL'  # Default to retrieving all emails
    if subject_filter:
        search_criteria = f'SUBJECT "{subject_filter}"'
    if sender_filter:
        search_criteria = f'FROM "{sender_filter}"'

    # Search for emails based on the criteria
    status, messages = mail.search(None, search_criteria)
    messages = messages[0].split()

    # Create a Markdown file
    with open("email_chain.md", "w", encoding="utf-8") as md_file:
        md_file.write("# Email Chain\n")

        # Loop through each email in the thread
        for msg_id in messages:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            # Extract sender and content
            sender = msg.get("From")
            subject = msg.get("Subject")
            body = ""

            # Extract content from the email body (support for HTML emails)
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    if part.get_payload(decode=True) is not None:
                        try:
                            body = part.get_payload(decode=True).decode("utf-8")
                        except UnicodeDecodeError:
                            # Try decoding with ISO-8859-1 if UTF-8 fails
                            body = part.get_payload(decode=True).decode("ISO-8859-1")
                        break
            else:
                try:
                    body = msg.get_payload(decode=True).decode("utf-8")
                except UnicodeDecodeError:
                    # Try decoding with ISO-8859-1 if UTF-8 fails
                    body = msg.get_payload(decode=True).decode("ISO-8859-1")

            # Convert HTML to plain text using BeautifulSoup
            soup = BeautifulSoup(body, "html.parser")
            body_text = soup.get_text()

            # Add sender and content to the Markdown file
            md_file.write(f"\n## {sender}\n")
            md_file.write(f"**Subject:** {subject}\n\n")
            md_file.write(markdown.markdown(body_text))
            md_file.write("\n---\n")

    markdown2pdf.convert_md_2_pdf('email_chain.md', 'email_chain.pdf')
    # Close the connection
    mail.logout()

def main():
    scriptname = 'email2md&pdf' 
    parser = argparse.ArgumentParser()

    # Main Arguments
    parser.add_argument('--tomlpath', type=str, help='Path to the TOML configuration file')
    args = parser.parse_args()

    # Get user input for email subject or sender
    subject_filter = input("Enter the email subject (or leave blank for no subject filter): ").strip()
    sender_filter = input("Enter the sender's email address (or leave blank for no sender filter): ").strip()
    controller(args.tomlpath, subject_filter, sender_filter)


if __name__ == "__main__":
    main()