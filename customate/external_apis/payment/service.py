from os import environ
import logging
from datetime import datetime
import requests
from uuid import UUID, uuid4

from core.fields import PaymentStatusType, Currency, PayeeType

from external_apis.payment.models import PaymentResult, PayeeDetails
from external_apis.payment.models import FundingSourceDetails, FundingSourceType
from external_apis.payment.models import WalletDetails

logger = logging.getLogger(__name__)

SERVICE = 'PaymentAPI'
BASE_URL = environ['PAYMENT_API_URL']  # http://localhost:8080/
BASE_URL = "%s/" % BASE_URL if not BASE_URL.endswith("/") else BASE_URL


class PaymentApiError(requests.HTTPError):
    """
    Explicitly thrown if PaymentAPI returns some validation(HTTP 400) errors
    """

    def __init__(self, *args, **kwargs):
        self.json_response = kwargs.pop('json_response', None)
        self.error_detail = self.json_response["errors"][0]["detail"] if self.json_response else None
        super().__init__(*args, **kwargs)

    def __str__(self):
        return "detail=%s, response=%r" % (self.error_detail, self.json_response)


class SchedulePayments:
    """
    Schedule Payments Management
    https://customatepayment.docs.apiary.io/#reference/0/schedule-payments-management
    """

    @staticmethod
    def cancel_schedule_payments(schedule_id: UUID):
        r = requests.delete("{base_url}schedule_payments/{schedule_id}".format(
            base_url=BASE_URL,
            schedule_id=str(schedule_id)
        ), headers={
            "Content-Type": "application/json"
        })

        if r.status_code == requests.codes.bad_request:
            raise PaymentApiError(json_response=r.json())
        else:
            r.raise_for_status()


class Payments:
    """
    API docs:
    https://customatepayment.docs.apiary.io/#reference/0/payment-management
    """

    @staticmethod
    def force_payment(user_id: UUID, original_payment_id: UUID) -> (UUID, PaymentStatusType):
        """
        Returns (payment_id, status)

        :param user_id:
        :param original_payment_id:
        :return:
        """
        payload = {
            "data": {
                "type": "forced_payments",
                "attributes": {
                    "userId": str(user_id),
                    "originalPaymentId": str(original_payment_id)
                },
                "relationships": {}
            }
        }

        r = requests.post("{base_url}forced_payments/".format(base_url=BASE_URL), json=payload)
        if r.status_code == requests.codes.bad_request:
            raise PaymentApiError(json_response=r.json())
        else:
            r.raise_for_status()

        res = r.json()
        # {
        #   "data": {
        #     "type": "forced_payments",
        #     "id": "ae1d1bc8-c2d0-481a-9fc2-dbddad697071",
        #     "attributes": {
        #       "userId": "164552d4-8bf1-44f9-aacd-4a670936df65",
        #       "originalPaymentId": "7abb6f11-493e-4b1b-a8aa-2bdb2de9c125"
        #       "newPaymentId": "bcf1dee2-8f80-4fd3-82f5-4f08d2d2e6d3",
        #       "newPaymentStatus": "PENDING"
        #     },
        #     "relationships": {}
        #   }
        # }
        logger.debug("res=%r" % res)
        payment_id = UUID(res["data"]["attributes"]["newPaymentId"])
        status = PaymentStatusType(res["data"]["attributes"]["newPaymentStatus"])
        return payment_id, status

    @staticmethod
    def create_payment(user_id: UUID, payment_account_id: UUID, schedule_id: UUID,
                       currency: Currency, amount: int, description: str,
                       payee_id: UUID, funding_source_id: UUID,
                       payment_id: UUID = None, parent_payment_id: UUID = None, execution_date: datetime = None):
        """
        Initiates payment.

        https://customatepayment.docs.apiary.io/#reference/0/payment-management/create-payment

        :param payment_id:
        :param user_id:
        :param payment_account_id:
        :param schedule_id:
        :param currency:
        :param amount:
        :param description:
        :param payee_id:
        :param funding_source_id:
        :param parent_payment_id:
        :param execution_date:
        :return:
        """

        payload = {
            "data": {
                "type": "payments",
                "id": str(payment_id) if payment_id else str(uuid4()),
                "attributes": {
                    "userId": str(user_id),
                    "currency": currency.value,
                    "scheduleId": str(schedule_id),
                    "data": {
                        "amount": amount,
                        "description": description,
                        "parentPaymentId": str(parent_payment_id) if parent_payment_id else None,
                        "executionDate": datetime.timestamp(execution_date) if execution_date else None
                    }
                },
                "relationships": {
                    "account": {
                        "data": {
                            "type": "accounts",
                            "id": str(payment_account_id)
                        }
                    },
                    "origin": {
                        "data": {
                            "type": "funding_sources",
                            "id": str(funding_source_id)
                        }
                    },
                    "recipient": {
                        "data": {
                            "type": "payees",
                            "id": str(payee_id)
                        }
                    }
                }
            }
        }
        r = requests.post("{base_url}payments/".format(base_url=BASE_URL), json=payload)
        if r.status_code == requests.codes.bad_request:
            raise PaymentApiError(json_response=r.json())
        else:
            r.raise_for_status()

        res = r.json()
        logger.debug("res=%r" % res)

        # {
        #   "data": {
        #     "type": "payments",
        #     "id": "ae1d1bc8-c2d0-481a-9fc2-dbddad697071",
        #     "attributes": {
        #       "active": 1,
        #       "scheduleId": "bcf1dee2-8f80-4fd3-82f5-4f08d2d2e6d3",
        #       "creationDate": 1557321296633,
        #       "currency": "EUR",
        #       "data": {
        #         "amount": 100,
        #         "origin": {
        #           "paymentIndexNumber": 1
        #         },
        #         "version": 1,
        #         "settings": {
        #           "fee": {},
        #           "tax": {}
        #         }
        #       },
        #       "scenario": "OutgoingInternal",
        #       "status": "PENDING",
        #       "updateDate": 1557321296680,
        #       "userId": "c2688fb8-a987-47ef-9a46-d8a9e3165c45"
        #     },
        #     "relationships": {
        #       "account": {
        #         "data": {
        #           "type": "accounts",
        #           "id": "4c6aa64d-8361-48e4-ba2f-d2d2536ddb93"
        #         }
        #       },
        #       "origin": {
        #         "data": {
        #           "type": "funding_sources",
        #           "id": "e40c61db-c3a5-4486-814f-c700948a5dc4"
        #         }
        #       },
        #       "recipient": {
        #         "data": {
        #           "type": "payees",
        #           "id": "6a997a63-18f0-4c7a-b2f3-7bb6b1545736"
        #         }
        #       },
        #       "transactions": {
        #         "data": []
        #       }
        #     }
        #   }
        # }
        return PaymentResult(
            id=UUID(res["data"]["id"]),
            status=PaymentStatusType(res["data"]["attributes"]["status"])
        )


