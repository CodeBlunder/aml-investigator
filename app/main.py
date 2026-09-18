from fastapi import FastAPI

app = FastAPI(
    title="AML Investigator",
    description="Agentic AML and Transaction Monitoring Investigation Platform",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "application": "AML Investigator",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }

