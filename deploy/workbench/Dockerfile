FROM lscr.io/linuxserver/webtop:ubuntu-xfce

ARG SH3D_VERSION=7.5
ARG BLENDER_VERSION=5.1.2
ARG MPFB_VERSION=2.0.17
ARG SH3D_MCP_VERSION=1.1.0
ARG BLENDER_MCP_VERSION=1.0.0
ARG MCP_PROXY_VERSION=0.12.0

USER root

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    libegl1 \
    libgl1 \
    libgl1-mesa-dri \
    libglu1-mesa \
    libx11-6 \
    libxext6 \
    libxi6 \
    libxrender1 \
    libxtst6 \
    mesa-vulkan-drivers \
    openjdk-21-jre \
    python3 \
    python3-pip \
    python3-venv \
    socat \
    tar \
    unzip \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/sweethome3d /opt/blender /opt/personal-twin/extensions && \
    curl -fL --retry 3 \
      "https://phoenixnap.dl.sourceforge.net/project/sweethome3d/SweetHome3D/SweetHome3D-${SH3D_VERSION}/SweetHome3D-${SH3D_VERSION}-linux-x64.tgz" \
      -o /tmp/sweethome3d.tgz && \
    tar -xzf /tmp/sweethome3d.tgz --strip-components=1 -C /opt/sweethome3d && \
    rm /tmp/sweethome3d.tgz && \
    ln -s /opt/sweethome3d/SweetHome3D /usr/local/bin/sweethome3d

RUN curl -fL --retry 3 \
      "https://mirror.blender.org/release/Blender5.1/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
      -o /tmp/blender.tar.xz && \
    tar -xJf /tmp/blender.tar.xz --strip-components=1 -C /opt/blender && \
    rm /tmp/blender.tar.xz && \
    ln -s /opt/blender/blender /usr/local/bin/blender

RUN curl -fL --retry 3 \
      "https://github.com/grimashevich/sweethome3d-mcp-server/releases/download/v${SH3D_MCP_VERSION}/sh3d-mcp-plugin-${SH3D_MCP_VERSION}.sh3p" \
      -o /opt/personal-twin/extensions/sh3d-mcp-plugin.sh3p && \
    curl -fL --retry 3 \
      "https://extensions.blender.org/download/sha256:4f0a879d64a39bf646fbf5f53601ac678855da329d650617dca5737548239a87/add-on-mpfb-v${MPFB_VERSION}.zip?repository=%2Fapi%2Fv1%2Fextensions%2F&blender_version_min=4.2.0" \
      -o /opt/personal-twin/extensions/mpfb.zip && \
    curl -fL --retry 3 \
      "https://projects.blender.org/lab/blender_mcp/releases/download/v${BLENDER_MCP_VERSION}/mcp-${BLENDER_MCP_VERSION}.zip" \
      -o /opt/personal-twin/extensions/blender-mcp.zip

RUN python3 -m venv /opt/personal-twin/mcp-venv && \
    /opt/personal-twin/mcp-venv/bin/pip install --no-cache-dir \
      "mcp==1.29.0" \
      "mcp-proxy==${MCP_PROXY_VERSION}" \
      "git+https://projects.blender.org/lab/blender_mcp.git@v${BLENDER_MCP_VERSION}#subdirectory=mcp"

COPY root/ /

RUN chmod +x \
      /usr/local/bin/personal-twin-blender \
      /usr/local/bin/personal-twin-sh3d \
      /custom-cont-init.d/10-personal-twin-init \
      /custom-services.d/blender-mcp-http \
      /custom-services.d/personal-twin-memory \
      /custom-services.d/sh3d-mcp-forwarder \
      /custom-services.d/sweethome3d-app \
      /custom-services.d/blender-app && \
    chmod 0644 /usr/share/applications/personal-twin-*.desktop

ENV TITLE="Personal Twin Workbench"
ENV TZ="Asia/Tokyo"

EXPOSE 3000 3001 9878 9879 9880