class Payee:
    """
    Payee Management.
    Payee types: WALLET, BANK_ACCOUNT

    https://customatepayment.docs.apiary.io/#reference/0/payee-management
    """

    @staticmethod
    def get_payee_details(payee_id: UUID) -> PayeeDetails:
        """
        Get details about specific Payee (money recipient)
        :param self:
        :param payee_id:
        :return:
        """

        r = requests.get("{base_url}payees/{payee_id}".format(
            base_url=BASE_URL,
            payee_id=str(payee_id)
        ), headers={
            "Content-Type": "application/json"
        })

        if r.status_code == requests.codes.bad_request:
            raise PaymentApiError(json_response=r.json())
        else:
            r.raise_for_status()

        # {
        #   "data": {
        #     "id": "1119e2b2-0641-48bf-a9ce-55020b745b61",
        #     "type": "payees",
        #     "attributes": {
        #       "title": "Test Payee",
        #       "type": "BANK_ACCOUNT",
        #       "active": 1,
        #       "currency": "EUR",
        #       "data": {
        #         "recipient": {
        #           "fullName": "Gilbert Mendoza",
        #           "email": "fisher.octua@email.com",
        #           "address": {
        #             "postcode": "EC3N 2EX",
        #             "city": "London",
        #             "address_line_1": "Dawson House 5 Jewry Street",
        #             "address_line_2": "",
        #             "country": "GB"
        #           }
        #         },
        #         "bank": {
        #           "name": "SAXO PAYMENTS A/S",
        #           "address": {
        #             "postcode": "EC3N 2EX",
        #             "city": "London",
        #             "address_line_1": "Dawson House 5 Jewry Street",
        #             "address_line_2": "",
        #             "country": "GB"
        #           }
        #         },
        #         "account": {
        #           "bic": "SAPYGB2L",
        #           "iban": "DE85202208000090025795"
        #         }
        #       }
        #     },
        #     "relationships": {
        #       "account": {
        #         "data": {
        #           "type": "accounts",
        #           "id": "9479e3b3-0641-48bf-a9ce-55020b745b61"
        #         }
        #       }
        #     }
        #   }
        # }
        res = r.json()
        logger.debug("res=%r" % res)

        return PayeeDetails(
            id=UUID(res["data"]["id"]),
            title=res["data"]["attributes"]["title"],
            type=PayeeType(res["data"]["attributes"]["type"]),
            iban=res['data']['attributes']['data']['account']['iban'],
            recipient_name=res['data']['attributes']['data']['recipient']['fullName'],
            recipient_email=res['data']['attributes']['data']['recipient']['email'],
            payment_account_id=UUID(res['data']['relationships']['account']['data']['id'])
        )


