FROM openeuler/openeuler:22.03

ARG user=meetingserver
ARG group=meetingserver
ARG uid=1000
ARG gid=1000

# 1.copy
RUN groupadd -g ${gid} ${group}
RUN useradd -u ${uid} -g ${group} -d /home/meetingserver/ -s /sbin/nologin -m ${user}
WORKDIR /home/meetingserver/app-meeting-server
COPY --chown=meetingserver ./app_meeting_server /home/meetingserver/app-meeting-server/app_meeting_server
COPY --chown=meetingserver ./manage.py /home/meetingserver/app-meeting-server
COPY --chown=meetingserver ./docker-entrypoint.sh /home/meetingserver/app-meeting-server
COPY --chown=meetingserver ./deploy /home/meetingserver/app-meeting-server/deploy
COPY --chown=meetingserver ./deploy/fonts/simsun.ttc /usr/share/fonts
COPY --chown=meetingserver ./requirements.txt /home/meetingserver/app-meeting-server

# 2.install
RUN yum install -y wget git openssl openssl-devel tzdata python3-devel mariadb-devel python3-pip libXext libjpeg xorg-x11-fonts-75dpi xorg-x11-fonts-Type1 gcc
RUN pip3 install -r /home/meetingserver/app-meeting-server/requirements.txt && rm -rf /home/meetingserver/app-meeting-server/requirements.txt
RUN wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.centos8.x86_64.rpm && \
    rpm -i wkhtmltox-0.12.6-1.centos8.x86_64.rpm && \
    rm -f wkhtmltox-0.12.6-1.centos8.x86_64.rpm


# 3.clean
RUN yum remove -y gcc python3-pip python3-setuptools procps-ng
RUN rm -rf /usr/bin/kill
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN chmod -R 550 /home/meetingserver/app-meeting-server/
RUN chmod 640 /home/meetingserver/app-meeting-server/app_meeting_server/settings/prod.py
RUN chmod -R 750 /home/meetingserver/app-meeting-server/deploy/production
RUN mkdir -p /home/meetingserver/app-meeting-server/logs
RUN chmod 750 /home/meetingserver/app-meeting-server/logs
RUN echo > /etc/issue && echo > /etc/issue.net && echo > /etc/motd
RUN sed -i 's/^PASS_MAX_DAYS.*/PASS_MAX_DAYS   90/' /etc/login.defs
RUN echo 'set +o history' >> /root/.bashrc
RUN rm -rf /tmp/*

# 4.Run server
ENV LANG=en_US.UTF-8
RUN chown -R ${user}:${group} /home/meetingserver/
USER ${uid}:${gid}

RUN history -c && echo "set +o history" >> /home/meetingserver/.bashrc  && echo "umask 027" >> /home/meetingserver/.bashrc && source /home/meetingserver/.bashrc
ENTRYPOINT ["/home/meetingserver/app-meeting-server/docker-entrypoint.sh"]
CMD ["uwsgi", "--ini", "/home/meetingserver/app-meeting-server/deploy/production/uwsgi.ini"]
EXPOSE 8080
