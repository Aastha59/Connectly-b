from datetime import datetime
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from utils import extract_contacts
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
import os
import uvicorn
from dotenv import load_dotenv

import motor.motor_asyncio
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")  # Your MongoDB connection string in .env

client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client.connectly_db           # database named "connectly_db"
email_collection = db.connectly_collection  # collection named "connectly_collection"


GOOGLE_CUSTOM_SEARCH_API = os.getenv("GOOGLE_CUSTOM_SEARCH_API")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "https://connectly-f-r9k1.vercel.app", "https://www.connectlyai.in", "https://connectlyai.in", "https://connectlyai.in/", "connectlyai.in"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    
)

class SearchRequest(BaseModel):
    role: str
    country: str
    profile: str
    contact_type: str 

# def serp_search(query):
#     # url = "https://serpapi.com/search"
#     url = "https://www.googleapis.com/customsearch/v1"
#     params = {
#         "engine": "google",
#         "q": query,
#         "api_key": GOOGLE_CUSTOM_SEARCH_API,
#         "hl": "en",
#         "num": "6"
#     }
#     resp = requests.get(url, params=params)
#     if resp.status_code != 200:
#         print(f"Google Custom Search API error {resp.status_code}: {resp.text}")
#         resp.raise_for_status()
#     return resp.json()

