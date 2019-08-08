FROM python:3.7-alpine
WORKDIR /silkyy
ADD . /silkyy_src
RUN cd /silkyy_src && pip install -r requirements.txt && python setup.py install
EXPOSE 8889
CMD ["python", "-m", "silkyy.service"]