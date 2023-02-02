## SciencePublishingWebsite

Very simple website:

- no SEO settings
- no content editor
- no any security

Project is written with Python Flask andand can be run both from the terminal via `start.py`, and via Gunicorn via `start.sh`

### Run guide

1. Install requirements via `pip3 install -r requirements.txt`
2. Run `reset.py` script to fill database with website settings.
3. Run `start.py` to serve Flask app.