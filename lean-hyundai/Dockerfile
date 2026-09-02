FROM quantconnect/lean:latest

USER root

COPY HyundaiTrendBacktest.py /module/HyundaiTrendBacktest.py
COPY download_hyundai_data.py /module/download_hyundai_data.py
COPY render_report.py /module/render_report.py
COPY config.json /module/config.json
COPY entrypoint.sh /module/entrypoint.sh

RUN chmod +x /module/entrypoint.sh \
    && mkdir -p /results

ENTRYPOINT ["/module/entrypoint.sh"]
