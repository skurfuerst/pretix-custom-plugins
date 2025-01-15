FROM pretix/standalone:latest

USER root
RUN chmod -R 777 /usr/local/lib/python3.11/site-packages/
USER pretixuser
ADD .docker-dev/dev_entrypoint.sh /
ENTRYPOINT ["/dev_entrypoint.sh"]