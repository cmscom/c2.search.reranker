FROM plone/plone-backend:6.1

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
USER 500
