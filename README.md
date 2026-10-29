# DevVibe - GitHub Developer Portfolio & Vibe Check Platform

An intelligent developer dashboard and personal branding platform that visualizes GitHub activity, repository metrics, coding streaks, and provides a server-side **Tech Stack Compatibility Engine ("The Vibe Check")** along with an **AI Recruiter & Mock Interview Chatbot**.

---

## 🌟 Key Features

### 1. Frontend UI & Data Visualization
* **Profile Header**: Avatar, bio, followers, total accumulated stars, and an interactive **Chart.js "Top Languages" Donut Chart**.
* **Contribution Heatmap Grid**: Visual 52-week calendar grid displaying daily coding activity with intensity levels, tooltips, and calculated streaks (**Current streak**, **Longest streak**, **Total contributions**).
* **Repository Cards**: Ranked showcase cards featuring star counts, forks, primary language indicators, topic tags, and direct repository links.

### 2. Backend Logic & State Management
* **Strict Server-Side Computation**: All business logic, streak calculations, keyword extractions, and compatibility scoring are computed on the server side using FastAPI.
* **SQLite Caching Engine**: Persistent local caching in `dev_portfolio.db` for user profiles, repository metadata, language distributions, and contribution history. Prevents external API bottlenecks and ensures instant page load speeds.

### 3. The "Vibe Check" (Tech Stack Compatibility Engine)
* Allows recruiters and users to paste any Job Description (JD).
* The backend parses technical keywords from the JD and evaluates them against the developer's cached repositories, languages, and topics.
* Produces a dynamic **"Match Percentage"** badge at the top of the profile, accompanied by a breakdown of **Matched Skills** vs. **Skill Gaps**.

### 4. Advanced Chatbot Capabilities
* **Feature 1: "Ask My Codebase" Recruiter Assistant**: An embedded AI chatbot that answers natural-language questions regarding the developer's highlighted repositories, architectural strengths, and framework experience.
* **Feature 2: AI Skill Gap & Mock Technical Interviewer**: Dynamically generates tailored technical interview questions based on the intersection between the target Job Description and the developer's actual public repositories.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* Git

### Installation & Execution
1. **Activate the virtual environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
2. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
3. **Run the FastAPI server**:
   ```powershell
   python -m uvicorn backend.main:app --reload --port 8000
   ```
4. **Open the Dashboard**:
   Visit [http://localhost:8000](http://localhost:8000) in your web browser.

---

## 🔑 GitHub API Token & Rate Limits

GitHub imposes a rate limit of **60 unauthenticated requests/hour** per IP address.
To increase your rate limit to **5,000 requests/hour**:
1. Generate a Personal Access Token (classic or fine-grained) at [GitHub Token Settings](https://github.com/settings/tokens). No special permissions/scopes are required for public repositories.
2. Create a `.env` file in the root directory:
   ```env
   GITHUB_TOKEN=ghp_your_personal_access_token_here
   CACHE_EXPIRY_MINUTES=60
   ```
3. Restart the server. The application will automatically use authenticated requests and seamlessly cache all data in SQLite.
