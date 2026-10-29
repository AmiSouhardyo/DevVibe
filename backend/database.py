"""
Database module using Python's built-in sqlite3.
Handles SQLite caching for user profiles, repository metadata, language distributions,
contribution heatmaps, and user settings to prevent GitHub API rate-limiting.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dev_portfolio.db")

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite schema for local caching."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            name TEXT,
            avatar_url TEXT,
            bio TEXT,
            company TEXT,
            location TEXT,
            blog TEXT,
            followers INTEGER DEFAULT 0,
            following INTEGER DEFAULT 0,
            public_repos INTEGER DEFAULT 0,
            total_stars INTEGER DEFAULT 0,
            total_forks INTEGER DEFAULT 0,
            top_languages TEXT, -- JSON string
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Repositories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repositories (
            id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            full_name TEXT,
            description TEXT,
            html_url TEXT,
            stars INTEGER DEFAULT 0,
            forks INTEGER DEFAULT 0,
            language TEXT,
            topics TEXT, -- JSON string
            updated_at TEXT,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    """)
    
    # Daily contribution heatmap table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contributions (
            username TEXT,
            date TEXT,
            count INTEGER DEFAULT 0,
            intensity INTEGER DEFAULT 0,
            PRIMARY KEY (username, date),
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    """)

    # User settings / key-value store
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# Helper queries
def save_user_profile(user_data: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (
            username, name, avatar_url, bio, company, location, blog,
            followers, following, public_repos, total_stars, total_forks,
            top_languages, cached_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_data["username"].lower(),
        user_data.get("name") or user_data["username"],
        user_data.get("avatar_url", ""),
        user_data.get("bio", ""),
        user_data.get("company", ""),
        user_data.get("location", ""),
        user_data.get("blog", ""),
        user_data.get("followers", 0),
        user_data.get("following", 0),
        user_data.get("public_repos", 0),
        user_data.get("total_stars", 0),
        user_data.get("total_forks", 0),
        json.dumps(user_data.get("top_languages", {})),
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()

def get_cached_user(username: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username.lower(),))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    data["top_languages"] = json.loads(data["top_languages"]) if data["top_languages"] else {}
    return data

def save_repositories(username: str, repos: List[Dict[str, Any]]):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Delete existing repos for this user to keep fresh list
    cursor.execute("DELETE FROM repositories WHERE username = ?", (username.lower(),))
    now = datetime.now(timezone.utc).isoformat()
    for repo in repos:
        cursor.execute("""
            INSERT OR REPLACE INTO repositories (
                id, username, name, full_name, description, html_url,
                stars, forks, language, topics, updated_at, cached_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            repo["id"],
            username.lower(),
            repo["name"],
            repo.get("full_name", repo["name"]),
            repo.get("description") or "No description provided.",
            repo.get("html_url", ""),
            repo.get("stars", 0),
            repo.get("forks", 0),
            repo.get("language") or "Other",
            json.dumps(repo.get("topics", [])),
            repo.get("updated_at", ""),
            now
        ))
    conn.commit()
    conn.close()

def get_cached_repositories(username: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repositories WHERE username = ? ORDER BY stars DESC", (username.lower(),))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for row in rows:
        item = dict(row)
        item["topics"] = json.loads(item["topics"]) if item["topics"] else []
        results.append(item)
    return results

def save_contributions(username: str, contributions: List[Dict[str, Any]]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contributions WHERE username = ?", (username.lower(),))
    for c in contributions:
        cursor.execute("""
            INSERT OR REPLACE INTO contributions (username, date, count, intensity)
            VALUES (?, ?, ?, ?)
        """, (username.lower(), c["date"], c.get("count", 0), c.get("intensity", 0)))
    conn.commit()
    conn.close()

def get_cached_contributions(username: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date, count, intensity FROM contributions WHERE username = ? ORDER BY date ASC", (username.lower(),))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def set_setting(key: str, value: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_settings (key, value, updated_at) VALUES (?, ?, ?)",
                   (key, value, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()

def get_setting(key: str) -> Optional[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM user_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else None
