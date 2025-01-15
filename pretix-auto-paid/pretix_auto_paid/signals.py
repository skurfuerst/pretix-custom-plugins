import logging
from django.dispatch import receiver
from pretix.base.signals import order_placed
from pretix.base.models import OrderPayment
from django.utils.timezone import now

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
                info={}
            )

            # Confirm payment with send_mail=False to suppress notification
            payment.confirm(send_mail=False)

            logger.info(f"Successfully auto-marked order {order.code} as paid")

    except Exception as e:
        # Log the error but don't raise it to avoid breaking order creation
        logger.error(f"Failed to auto-mark order {order.code} as paid: {str(e)}")
