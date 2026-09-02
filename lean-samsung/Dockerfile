FROM quantconnect/lean:latest

USER root

COPY SamsungBuyAndHold.py /module/SamsungBuyAndHold.py
COPY download_samsung_data.py /module/download_samsung_data.py
COPY config.json /module/config.json
COPY entrypoint.sh /module/entrypoint.sh

RUN chmod +x /module/entrypoint.sh \
    && mkdir -p /results

ENTRYPOINT ["/module/entrypoint.sh"]