class FundingSource:
    """
    Funding source statuses: UNVERIFIED, PENDING, VALID, INVALID.
    Funding source types: WALLET, DIRECT_DEBIT, CREDIT_CARD.

    https://customatepayment.docs.apiary.io/#reference/0/funding-source-management
    """

    @staticmethod
    def get_funding_source_details(fs_id: UUID) -> FundingSourceDetails:
        """
        Get details about funding source
        :param fs_id:
        :return:
        """

        r = requests.get("{base_url}funding_sources/{fs_id}".format(
            base_url=BASE_URL,
            fs_id=str(fs_id)
        ), headers={
            "Content-Type": "application/json"
        })

        if r.status_code == requests.codes.bad_request:
            raise PaymentApiError(json_response=r.json())
        else:
            r.raise_for_status()

        # {
        #   "data": {
        #     "type": "funding_sources",
        #     "id": "223c7717-0655-4bde-9a3b-98be47d6abe7",
        #     "attributes": {
        #       "active": 1,
        #       "creationDate": 1544029100400,
        #       "currency": "EUR",
        #       "data": {
        #         "walletId": "5a382426-cd68-485e-8ed7-81e6f65efd1b",
        #         "iban": "084caae1-d71c-48a3-bdfc-9c76326c6b1e",
        #         "bank": {
        #           "zip": "20095",
        #           "city": "Hamburg",
        #           "name": "SAXO PAYMENTS",
        #           "address": {
        #             "city": "London",
        #             "country": "GB",
        #             "postcode": "EC3N 2EX",
        #             "address_line_1": "Dawson House 5 Jewry Street",
        #             "address_line_2": ""
        #           },
        #           "country": "Germany"
        #         },
        #         "account": {
        #           "bic": "SXPYDEHH",
        #           "sortCode": null,
        #           "accountNumber": null
        #         }
        #       },
        #       "title": "Test Funding Source",
        #       "type": "WALLET",
        #       "status": "VALID",
        #       "validationMessage": null
        #     },
        #     "relationships": {
        #       "account": {
        #         "data": {
        #           "type": "accounts",
        #           "id": "dedf7a91-f113-4977-a02b-440ed766a962"
        #         }
        #       }
        #     }
        #   }
        # }
        res = r.json()
        logger.debug("res=%r" % res)
        return FundingSourceDetails(
            id=UUID(res["data"]["id"]),
            type=FundingSourceType(res["data"]["attributes"]["type"]),
            currency=Currency(res["data"]["attributes"]["currency"]),
            payment_account_id=UUID(res['data']['relationships']['account']['data']['id'])
        )


class Wallets:
    """
    Wallet management
    https://customatepayment.docs.apiary.io/#reference/0/wallet-management/
    """

    @staticmethod
    def create(currency: Currency, payment_account_id: UUID) -> WalletDetails:
        """
        Virtual wallet is a wallet that doesn't have a real VIBAN (from the list provided by bank) attached to it,
        instead we generate and set random UUID as iban field. Also make sure that you fill related account in relationships section,
        such virtual wallet should be assigned during creation.

        :param currency:
        :param payment_account_id:
        :return:
        """
        payload = {
            "data": {
                "type": "wallets",
                "attributes": {
                    "currency": str(currency.value)
                },
                "relationships": {
                    "account": {
                        "data": {
                            "type": "accounts",
                            "id": str(payment_account_id)
                        }
                    }
                }
            }
        }
        r = requests.post("{base_url}wallets/".format(base_url=BASE_URL), json=payload)
        if r.status_code == requests.codes.bad_request:
            raise PaymentApiError(json_response=r.json())
        else:
            r.raise_for_status()

        # {
        #   "data": {
        #     "type": "wallets",
        #     "id": "16d14ddb-8c9d-49ef-bdda-21a03c200769",
        #     "attributes": {
        #       "active": 1,
        #       "balance": 0,
        #       "creationDate": 1573490485815,
        #       "currency": "EUR",
        #       "data": null,
        #       "iban": "1f283a9e-5de2-4683-982c-e793576dd0e9",
        #       "ibanGeneralPart": "576dd0e9",
        #       "isVirtual": 1,
        #       "usedDate": null
        #     },
        #     "relationships": {
        #       "account": {
        #         "data": {
        #           "type": "accounts",
        #           "id": "6e977bac-389b-4f5b-811f-7bff694de1cc"
        #         }
        #       },
        #       "fundingSource": {
        #         "data": {
        #           "type": "funding_sources",
        #           "id": "41bca7e4-12a1-4e63-a2dd-261930cb5e98"
        #         }
        #       },
        #       "payee": {
        #         "data": {
        #           "type": "payees",
        #           "id": "0e304cb4-b5b6-4062-b442-e7a5b9f056df"
        #         }
        #       }
        #     }
        #   }
        # }
        res = r.json()
        logger.debug("res=%r" % res)

        return WalletDetails(
            id=UUID(res["data"]["id"]),
            currency=Currency(res["data"]["attributes"]["currency"]),
            iban=res["data"]["attributes"]["iban"],
            balance=int(res["data"]["attributes"]["balance"]),
            is_virtual=bool(int(res["data"]["attributes"]["isVirtual"])),
            payment_account_id=UUID(res['data']['relationships']['account']['data']['id']),
            funding_source_id=UUID(res['data']['relationships']['fundingSource']['data']['id']),
            payee_id=UUID(res['data']['relationships']['payee']['data']['id']),
        )