import asyncio
import pandas as pd
import json
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import time

BASE_URL = "https://remoteok.com"
WEB_URL = f"{BASE_URL}/remote-engineer-jobs"

async def scrape_jobs():
    jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # show browser
        page = await browser.new_page()

        print("🔎 Opening job listing page...")
        await page.goto(WEB_URL, timeout=60000)
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Step 1: collect job links + location
        job_entries = []
        for td in soup.select("td.company.position.company_and_position"):
            link_tag = td.select_one("a.preventLink")
            if not link_tag:
                continue

            href = link_tag.get("href")
            if href and href.startswith("/"):
                url = BASE_URL + href

                # ✅ Correct location path (inside same td)
                loc_tag = td.select_one("div.location.tooltip")
                location = loc_tag.get_text(strip=True) if loc_tag else None

                job_entries.append({
                    "url": url,
                    "location": location
                })

        print(f"✅ Found {len(job_entries)} job links. Scraping first 60...")
        job_entries = job_entries[:60]

        # Step 2: go to each job page (but skip location here)
        for idx, job in enumerate(job_entries, 1):
            url = job["url"]
            location = job["location"]

            print(f"➡️ Visiting job {idx}: {url}")
            try:
                await page.goto(url, timeout=60000)
                job_html = await page.content()
                job_soup = BeautifulSoup(job_html, "html.parser")

                # Title
                title_tag = job_soup.select_one("td.company.position.company_and_position h2")
                title = title_tag.get_text(strip=True) if title_tag else None

                # Company name
                company_tag = job_soup.select_one("td.company.position.company_and_position span.companyLink")
                company = company_tag.get_text(strip=True) if company_tag else None

                # Description (clean text instead of HTML)
                desc_div = job_soup.select_one("div.description div.markdown")
                description = desc_div.get_text(separator="\n", strip=True) if desc_div else None

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,  # ✅ keep from first page
                    "salary": None,
                    "description": description,
                    "url": url
                })

                time.sleep(1)  # polite delay

            except Exception as e:
                print(f"⚠️ Failed for {url}: {e}")

        await browser.close()

    # Step 3: save results
    print(f"✅ Got {len(jobs)} jobs")

    df = pd.DataFrame(jobs)
    df.to_csv("remoteok_engineer_jobs.csv", index=False, encoding="utf-8")
    print("💾 Saved to remoteok_engineer_jobs.csv")

    with open("remoteok_engineer_jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)
    print("💾 Saved to remoteok_engineer_jobs.json")

asyncio.run(scrape_jobs())
