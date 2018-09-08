FROM ubuntu:18.04
LABEL author="WizardMeow"

ARG GIT_USER=BlueCat0
ARG GIT_REPO=HDU_library_watcher
ARG GIT_BRANCE=master
ARG GIT_HOME=/root/HDU_library_watcher

ENV LANG="en_US.UTF-8" \
    PYTHONIOENCODING=utf-8

RUN rm /etc/apt/sources.list
COPY sources.list /etc/apt/sources.list

RUN apt update -qq && \
    apt upgrade -y -qq && \
    apt autoremove -y -qq && \
    apt install python3 python3-pip git vim -y -qq

ADD https://api.github.com/repos/$GIT_USER/$GIT_REPO/git/refs/heads/$GIT_BRANCE version.json
RUN git clone -b$GIT_BRANCE https://github.com/$GIT_USER/$GIT_REPO.git $GIT_HOME/
WORKDIR $GIT_HOME
RUN pip3 install -r requirements.txt

ENTRYPOINT ["python3", "-u", "watcher.py"]