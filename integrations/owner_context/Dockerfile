# Host-neutral always-on image for the owner-context display host.
# Build from the repository root:
#   docker build -f integrations/owner_context/Dockerfile -t commons-owner-context .
# GitHub Actions is not an always-on host.
# Copy named files only so a local gitignored env file cannot bake into the image.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OWNER_CONTEXT_BIND=0.0.0.0:8789

RUN useradd --system --uid 10001 --create-home --home-dir /var/lib/commons commons

WORKDIR /opt/commons
RUN mkdir -p /opt/commons/host /opt/commons/integrations/owner_context /opt/commons/api
COPY owner.json owner_net.py owner_enroll.py /opt/commons/
COPY host/owner_context.py /opt/commons/host/owner_context.py
COPY integrations/owner_context/__init__.py \
     integrations/owner_context/service.py \
     integrations/owner_context/env.example \
     integrations/owner_context/run.sh \
     integrations/owner_context/Dockerfile \
     integrations/owner_context/compose.yml \
     integrations/owner_context/commons-owner-context.service \
     integrations/owner_context/README.md \
     /opt/commons/integrations/owner_context/

USER commons
EXPOSE 8789

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python /opt/commons/host/owner_context.py doctor --no-probe --json

CMD ["python", "/opt/commons/integrations/owner_context/service.py", "serve"]
