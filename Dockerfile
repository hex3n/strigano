# Strigano with the full forensics toolchain preinstalled.
# Build:  docker build -t strigano .
# Run:    docker run --rm -p 8000:8000 -v "$PWD/out:/data" strigano
FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv \
      libimage-exiftool-perl binwalk foremost steghide \
      tesseract-ocr ffmpeg libsndfile1 \
      ruby ruby-dev build-essential \
 && gem install zsteg --no-document \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/strigano
COPY . /opt/strigano
RUN pip3 install --break-system-packages --no-cache-dir .

ENV STRIGANO_OUTPUT=/data
VOLUME ["/data"]
EXPOSE 8000

ENTRYPOINT ["strigano"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
