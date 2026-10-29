"""
Chatbot service implementing the two extra required features:
1. 'Ask My Codebase' Recruiter Assistant (natural language Q&A on developer repositories)
2. 'AI Skill Gap & Mock Technical Interviewer' (tailored technical interview simulations)
"""

import os
from typing import Dict, Any, List
from .database import get_cached_user, get_cached_repositories
from .vibe_check import calculate_compatibility

def generate_codebase_response(username: str, question: str) -> Dict[str, Any]:
    """Feature 1: Recruiter Q&A based on cached repository knowledge."""
    q_lower = question.lower()
    user = get_cached_user(username)
    repos = get_cached_repositories(username)
    
    if not user:
        return {
            "reply": f"No data found for @{username}. Please fetch their profile first.",
            "mode": "error"
        }
    
    top_repos = sorted(repos, key=lambda x: x["stars"], reverse=True)[:3]
    top_langs = list(user.get("top_languages", {}).keys())
    
    # 1. Questions about top projects / best work
    if any(k in q_lower for k in ["top project", "best project", "starred", "popular", "highlight", "showcase"]):
        if not top_repos:
            return {"reply": f"@{username} doesn't have any public repositories listed yet."}
        repo_summaries = []
        for r in top_repos:
            repo_summaries.append(f"⭐ **{r['name']}** ({r['stars']} stars, {r['language']}): {r['description']}")
        return {
            "reply": f"Here are the top highlighted repositories for **@{username}**:\n\n" + "\n\n".join(repo_summaries),
            "sources": [r["name"] for r in top_repos]
        }
        
    # 2. Questions about languages / tech stack
    elif any(k in q_lower for k in ["tech stack", "languages", "what does", "frameworks", "technologies", "know"]):
        langs_str = ", ".join([f"**{l}** ({pct}%)" for l, pct in list(user.get("top_languages", {}).items())[:5]])
        return {
            "reply": f"Based on cached repository analysis, **@{username}** predominantly works with:\n\n"
                     f"{langs_str}\n\nAcross {len(repos)} repositories, with a total of **{user['total_stars']} stars**.",
            "sources": top_langs
        }
        
    # 3. Specific technology inquiries (e.g., Python, React, Docker)
    matched_repos = []
    for r in repos:
        combined = f"{r['name']} {r['description']} {r['language']} {' '.join(r.get('topics', []))}".lower()
        words = q_lower.replace("?", "").replace("!", "").split()
        for w in words:
            if len(w) > 2 and w in combined and w not in ["the", "and", "have", "you", "does", "any", "project"]:
                matched_repos.append(r)
                break
                
    if matched_repos:
        repo_bullets = "\n".join([f"• [{r['name']}]({r['html_url']}) ({r['language']}) - {r['description']}" for r in matched_repos[:3]])
        return {
            "reply": f"Yes! Here are repositories by **@{username}** relevant to your inquiry:\n\n{repo_bullets}",
            "sources": [r["name"] for r in matched_repos[:3]]
        }

    # 4. General overview fallback
    return {
        "reply": f"**@{username}** is a software developer with **{len(repos)} public repositories** and **{user['total_stars']} stars** on GitHub.\n"
                 f"Their primary languages are {', '.join(top_langs[:3]) or 'varied'}.\n\n"
                 f"Try asking:\n"
                 f"• *'What is their most starred project?'*\n"
                 f"• *'Do they have projects in Python or React?'*\n"
                 f"• *'Summarize their coding background'*",
        "sources": []
    }

def generate_interview_prep(username: str, job_description: str) -> Dict[str, Any]:
    """Feature 2: AI Skill Gap & Mock Technical Interviewer."""
    comp = calculate_compatibility(username, job_description)
    matched = comp["matched_skills"]
    missing = comp["missing_skills"]
    repos = get_cached_repositories(username)
    
    questions = []
    
    # Generate tailored technical questions for matched skills
    for skill in matched[:3]:
        questions.append({
            "skill": skill.capitalize(),
            "type": "Depth & Experience",
            "question": f"In your GitHub projects utilizing {skill.capitalize()}, what architectural trade-offs or scalability challenges did you address?"
        })
        
    # Generate question for missing or gap skills
    for skill in missing[:2]:
        questions.append({
            "skill": skill.capitalize(),
            "type": "Skill Gap / Rapid Onboarding",
            "question": f"This role requires {skill.capitalize()}, which isn't prominent in your public GitHub repos. How would your background allow you to ramp up quickly?"
        })
        
    # Project-specific question
    if repos:
        top_repo = max(repos, key=lambda x: x["stars"])
        questions.append({
            "skill": top_repo["name"],
            "type": "Project Deep Dive",
            "question": f"Walk me through the design choices in your project '{top_repo['name']}'. If you had to rewrite it today, what would you do differently?"
        })

    return {
        "compatibility_summary": f"Compatibility Score: {comp['match_percentage']}% ({comp['badge_level']})",
        "matched_skills": matched,
        "missing_skills": missing,
        "interview_questions": questions,
        "coaching_tip": "Focus on quantitative metrics during your answers (e.g., latency, users, code structure) to substantiate your GitHub work."
    }
