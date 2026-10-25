import os
import sys
from datetime import datetime
from google import genai

# 1. API Key और YouTube Link सेटअप
api_key = os.getenv("GEMINI_API_KEY")
youtube_url = sys.argv[1] if len(sys.argv) > 1 else "YOUR_YOUTUBE_URL_HERE"

client = genai.Client(api_key=api_key)

prompt = f"""
Watch and analyze this YouTube video: {youtube_url}

Please write a comprehensive, engaging, and SEO-friendly blog article based on the video's content.
Requirements:
1. Catchy Title as H1.
2. An engaging introduction.
3. Key takeaways with proper subheadings (H2, H3).
4. Bullet points and detailed explanations.
5. Final conclusion and summary.
Format strictly in Markdown with Jekyll/Hugo Frontmatter:

---
title: "Auto Generated Article Title"
date: {datetime.now().strftime('%Y-%m-%d')}
tags: [YouTube, AI, Summary]
---

(Article Content here)
"""

# Gemini 2.0 / 1.5 Flash direct video URL support karta hai
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[prompt]
)

# 2. File ko posts folder me save karein
filename = f"_posts/{datetime.now().strftime('%Y-%m-%d')}-new-blog.md"
os.makedirs("_posts", exist_ok=True)

with open(filename, "w", encoding="utf-8") as f:
    f.write(response.text)

print(f"Article saved successfully as {filename}")
