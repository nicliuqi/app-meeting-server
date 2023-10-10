FROM openeuler/openeuler:22.03

MAINTAINER TommyLike<tommylikehu@gmail.com>

RUN yum install -y vim wget git openssl openssl-devel tzdata python3-devel mariadb-devel python3-pip libXext libjpeg xorg-x11-fonts-75dpi xorg-x11-fonts-Type1 gcc

WORKDIR /work/app-meeting-server
COPY . /work/app-meeting-server
COPY ./deploy/fonts/simsun.ttc /usr/share/fonts

RUN cd /work/app-meeting-server && pip3 install -r requirements.txt
RUN wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.centos8.x86_64.rpm && \
    rpm -i wkhtmltox-0.12.6-1.centos8.x86_64.rpm && \
    rm -f wkhtmltox-0.12.6-1.centos8.x86_64.rpm

RUN yum remove -y gcc

RUN ln -s /usr/bin/python3 /usr/bin/python
RUN chmod -R 550 /work/app-meeting-server/docker-entrypoint.sh

# RASP install
ARG PUBLIC_USER
ARG PUBLIC_PASSWORD
RUN git clone https://$PUBLIC_USER:$PUBLIC_PASSWORD@github.com/Open-Infra-Ops/plugins  &&\
    cp plugins/armorrasp/armorrasp.tar.gz .  &&\
    rm -rf plugins  &&\
    pip3 install armorrasp.tar.gz && \
    rm -rf armorrasp.tar.gz \

# Run server
ENV LANG=en_US.UTF-8
ARG user=meetingserver
ARG group=meetingserver
ARG uid=1000
ARG gid=1000
RUN groupadd -g ${gid} ${group}
RUN useradd -u ${uid} -g ${group} -s /bin/sh -m ${user}
RUN chown -R ${user}:${group} /work/app-meeting-server
USER ${uid}:${gid}
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uwsgi", "--ini", "/work/app-meeting-server/production/uwsgi.ini"]
EXPOSE 8080
