"""
Sync local Plan objects to Stripe Products + Prices.

For each active Plan:
- Creates a Stripe Product if `stripe_product_id` is empty (otherwise updates name/description)
- Creates a recurring monthly Price if `stripe_price_id` is empty OR if the local price changed
  (Stripe Prices are immutable, so price changes mean a new Price is created and the old one is archived)
"""
import stripe
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.models import Plan


class Command(BaseCommand):
    help = "Create or update Stripe Products and Prices to match local Plan rows."

    def handle(self, *args, **options):
        if not settings.STRIPE_SECRET_KEY:
            raise CommandError("STRIPE_SECRET_KEY is not configured in environment.")

        stripe.api_key = settings.STRIPE_SECRET_KEY

        plans = Plan.objects.filter(is_active=True).order_by('price_monthly')
        if not plans.exists():
            self.stdout.write(self.style.WARNING("No active plans found."))
            return

        for plan in plans:
            self.stdout.write(f"\n— {plan.name} (€{plan.price_monthly}/mo) —")
            self._sync_plan(plan)

        self.stdout.write(self.style.SUCCESS("\nDone."))

    def _sync_plan(self, plan):
        # 1. Product
        if plan.stripe_product_id:
            try:
                stripe.Product.modify(
                    plan.stripe_product_id,
                    name=plan.name,
                    description=plan.description or f"Monthly Guardian Agent {plan.name} subscription.",
                )
                self.stdout.write(f"  Updated product {plan.stripe_product_id}")
            except stripe.error.InvalidRequestError:
                # Product was deleted in Stripe — create a new one
                plan.stripe_product_id = ''
                plan.stripe_price_id = ''

        if not plan.stripe_product_id:
            product = stripe.Product.create(
                name=plan.name,
                description=plan.description or f"Monthly Guardian Agent {plan.name} subscription.",
                metadata={'plan_id': str(plan.id)},
            )
            plan.stripe_product_id = product.id
            self.stdout.write(f"  Created product {product.id}")

        # 2. Price — check if existing price still matches our amount
        expected_amount = int(plan.price_monthly * 100)
        existing_price = None
        if plan.stripe_price_id:
            try:
                existing_price = stripe.Price.retrieve(plan.stripe_price_id)
                if (existing_price.unit_amount != expected_amount
                        or existing_price.currency != 'eur'
                        or existing_price.product != plan.stripe_product_id):
                    existing_price = None  # price drifted — make a new one
            except stripe.error.InvalidRequestError:
                existing_price = None

        if existing_price:
            self.stdout.write(f"  Price {existing_price.id} already matches")
        else:
            # Archive the old one if it exists
            if plan.stripe_price_id:
                try:
                    stripe.Price.modify(plan.stripe_price_id, active=False)
                    self.stdout.write(f"  Archived old price {plan.stripe_price_id}")
                except stripe.error.StripeError:
                    pass

            new_price = stripe.Price.create(
                product=plan.stripe_product_id,
                unit_amount=expected_amount,
                currency='eur',
                recurring={'interval': 'month'},
                metadata={'plan_id': str(plan.id)},
            )
            plan.stripe_price_id = new_price.id
            self.stdout.write(self.style.SUCCESS(f"  Created price {new_price.id}"))

        plan.save(update_fields=['stripe_product_id', 'stripe_price_id'])
