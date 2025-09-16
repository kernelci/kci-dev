FROM python:3.10
RUN apt-get update && apt-get install -y cron
RUN pip install poetry
WORKDIR /home/kernelci
COPY . .
RUN chmod +x /home/kernelci/run_cron.sh
RUN poetry install
COPY maestro-validate-cron.txt /etc/cron.d/maestro-validate-cron-job
RUN chmod 0644 /etc/cron.d/maestro-validate-cron-job
RUN crontab /etc/cron.d/maestro-validate-cron-job
CMD ["cron", "-f"]
