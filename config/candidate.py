"""
candidate.py — Karthik's profile, skills, target roles, and H1B sponsor list.
Merged from: OPT-Job-Scrapper, F1_H1B_Scraper, career-ops.
"""

# ─────────────────────────────────────────────────────────────────
# CANDIDATE PROFILE
# ─────────────────────────────────────────────────────────────────

CANDIDATE_NAME = "Karthik"
CANDIDATE_FULL_NAME = "Karthik Kumar Reddy Kota"
CANDIDATE_EMAIL = "kotakarthik.ai@gmail.com"
CANDIDATE_LOCATION = "Dallas, TX"
CANDIDATE_VISA = "OPT → H1B"
CANDIDATE_SALARY_RANGE = "$140k–$200k"

RESUME_TEXT = """
KARTHIK KOTA | AI Engineer | Machine Learning | GenAI & LLM Applications
Allen, TX | +1 (469) 396-2619 | kotakarthik.ai@gmail.com | LinkedIn | Portfolio | Kaggle

SUMMARY
AI Engineer with 3+ years building production-grade ML models, RAG architectures, and LLM-powered
apps across financial services, healthcare, and enterprise. Delivered $1.2M+ annual savings,
40% latency reduction, 91% accuracy at scale. Expert in NLP, Computer Vision, MLOps, and GCP Vertex AI.

SKILLS
Languages: Python, SQL, Java, C++, JavaScript, Bash
AI & LLMs: OpenAI API, RAG, LangChain, NLP, Hugging Face Transformers, LLMs, AWS Bedrock,
           Claude API, NER, Prompt Engineering, Transformer Architecture
ML & DL: TensorFlow, PyTorch, scikit-learn, XGBoost, LightGBM, Keras, CNN, LSTM, SVM,
         Random Forest, SHAP, ARIMA, Prophet, Reinforcement Learning, Feature Engineering
Computer Vision: OpenCV, YOLO, Detectron2, TensorRT, Transfer Learning, Object Detection
MLOps & DevOps: MLflow, Docker, GitHub, FastAPI, REST APIs, FAISS, Pinecone, CI/CD,
                Model Versioning, Distributed Training
Cloud: AWS (EC2, S3, Lambda, SageMaker, Bedrock, IAM, CloudWatch), GCP (Vertex AI, BigQuery), Terraform
Data Engineering: Apache Spark, Spark Streaming, Kafka, NumPy, Pandas, ETL Pipelines, Tableau, Power BI
Databases: PostgreSQL, MySQL, MongoDB, DynamoDB, Cassandra

EXPERIENCE
AI Engineer — Vertraus Inc (Current)
AI Engineer — Mr. Cooper (Feb 2025 – Present) Dallas, TX
  • Deployed LLM-powered mortgage doc intelligence using RAG, LangChain, OpenAI API on AWS SageMaker —
    cut review time 45% across 500K+ annual transactions, saving $800K+.
  • Built real-time XGBoost risk scoring at sub-100ms latency processing 1M+ loan records monthly.
  • Engineered NLP/NER pipelines on loan apps, improving data accuracy 32%.
  • Developed Spark ETL ingesting 200GB+ daily on AWS S3 at 99.9% uptime.
  • Deployed LangChain+FAISS conversational assistants achieving 87% self-resolution.

AI/ML Engineer — Tata Consultancy Services (TCS) (Apr 2021 – Jun 2023) Hyderabad, India
  • Delivered XGBoost credit risk classifier at 91% accuracy on 800K+ records.
  • Built LSTM+TensorFlow fraud detection on Kafka streams processing 50K+ txns/min at 94% precision.
  • Created NLP pipelines for financial report summarization — 35% reduction in analyst effort.
  • Engineered CNN/LSTM models with 95% accuracy; Docker on AWS Lambda/EC2, reducing latency 40%.

PROJECTS
  • Enterprise Financial Fraud Intelligence Platform: RAG+BERT+FAISS+Pinecone, 1M+ daily txns,
    95ms latency, saved $1.2M annually.
  • AI-Powered Enterprise Knowledge Copilot: RAG over 2M+ docs for 5K+ users, sub-150ms latency.
  • IoT Predictive Maintenance & Financial Forecasting: PyTorch+Spark+Kafka on GCP Vertex AI.

EDUCATION
M.S. Computer & Information Science — University of North Texas (May 2025)
B.Tech CS & Engineering (AI) — Vellore Institute of Technology (May 2023)

CERTIFICATIONS
  • AWS Certified Machine Learning – Associate
  • TensorFlow Developer Certificate (Google)
  • Deep Learning Specialization (Coursera – deeplearning.ai)

TARGET ROLES: Senior ML Engineer, AI Engineer, MLOps Engineer, LLM Engineer, GenAI Engineer,
              Applied Scientist, Research Engineer, Data Scientist
"""

