FROM mcr.microsoft.com/devcontainers/python:0-3.8

ENV PYTHONUNBUFFERED 1

# [Optional] If your requirements rarely change, uncomment this section to add them to the image.
COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
   && rm -rf /tmp/pip-tmp

# [Optional] Uncomment this section to install additional OS packages.
# RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
#     && apt-get -y install --no-install-recommends <your-package-list-here>

# Make the shebang path used in the original python scripts available in this container.
RUN mkdir -p /Library/Frameworks/Python.framework/Versions/3.8/bin \
    && ln -s /usr/local/bin/python3.8 /Library/Frameworks/Python.framework/Versions/3.8/bin/