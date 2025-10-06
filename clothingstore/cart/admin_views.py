from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils import timezone
from .models import Cart, Coupon, AppliedCoupon
from django.shortcuts import render

@staff_member_required
def apply_coupon_admin(request):
    if request.method == 'POST':
        cart_id = request.POST.get('cart_id')
        coupon_code = request.POST.get('coupon_code', '').strip().upper()
        
        if not cart_id or not coupon_code:
            messages.error(request, 'Cart ID and Coupon Code are required')
            return redirect('admin:cart_cart_changelist')
            
        try:
            cart = Cart.objects.get(id=cart_id)
            coupon = Coupon.objects.get(code__iexact=coupon_code, is_active=True)
            
            # Remove any existing coupon
            AppliedCoupon.objects.filter(cart=cart).delete()
            
            # Apply new coupon
            discount_amount = coupon.calculate_discount(cart.subtotal_price)
            AppliedCoupon.objects.create(
                coupon=coupon,
                user=cart.user,
                cart=cart,
                discount_amount=discount_amount
            )
            
            messages.success(request, f'Coupon {coupon.code} applied successfully!')
            
        except Cart.DoesNotExist:
            messages.error(request, 'Invalid cart ID')
        except Coupon.DoesNotExist:
            messages.error(request, 'Invalid or inactive coupon code')
        except Exception as e:
            messages.error(request, f'Error applying coupon: {str(e)}')
        
        return redirect('admin:cart_cart_change', cart_id)
    
    # GET request - show form
    cart_id = request.GET.get('cart_id')
    if not cart_id:
        messages.error(request, 'No cart specified')
        return redirect('admin:cart_cart_changelist')
    
    try:
        cart = Cart.objects.get(id=cart_id)
        context = {
            'title': 'Apply Coupon',
            'cart': cart,
            'opts': Cart._meta,
            'has_view_permission': True,
            'has_add_permission': True,
            'has_change_permission': True,
            'has_delete_permission': True,
        }
        return render(request, 'admin/cart/apply_coupon.html', context)
    except Cart.DoesNotExist:
        messages.error(request, 'Invalid cart ID')
        return redirect('admin:cart_cart_changelist')
