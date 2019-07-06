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







