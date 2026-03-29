FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY core/ core/
COPY apps/ apps/

RUN pip install --no-cache-dir -e ".[web,observability,kr-seoul-apartment]"

EXPOSE 8000

CMD ["python", "-m", "younggeul_app_kr_seoul_apartment.cli", "serve", "--host", "0.0.0.0", "--port", "8000"]
