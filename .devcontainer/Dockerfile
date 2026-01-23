FROM plone/plone-backend:6.1

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential zsh \
    # Install Node.js 20 directly to avoid slow features installation
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
 && rm -rf /var/lib/apt/lists/* \
    # Force /bin/sh to be bash to avoid "source: not found" errors in devcontainer features
 && ln -sf /bin/bash /bin/sh

SHELL ["/bin/bash", "-c"]

WORKDIR /workspace
USER plone
