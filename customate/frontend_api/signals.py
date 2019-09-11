# -*- coding: utf-8 -*-
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.fields import PaymentStatusType
from frontend_api.models.schedule import SchedulePayments

from frontend_api.utils.notifiers import EmailNotifier, SMSNotifier


@receiver(post_save, sender=SchedulePayments)
def transaction_failed(sender, instance, **kwargs) -> None:
    """
    Sends email and sms notifications for sender if
        transaction has failed.
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    action = "transaction_failed"
    if instance.payment_status == PaymentStatusType.FAILED:
        schedule = instance.schedule
        # Send email notification
        email_notificator = EmailNotifier(funds_sender_email=schedule.origin_user.email,
                                          payment_id=instance.payment_id,
                                          amount=instance.original_amount,
                                          action=action)
        email_notificator.send_message()
        # Send sms notification
        sms_notification = SMSNotifier(funds_sender_phone=schedule.origin_user.phone_number.as_e164,
                                       payment_id=instance.payment_id,
                                       amount=instance.original_amount,
                                       action=action)
        sms_notification.send_message()


@receiver(post_save, sender=SchedulePayments)
def balance_changed(sender, instance, **kwargs) -> None:
    """
    Sends email and sms notifications for both sender and recipient if
        their balance has updated.
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    action = "balance_changed"
    if instance.payment_status == PaymentStatusType.SUCCESS:
        schedule = instance.schedule
        # Send email notification
        email_notificator = EmailNotifier(funds_sender_email=schedule.recipient_user.email,
                                          funds_recipient_email=schedule.origin_user.email,
                                          amount=instance.original_amount,
                                          action=action)
        email_notificator.send_message()
        # Send sms notification
        sms_notification = SMSNotifier(funds_sender_phone=schedule.origin_user.phone_number.as_e164,
                                       funds_recipient_phone=schedule.recipient_user.phone_number.as_e164,
                                       amount=instance.original_amount,
                                       action=action)
        sms_notification.send_message()
