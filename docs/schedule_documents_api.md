# Schedule documents API

## What
Creating of presigned urls for further posting/removing in S3, sharing.

**Endpoint**: ```/api/v1/presigned-urls/```

**Parameters**:

* _method_name_, required. Can be one of `get_s3_object, delete_s3_object, post_s3_object` 
* _schedule_, required for `post_s3_object`. Id of schedule.
* _document_, required for `delete_s3_object`. Id of document.



## Generate presigned url for getting file from S3

```http
GET /api/v1/presigned-urls/?method_name=get_s3_object&document=56a4602f-a621-46ec-b1df-c55d4c60f10b 
HTTP/1.1
ACCESSTOKEN: eyJraWQiOiJNZ2dVVnNzdjY2QUdmRkdZaEY4a1dJVUl0bFdFeFpwcnNKNm51WmZMazFRPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzNjIzZWQxZS03MDM4LTQ1ZDctYjAzMS1lZmRiZWU5MTIzYjciLCJldmVudF9pZCI6ImFiMTkyZDk2LTllODQtNDRiYy05NTllLTEzNDcwNzI0YTUyYSIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoiYXdzLmNvZ25pdG8uc2lnbmluLnVzZXIuYWRtaW4iLCJhdXRoX3RpbWUiOjE1NjMzMTY0NjEsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5ldS13ZXN0LTIuYW1hem9uYXdzLmNvbVwvZXUtd2VzdC0yX2J6U2ZnQ3pYSiIsImV4cCI6MTU2MzMyMDA2MSwiaWF0IjoxNTYzMzE2NDYxLCJqdGkiOiI0NDkzZmMxMC00MzZmLTQxZmUtOWFkZi1lMTdkOGRiMGRjZDMiLCJjbGllbnRfaWQiOiIxdDkzYm5tajFsbTY0dWQyb3ZuaTExdmZrNiIsInVzZXJuYW1lIjoiMzYyM2VkMWUtNzAzOC00NWQ3LWIwMzEtZWZkYmVlOTEyM2I3In0.PWBX8uXhijDlJZZT7nNuw_v6uiI8_mWoBx4bOQED3_wpnVwKF1FYVr0qfjQlwv0Jdwhlut7h_GI__L2smv_junkinWmq2ieCYQ4C-n9Rvoe4yYFK4NmcxcXXN1jU0kHIkjiOP-sh1ra2CJCP1wC6S-n_z7S_9Wj-etVbmmCwNdx2JhnBiZfnmcu31tubXF_AIXr4ngpwlv1KuOabuZEHX-LL-hxaF2lJaZTUES-WG2Cx8faqWXmI-5DbNGwi0aCMAScOeMI-DMQZpoqcdXT_BGFjZTBqKXTZ6Qr_aQegS3xEDsqP99CyHDC1PfgrsSvG80uQ3ZP3kSzighBjSJfJWw
Accept: application/json, */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
Content-Length: 573
Content-Type: application/vnd.api+json
Host: localhost:8000
IDTOKEN: eyJraWQiOiJpc2J6dmY0REpaNjM1UjI2dENhd1l2bVhRR09FUDJzdFY5aXhDd3NvZ2RRPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzNjIzZWQxZS03MDM4LTQ1ZDctYjAzMS1lZmRiZWU5MTIzYjciLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiaXNzIjoiaHR0cHM6XC9cL2NvZ25pdG8taWRwLmV1LXdlc3QtMi5hbWF6b25hd3MuY29tXC9ldS13ZXN0LTJfYnpTZmdDelhKIiwicGhvbmVfbnVtYmVyX3ZlcmlmaWVkIjpmYWxzZSwiY29nbml0bzp1c2VybmFtZSI6IjM2MjNlZDFlLTcwMzgtNDVkNy1iMDMxLWVmZGJlZTkxMjNiNyIsImdpdmVuX25hbWUiOiJCcnVjZSIsImF1ZCI6IjF0OTNibm1qMWxtNjR1ZDJvdm5pMTF2Zms2IiwiY3VzdG9tOmFjY291bnRfdHlwZSI6Ik93bmVyIiwiZXZlbnRfaWQiOiJhYjE5MmQ5Ni05ZTg0LTQ0YmMtOTU5ZS0xMzQ3MDcyNGE1MmEiLCJ0b2tlbl91c2UiOiJpZCIsImF1dGhfdGltZSI6MTU2MzMxNjQ2MSwicGhvbmVfbnVtYmVyIjoiKzQ5MzM0NDQ0MjIyMjIiLCJleHAiOjE1NjMzMjAwNjEsImlhdCI6MTU2MzMxNjQ2MSwiZmFtaWx5X25hbWUiOiJTdGV3YXJ0IiwiZW1haWwiOiJhcGlfdGVzdEBtYWlsaW5hdG9yLmNvbSJ9.h4aGm5X5wtbVi73BJm5ptH6bM8d-YN5-OlayFH_gBn--jGZNG0LM1csRUqWyEFznZmEXPzTH9VNJNULdDDFABU-EsLVwjL2A8cw-oiS11WNvWYj3UqRzVCZCG9cLaQ7WDhShdhJbUxHqzLNK-RgshHmIBYeqOChK4LDwACdCv4N9wP0kGWLbMg-IFzkoT-BdusbwR6ZG_3ci0daDc9IwIdzz4inDuoC-5JxCq6edz17Xk2lZkRhfq6qKq8YVYh6HrfZBI_GEfXV6ugHFYaZ1Xts0oqv2LxV2xv7UQ1mWILGO17IhXo8642CmVPzo6HOQxRBYz5p8Y3xikldAacJZvQ
User-Agent: HTTPie/1.0.2

```
```http
HTTP/1.1 200 OK
Allow: GET, HEAD, OPTIONS
Content-Length: 486
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 22:37:05 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "data": {
        "url": "https://customate-dev-django.s3.amazonaws.com/file.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAIE3XSV36KZDA26WQ%2F20190809%2Feu-west-2%2Fs3%2Faws4_request&X-Amz-Date=20190809T121941Z&X-Amz-Expires=20&X-Amz-SignedHeaders=host&X-Amz-Signature=600aca7d7b8999d8544ca9506746cfea59d63a1839d6de745e26cea1e3245f11"
    }
}

```
### Possible error responses
```http
HTTP/1.1 400 Bad Request
Allow: GET, HEAD, OPTIONS
Content-Length: 136
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:41:13 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "Unrecognized method: <method_name>",
            "source": {
                "pointer": "/data"
            },
            "status": "400"
        }
    ]
}

```
```http

HTTP/1.1 403 Forbidden
Allow: GET, HEAD, OPTIONS
Content-Length: 124
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:45:02 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "You do not have permission to perform this action.",
            "source": {
                "pointer": "/data"
            },
            "status": "403"
        }
    ]
}
```
```http

HTTP/1.1 404 Not Found
Allow: GET, HEAD, OPTIONS
Content-Length: 124
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:45:02 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "Not found.",
            "source": {
                "pointer": "/data/attributes/detail"
            },
            "status": "404"
        }
    ]
}
```
```http

HTTP/1.1 410 Service Unavailable
Allow: GET, HEAD, OPTIONS
Content-Length: 124
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:45:02 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "Our file upload service is currently unavailable, please try again later",
            "source": {
                "pointer": "/data/attributes/detail"
            },
            "status": "404"
        }
    ]
}
```
## Generate presigned url for posting file to S3
```http
GET /api/v1/presigned-urls/?schedule=7e06b0da-5959-40bc-b583-464b721b3f77&method_name=post_s3_object&filename=file.pdf HTTP/1.1
ACCESSTOKEN: eyJraWQiOiJNZ2dVVnNzdjY2QUdmRkdZaEY4a1dJVUl0bFdFeFpwcnNKNm51WmZMazFRPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzNjIzZWQxZS03MDM4LTQ1ZDctYjAzMS1lZmRiZWU5MTIzYjciLCJldmVudF9pZCI6ImFiMTkyZDk2LTllODQtNDRiYy05NTllLTEzNDcwNzI0YTUyYSIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoiYXdzLmNvZ25pdG8uc2lnbmluLnVzZXIuYWRtaW4iLCJhdXRoX3RpbWUiOjE1NjMzMTY0NjEsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5ldS13ZXN0LTIuYW1hem9uYXdzLmNvbVwvZXUtd2VzdC0yX2J6U2ZnQ3pYSiIsImV4cCI6MTU2MzMyMDA2MSwiaWF0IjoxNTYzMzE2NDYxLCJqdGkiOiI0NDkzZmMxMC00MzZmLTQxZmUtOWFkZi1lMTdkOGRiMGRjZDMiLCJjbGllbnRfaWQiOiIxdDkzYm5tajFsbTY0dWQyb3ZuaTExdmZrNiIsInVzZXJuYW1lIjoiMzYyM2VkMWUtNzAzOC00NWQ3LWIwMzEtZWZkYmVlOTEyM2I3In0.PWBX8uXhijDlJZZT7nNuw_v6uiI8_mWoBx4bOQED3_wpnVwKF1FYVr0qfjQlwv0Jdwhlut7h_GI__L2smv_junkinWmq2ieCYQ4C-n9Rvoe4yYFK4NmcxcXXN1jU0kHIkjiOP-sh1ra2CJCP1wC6S-n_z7S_9Wj-etVbmmCwNdx2JhnBiZfnmcu31tubXF_AIXr4ngpwlv1KuOabuZEHX-LL-hxaF2lJaZTUES-WG2Cx8faqWXmI-5DbNGwi0aCMAScOeMI-DMQZpoqcdXT_BGFjZTBqKXTZ6Qr_aQegS3xEDsqP99CyHDC1PfgrsSvG80uQ3ZP3kSzighBjSJfJWw
Accept: application/json, */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
Content-Length: 573
Content-Type: application/vnd.api+json
Host: localhost:8000
IDTOKEN: eyJraWQiOiJpc2J6dmY0REpaNjM1UjI2dENhd1l2bVhRR09FUDJzdFY5aXhDd3NvZ2RRPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzNjIzZWQxZS03MDM4LTQ1ZDctYjAzMS1lZmRiZWU5MTIzYjciLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiaXNzIjoiaHR0cHM6XC9cL2NvZ25pdG8taWRwLmV1LXdlc3QtMi5hbWF6b25hd3MuY29tXC9ldS13ZXN0LTJfYnpTZmdDelhKIiwicGhvbmVfbnVtYmVyX3ZlcmlmaWVkIjpmYWxzZSwiY29nbml0bzp1c2VybmFtZSI6IjM2MjNlZDFlLTcwMzgtNDVkNy1iMDMxLWVmZGJlZTkxMjNiNyIsImdpdmVuX25hbWUiOiJCcnVjZSIsImF1ZCI6IjF0OTNibm1qMWxtNjR1ZDJvdm5pMTF2Zms2IiwiY3VzdG9tOmFjY291bnRfdHlwZSI6Ik93bmVyIiwiZXZlbnRfaWQiOiJhYjE5MmQ5Ni05ZTg0LTQ0YmMtOTU5ZS0xMzQ3MDcyNGE1MmEiLCJ0b2tlbl91c2UiOiJpZCIsImF1dGhfdGltZSI6MTU2MzMxNjQ2MSwicGhvbmVfbnVtYmVyIjoiKzQ5MzM0NDQ0MjIyMjIiLCJleHAiOjE1NjMzMjAwNjEsImlhdCI6MTU2MzMxNjQ2MSwiZmFtaWx5X25hbWUiOiJTdGV3YXJ0IiwiZW1haWwiOiJhcGlfdGVzdEBtYWlsaW5hdG9yLmNvbSJ9.h4aGm5X5wtbVi73BJm5ptH6bM8d-YN5-OlayFH_gBn--jGZNG0LM1csRUqWyEFznZmEXPzTH9VNJNULdDDFABU-EsLVwjL2A8cw-oiS11WNvWYj3UqRzVCZCG9cLaQ7WDhShdhJbUxHqzLNK-RgshHmIBYeqOChK4LDwACdCv4N9wP0kGWLbMg-IFzkoT-BdusbwR6ZG_3ci0daDc9IwIdzz4inDuoC-5JxCq6edz17Xk2lZkRhfq6qKq8YVYh6HrfZBI_GEfXV6ugHFYaZ1Xts0oqv2LxV2xv7UQ1mWILGO17IhXo8642CmVPzo6HOQxRBYz5p8Y3xikldAacJZvQ
User-Agent: HTTPie/1.0.2
```
```http
HTTP/1.1 200 OK
Allow: GET, HEAD, OPTIONS
Content-Length: 486
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 22:37:05 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "data": {
        "id": "f013bcc7-4622-4086-98e9-4feb1b1c692c",
        "slug": "file.pdf",
        "delete": true,
        "presigned_data": {
            "url": "https://customate-dev-django.s3.amazonaws.com/",
            "fields": {
                "key": "file.pdf",
                "x-amz-algorithm": "AWS4-HMAC-SHA256",
                "x-amz-credential": "AKIAIE3XSV36KZDA26WQ/20190814/eu-west-2/s3/aws4_request",
                "x-amz-date": "20190814T112929Z",
                "policy": "eyJleHBpcmF0aW9uIjogIjIwMTktMDgtMTRUMTE6Mjk6NDlaIiwgImNvbmRpdGlvbnMiOiBbeyJidWNrZXQiOiAiY3VzdG9tYXRlLWRldi1kamFuZ28ifSwgeyJrZXkiOiAiZmlsZWZpbGUucGRmIn0sIHsieC1hbXotYWxnb3JpdGhtIjogIkFXUzQtSE1BQy1TSEEyNTYifSwgeyJ4LWFtei1jcmVkZW50aWFsIjogIkFLSUFJRTNYU1YzNktaREEyNldRLzIwMTkwODE0L2V1LXdlc3QtMi9zMy9hd3M0X3JlcXVlc3QifSwgeyJ4LWFtei1kYXRlIjogIjIwMTkwODE0VDExMjkyOVoifV19",
                "x-amz-signature": "f4bed627e22bb976c647ed1e82854e4450c6bb4acae9c92f8a38708ca8259cb1"
            }
        }
    }
}

```
### Possible error responses
```http
HTTP/1.1 400 Bad Request
Allow: GET, HEAD, OPTIONS
Content-Length: 136
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:41:13 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "Dublicate file name. Please choose another one.",
            "source": {
                "pointer": "/data"
            },
            "status": "400"
        }
    ]
}

```
```http

HTTP/1.1 403 Forbidden
Allow: GET, HEAD, OPTIONS
Content-Length: 124
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:45:02 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "You do not have permission to perform this action.",
            "source": {
                "pointer": "/data"
            },
            "status": "403"
        }
    ]
}
```
```http
HTTP/1.1 400 Bad Request
Allow: GET, HEAD, OPTIONS
Content-Length: 136
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:41:13 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "Unrecognized method: <method_name>",
            "source": {
                "pointer": "/data"
            },
            "status": "400"
        }
    ]
}
```
```http
HTTP/1.1 400 Bad Request
Allow: GET, HEAD, OPTIONS
Content-Length: 136
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:41:13 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "<filename> is not in supported format",
            "source": {
                "pointer": "/data"
            },
            "status": "400"
        }
    ]
}
```
```http

HTTP/1.1 410 Service Unavailable
Allow: GET, HEAD, OPTIONS
Content-Length: 124
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:45:02 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "Our file upload service is currently unavailable, please try again later",
            "source": {
                "pointer": "/data/attributes/detail"
            },
            "status": "404"
        }
    ]
}
```
## Generate presigned url for removing file from S3
```http
GET /api/v1/presigned-urls/?method_name=delete_s3_object&document=56a4602f-a621-46ec-b1df-c55d4c60f10b
HTTP/1.1
ACCESSTOKEN: eyJraWQiOiJNZ2dVVnNzdjY2QUdmRkdZaEY4a1dJVUl0bFdFeFpwcnNKNm51WmZMazFRPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzNjIzZWQxZS03MDM4LTQ1ZDctYjAzMS1lZmRiZWU5MTIzYjciLCJldmVudF9pZCI6ImFiMTkyZDk2LTllODQtNDRiYy05NTllLTEzNDcwNzI0YTUyYSIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoiYXdzLmNvZ25pdG8uc2lnbmluLnVzZXIuYWRtaW4iLCJhdXRoX3RpbWUiOjE1NjMzMTY0NjEsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5ldS13ZXN0LTIuYW1hem9uYXdzLmNvbVwvZXUtd2VzdC0yX2J6U2ZnQ3pYSiIsImV4cCI6MTU2MzMyMDA2MSwiaWF0IjoxNTYzMzE2NDYxLCJqdGkiOiI0NDkzZmMxMC00MzZmLTQxZmUtOWFkZi1lMTdkOGRiMGRjZDMiLCJjbGllbnRfaWQiOiIxdDkzYm5tajFsbTY0dWQyb3ZuaTExdmZrNiIsInVzZXJuYW1lIjoiMzYyM2VkMWUtNzAzOC00NWQ3LWIwMzEtZWZkYmVlOTEyM2I3In0.PWBX8uXhijDlJZZT7nNuw_v6uiI8_mWoBx4bOQED3_wpnVwKF1FYVr0qfjQlwv0Jdwhlut7h_GI__L2smv_junkinWmq2ieCYQ4C-n9Rvoe4yYFK4NmcxcXXN1jU0kHIkjiOP-sh1ra2CJCP1wC6S-n_z7S_9Wj-etVbmmCwNdx2JhnBiZfnmcu31tubXF_AIXr4ngpwlv1KuOabuZEHX-LL-hxaF2lJaZTUES-WG2Cx8faqWXmI-5DbNGwi0aCMAScOeMI-DMQZpoqcdXT_BGFjZTBqKXTZ6Qr_aQegS3xEDsqP99CyHDC1PfgrsSvG80uQ3ZP3kSzighBjSJfJWw
Accept: application/json, */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
Content-Length: 573
Content-Type: application/vnd.api+json
Host: localhost:8000
IDTOKEN: eyJraWQiOiJpc2J6dmY0REpaNjM1UjI2dENhd1l2bVhRR09FUDJzdFY5aXhDd3NvZ2RRPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzNjIzZWQxZS03MDM4LTQ1ZDctYjAzMS1lZmRiZWU5MTIzYjciLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiaXNzIjoiaHR0cHM6XC9cL2NvZ25pdG8taWRwLmV1LXdlc3QtMi5hbWF6b25hd3MuY29tXC9ldS13ZXN0LTJfYnpTZmdDelhKIiwicGhvbmVfbnVtYmVyX3ZlcmlmaWVkIjpmYWxzZSwiY29nbml0bzp1c2VybmFtZSI6IjM2MjNlZDFlLTcwMzgtNDVkNy1iMDMxLWVmZGJlZTkxMjNiNyIsImdpdmVuX25hbWUiOiJCcnVjZSIsImF1ZCI6IjF0OTNibm1qMWxtNjR1ZDJvdm5pMTF2Zms2IiwiY3VzdG9tOmFjY291bnRfdHlwZSI6Ik93bmVyIiwiZXZlbnRfaWQiOiJhYjE5MmQ5Ni05ZTg0LTQ0YmMtOTU5ZS0xMzQ3MDcyNGE1MmEiLCJ0b2tlbl91c2UiOiJpZCIsImF1dGhfdGltZSI6MTU2MzMxNjQ2MSwicGhvbmVfbnVtYmVyIjoiKzQ5MzM0NDQ0MjIyMjIiLCJleHAiOjE1NjMzMjAwNjEsImlhdCI6MTU2MzMxNjQ2MSwiZmFtaWx5X25hbWUiOiJTdGV3YXJ0IiwiZW1haWwiOiJhcGlfdGVzdEBtYWlsaW5hdG9yLmNvbSJ9.h4aGm5X5wtbVi73BJm5ptH6bM8d-YN5-OlayFH_gBn--jGZNG0LM1csRUqWyEFznZmEXPzTH9VNJNULdDDFABU-EsLVwjL2A8cw-oiS11WNvWYj3UqRzVCZCG9cLaQ7WDhShdhJbUxHqzLNK-RgshHmIBYeqOChK4LDwACdCv4N9wP0kGWLbMg-IFzkoT-BdusbwR6ZG_3ci0daDc9IwIdzz4inDuoC-5JxCq6edz17Xk2lZkRhfq6qKq8YVYh6HrfZBI_GEfXV6ugHFYaZ1Xts0oqv2LxV2xv7UQ1mWILGO17IhXo8642CmVPzo6HOQxRBYz5p8Y3xikldAacJZvQ
User-Agent: HTTPie/1.0.2
```
```http
HTTP/1.1 200 OK
Allow: GET, HEAD, OPTIONS
Content-Length: 486
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 22:37:05 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "data": {
        "url": "https://customate-dev-django.s3.amazonaws.com/file.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAIE3XSV36KZDA26WQ%2F20190809%2Feu-west-2%2Fs3%2Faws4_request&X-Amz-Date=20190809T123959Z&X-Amz-Expires=20&X-Amz-SignedHeaders=host&X-Amz-Signature=6f0887c2bc391a20bd5582ade2b7019612be3de797a267b3cab5494809f12af8"
    }
}

```
### Possible error responses
```http

HTTP/1.1 403 Forbidden
Allow: GET, HEAD, OPTIONS
Content-Length: 124
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:45:02 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "You do not have permission to perform this action.",
            "source": {
                "pointer": "/data"
            },
            "status": "403"
        }
    ]
}
```
```http
HTTP/1.1 400 Bad Request
Allow: GET, HEAD, OPTIONS
Content-Length: 136
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:41:13 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "Unrecognized method: <method_name>",
            "source": {
                "pointer": "/data"
            },
            "status": "400"
        }
    ]
}
```
```http
HTTP/1.1 404 Not Found
Allow: GET, HEAD, OPTIONS
Content-Length: 136
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:41:13 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN
{
    "errors": [
        {
            "detail": "Not found.",
            "source": {
                "pointer": "/data/attributes/detail"
            },
            "status": "404"
        }
    ]
}
```
```http

HTTP/1.1 410 Service Unavailable
Allow: GET, HEAD, OPTIONS
Content-Length: 124
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:45:02 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "Our file upload service is currently unavailable, please try again later",
            "source": {
                "pointer": "/data/attributes/detail"
            },
            "status": "404"
        }
    ]
}
```
## Remove document from server
```http
DELETE /api/v1/schedules/7e06b0da-5959-40bc-b583-464b721b3f77/documents/?document=56a4602f-a621-46ec-b1df-c55d4c60f10b
HTTP/1.1
ACCESSTOKEN: eyJraWQiOiJNZ2dVVnNzdjY2QUdmRkdZaEY4a1dJVUl0bFdFeFpwcnNKNm51WmZMazFRPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzNjIzZWQxZS03MDM4LTQ1ZDctYjAzMS1lZmRiZWU5MTIzYjciLCJldmVudF9pZCI6ImFiMTkyZDk2LTllODQtNDRiYy05NTllLTEzNDcwNzI0YTUyYSIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoiYXdzLmNvZ25pdG8uc2lnbmluLnVzZXIuYWRtaW4iLCJhdXRoX3RpbWUiOjE1NjMzMTY0NjEsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5ldS13ZXN0LTIuYW1hem9uYXdzLmNvbVwvZXUtd2VzdC0yX2J6U2ZnQ3pYSiIsImV4cCI6MTU2MzMyMDA2MSwiaWF0IjoxNTYzMzE2NDYxLCJqdGkiOiI0NDkzZmMxMC00MzZmLTQxZmUtOWFkZi1lMTdkOGRiMGRjZDMiLCJjbGllbnRfaWQiOiIxdDkzYm5tajFsbTY0dWQyb3ZuaTExdmZrNiIsInVzZXJuYW1lIjoiMzYyM2VkMWUtNzAzOC00NWQ3LWIwMzEtZWZkYmVlOTEyM2I3In0.PWBX8uXhijDlJZZT7nNuw_v6uiI8_mWoBx4bOQED3_wpnVwKF1FYVr0qfjQlwv0Jdwhlut7h_GI__L2smv_junkinWmq2ieCYQ4C-n9Rvoe4yYFK4NmcxcXXN1jU0kHIkjiOP-sh1ra2CJCP1wC6S-n_z7S_9Wj-etVbmmCwNdx2JhnBiZfnmcu31tubXF_AIXr4ngpwlv1KuOabuZEHX-LL-hxaF2lJaZTUES-WG2Cx8faqWXmI-5DbNGwi0aCMAScOeMI-DMQZpoqcdXT_BGFjZTBqKXTZ6Qr_aQegS3xEDsqP99CyHDC1PfgrsSvG80uQ3ZP3kSzighBjSJfJWw
Accept: application/json, */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
Content-Length: 573
Content-Type: application/vnd.api+json
Host: localhost:8000
IDTOKEN: eyJraWQiOiJpc2J6dmY0REpaNjM1UjI2dENhd1l2bVhRR09FUDJzdFY5aXhDd3NvZ2RRPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzNjIzZWQxZS03MDM4LTQ1ZDctYjAzMS1lZmRiZWU5MTIzYjciLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiaXNzIjoiaHR0cHM6XC9cL2NvZ25pdG8taWRwLmV1LXdlc3QtMi5hbWF6b25hd3MuY29tXC9ldS13ZXN0LTJfYnpTZmdDelhKIiwicGhvbmVfbnVtYmVyX3ZlcmlmaWVkIjpmYWxzZSwiY29nbml0bzp1c2VybmFtZSI6IjM2MjNlZDFlLTcwMzgtNDVkNy1iMDMxLWVmZGJlZTkxMjNiNyIsImdpdmVuX25hbWUiOiJCcnVjZSIsImF1ZCI6IjF0OTNibm1qMWxtNjR1ZDJvdm5pMTF2Zms2IiwiY3VzdG9tOmFjY291bnRfdHlwZSI6Ik93bmVyIiwiZXZlbnRfaWQiOiJhYjE5MmQ5Ni05ZTg0LTQ0YmMtOTU5ZS0xMzQ3MDcyNGE1MmEiLCJ0b2tlbl91c2UiOiJpZCIsImF1dGhfdGltZSI6MTU2MzMxNjQ2MSwicGhvbmVfbnVtYmVyIjoiKzQ5MzM0NDQ0MjIyMjIiLCJleHAiOjE1NjMzMjAwNjEsImlhdCI6MTU2MzMxNjQ2MSwiZmFtaWx5X25hbWUiOiJTdGV3YXJ0IiwiZW1haWwiOiJhcGlfdGVzdEBtYWlsaW5hdG9yLmNvbSJ9.h4aGm5X5wtbVi73BJm5ptH6bM8d-YN5-OlayFH_gBn--jGZNG0LM1csRUqWyEFznZmEXPzTH9VNJNULdDDFABU-EsLVwjL2A8cw-oiS11WNvWYj3UqRzVCZCG9cLaQ7WDhShdhJbUxHqzLNK-RgshHmIBYeqOChK4LDwACdCv4N9wP0kGWLbMg-IFzkoT-BdusbwR6ZG_3ci0daDc9IwIdzz4inDuoC-5JxCq6edz17Xk2lZkRhfq6qKq8YVYh6HrfZBI_GEfXV6ugHFYaZ1Xts0oqv2LxV2xv7UQ1mWILGO17IhXo8642CmVPzo6HOQxRBYz5p8Y3xikldAacJZvQ
User-Agent: HTTPie/1.0.2

```
```http
HTTP/1.1 204 OK
Allow: DELETE, OPTIONS
Content-Length: 486
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 22:37:05 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

```
### Possible error responses
```http

HTTP/1.1 403 Forbidden
Allow: GET, HEAD, OPTIONS
Content-Length: 124
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:45:02 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "You do not have permission to perform this action.",
            "source": {
                "pointer": "/data"
            },
            "status": "403"
        }
    ]
}
```
```http
HTTP/1.1 404 Not found
Allow: DELETE, OPTIONS
Content-Length: 136
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:41:13 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "Not found.",
            "source": {
                "pointer": "/data/attributes/detail"
            },
            "status": "404"
        }
    ]
}
```
```http
HTTP/1.1 400 Bad Request
Allow: DELETE, OPTIONS
Content-Length: 136
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:41:13 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "The 'document_name' parameter is required",
            "source": {
                "pointer": "/data"
            },
            "status": "400"
        }
    ]
}
```

