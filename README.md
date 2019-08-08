# Silkyy
A web spider state storage service.

Silkyy means that spiders produce some web silk as its steptrace, on next time it goes out, it can guide itself.

Silkyy can store spider's walked places (called SEEN in silkyy, which can be very useful when performing incremental
crawling), shared scheduler (to support high concurrency crawling),

# Installation



# Setup
Silkyy server depends on a backend database to storage meta data and also a redis to effectively store spider state
data.

A config file can be place in these following places:

* /etc/silkyy/silkyy.conf
* ./conf/silkyy.conf
* ./silkyy.conf

## Modes
### Mode 1 Solo
In solo mode, it is easy to setup and just run.

Run service:

    python -m silkyy.service

Spiders can call apis with a context of the same default application.


### Mode 2 Multi-tanents
In multi-tanent mode, user have to register account on service and create some application.

User should always call api with AppKey and give a digest about the request with AppSecret (which is also well-known
as HMAC)

Silkyy apis don't support encrypting to pretect data sniffing, the best way to avoid this is to connect to Silkyy with
TLS.


### Use Silkyy DupeFilter in scrapy

add two config in settings.py

    DUPEFILTER_CLASS = "silkyy.middleware.scrapy.dupefilter.SilkyyDupeFilter"
    SILKYY_BASEURL = "http://localhost:8889/"
    
which silkyy_baseurl should be pointed to your silkyy base url.


### Docker 

    version: '3'
    services:
      redis:
        image: "redis:alpine"
        volumes:
          - './redis/data:/data:z'
        ports:
          - "6379:6379"
        command: redis-server --appendonly yes
      silkyy:
        image: kevenli/silkyy
        volumes:
          - "./silkyy/:/silkyy/:z"
        ports:
          - 8889:8889
        links:
          - redis
        environment:
          - SILKYY_REDIS_URL=redis://redis:6379/0





