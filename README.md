# Agentic Image Workflow

An AI-powered food image generation workflow using Google's Gemini (Nano Banana) model.

## Features
- Upload background and angle reference images
- Generate photorealistic food images using AI
- Approve and save images to S3

## Local Development
```bash
pip install -r requirements.txt
python app.py
```

## Deployment (Render.com)
1. Push this repo to GitHub
2. Connect to Render.com
3. Set environment variables:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_SESSION_TOKEN`
   - `GOOGLE_API_KEY`
4. Deploy!

## Environment Variables
| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS Access Key |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Key |
| `AWS_SESSION_TOKEN` | AWS Session Token (for temporary creds) |
| `AWS_REGION` | AWS Region (default: ap-south-1) |
| `S3_BUCKET_NAME` | S3 Bucket Name |
| `GOOGLE_API_KEY` | Google AI API Key |
