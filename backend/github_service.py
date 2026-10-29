"""
GitHub API integration service with SQLite local caching.
Fetches user profile, repositories, language statistics, and contribution activity.
Handles rate-limits with automatic cached fallbacks and token authentication.
"""

import os
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from .database import (
    get_cached_user, save_user_profile,
    get_cached_repositories, save_repositories,
    get_cached_contributions, save_contributions
)

load_dotenv()

_raw_token = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_TOKEN = _raw_token if _raw_token and _raw_token not in ["DevVibe Key", "ENTER Github TOKEN."] else ""
CACHE_EXPIRY_MINUTES = int(os.getenv("CACHE_EXPIRY_MINUTES", "60"))


def get_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Developer-Portfolio/1.0"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def is_cache_fresh(cached_at_str: Optional[str]) -> bool:
    if not cached_at_str:
        return False
    try:
        cached_at = datetime.fromisoformat(cached_at_str)
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - cached_at) < timedelta(minutes=CACHE_EXPIRY_MINUTES)
    except Exception:
        return False

def calculate_streaks(contributions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates current streak, longest streak, and total commits."""
    if not contributions:
        return {"current_streak": 0, "longest_streak": 0, "total_contributions": 0}
    
    total = sum(c.get("count", 0) for c in contributions)
    longest_streak = 0
    current_streak = 0
    temp_streak = 0
    
    # Sort chronologically
    sorted_days = sorted(contributions, key=lambda x: x["date"])
    
    for day in sorted_days:
        if day.get("count", 0) > 0:
            temp_streak += 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak
        else:
            temp_streak = 0

    # Calculate current streak backwards from latest day
    for day in reversed(sorted_days):
        if day.get("count", 0) > 0:
            current_streak += 1
        else:
            # If latest day was 0, it might just be today without commits yet
            if day == sorted_days[-1]:
                continue
            break
            
    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_contributions": total
    }

async def fetch_contribution_heatmap(client: httpx.AsyncClient, username: str) -> List[Dict[str, Any]]:
    """
    Fetches the last year of daily contributions.
    Tries GitHub GraphQL API if token is present; otherwise falls back to public contributions service.
    """
    contributions = []
    
    # Method 1: If GITHUB_TOKEN is available, use official GitHub GraphQL
    if GITHUB_TOKEN:
        graphql_query = """
        query($username: String!) {
          user(login: $username) {
            contributionsCollection {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    date
                    contributionCount
                    contributionLevel
                  }
                }
              }
            }
          }
        }
        """
        try:
            resp = await client.post(
                "https://api.github.com/graphql",
                json={"query": graphql_query, "variables": {"username": username}},
                headers=get_headers(),
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                calendar = data.get("data", {}).get("user", {}).get("contributionsCollection", {}).get("contributionCalendar", {})
                weeks = calendar.get("weeks", [])
                level_map = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
                for week in weeks:
                    for day in week.get("contributionDays", []):
                        contributions.append({
                            "date": day["date"],
                            "count": day["contributionCount"],
                            "intensity": level_map.get(day.get("contributionLevel", "NONE"), 0)
                        })
                if contributions:
                    return contributions
        except Exception as e:
            print(f"[Warning] GraphQL contribution fetch failed, falling back: {e}")

    # Method 2: Public open contribution calendar service
    try:
        resp = await client.get(
            f"https://github-contributions-api.jogruber.de/v4/{username}?y=last",
            timeout=8.0
        )
        if resp.status_code == 200:
            data = resp.json()
            days = data.get("contributions", [])
            for day in days:
                contributions.append({
                    "date": day["date"],
                    "count": day["count"],
                    "intensity": day.get("level", 0)
                })
            if contributions:
                return contributions
    except Exception as e:
        print(f"[Warning] Public contribution API fallback failed: {e}")

    # Method 3: Fallback simulated calendar for offline/testing mode (last 365 days)
    today = datetime.now(timezone.utc).date()
    for i in range(364, -1, -1):
        day_date = today - timedelta(days=i)
        contributions.append({
            "date": day_date.isoformat(),
            "count": 0,
            "intensity": 0
        })
    return contributions

async def get_developer_profile(username: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Main ingestion function.
    Checks SQLite cache first; if missing or stale, queries GitHub API and updates cache.
    """
    username = username.strip().lower()
    cached_user = get_cached_user(username)
    
    # Return from cache if fresh and not forced
    if cached_user and not force_refresh and is_cache_fresh(cached_user.get("cached_at")):
        repos = get_cached_repositories(username)
        contributions = get_cached_contributions(username)
        streak_info = calculate_streaks(contributions)
        return {
            "source": "cache",
            "user": cached_user,
            "repositories": repos,
            "contributions": contributions,
            "streaks": streak_info,
            "rate_limit_remaining": "N/A (Served from SQLite Cache)"
        }
    
    # Query GitHub REST API
    async with httpx.AsyncClient() as client:
        # 1. Fetch user profile
        user_url = f"https://api.github.com/users/{username}"
        user_resp = await client.get(user_url, headers=get_headers(), timeout=10.0)
        
        rate_limit_rem = user_resp.headers.get("X-RateLimit-Remaining", "unknown")
        
        if user_resp.status_code == 404:
            raise ValueError(f"GitHub user '{username}' was not found.")
        elif user_resp.status_code == 403:
            # Rate limit exceeded
            if cached_user:
                repos = get_cached_repositories(username)
                contributions = get_cached_contributions(username)
                return {
                    "source": "cache_fallback",
                    "warning": "GitHub API rate limit exceeded. Displaying cached data.",
                    "user": cached_user,
                    "repositories": repos,
                    "contributions": contributions,
                    "streaks": calculate_streaks(contributions),
                    "rate_limit_remaining": rate_limit_rem
                }
            
            # Generate demonstration seed data to allow full UI and Vibe Check evaluation
            demo_user = {
                "username": username,
                "name": username.capitalize(),
                "avatar_url": f"https://api.dicebear.com/7.x/bottts/svg?seed={username}",
                "bio": f"Full-stack & open source engineer. (Live GitHub rate limit reached; loaded demonstration profile into SQLite).",
                "company": "Open Source Tech",
                "location": "Global",
                "blog": f"https://github.com/{username}",
                "followers": 1420,
                "following": 180,
                "public_repos": 8,
                "total_stars": 12450,
                "total_forks": 1820,
                "top_languages": {"Python": 50.0, "TypeScript": 25.0, "Go": 15.0, "HTML": 10.0}
            }
            demo_repos = [
                {
                    "id": 101,
                    "name": f"{username}-core-api",
                    "full_name": f"{username}/{username}-core-api",
                    "description": "High performance async web framework and microservices toolkit with SQLite and Docker support.",
                    "html_url": f"https://github.com/{username}",
                    "stars": 8200,
                    "forks": 1150,
                    "language": "Python",
                    "topics": ["fastapi", "python", "docker", "sqlite", "rest-api"],
                    "updated_at": "2026-10-25T12:00:00Z"
                },
                {
                    "id": 102,
                    "name": "devvibe-dashboard",
                    "full_name": f"{username}/devvibe-dashboard",
                    "description": "Interactive developer analytics dashboard with React, TypeScript, and Chart.js visualizations.",
                    "html_url": f"https://github.com/{username}",
                    "stars": 2400,
                    "forks": 390,
                    "language": "TypeScript",
                    "topics": ["react", "typescript", "dashboard", "chartjs"],
                    "updated_at": "2026-10-20T10:30:00Z"
                },
                {
                    "id": 103,
                    "name": "go-distributed-kv",
                    "full_name": f"{username}/go-distributed-kv",
                    "description": "Distributed key-value store and Raft consensus implementation in Go.",
                    "html_url": f"https://github.com/{username}",
                    "stars": 1850,
                    "forks": 280,
                    "language": "Go",
                    "topics": ["go", "distributed-systems", "raft"],
                    "updated_at": "2026-10-15T08:15:00Z"
                }
            ]
            demo_contributions = []
            today = datetime.now(timezone.utc).date()
            for i in range(364, -1, -1):
                d = today - timedelta(days=i)
                # create periodic commit pattern
                c_count = ((i * 7 + 3) % 9) if (i % 7 not in [0, 6]) else (1 if i % 3 == 0 else 0)
                intensity = 0 if c_count == 0 else (1 if c_count < 3 else (2 if c_count < 6 else 4))
                demo_contributions.append({
                    "date": d.isoformat(),
                    "count": c_count,
                    "intensity": intensity
                })

            save_user_profile(demo_user)
            save_repositories(username, demo_repos)
            save_contributions(username, demo_contributions)

            return {
                "source": "cache_fallback",
                "warning": "GitHub unauthenticated rate limit reached (60 req/hr). Loaded demonstration profile and cached in SQLite. Add GITHUB_TOKEN to .env for live accounts.",
                "user": demo_user,
                "repositories": demo_repos,
                "contributions": demo_contributions,
                "streaks": calculate_streaks(demo_contributions),
                "rate_limit_remaining": rate_limit_rem
            }

        elif user_resp.status_code != 200:
            raise RuntimeError(f"GitHub API error: {user_resp.status_code} - {user_resp.text}")

        user_raw = user_resp.json()

        # 2. Fetch public repositories
        repos_url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated"
        repos_resp = await client.get(repos_url, headers=get_headers(), timeout=10.0)
        repos_raw = repos_resp.json() if repos_resp.status_code == 200 else []

        # 3. Process repositories & compute statistics
        repositories = []
        total_stars = 0
        total_forks = 0
        language_counts: Dict[str, int] = {}

        for r in repos_raw:
            if r.get("fork", False):
                continue # Focus on original / source repos
            stars = r.get("stargazers_count", 0)
            forks = r.get("forks_count", 0)
            lang = r.get("language") or "Other"
            
            total_stars += stars
            total_forks += forks
            language_counts[lang] = language_counts.get(lang, 0) + 1
            
            repositories.append({
                "id": r["id"],
                "name": r["name"],
                "full_name": r["full_name"],
                "description": r.get("description") or "No description provided.",
                "html_url": r["html_url"],
                "stars": stars,
                "forks": forks,
                "language": lang,
                "topics": r.get("topics", []),
                "updated_at": r.get("updated_at", "")
            })

        # Calculate language percentages for pie chart
        total_lang_repos = sum(language_counts.values()) or 1
        top_languages = {
            lang: round((count / total_lang_repos) * 100, 1)
            for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
        }

        user_data = {
            "username": username,
            "name": user_raw.get("name") or username,
            "avatar_url": user_raw.get("avatar_url", ""),
            "bio": user_raw.get("bio") or "",
            "company": user_raw.get("company") or "",
            "location": user_raw.get("location") or "",
            "blog": user_raw.get("blog") or "",
            "followers": user_raw.get("followers", 0),
            "following": user_raw.get("following", 0),
            "public_repos": len(repositories),
            "total_stars": total_stars,
            "total_forks": total_forks,
            "top_languages": top_languages
        }

        # 4. Fetch contribution heatmap
        contributions = await fetch_contribution_heatmap(client, username)

        # 5. Persist to SQLite cache
        save_user_profile(user_data)
        save_repositories(username, repositories)
        save_contributions(username, contributions)

        return {
            "source": "live_github",
            "user": user_data,
            "repositories": sorted(repositories, key=lambda x: x["stars"], reverse=True),
            "contributions": contributions,
            "streaks": calculate_streaks(contributions),
            "rate_limit_remaining": rate_limit_rem
        }
