FROM ubuntu:18.04
LABEL author="WizardMeow"

ENV LANG="en_US.UTF-8"
ENV PYTHONIOENCODING=utf-8

RUN rm /etc/apt/sources.list
COPY sources.list /etc/apt/sources.list
COPY pip.conf /root/.pip/pip.conf

RUN apt update -qq && apt upgrade -y -qq && apt autoremove -y -qq
RUN apt install python3 python3-pip git vim -y -qq
RUN pip3 install aiohttp lxml -q

RUN git clone https://github.com/BlueCat0/HDU_library_watcher.git "/root/HDU_library_watcher"
COPY config.ini /root/HDU_library_watcher/config.ini
