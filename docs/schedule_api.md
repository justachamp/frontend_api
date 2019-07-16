# Schedule API

## What
Create ongoing payments in time based on previously setup contracts/agreements.

**Endpoint**: ```/api/v1/schedules/```

**Parameters**:

* _name_, required. Human-readable name of schedule
* _status_, optional. Currently, can be one of `open, closed, overdue, cancelled`
* _purpose_, required. Can be one of `pay, receive`
* _currency_, required. 3-letter ISO code of corresponding currency
* _period_, required. Can be one of `one_time, weekly, monthly, quarterly, yearly`
* _number_of_payments_left_, required. Integer, which specifies the number of ongoing payments to be made.
* _start_date_, required. Date in `YYYY-MM-DD` format to initiate first payment
* _payment_amount_, required. Integer, payment amount
* _deposit_payment_date_, optional.  This should be strictly less _start_date_
* _deposit_amount_, optional. Integer, amount of deposit. Deposit is a one-off payment initiated **prior** to any payments in the schedule
* _additional_information_, optional. Any textual information
* _payee_id_, required. UUID, identifies who should receive the money
* _funding_source_id_, required. UUID, identifies the source of money (see Funding Source API)



## Create new schedule

```http
POST /api/v1/schedules/ HTTP/1.1
ACCESSTOKEN: eyJraWQiOiJNZ2dVVnNzdjY2QUdmRkdZaEY4a1dJVUl0bFdFeFpwcnNKNm51WmZMazFRPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzNjIzZWQxZS03MDM4LTQ1ZDctYjAzMS1lZmRiZWU5MTIzYjciLCJldmVudF9pZCI6ImFiMTkyZDk2LTllODQtNDRiYy05NTllLTEzNDcwNzI0YTUyYSIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoiYXdzLmNvZ25pdG8uc2lnbmluLnVzZXIuYWRtaW4iLCJhdXRoX3RpbWUiOjE1NjMzMTY0NjEsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5ldS13ZXN0LTIuYW1hem9uYXdzLmNvbVwvZXUtd2VzdC0yX2J6U2ZnQ3pYSiIsImV4cCI6MTU2MzMyMDA2MSwiaWF0IjoxNTYzMzE2NDYxLCJqdGkiOiI0NDkzZmMxMC00MzZmLTQxZmUtOWFkZi1lMTdkOGRiMGRjZDMiLCJjbGllbnRfaWQiOiIxdDkzYm5tajFsbTY0dWQyb3ZuaTExdmZrNiIsInVzZXJuYW1lIjoiMzYyM2VkMWUtNzAzOC00NWQ3LWIwMzEtZWZkYmVlOTEyM2I3In0.PWBX8uXhijDlJZZT7nNuw_v6uiI8_mWoBx4bOQED3_wpnVwKF1FYVr0qfjQlwv0Jdwhlut7h_GI__L2smv_junkinWmq2ieCYQ4C-n9Rvoe4yYFK4NmcxcXXN1jU0kHIkjiOP-sh1ra2CJCP1wC6S-n_z7S_9Wj-etVbmmCwNdx2JhnBiZfnmcu31tubXF_AIXr4ngpwlv1KuOabuZEHX-LL-hxaF2lJaZTUES-WG2Cx8faqWXmI-5DbNGwi0aCMAScOeMI-DMQZpoqcdXT_BGFjZTBqKXTZ6Qr_aQegS3xEDsqP99CyHDC1PfgrsSvG80uQ3ZP3kSzighBjSJfJWw
Accept: application/json, */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
Content-Length: 573
Content-Type: application/vnd.api+json
Host: localhost:8000
IDTOKEN: eyJraWQiOiJpc2J6dmY0REpaNjM1UjI2dENhd1l2bVhRR09FUDJzdFY5aXhDd3NvZ2RRPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzNjIzZWQxZS03MDM4LTQ1ZDctYjAzMS1lZmRiZWU5MTIzYjciLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiaXNzIjoiaHR0cHM6XC9cL2NvZ25pdG8taWRwLmV1LXdlc3QtMi5hbWF6b25hd3MuY29tXC9ldS13ZXN0LTJfYnpTZmdDelhKIiwicGhvbmVfbnVtYmVyX3ZlcmlmaWVkIjpmYWxzZSwiY29nbml0bzp1c2VybmFtZSI6IjM2MjNlZDFlLTcwMzgtNDVkNy1iMDMxLWVmZGJlZTkxMjNiNyIsImdpdmVuX25hbWUiOiJCcnVjZSIsImF1ZCI6IjF0OTNibm1qMWxtNjR1ZDJvdm5pMTF2Zms2IiwiY3VzdG9tOmFjY291bnRfdHlwZSI6Ik93bmVyIiwiZXZlbnRfaWQiOiJhYjE5MmQ5Ni05ZTg0LTQ0YmMtOTU5ZS0xMzQ3MDcyNGE1MmEiLCJ0b2tlbl91c2UiOiJpZCIsImF1dGhfdGltZSI6MTU2MzMxNjQ2MSwicGhvbmVfbnVtYmVyIjoiKzQ5MzM0NDQ0MjIyMjIiLCJleHAiOjE1NjMzMjAwNjEsImlhdCI6MTU2MzMxNjQ2MSwiZmFtaWx5X25hbWUiOiJTdGV3YXJ0IiwiZW1haWwiOiJhcGlfdGVzdEBtYWlsaW5hdG9yLmNvbSJ9.h4aGm5X5wtbVi73BJm5ptH6bM8d-YN5-OlayFH_gBn--jGZNG0LM1csRUqWyEFznZmEXPzTH9VNJNULdDDFABU-EsLVwjL2A8cw-oiS11WNvWYj3UqRzVCZCG9cLaQ7WDhShdhJbUxHqzLNK-RgshHmIBYeqOChK4LDwACdCv4N9wP0kGWLbMg-IFzkoT-BdusbwR6ZG_3ci0daDc9IwIdzz4inDuoC-5JxCq6edz17Xk2lZkRhfq6qKq8YVYh6HrfZBI_GEfXV6ugHFYaZ1Xts0oqv2LxV2xv7UQ1mWILGO17IhXo8642CmVPzo6HOQxRBYz5p8Y3xikldAacJZvQ
User-Agent: HTTPie/1.0.2

{
    "data": {
        "attributes": {
            "currency": "EUR",
            "funding_source_id": "b51bd89f-09db-4597-96d3-33f04de06740",
            "name": "My test schedule",
            "number_of_payments_left": "12",
            "payee_id": "b51bd89f-09db-4597-96d3-33f04de06740",
            "payment_amount": "100",
            "period": "monthly",
            "purpose": "pay",
            "start_date": "2019-08-01"
        },
        "relationships": {
            "payment_account": {
                "data": {
                    "id": "bc29764f-3d51-4de3-baff-5f38fee5acd9",
                    "type": "payment_accounts"
                }
            }
        },
        "type": "Schedule"
    }
}
```

