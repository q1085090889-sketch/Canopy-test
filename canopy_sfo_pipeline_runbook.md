# Canopy SFO API Pipeline Runbook

## What This Does

This pipeline uses Apollo, Hunter.io, Serper, Brave Search and Gemini to produce a validated Canopy prospecting table for Mainland China, Hong Kong, Taiwan, Thailand and Malaysia.

The final table requires person-level reachability. Company contact forms, company switchboards, generic emails and company LinkedIn pages are not enough.

It exports:

- CSV lead table
- JSON lead table
- Excel workbook when `openpyxl` is available
- Workflow and scoring Markdown document
- Optional JWT-signed run manifest

## Important Security Step

Do not paste API keys into the Python file. Put them in environment variables for the current terminal session only. The keys previously pasted in chat should be rotated in Apollo, Hunter, Serper, Brave and Google AI Studio.

## Run

PowerShell example:

```powershell
$env:APOLLO_API_KEY="..."
$env:HUNTER_API_KEY="..."
$env:SERPER_API_KEY="..."
$env:BRAVE_API_KEY="..."
$env:GEMINI_API_KEY="..."
$env:JWT_SECRET="..."
python .\canopy_sfo_pipeline.py --stage discover --config .\canopy_sfo_task_config.example.json --out-dir .\output
```

After reviewing `review_candidate_discovery.csv`, continue research:

```powershell
python .\canopy_sfo_pipeline.py --stage research --config .\canopy_sfo_task_config.example.json --review-input .\output\review_candidate_discovery.csv --out-dir .\output
```

After reviewing `review_before_outreach_generation.csv`, generate emails:

```powershell
python .\canopy_sfo_pipeline.py --stage outreach --config .\canopy_sfo_task_config.example.json --review-input .\output\review_before_outreach_generation.csv --out-dir .\output
```

## Output Fields

- Region, company, domain and website
- Contact name, title, LinkedIn, phone if publicly available
- Hunter email and confidence
- Personal reachability status
- AUM and estimated AUM where available
- Core business, family background and likely Canopy pain point
- Source URLs from search results
- Four Gemini scores and A/B/C level
- 190-210 word personalized English outreach email

## Review Before Sending

Before using any generated email, check `source_urls`, confirm the contact still holds the stated role, and verify that the email is a personal business address or that the LinkedIn URL is a personal `/in/` profile. Final outreach should still be manually approved.
