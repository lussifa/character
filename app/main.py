from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Character AI Studio")

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head><title>Character AI Studio</title></head>
    <body>
        <h1>Character AI Studio (Python)</h1>
        <p>Backend is running.</p>
        <p><a href=\"/docs\">API Docs</a></p>
    </body>
    </html>
    """
