from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from cart.models import Cart, Coupon, AppliedCoupon

class Command(BaseCommand):
    help = 'Applies a coupon to a cart'

    def add_arguments(self, parser):
        parser.add_argument('cart_id', type=int, help='ID of the cart')
        parser.add_argument('coupon_code', type=str, help='Coupon code to apply')

    def handle(self, *args, **options):
        cart_id = options['cart_id']
        coupon_code = options['coupon_code'].upper()
        
        try:
            # Get the cart and coupon
            cart = Cart.objects.get(id=cart_id)
            coupon = Coupon.objects.get(code__iexact=coupon_code, is_active=True)
            
            # Validate the coupon
            is_valid, message = coupon.is_valid(cart.user, float(cart.subtotal_price))
            if not is_valid:
                raise CommandError(f'Cannot apply coupon: {message}')
            
            # Remove any existing coupon
            AppliedCoupon.objects.filter(cart=cart).delete()
            
            # Calculate and apply the discount
            discount = coupon.calculate_discount(cart.subtotal_price)
            AppliedCoupon.objects.create(
                coupon=coupon,
                user=cart.user,
                cart=cart,
                discount_amount=discount
            )
            
            # Update coupon usage
            coupon.times_used += 1
            coupon.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully applied coupon {coupon.code} to cart #{cart.id}. '
                    f'Discount: ₹{discount:.2f} | New Total: ₹{cart.total_price:.2f}'
                )
            )
            
        except Cart.DoesNotExist:
            raise CommandError(f'Cart with ID {cart_id} does not exist')
        except Coupon.DoesNotExist:
            raise CommandError(f'Coupon with code {coupon_code} does not exist or is not active')
        except Exception as e:
            raise CommandError(f'Error applying coupon: {str(e)}')
