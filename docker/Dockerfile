# Container for the codameter config-sweep benchmark (codameter-bench).
# Built to run as one task of an array job (AWS Batch on Fargate, or any array
# runner): each task computes one --shard of the case x config grid and writes a
# shard-<k>-of-<N>.jsonl to the --out path (local or s3://).
FROM python:3.11-slim

# Non-interactive, no .pyc, unbuffered logs (so CloudWatch sees progress live).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install the package (with the aws extra for s3:// output). Only the bits the
# sweep needs are imported at runtime; wheels cover the scientific stack.
COPY pyproject.toml README.md ./
COPY src ./src
COPY tests/data/golden/manifest.json ./tests/data/golden/manifest.json
RUN pip install ".[aws]"

# The array runner sets the shard: pass --shard k/N explicitly, or set
# CODAMETER_SHARDS=N and let the CLI read AWS_BATCH_JOB_ARRAY_INDEX.
ENTRYPOINT ["codameter-bench"]
CMD ["--help"]
