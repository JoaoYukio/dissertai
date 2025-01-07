# Dissert AI

Demo Application

# Installation

Requires Python / UV

https://docs.astral.sh/uv/guides/install-python/

1. **Clone the repository**

2. **Install dependencies**

```bash
uv sync
```

3. **Setup OpenAI Credentials**

```bash
export OPENAI_API_KEY="your_key"
```

## Run Back-End

```bash
make run_api
```

Access through browser:

http://localhost:5000/docs

If everything goes smoothly you should see our swagger docs:

![Default Swagger by FastAPI](static/image.png)