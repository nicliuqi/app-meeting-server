FROM openeuler/openeuler:22.03

MAINTAINER TommyLike<tommylikehu@gmail.com>

ARG user=meetingserver
ARG group=meetingserver
ARG uid=1000
ARG gid=1000

# 1.copy
WORKDIR /work/app-meeting-server
COPY ./app_meeting_server /work/app-meeting-server/app_meeting_server
COPY ./manage.py /work/app-meeting-server
COPY ./docker-entrypoint.sh /work/app-meeting-server
COPY ./deploy /work/app-meeting-server/deploy
COPY ./deploy/fonts/simsun.ttc /usr/share/fonts
COPY ./requirements.txt /work/app-meeting-server

# 2.install
RUN yum install -y wget git openssl openssl-devel tzdata python3-devel mariadb-devel python3-pip libXext libjpeg xorg-x11-fonts-75dpi xorg-x11-fonts-Type1 gcc
RUN cd /work/app-meeting-server && pip3 install -r requirements.txt && rm -rf /work/app-meeting-server/requirements.txt
RUN wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.centos8.x86_64.rpm && \
    rpm -i wkhtmltox-0.12.6-1.centos8.x86_64.rpm && \
    rm -f wkhtmltox-0.12.6-1.centos8.x86_64.rpm


# 3.clean
RUN yum remove -y gcc python3-pip
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN chmod -R 550 /work/app-meeting-server/
RUN chmod 640 /work/app-meeting-server/app_meeting_server/settings/prod.py
RUN chmod -R 750 /work/app-meeting-server/deploy/production
RUN mkdir -p /work/app-meeting-server/logs
RUN chmod 750 /work/app-meeting-server/logs

# 4.Run server
ENV LANG=en_US.UTF-8
RUN groupadd -g ${gid} ${group}
RUN useradd -u ${uid} -g ${group} -s /bin/sh -m ${user}
RUN chown -R ${user}:${group} /work/app-meeting-server
USER ${uid}:${gid}

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uwsgi", "--ini", "/work/app-meeting-server/production/uwsgi.ini"]
EXPOSE 8080
