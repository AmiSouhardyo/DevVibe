"""
The Vibe Check - Tech Stack Compatibility Engine.
Performs server-side keyword extraction and matching between a provided Job Description (JD)
and the developer's cached GitHub repositories, languages, and topics.
"""

import re
from typing import Dict, Any, List, Set
from .database import get_cached_user, get_cached_repositories

# Standard tech catalog for normalization and extraction
TECH_KEYWORDS = {
    # Programming Languages
    "python": ["python", "py"],
    "javascript": ["javascript", "js", "ecmascript"],
    "typescript": ["typescript", "ts"],
    "java": ["java"],
    "c++": ["c++", "cpp"],
    "c#": ["c#", "csharp", ".net"],
    "c": ["\\bc\\b"],
    "go": ["\\bgo\\b", "golang"],
    "rust": ["rust"],
    "php": ["php"],
    "ruby": ["ruby", "rails"],
    "kotlin": ["kotlin"],
    "swift": ["swift"],
    "scala": ["scala"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "sql": ["sql"],
    
    # Frontend Frameworks & Libraries
    "react": ["react", "reactjs", "react.js"],
    "vue": ["vue", "vuejs", "vue.js"],
    "angular": ["angular"],
    "svelte": ["svelte"],
    "next.js": ["next.js", "nextjs"],
    "tailwind": ["tailwind", "tailwindcss"],
    "bootstrap": ["bootstrap"],
    "redux": ["redux"],
    
    # Backend & API Frameworks
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "django": ["django"],
    "express": ["express", "expressjs"],
    "node.js": ["node.js", "nodejs", "node"],
    "spring": ["spring", "spring boot"],
    "graphql": ["graphql"],
    "rest": ["rest", "restful", "rest api"],
    
    # Databases & Caching
    "postgresql": ["postgres", "postgresql"],
    "mysql": ["mysql"],
    "sqlite": ["sqlite", "sqlite3"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    
    # Cloud, DevOps & Tools
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure"],
    "gcp": ["gcp", "google cloud"],
    "git": ["git", "github", "gitlab"],
    "ci/cd": ["ci/cd", "github actions", "jenkins"],
    "linux": ["linux", "bash", "shell"],
    
    # AI & Data Science
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning"],
    "pytorch": ["pytorch"],
    "tensorflow": ["tensorflow"],
    "pandas": ["pandas"],
    "numpy": ["numpy"]
}

def extract_tech_keywords(text: str) -> Set[str]:
    """Extracts standardized tech skills present in text."""
    found_skills = set()
    text_lower = text.lower()
    
    for tech_name, patterns in TECH_KEYWORDS.items():
        for pat in patterns:
            # Check for word boundary matches
            if pat.startswith("\\b"):
                if re.search(pat, text_lower):
                    found_skills.add(tech_name)
                    break
            else:
                escaped_pat = re.escape(pat)
                if re.search(rf"\b{escaped_pat}\b", text_lower):
                    found_skills.add(tech_name)
                    break
    return found_skills

def extract_developer_skills(username: str) -> Set[str]:
    """Inspects cached user repos, languages, descriptions, and topics."""
    dev_skills = set()
    user = get_cached_user(username)
    repos = get_cached_repositories(username)
    
    # 1. From user top_languages
    if user and user.get("top_languages"):
        for lang in user["top_languages"].keys():
            normalized = lang.lower()
            if normalized in TECH_KEYWORDS:
                dev_skills.add(normalized)
            else:
                # Search partial
                dev_skills.update(extract_tech_keywords(lang))

    # 2. From repositories (languages, topics, names, and descriptions)
    for repo in repos:
        if repo.get("language"):
            lang = repo["language"].lower()
            if lang in TECH_KEYWORDS:
                dev_skills.add(lang)
            else:
                dev_skills.update(extract_tech_keywords(lang))
                
        # Topics
        for topic in repo.get("topics", []):
            dev_skills.update(extract_tech_keywords(topic))
            
        # Description and Repo Name
        desc = f"{repo.get('name', '')} {repo.get('description', '')}"
        dev_skills.update(extract_tech_keywords(desc))
        
    return dev_skills

def calculate_compatibility(username: str, job_description: str) -> Dict[str, Any]:
    """
    Computes tech stack match percentage and categorization.
    Implemented server-side as required.
    """
    if not job_description or not job_description.strip():
        return {
            "match_percentage": 0,
            "badge_level": "No Input",
            "matched_skills": [],
            "missing_skills": [],
            "total_jd_skills": 0,
            "recommendation": "Paste a job description to calculate compatibility."
        }
        
    jd_skills = extract_tech_keywords(job_description)
    if not jd_skills:
        return {
            "match_percentage": 50,
            "badge_level": "General Match",
            "matched_skills": [],
            "missing_skills": [],
            "total_jd_skills": 0,
            "recommendation": "No specific technical keywords detected in the job description."
        }
        
    dev_skills = extract_developer_skills(username)
    matched = sorted(list(jd_skills.intersection(dev_skills)))
    missing = sorted(list(jd_skills.difference(dev_skills)))
    
    match_percentage = round((len(matched) / len(jd_skills)) * 100)
    
    if match_percentage >= 75:
        badge_level = "High Match 🔥"
        badge_color = "#10b981" # Green
        recommendation = "Strong technical synergy! The candidate's public projects demonstrate most required technologies."
    elif match_percentage >= 45:
        badge_level = "Moderate Match ⚡"
        badge_color = "#f59e0b" # Amber
        recommendation = "Promising fit. Candidate covers core areas but could expand on secondary requirements."
    else:
        badge_level = "Growth Opportunity 🌱"
        badge_color = "#ef4444" # Red
        recommendation = "Significant skill delta between this role and public repository projects."

    return {
        "match_percentage": match_percentage,
        "badge_level": badge_level,
        "badge_color": badge_color,
        "matched_skills": matched,
        "missing_skills": missing,
        "developer_skills": sorted(list(dev_skills)),
        "total_jd_skills": len(jd_skills),
        "recommendation": recommendation
    }
