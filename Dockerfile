FROM python:3.7-alpine
WORKDIR /silkyy
RUN pip install silkyy 
EXPOSE 8889
CMD ["python", "-m", "silkyy.service"]