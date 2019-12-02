# Escrow API

## What
Create payments through third-party trusted intermediary.

**Endpoint**: ```/api/v1/escrows/```

**Parameters**:

* _name_, required. Human-readable name of schedule
* _status_, optional. Currently, can be one of `open, closed, overdue, cancelled`
* _currency_, required. 3-letter ISO code of corresponding currency
* _additional_information_, optional. Any textual information
* _payee_id_, required. UUID, identifies who should receive the money
* _funding_source_id_, required. UUID, identifies the source of money (see Funding Source API)
* _initial_amount_, required. Positive integer, identifies amount of money to be initially deposited
* _documents_, optional. Array of objects:
    * _slug_, String. Slug of uploaded filename
    * _filename_, String. Name of uploaded file
    * _id_, UUID. Identifier taken from server side
    * _delete_, Boolean. The value taken from server side.


## Create new schedule


```http
POST /api/v1/escrows/ HTTP/1.1
ACCESSTOKEN: eyJraWQiOiJNZ2dVVnNzdjY2QUdmRkdZaEY4a1dJVUl0bFdFeFpwcnNKNm51WmZMazFRPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJjNmE4YTUwMS1jMzIwLTQ2ZTktYjJmZi1kNGUyZDE1NGNkZWQiLCJldmVudF9pZCI6IjQ4NmNkNDFkLWE3MWYtNGUwMy05NGNiLTM4MTJjODk2NjllMCIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoiYXdzLmNvZ25pdG8uc2lnbmluLnVzZXIuYWRtaW4iLCJhdXRoX3RpbWUiOjE1NzUyOTQzOTIsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5ldS13ZXN0LTIuYW1hem9uYXdzLmNvbVwvZXUtd2VzdC0yX2J6U2ZnQ3pYSiIsImV4cCI6MTU3NTI5Nzk5MiwiaWF0IjoxNTc1Mjk0MzkyLCJqdGkiOiI3OGNhMGVhMy0yMmYyLTRkOTMtYTU0Yy0xY2ZjNTBkODBlODQiLCJjbGllbnRfaWQiOiIxdDkzYm5tajFsbTY0dWQyb3ZuaTExdmZrNiIsInVzZXJuYW1lIjoiYzZhOGE1MDEtYzMyMC00NmU5LWIyZmYtZDRlMmQxNTRjZGVkIn0.eR3jAuGurKIwl4CZz9NPTDN-wvdkbX-A38yR6LhAOCDfYHdosuZgdPssD7JoPL6j3Co-sth8D9r08K5MGNmEaTDb5ZPIlny4712imtizCfJp7cmaZXPTB0aSXDw7-V4korw-oUs94MSI0CHAYfoSN0JzCNepqDIRLin19WQvFUvsRbMY-mdemY6hASe1g2Jpu8fP3-G3LK_3ajF6QV03sXWER9J22EbY4efXkabMyGzqLeQ9uiMF57s1GxiYWEDKf3zED18P5cCmSoNfqoZp7GHQ203WXIHYUXzx1Xh8xKVSlq9Bin0EY23xsu1wqu8d8mKV4UgaXCum7VbPLC_tSQ
Accept: application/json, */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
Content-Length: 519
Content-Type: application/vnd.api+json
Host: localhost:8000
IDTOKEN: eyJraWQiOiJpc2J6dmY0REpaNjM1UjI2dENhd1l2bVhRR09FUDJzdFY5aXhDd3NvZ2RRPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJjNmE4YTUwMS1jMzIwLTQ2ZTktYjJmZi1kNGUyZDE1NGNkZWQiLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiaXNzIjoiaHR0cHM6XC9cL2NvZ25pdG8taWRwLmV1LXdlc3QtMi5hbWF6b25hd3MuY29tXC9ldS13ZXN0LTJfYnpTZmdDelhKIiwicGhvbmVfbnVtYmVyX3ZlcmlmaWVkIjpmYWxzZSwiY29nbml0bzp1c2VybmFtZSI6ImM2YThhNTAxLWMzMjAtNDZlOS1iMmZmLWQ0ZTJkMTU0Y2RlZCIsImdpdmVuX25hbWUiOiJCcnVjZSIsImF1ZCI6IjF0OTNibm1qMWxtNjR1ZDJvdm5pMTF2Zms2IiwiY3VzdG9tOmFjY291bnRfdHlwZSI6Ik93bmVyIiwiZXZlbnRfaWQiOiI0ODZjZDQxZC1hNzFmLTRlMDMtOTRjYi0zODEyYzg5NjY5ZTAiLCJ0b2tlbl91c2UiOiJpZCIsImF1dGhfdGltZSI6MTU3NTI5NDM5MiwicGhvbmVfbnVtYmVyIjoiKzQ0NzM2NTAyMjYxMiIsImV4cCI6MTU3NTI5Nzk5MiwiaWF0IjoxNTc1Mjk0MzkyLCJmYW1pbHlfbmFtZSI6IlN0ZXdhcnQiLCJlbWFpbCI6Im9sZWcucnlhYmluc2tpeUBwb3N0aW5kdXN0cmlhLmNvbSJ9.EMvFgIDq6gsztgi1vJzmmFHg6lb-b6r_MH4VgKTD6AnISZGLBbx3g1UqOjIQQ-9BedOC6ZjwnBjTvilBiuOpN6T7VkSdrHn5A5s6XeLEuIZtIrXnWQZBJj92cdka1-N4_4ZQAJhHAO54QQMo2v8s8-_EsAwW7A_sFLudVvxjLBgfuQ3dJ6syaWXMmKjF0wPVG21-CWwW7CwfiUkDNsCqc5JktIFL9ksUa0JOrlBQq63mgw7FPliKItKTkVBvEOwt3mgUN4o0bmygNRges5tuDunCCER3qqfhynRD8IaFdMxkxEi85BkyOdV6bP5BsKQhP4cx0Vbwxybwebh8DELLSQ
User-Agent: HTTPie/1.0.2

{
    "data": {
        "attributes": {
            "additional_information": "Some random description",
            "currency": "GBP",
            "funder_user_id": "c6a8a501-c320-46e9-b2ff-d4e2d154cded",
            "funding_deadline": "2019-08-08",
            "funding_source_id": "5c490878-b2ad-4ab6-99dd-6d2726c5bc97",
            "initial_amount": "100",
            "name": "My test escrow",
            "payee_id": "c5a239a6-7998-4a75-a7f9-ec7e24e1a356",
            "recipient_user_id": "59d66f57-6340-48e3-921b-cbd6918a7bd9"
        },
        "type": "Escrow"
    }
}

```



```http
HTTP/1.1 201 Created
Allow: GET, POST, HEAD, OPTIONS
Content-Length: 583
Content-Type: application/vnd.api+json
Date: Mon, 02 Dec 2019 13:53:55 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{
    "data": {
        "attributes": {
            "additional_information": "Some random description",
            "currency": "GBP",
            "documents": null,
            "funder_user_id": "c6a8a501-c320-46e9-b2ff-d4e2d154cded",
            "funding_deadline": "2019-08-08",
            "initial_amount": 100,
            "name": "My test escrow",
            "payee_iban": null,
            "payee_id": "c5a239a6-7998-4a75-a7f9-ec7e24e1a356",
            "payee_recipient_email": null,
            "payee_recipient_name": null,
            "payee_title": null,
            "payee_type": null,
            "recipient_user_id": "59d66f57-6340-48e3-921b-cbd6918a7bd9",
            "status": "pending",
            "transit_funding_source_id": null,
            "transit_payee_id": null,
            "wallet_id": null
        },
        "id": null,
        "type": "Escrow"
    }
}

```