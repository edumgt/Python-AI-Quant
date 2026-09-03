FROM quantconnect/lean:latest

USER root

COPY SamsungEMBuyAndHold.py /module/SamsungEMBuyAndHold.py
COPY download_sem_data.py /module/download_sem_data.py
COPY config.json /module/config.json
COPY entrypoint.sh /module/entrypoint.sh

RUN chmod +x /module/entrypoint.sh \
    && mkdir -p /results

ENTRYPOINT ["/module/entrypoint.sh"]
