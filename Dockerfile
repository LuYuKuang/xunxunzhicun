FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements-vision.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-vision.txt

COPY . .

ARG FLOODNET_WEIGHTS_URL=https://github.com/LuYuKuang/xunxunzhicun/releases/download/v1.0.0-vision/floodnet_deeplabv3.pt
ARG FLOODNET_WEIGHTS_SHA256=88a36f7df3b143f5263d6ad0245e801aca068f6687b3fd677a69b68537634e5a
RUN python -c "import hashlib, pathlib, urllib.request; target=pathlib.Path('vision/weights/floodnet_deeplabv3.pt'); target.parent.mkdir(parents=True, exist_ok=True); data=urllib.request.urlopen('${FLOODNET_WEIGHTS_URL}', timeout=180).read(); digest=hashlib.sha256(data).hexdigest(); expected='${FLOODNET_WEIGHTS_SHA256}'; assert digest == expected, f'权重 SHA256 不匹配: {digest} != {expected}'; target.write_bytes(data); print(f'downloaded {target} ({len(data)} bytes)')"

RUN python manage.py collectstatic --noinput
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