```http
HTTP/1.1 201 Created
Allow: GET, POST, HEAD, OPTIONS
Content-Length: 486
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 22:37:05 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "data": {
        "attributes": {
            "additional_information": null,
            "currency": "EUR",
            "deposit_amount": null,
            "deposit_payment_date": null,
            "funding_source_id": "b51bd89f-09db-4597-96d3-33f04de06740",
            "name": "My test schedule",
            "number_of_payments_left": 12,
            "payee_id": "b51bd89f-09db-4597-96d3-33f04de06740",
            "payment_amount": 100,
            "period": "monthly",
            "purpose": "pay",
            "start_date": "2019-08-01",
            "status": "open",
            "total_paid_sum": 0,
            "total_sum_to_pay": 0
        },
        "id": "b0e0ecbf-371e-4496-b28f-5f8256dac550",
        "type": "Schedule"
    }
}

```


### Possible error responses


```http
HTTP/1.1 400 Bad Request
Allow: GET, POST, HEAD, OPTIONS
Content-Length: 136
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:41:13 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "Deposit amount should be positive number",
            "source": {
                "pointer": "/data/attributes/deposit_amount"
            },
            "status": "400"
        }
    ]
}

```


```http

HTTP/1.1 400 Bad Request
Allow: GET, POST, HEAD, OPTIONS
Content-Length: 124
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:45:02 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "Start date cannot be in the past",
            "source": {
                "pointer": "/data/attributes/start_date"
            },
            "status": "400"
        }
    ]
}

```


```http

HTTP/1.1 400 Bad Request
Allow: GET, POST, HEAD, OPTIONS
Content-Length: 125
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 23:45:55 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "errors": [
        {
            "detail": "\"monthlyddd\" is not a valid choice.",
            "source": {
                "pointer": "/data/attributes/period"
            },
            "status": "400"
        }
    ]
}

```


## Edit schedule (change schedule status + number of payments)
TBD

## Delete schedule
TBD

## List schedules
TBD
