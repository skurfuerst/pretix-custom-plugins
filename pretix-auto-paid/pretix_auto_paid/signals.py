import logging
import json
from django.dispatch import receiver
from pretix.base.signals import order_placed, order_canceled
from pretix.base.models import OrderPayment, OrderFee, Order
from django.utils.timezone import now
from django.db import transaction


logger = logging.getLogger(__name__)

@receiver(order_placed, dispatch_uid="auto_mark_paid")
def auto_mark_paid(sender, order, **kwargs):
    """
    Signal receiver that marks an order as paid immediately after it is placed

    Args:
        sender: The event that the order belongs to
        order: The order object that was just created
    """
    try:
        if order.status == 'n':  # Only handle pending orders
            payment = OrderPayment.objects.create(
                order=order,
                state=OrderPayment.PAYMENT_STATE_PENDING,
                amount=order.total,
                provider='manual',
                info=json.dumps({
                    'auto_created': True,  # Mark this payment as auto-created
                    'created_by': 'pretix_auto_paid'
                })
            )

            # Confirm payment with send_mail=False to suppress notification
            payment.confirm(send_mail=False)
            order.create_transactions()
            logger.info(f"Successfully auto-marked order {order.code} as paid")

    except Exception as e:
        # Log the error but don't raise it to avoid breaking order creation
        logger.error(f"Failed to auto-mark order {order.code} as paid: {str(e)}")


@receiver(order_canceled, dispatch_uid="remove_cancellation_fee")
def remove_cancellation_fee(sender, order, **kwargs):
    """
    Signal receiver that removes any cancellation fees after order cancellation
    """
    with transaction.atomic():
        # Find and delete any cancellation fees
        cancellation_fees = OrderFee.objects.filter(
            order=order,
            fee_type=OrderFee.FEE_TYPE_CANCELLATION
        )

        if cancellation_fees.exists():
            # Delete the fees
            cancellation_fees.delete()

            # Update order total
            order.total = sum(
                p.price for p in order.positions.all() if not p.canceled
            ) + sum(
                f.value for f in order.fees.all() if not f.canceled
            )
            # Set status to cancelled (not paid with cancellation fee)
            order.status = Order.STATUS_CANCELED
            order.save(update_fields=['total', 'status'])

            # Remove only auto-created manual payments
            for payment in order.payments.filter(provider='manual'):
                try:
                    info = json.loads(payment.info) if payment.info else {}
                    if info.get('auto_created') and info.get('created_by') == 'pretix_auto_paid':
                        payment.delete()
                        logger.info(f"Removed auto-created payment for order {order.code}")
                except json.JSONDecodeError:
                    continue  # Skip if payment info is not valid JSON

            # Create the required transactions
            order.create_transactions()

            logger.info(f"Successfully removed cancellation fee for order {order.code}")

