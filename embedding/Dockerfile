FROM python:3.11-slim

WORKDIR /opt/app

COPY requirements.txt .
# CPU-only torch: nhẹ hơn nhiều so với bản có CUDA (~200MB thay vì ~2GB)
RUN pip install --no-cache-dir torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

# Tải model NGAY LÚC BUILD, không tải lúc job chạy — nhanh, ổn định, tái lập được
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True)"

COPY s3.sagemaker.process.py .

ENTRYPOINT ["python3", "/opt/app/s3.sagemaker.process.py"]