# ─────────────────────────────────────────────────────────────────
# TARGET ROLES
# ─────────────────────────────────────────────────────────────────

EXACT_ROLES = [
    "senior ml engineer", "senior machine learning engineer",
    "ai engineer", "ml engineer", "machine learning engineer",
    "mlops engineer", "llm engineer", "genai engineer",
    "generative ai engineer", "applied scientist",
    "research engineer", "nlp engineer",
    "forward deployed engineer", "data scientist",
    "computer vision engineer", "ai/ml engineer",
    "gen ai engineer", "founding ai engineer",
]

KEYWORD_FILTER = [
    "ML Engineer", "Machine Learning", "AI Engineer", "MLOps",
    "LLM", "NLP", "Deep Learning", "Applied Scientist",
    "Research Engineer", "GenAI", "RAG", "Foundation Model",
    "Data Scientist", "Computer Vision", "Generative AI",
    "Large Language", "Transformer", "PyTorch", "TensorFlow",
]

# ─────────────────────────────────────────────────────────────────
# CORE SKILLS (used for keyword pre-filter matching)
# ─────────────────────────────────────────────────────────────────

CORE_SKILLS = {
    "python", "pytorch", "tensorflow", "machine learning", "deep learning",
    "llm", "nlp", "rag", "langchain", "aws", "sagemaker", "bedrock",
    "mlops", "mlflow", "docker", "fastapi", "spark", "kafka",
    "sql", "pandas", "numpy", "scikit-learn", "hugging face",
    "transformers", "faiss", "pinecone", "data science",
    "neural network", "ai", "gen ai", "computer vision", "bert",
    "generative ai", "large language model", "fine-tuning", "lora",
}

# ─────────────────────────────────────────────────────────────────
# EXCLUDE KEYWORDS — Hard filters (never alert)
# ─────────────────────────────────────────────────────────────────

EXCLUDE_KEYWORDS = [
    # Visa disqualifiers
    "no sponsorship", "no visa", "us citizen only", "us citizens only",
    "security clearance", "clearance required", "must be authorized",
    "will not sponsor", "sponsorship not available", "green card only",
    "active clearance", "top secret", "ts/sci", "usc only",
    "citizens or permanent residents", "permanent resident only",
    "not able to sponsor", "cannot sponsor", "unable to sponsor",
    # Seniority
    "staff engineer", "senior staff", "principal engineer",
    "distinguished engineer", "director of engineering",
    "vp of engineering", "engineering manager",
    # Level
    "intern", "internship", "entry level",
    # Contract-only
    "corp to corp", "c2c", "contract only", "1099 only",
]

# ─────────────────────────────────────────────────────────────────
# STAFFING FIRMS TO EXCLUDE
# ─────────────────────────────────────────────────────────────────