def serp_search(query, start=0):
    url = "https://www.googleapis.com/customsearch/v1"
    # params = {
    #     "q": query,
    #     "key": GOOGLE_CUSTOM_SEARCH_API,   # ✅ correct param name
    #     "cx": os.getenv("GOOGLE_CSE_ID"),  # ✅ add your Search Engine ID
    #     "hl": "en",
    #     "num": 5,
    #     "start": start + 1                 # Google’s "start" is 1-based
    # }
    params = {
    "q": query,
    "key": GOOGLE_CUSTOM_SEARCH_API,      # ✅ correct
    "cx": os.getenv("GOOGLE_CSE_ID"),     # ✅ required (your CSE ID)
    "num": 5,
    "start": start + 1                    # Google is 1-based
    }

    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print(f"Google Custom Search API error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    return resp.json()


@app.get("/")
def read_root():
    return {"status": "Backend is running!"}

# @app.post("/api/search")
# def search_contacts(req: SearchRequest):
#     profile_map = {
#         "linkedin": "linkedin.com",
#         "instagram": "instagram.com",
#         "youtube": "youtube.com"
#     }
#     profile_site = profile_map.get(req.profile.lower(), "linkedin.com")
#     qry = f'site:{profile_site} "{req.role}" "{req.country}"'
#     if req.contact_type.lower() == 'gmail':
#         qry += ' "@gmail.com"'
#     if req.contact_type.lower() == 'mobile':
#         qry += ' "contact number"'

#     data = serp_search(qry)
#     results = []
#     count = 0

#     for result in data.get("organic_results", []):
#         snippet = result.get("snippet", "")
#         contacts = extract_contacts(snippet, req.contact_type)
#         for c in contacts:
#             if c not in results:
#                 results.append(c)
#                 count += 1
#                 if count >= 50:
#                     break
#         if count >= 50:
#             break

#     contacts_to_return = results[:50]
#     print("Extracted contacts:", contacts_to_return)
#     return {"contacts": contacts_to_return}

@app.post("/api/search")
def search_contacts(req: SearchRequest):
    try:
        profile_map = {
            "linkedin": "linkedin.com",
            "instagram": "instagram.com",
            "youtube": "youtube.com"
        }
        profile_site = profile_map.get(req.profile.lower(), "linkedin.com")
        
        # More robust query construction
        qry = f'site:{profile_site} "{req.role}" "{req.country}"'
        if req.contact_type.lower() == 'gmail':
            qry += ' ("@gmail.com" OR "gmail.com")'
        if req.contact_type.lower() == 'mobile':
            qry += ' ("contact number" OR "phone" OR "mobile")'
    
        results = []
        seen = set()
        count = 0
        start = 0
    
        # Paginate through multiple Google custom pages to get more data
        # while count < 7 and start < 30:  # limit to first 30 results (safety)
        #     params = {
        #         "engine": "google",
        #         "q": qry,
        #         "api_key": GOOGLE_CUSTOM_SEARCH_API,
        #         "hl": "en",
        #         "num": "5",  # fetch 5 per page
        #         "start": start
        #     }
        #     resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
        #     if resp.status_code != 200:
        #         print(f"Google Custom Search API error {resp.status_code}: {resp.text}")
        #         break
            
        #     # data = resp.json()
        #     # organic_results = data.get("organic_results", [])
        #     # if not organic_results:
        #     #     break  # no more results
    
        #     # for result in organic_results:
        #     #     snippet = result.get("snippet", "")
        #     #     title = result.get("title", "")
        #     #     link = result.get("link", "")
    
        #     #     text_to_parse = f"{title}\n{snippet}\n{link}"
        #     #     contacts = extract_contacts(text_to_parse, req.contact_type)
    
        #     #     for c in contacts:
        #     #         if c not in seen:
        #     #             results.append(c)
        #     #             seen.add(c)
        #     #             count += 1
        #     #             if count >= 7:
        #     #                 break
        #     #     if count >= 7:
        #     #         break
    
        #     data = serp_search(qry, start)   # use our helper function
        #     items = data.get("items", [])
        #     if not items:
        #         break  # no more results
            
        #     for result in items:
        #         snippet = result.get("snippet", "")
        #         title = result.get("title", "")
        #         link = result.get("link", "")
            
        #         text_to_parse = f"{title}\n{snippet}\n{link}"
        #         contacts = extract_contacts(text_to_parse, req.contact_type)
            
        #         for c in contacts:
        #             if c not in seen:
        #                 results.append(c)
        #                 seen.add(c)
        #                 count += 1
        #                 if count >= 7:
        #                     break
        #         if count >= 7:
        #             break
    
        #     start += 5  # next page
        
        while count < 7 and start < 30:
            data = serp_search(qry, start)
            items = data.get("items", [])
            if not items:
                break
        
            for result in items:
                snippet = result.get("snippet", "")
                title = result.get("title", "")
                link = result.get("link", "")
        
                text_to_parse = f"{title}\n{snippet}\n{link}"
                contacts = extract_contacts(text_to_parse, req.contact_type)
        
                for c in contacts:
                    if c not in seen:
                        results.append(c)
                        seen.add(c)
                        count += 1
                        if count >= 7:
                            break
                if count >= 7:
                    break
        
            start += 5
        
    
        print(f"Extracted {len(results)} contacts:", results)
        return {"contacts": results}
    except Exception as e:
        print(f"❌ Backend error in /api/search: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "detail": str(e)}
        )


@app.post("/api/templates")
def get_email_templates():
    templates = [
        {
            "subject": "Exploring Opportunities for {role} in {country}",
            "body": """Dear [Recipient’s Name],

I hope this message finds you well. I came across your profile and was impressed by your experience and expertise. I am reaching out to explore potential opportunities for the position of {role} within {country}.

I believe your skills and background align well with current needs, and I would love to discuss how we might collaborate or connect.

Looking forward to hearing from you.

Best regards,
[Your Name]"""
        },
        {
            "subject": "Potential Collaboration Regarding {role} Role in {country}",
            "body": """Hello,

My name is [Your Name], and I am interested in connecting regarding possible roles related to {role} in {country}. Your professional background caught my attention, and I would appreciate the chance to discuss any available opportunities or mutual interests.

Please let me know if you are open for a brief conversation.

Warm regards,
[Your Name]"""
        },
        {
            "subject": "Opportunity Discussion for {role} in {country}",
            "body": """Dear [Recipient’s Name],

I hope this email reaches you well. I am currently seeking to connect with professionals experienced in the field of {role} within {country}. Your profile stood out as a strong fit, and I am eager to explore how we might engage professionally.

If convenient, I would be grateful for a moment of your time to discuss potential collaborations.

Thank you for your consideration.

Sincerely,
[Your Name]"""
        },
        {
            "subject": "Networking and {role} Opportunities in {country}",
            "body": """Hi there,

I hope you are doing well. I am reaching out to professionals like yourself to discuss prospects related to {role} in {country}. Your accomplishments and expertise greatly impressed me, and I believe there might be valuable synergies between us.

I look forward to the possibility of connecting.

Best regards,
[Your Name]"""
        }
    ]
    return {"templates": templates}

@app.post("/api/send_email_with_attachment_oauth")
async def send_email_with_attachment_oauth(
    emails: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    sender_email: str = Form(...),
    gmail_token: str = Form(...),
    attachment: Optional[UploadFile] = File(None),
):
    email_list = [e.strip() for e in emails.split(",") if e.strip()]
    sent = 0
    failed = 0

    # Store sender_email in MongoDB
    try:
        await email_collection.insert_one({"sender_email": sender_email})
    except Exception as e:
        print(f"Error saving sender_email to DB: {str(e)}")

    attachment_content = None
    attachment_filename = None
    if attachment:
        attachment_content = await attachment.read()
        attachment_filename = attachment.filename

    for recipient in email_list:
        try:
            # Build email
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            if attachment and attachment_content:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment_content)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{attachment_filename}"')
                msg.attach(part)

            # Encode message properly
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

            # Gmail API credentials
            creds = Credentials(token=gmail_token)
            service = build("gmail", "v1", credentials=creds)

            message = service.users().messages().send(
                userId="me",
                body={"raw": raw_message}
            ).execute()

            print(f"✅ Email sent to {recipient}, message ID: {message['id']}")
            sent += 1

        except HttpError as error:
            print(f"❌ Gmail API error sending to {recipient}: {error}")
            failed += 1
        except Exception as e:
            print(f"❌ Unexpected error with {recipient}: {str(e)}")
            failed += 1

    return {"message": f"Emails sent: {sent}, failed: {failed}", "sent": sent, "failed": failed}

if __name__ == "__main__":
    import uvicorn, os
    port = int(os.environ.get("PORT", 8000))  # Render gives PORT, fallback to 8000 locally
    uvicorn.run("main:app", host="0.0.0.0", port=port)