import os
import json
import sqlite3
import pandas as pd
import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from email.header import decode_header
from google import genai

# 0. Load Config
CONFIG_PATH = "key.json"


with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

EMAIL_USER = config["gmail_assistant"]
EMAIL_PASS = config["app_pass"]
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
DB_PATH = "data/mini_datalake.db"
MODEL_NAME = config.get("model", "gemini-2.5-flash")

client = genai.Client(api_key=config["GEMINI_API_KEY"])

#1 Create Mini Datalake

def load_to_datalake(csv_path, table_name="sales_data"):
    os.makedirs("data", exist_ok=True)
    df = pd.read_csv(csv_path)
    conn = sqlite3.connect(DB_PATH)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    print(f"✅ Loaded {len(df)} rows into mini datalake ({table_name})")

#2. Schema reader
def get_db_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    schema_info = []
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for (t,) in tables:
        schema_info.append(f"Table: {t}")
        cols = cursor.execute(f"PRAGMA table_info({t});").fetchall()
        for c in cols:
            schema_info.append(f" - {c[1]} ({c[2]})")
    conn.close()
    return "\n".join(schema_info)

def ai_data_assistant(user_prompt):
    schema_text = get_db_schema(DB_PATH)

    # Generate SQL query
    sql_prompt = f"""
You are an expert SQL data analyst.
Use this SQLite schema to write a valid SQL query that answers the user's request.


### EXAMPLES
    User: Show total GMV by region last week
    SQL:
    SELECT region, SUM(GMV) AS total_gmv
    FROM sales_data
    WHERE date >= DATE('now', '-7 day')
    GROUP BY region
    ORDER BY total_gmv DESC;

    User: Get total quantity sold for each product this month
    SQL:
    SELECT product, SUM(quantity) AS total_qty
    FROM sales_data
    WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
    GROUP BY product
    ORDER BY total_qty DESC;

    User: List top 5 retailers by GMV in September
    SQL:
    SELECT retailer, SUM(GMV) AS total_gmv
    FROM sales_data
    WHERE strftime('%Y-%m', date) = '2024-09'
    GROUP BY retailer
    ORDER BY total_gmv DESC
    LIMIT 5;

Schema:
{schema_text}

User request: "{user_prompt}"

Rules:
- Output only the SQL code (no explanation)
- Use valid SQLite syntax
- Use correct column and table names
"""
    sql_response = client.models.generate_content(
        model=MODEL_NAME,
        contents=sql_prompt
    )

    sql_query = sql_response.text.strip().strip("```sql").strip("```").strip()
    print("🪄 Generated SQL:\n", sql_query)

    # Execute query
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql(sql_query, conn)
        print(f"📊 Query returned {len(df)} rows")
    except Exception as e:
        conn.close()
        return f"SQL Error: {e}"
    conn.close()

    # Summarize insight
    insight_prompt = f"""
You are a business data analyst.
Given this SQL query and its result, summarize the main insight clearly and concisely.

User question: "{user_prompt}"
SQL query: {sql_query}
SQL output sample:
{df.head(10).to_markdown()}
"""
    insight_response = client.models.generate_content(
        model=MODEL_NAME,
        contents=insight_prompt
    )

    return sql_response, df, insight_response

# 3. Read Email
def fetch_latest_insight_request():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    status, messages = mail.search(None, '(SUBJECT "Insight Request")')
    if status != "OK" or not messages[0]:
        print("No matching emails found.")
        return None, None, None

    email_ids = messages[0].split()
    latest_email_id = email_ids[-1]
    status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding if encoding else "utf-8")

    from_email = email.utils.parseaddr(msg["From"])[1]
    print(f"New email from: {from_email} | Subject: {subject}")

    # Get plain text body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode()
                break
    else:
        body = msg.get_payload(decode=True).decode()

    mail.logout()
    return from_email, subject.strip(), body.strip()

# 4. Send email
def send_email_reply(to_address, subject, body):
    msg = MIMEText(body, "plain")
    msg["Subject"] = f"Re: {subject}"
    msg["From"] = EMAIL_USER
    msg["To"] = to_address

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"✅ Sent reply to {to_address}")
    except Exception as e:
        print("❌ Email sending error:", e)


#5 main
def main():
    print("🚀 AI Insight Assistant started...")
    sender, subject, body = fetch_latest_insight_request()
    if not body:
        print("No new requests.")
        return

    insight = ai_data_assistant(body)
    send_email_reply(sender, subject, insight)


if __name__ == "__main__":
    # Optional: load your CSV on first run
    # load_to_datalake("data/sales_data.csv")
    main()

