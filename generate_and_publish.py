import importlib.util
import json
import os
from urllib import error, request

HAS_PYPDF2 = importlib.util.find_spec("PyPDF2") is not None

if HAS_PYPDF2:
    from PyPDF2 import PdfReader

# -----------------------
# GPT system prompt
# -----------------------

SYSTEM_PROMPT = """
You are a senior legal blog writer producing authoritative, legally accurate blog posts for Richmond Chambers Immigration Barristers, an immigration law firm specialising exclusively in UK immigration law and UK immigration routes.

Your role is to write in-depth, analytical blog posts aimed at educated, time-poor professionals seeking clear, reliable guidance on UK immigration options. Readers may be based in the UK or overseas and are looking for practical understanding grounded in law and regulatory practice, not marketing content.

You must demonstrate strong subject-matter expertise in UK immigration law, including UK Partner & Family visas, EU Settlement Scheme, UK Standard Visitor Visa, UK Short-term Work Visas, UK Long-term work visas, UK Business visas, UK Global Business Mobility Visas, UK Global Talent visas, Settlement / Indefinite Leave to remain in the UK, British citizenship, UK Sponsor licensing, UK Sponsor compliance, UK Sponsor management, UK Civil Penalties, Human Rights, UK Student Visas, UK BNO Visas and related regulatory frameworks. All content must be legally accurate. You must not speculate, invent rules, or hallucinate legal positions. Where necessary, you may supplement your knowledge with careful web research to ensure accuracy and currency.

Writing style and tone:

UK English

Authoritative, analytical, and calm

Professional and non-promotional

Clear, precise prose written in full paragraphs

Discursive and explanatory rather than schematic

No clichés

No emojis

No sales language

No references to yourself as an AI

Content requirements:

Length: typically 1,000–1,500 words per post (around 1,500 words unless the topic clearly requires less)

The blog post must be written predominantly in continuous prose

Lists (including bullet points, numbered lists, or hyphenated lists) should be used sparingly and only where they genuinely improve clarity

Maximum of two lists in total across the entire article

Lists must never be used as a substitute for legal analysis, reasoning, or explanation

The default mode of explanation should always be structured paragraphs, not itemised points

Concrete legal claims rather than vague generalities

Clear explanations of legal reasoning, statutory or regulatory context, and practical consequences

Examples may be included where they genuinely aid understanding, but should be embedded in prose rather than presented as lists

Avoid generic summaries, filler content, or checklist-style drafting

Search optimisation:

Optimise content for search engines using relevant keywords and keyword variations related to UK immigration law and UK immigration routes

Keywords must be integrated naturally into prose, without keyword stuffing or forced repetition

Structure:

A compelling, specific and concise title that clearly reflects the legal subject matter

A concise introduction that frames the legal or practical problem being addressed, without fluff

At least five substantive sections, each developed through paragraphs of analysis rather than lists

Section headings must be descriptive and signal the legal or practical issue being discussed, not merely label a list

A practical conclusion that distils key legal takeaways and implications for readers, written in prose

Mandatory final section:

A final section with the exact sub-heading:
Contact Our Immigration Barristers

Call to action requirement:

Under the sub-heading “Contact Our Immigration Barristers”, include a short, measured call to action written in restrained, professional prose.

The call to action must:

Be relevant to the subject matter of the blog post

Be framed as an invitation to obtain tailored legal advice

Invite readers to contact Richmond Chambers Immigration Barristers by telephone on +44 (0)203 617 9173 or by completing an enquiry form to arrange an initial consultation meeting

Remain factual, neutral, and non-promotional

Output format:

Plain text only

Headings clearly marked

No markdown

No citations or footnotes unless explicitly requested

No meta-commentary about the writing process

SEO requirements:

Generate an SEO meta title (maximum 60 characters)

Generate an SEO meta description (maximum 155 characters)

Meta text must be natural, accurate, and non-promotional

Your objective is to produce content that reads as a serious piece of legal analysis written for professionals, where clarity is achieved through careful prose and reasoning rather than through extensive use of lists.

SEO requirements:
- Generate an SEO meta title (max 60 characters)
- Generate an SEO meta description (max 155 characters)
- Meta text must be natural, accurate, and non-promotional

Output format EXACTLY as follows:

BLOG TITLE:
<text>

SEO META TITLE:
<text>

SEO META DESCRIPTION:
<text>

BLOG CONTENT:
<full article>
"""

def post_json(url, payload, headers):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")

    try:
        with request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Network error calling {url}: {exc.reason}") from exc

# -----------------------
# Load authoritative PDF knowledge
# -----------------------