STAFFING_FIRMS = {
    "teksystems", "tek systems", "cognizant", "wipro", "hcl",
    "capgemini", "randstad", "manpower", "kelly services",
    "robert half", "adecco", "kforce", "insight global",
    "cybercoders", "modis", "apex systems", "aerotek", "experis",
    "mastech", "synechron", "mphasis", "ltimindtree",
    "tech mahindra", "persistent", "zensar", "hexaware", "coforge",
    "staffing", "corp to corp", "c2c",
}

# ─────────────────────────────────────────────────────────────────
# VERIFIED H1B SPONSORS — merged from all 3 projects + system prompt
# ─────────────────────────────────────────────────────────────────

VERIFIED_H1B_SPONSORS = {
    # FAANG + Mega Tech
    "google", "amazon", "microsoft", "meta", "apple", "netflix", "nvidia",
    "intel", "ibm", "oracle", "salesforce", "adobe", "qualcomm",
    "cisco", "vmware", "linkedin", "uber", "lyft",
    "amd", "broadcom", "applied materials", "micron", "hp", "dell",
    "servicenow", "workday", "splunk", "palo alto networks", "crowdstrike",
    "fortinet", "zscaler", "cloudflare", "fastly",
    # Finance & Fintech
    "jpmorgan", "jp morgan", "goldman sachs", "stripe", "coinbase",
    "robinhood", "plaid", "brex", "ramp", "chime", "sofi",
    "square", "block", "affirm", "klarna", "marqeta", "adyen",
    "visa", "mastercard", "paypal", "american express", "discover",
    "wells fargo", "bank of america", "morgan stanley", "capital one",
    "bloomberg", "two sigma", "citadel", "jane street",
    # AI Companies
    "anthropic", "openai", "cohere", "mistral", "together ai",
    "scale ai", "hugging face", "anyscale", "databricks",
    # Cloud & Data
    "snowflake", "mongodb", "elastic", "confluent", "hashicorp",
    "palantir", "datadog", "dbt labs", "fivetran", "airbyte",
    # Product Startups
    "airbnb", "doordash", "canva", "figma", "notion", "vercel",
    "supabase", "linear", "loom", "retool", "perplexity",
    "twilio", "dropbox", "reddit", "rippling", "gusto",
    "airtable", "webflow", "postman", "grammarly", "deel",
    "remote", "lattice", "amplitude", "segment", "braze",
    "klaviyo", "attentive", "iterable", "sendgrid",
    "flexport", "checkr", "persona", "socure",
    "benchling", "ginkgo", "asana", "monday", "clickup",
    "box", "squarespace", "wix", "intercom", "zendesk",
    "freshworks", "hubspot", "okta", "auth0", "1password",
    "pulumi", "terraform", "ansible",
    # Consumer
    "spotify", "snap", "pinterest", "instacart",
    "tesla", "spacex", "doordash", "walmart", "target",
    "expedia", "booking", "zillow", "redfin",
    "github", "gitlab", "atlassian", "zoom",
    "intuit", "autodesk",
    # Healthcare & Life Sciences
    "johnson & johnson", "pfizer", "merck", "abbvie", "eli lilly",
    "genentech", "roche", "novartis",
    # Defense/Aerospace (with caveats)
    "boeing", "lockheed", "northrop", "general electric",
    # Universities (cap-exempt H1B — no lottery)
    "university", "college", "institute of technology", "polytechnic",
    "carnegie mellon", "mit", "stanford", "harvard", "berkeley",
    "umich", "michigan", "penn state", "purdue", "ut austin", "uiuc",
    "ohio state", "georgia tech", "columbia", "uw madison",
    "caltech", "cornell", "yale", "princeton", "duke", "nyu", "usc",
}

SCORING_RUBRIC = {
    "skills_match":     40,   # how many required skills match
    "seniority_match":  20,   # senior/staff level?
    "domain_match":     20,   # ML/AI/LLM focused?
    "company_quality":  10,   # FAANG/tier-1 startup?
    "visa_friendly":    10,   # remote ok + H1B sponsor history?
}
