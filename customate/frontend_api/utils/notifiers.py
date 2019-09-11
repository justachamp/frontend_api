# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from frontend_api.tasks import send_notification_email, send_notification_sms
from django.template.loader import render_to_string


class EmailNotifier:
    """
    Set of functions for sending of emails with boto3.
    Able notify about:
        - balance changing
        - transaction failing
    """

    def __init__(self, funds_sender_email, amount, action,
                 funds_recipient_email=None, payment_id=None):
        self.domain_sender = settings.AWS_SES_NOTIFICATIONS_GOCUSTOMATE_SENDER
        self.funds_sender_email = funds_sender_email
        self.funds_recipient_email = funds_recipient_email
        self.payment_id = payment_id
        self.amount = amount
        self.action = action

    @property
    def balance_changed_message_for_sender(self) -> str:
        """
        A message that should get user which sent money.
        :return:
        """
        message = {
            "Message": {
                'Body': {
                    'Html': {
                        'Charset': 'UTF-8',
                        'Data': render_to_string(
                                "notifications/email_senders_balance_updated.html",
                                context={"header": "Dummy template", "data": "Test info block."}
                        ),
                    },
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': "Gocustomate test notification.",
                    },
                }
        }
        return message

    @property
    def balance_changed_message_for_recipient(self) -> str:
        """
        A message that should get recipient of money.
        :return:
        """
        message = {
            "Message": {
                'Body': {
                    'Html': {
                        'Charset': 'UTF-8',
                        'Data': render_to_string(
                                "notifications/email_recipients_balance_updated.html",
                                context={"header": "Dummy template", "data": "Test info block."}
                        ),
                    },
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': "Gocustomate test notification.",
                    },
                }
        }
        return message

    @property
    def transaction_failed_message_for_sender(self) -> str:
        """
        A message that should get user which created transaction
        :return:
        """
        message = {
            "Message": {
                'Body': {
                    'Html': {
                        'Charset': 'UTF-8',
                        'Data': render_to_string(
                                "notifications/email_transaction_failed.html",
                                context={"header": "Dummy template", "data": "Test info block."}
                        ),
                    },
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': "Gocustomate test notification.",
                    },
                }
        }
        return message

    def balance_changed(self) -> None:
        """
        Sends emails to users about balance changes.
        :return:
        """
        # Send appropriate email for funds sender
        kwargs = {
            "Source": self.domain_sender,
            "Destination": {
                "ToAddresses": [self.funds_sender_email]
            }
        }
        message = self.balance_changed_message_for_sender
        send_notification_email.delay(kwargs, message)
        # Send appropriate email for funds recipient
        kwargs = {
            "Source": self.domain_sender,
            "Destination": {
                "ToAddresses": [self.funds_recipient_email]
            }
        }
        message = self.balance_changed_message_for_recipient
        send_notification_email.delay(kwargs, message)

    def transaction_failed(self) -> None:
        """
        Sends email to sender if transaction has failed.
        :return:
        """
        kwargs = {
            "Source": self.domain_sender,
            "Destination": {
                "ToAddresses": [self.funds_sender_email]
            }
        }
        message = self.transaction_failed_message_for_sender
        send_notification_email.delay(kwargs, message)

    def send_message(self) -> None:
        getattr(self, self.action)()


class SMSNotifier:
    """
    Set of functions for sending smses with boto3.
    Able notify about:
        - balance changing
        - transaction failing
    """

    def __init__(self, funds_sender_phone, amount, action,
                 funds_recipient_phone=None, payment_id=None):
        self.funds_sender_phone = funds_sender_phone
        self.funds_recipient_phone = funds_recipient_phone
        self.payment_id = payment_id
        self.amount = amount
        self.action = action

    @property
    def balance_changed_message_for_sender(self) -> str:
        """
        A message that should get user which sent money.
        :return:
        """
        return "balance changed message for sender"

    @property
    def balance_changed_message_for_recipient(self) -> str:
        """
        A message that should get recipient of money.
        :return:
        """
        return "balance changed message for recipient"

    @property
    def transaction_failed_message_for_sender(self) -> str:
        """
        A message that should get user which created transaction.
        :return:
        """
        return "Your payment has failed."

    def balance_changed(self) -> None:
        """
        Sms notification about balance changes
        :return:
        """
        # Send sms to funds sender
        senders_data = {"PhoneNumber": self.funds_sender_phone,
                        "Message": self.balance_changed_message_for_sender}
        send_notification_sms.delay(kwargs=senders_data)
        # Send sms to funds recipient
        recipients_data = {"PhoneNumber": self.funds_recipient_phone,
                           "Message": self.balance_changed_message_for_recipient}
        send_notification_sms.delay(kwargs=recipients_data)

    def transaction_failed(self) -> None:
        """
        Sms notification if transaction has failed
        :return:
        """
        senders_data = {"PhoneNumber": self.funds_sender_phone,
                        "Message": self.transaction_failed_message_for_sender}
        send_notification_sms.delay(kwargs=senders_data)

    def send_message(self) -> None:
        getattr(self, self.action)()