def load_pdf_knowledge(folder="knowledge", max_chars=12000):
    texts = []

    if not HAS_PYPDF2:
        print("Warning: PyPDF2 is not installed; continuing without PDF knowledge.")
        return ""

    if not os.path.isdir(folder):
        return ""

    for filename in sorted(os.listdir(folder)):
        if not filename.lower().endswith(".pdf"):
            continue

        path = os.path.join(folder, filename)
        reader = PdfReader(path)

        pdf_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pdf_text.append(text)

        combined = "\n".join(pdf_text)
        combined = " ".join(combined.split())

        if combined:
            texts.append(f"[SOURCE: {filename}]\n{combined}")

    full_text = "\n\n".join(texts)

    return full_text[:max_chars]

PDF_KNOWLEDGE = load_pdf_knowledge()

# -----------------------
# Load topics.json
# -----------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOPICS_PATH = os.path.join(SCRIPT_DIR, "topics.json")

with open(TOPICS_PATH, "r", encoding="utf-8") as f:
    topics = json.load(f)

unused_topics = [t for t in topics if t.get("status") == "unused"]
remaining_count = len(unused_topics)

# -----------------------
# Topics exhausted handling
# -----------------------

if remaining_count == 0:
    SENDGRID_API_KEY = os.environ["SENDGRID_API_KEY"]
    EMAIL_FROM = os.environ["paul.richmond@richmondchambers.com"]
    EMAIL_TO = os.environ["paul.richmond@richmondchambers.com"]

    notification_payload = {
        "personalizations": [
            {
                "to": [{"email": EMAIL_TO}],
                "subject": "Blog automation: topics exhausted",
            }
        ],
        "from": {"email": EMAIL_FROM},
        "content": [
            {
                "type": "text/plain",
                "value": (
                    "All blog topics in topics.json have been used.\n\n"
                    "No draft was generated on this run.\n\n"
                    "Please add new topics with status \"unused\" "
                    "and the automation will resume automatically."
                ),
            }
        ],
    }

    post_json(
        "https://api.sendgrid.com/v3/mail/send",
        payload=notification_payload,
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    print("Topics exhausted notification sent.")
    exit(0)

# -----------------------
# Select next unused topic
# -----------------------

for index, topic in enumerate(topics):
    if topic.get("status") == "unused":
        topic_index = index
        topic_entry = topic
        break

# -----------------------
# Generate blog post
# -----------------------

chat_payload = {
    "model": "gpt-5.2",
    "messages": [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "system",
            "content": f"""
The following documents are authoritative reference material produced or endorsed by the organisation.
Use them as your primary source of truth.

If there is any tension between general knowledge and these documents:
- Prefer these documents
- Be conservative
- Do not speculate beyond them

If the documents are silent on a point, you may rely on general knowledge but should qualify uncertainty.

AUTHORITATIVE MATERIAL:
{PDF_KNOWLEDGE}
"""
        },
        {
            "role": "user",
            "content": f"Topic: {topic_entry['topic']}\nAngle: {topic_entry['angle']}",
        },
    ],
}

_, chat_response = post_json(
    "https://api.openai.com/v1/chat/completions",
    payload=chat_payload,
    headers={
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json",
    },
)

content = chat_response["choices"][0]["message"]["content"].strip()

# -----------------------
# Robust section extractor
# -----------------------

def extract(section, until_next=True):
    start = content.find(section)
    if start == -1:
        return ""
    start += len(section)

    if until_next:
        end = content.find("\n\n", start)
        return content[start:end].strip() if end != -1 else content[start:].strip()
    else:
        return content[start:].strip()

title = extract("BLOG TITLE:")
meta_title = extract("SEO META TITLE:")[:60]
meta_description = extract("SEO META DESCRIPTION:")[:155]
body = extract("BLOG CONTENT:", until_next=False)

print("TITLE:", title)
print("SEO META TITLE:", meta_title)
print("SEO META DESCRIPTION:", meta_description)

# -----------------------
# Mark topic as used
# -----------------------

topics[topic_index]["status"] = "used"
topics[topic_index]["used_title"] = title

with open(TOPICS_PATH, "w", encoding="utf-8") as f:
    json.dump(topics, f, indent=2, ensure_ascii=False)

# -----------------------
# Send draft email via SendGrid
# -----------------------

SENDGRID_API_KEY = os.environ["SENDGRID_API_KEY"]
EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]

email_payload = {
    "personalizations": [
        {
            "to": [{"email": EMAIL_TO}],
            "subject": f"Blog draft: {title}",
        }
    ],
    "from": {"email": EMAIL_FROM},
    "content": [
        {
            "type": "text/plain",
            "value": f"""TOPIC BACKLOG:
{remaining_count - 1} topics remaining

BLOG TITLE:
{title}

SEO META TITLE:
{meta_title}

SEO META DESCRIPTION:
{meta_description}

---------------------------------

BLOG CONTENT:

{body}
""",
        }
    ],
}

post_json(
    "https://api.sendgrid.com/v3/mail/send",
    payload=email_payload,
    headers={
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    },
)

print("Draft email sent successfully via SendGrid.")
