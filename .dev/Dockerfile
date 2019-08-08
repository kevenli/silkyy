FROM python:3.7-alpine
WORKDIR /silkyy
RUN apk add git
RUN git clone https://github.com/kevenli/silkyy.git
RUN cd silkyy && pip install -r requirements.txt && python setup.py install
EXPOSE 8889
CMD ["python", "-m", "silkyy.service"]