import re

def extract_contacts(text, contact_type):
    if contact_type.lower() == "gmail":
        return re.findall(r"[a-zA-Z0-9._%+-]+@gmail\.com", text)
    if contact_type.lower() == "mobile":
        return re.findall(r"\b\d{10}\b", text)
    return []
