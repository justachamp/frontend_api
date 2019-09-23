# Notifications documents API

## What
Store choosen kinds of notifications in database.

**Endpoint**: ```/api/v1/profiles/<user-id>/```

**Parameters**:

* _notify_by_email_, required. Boolean
* _notify_by_phone_, required. Boolean



## Update notification settings

```http
PATCH /api/v1/profiles/<user-id:string>/ 
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
Allow: GET, PATCH, HEAD, OPTIONS
Content-Length: 2154
Content-Type: application/vnd.api+json
Date: Tue, 16 Jul 2019 22:37:05 GMT
Server: WSGIServer/0.2 CPython/3.7.2
Vary: Accept, Cookie, Origin
X-Frame-Options: SAMEORIGIN

{"data":
	{
		"type": "ProfileView",
		"id": "6a10b492-df0e-4487-a9c0-91d2541d3c1a",
		"attributes":
			{
				"user":
				{	
					"notify_by_email": true,
					"notify_by_phone": true
				}
			}
	}
}
```
```
{
    "data": {
        "type": "ProfileView",
        "id": "6a10b492-df0e-4487-a9c0-91d2541d3c1a",
        "attributes": {
            "user": {
                "url": "http://localhost:8000/api/v1/users/6a10b492-df0e-4487-a9c0-91d2541d3c1a/",
                "role": "owner",
                "status": "active",
                "username": "api_test@mailinator.com",
                "first_name": "Bruce",
                "last_name": "Stewart",
                "middle_name": "Mcleod",
                "phone_number": "+447787430205",
                "phone_number_verified": false,
                "email_verified": true,
                "contact_info_once_verified": true,
                "is_verified": false,
                "is_superuser": false,
                "birth_date": "1974-01-24",
                "email": "api_test@mailinator.com",
                "address": {
                    "type": "Address",
                    "id": "74c5ee9a-06f1-43e4-944d-f8ffe327c559"
                },
                "account": {
                    "type": "UserAccount",
                    "id": "c2e84b33-40c3-4d24-8242-acc9f256ea70"
                },
                "title": "mr",
                "gender": "male",
                "country_of_birth": "ZW",
                "mother_maiden_name": "mckenna",
                "passport_number": "",
                "passport_date_expiry": "2021-05-23",
                "passport_country_origin": "IE",
                "notify_by_email": true,
                "notify_by_phone": true
            },
            "address": {
                "url": "http://localhost:8000/api/v1/addresses/74c5ee9a-06f1-43e4-944d-f8ffe327c559/",
                "address": "14 Portland House, Station Road",
                "country": "GB",
                "address_line_1": "14 Portland House",
                "address_line_2": "Station Road",
                "address_line_3": "",
                "city": "Gerrards Cross",
                "locality": "Buckinghamshire",
                "postcode": "SL9 8FQ",
                "user": {
                    "type": "User",
                    "id": "6a10b492-df0e-4487-a9c0-91d2541d3c1a"
                }
            },
            "account": {
                "url": "http://localhost:8000/api/v1/accounts/c2e84b33-40c3-4d24-8242-acc9f256ea70/",
                "account_type": "personal",
                "payment_account_id": "8438292c-d4b2-481c-928d-39eccabd34be",
                "gbg_authentication_count": 1,
                "is_verified": true,
                "can_be_verified": false,
                "verification_status": "Pass",
                "position": null,
                "user": {
                    "type": "User",
                    "id": "6a10b492-df0e-4487-a9c0-91d2541d3c1a"
                },
                "company": null,
                "sub_user_accounts": [
                    {
                        "type": "SubUserAccount",
                        "id": "506b8dac-a72a-49a8-b4f2-4eb3c44e8010"
                    },
                    {
                        "type": "SubUserAccount",
                        "id": "5f56006a-97e2-474b-a5f3-92d9f5b0b583"
                    },
                    {
                        "type": "SubUserAccount",
                        "id": "565053b6-2086-4ba5-be29-08d3ca59577f"
                    },
                    {
                        "type": "SubUserAccount",
                        "id": "c467dd80-0f9d-4750-ab84-7a7b82903730"
                    }
                ],
                "payment_account": {
                    "type": "payment_accounts",
                    "id": "8438292c-d4b2-481c-928d-39eccabd34be"
                },
                "driver_licence_number": null,
                "driver_licence_postcode": null,
                "driver_licence_issue_date": null
            }
        }
    }
}
```
### Possible error responses

```http

HTTP/1.1 403 Forbidden
Allow: GET, PATCH, HEAD, OPTIONS
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
Allow: GET, PATCH, HEAD, OPTIONS
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





