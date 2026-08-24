from unittest import TestCase
from ..engines import compute_discount, DiscountContext, DiscountDecision


class TestDiscountEngine(TestCase):
    """Unit tests for pure Python discount engine."""

    def test_apply_discount_to_qualifying_order(self):
        """Discount applies when all conditions are met."""
        ctx = DiscountContext(
            partner_id=1,
            allowed_partner_ids=[1, 2],
            warehouse_id=1,
            allowed_warehouse_ids=[1, 2],
            product_tag_names=['generic_tag'],
            restricted_default_codes=set(),
            product_codes={'PROD001'},
        )
        decision = compute_discount(ctx, 2.0)
        self.assertTrue(decision.apply_discount)
        self.assertEqual(decision.discount_pct, 2.0)
        self.assertEqual(decision.reason, 'APPLIED')

    def test_no_discount_wrong_group(self):
        """Discount denied if partner is not in allowed_partner_ids."""
        ctx = DiscountContext(
            partner_id=99,
            allowed_partner_ids=[1, 2],
            warehouse_id=1,
            allowed_warehouse_ids=[1],
            product_tag_names=[],
            restricted_default_codes=set(),
            product_codes={'PROD001'},
        )
        decision = compute_discount(ctx, 2.0)
        self.assertFalse(decision.apply_discount)
        self.assertEqual(decision.discount_pct, 0.0)
        self.assertEqual(decision.reason, 'WRONG_GROUP')

    def test_no_discount_wrong_branch(self):
        """Discount denied if warehouse is not in allowed list."""
        ctx = DiscountContext(
            partner_id=1,
            allowed_partner_ids=[1],
            warehouse_id=99,
            allowed_warehouse_ids=[1, 2],
            product_tag_names=[],
            restricted_default_codes=set(),
            product_codes={'PROD001'},
        )
        decision = compute_discount(ctx, 2.0)
        self.assertFalse(decision.apply_discount)
        self.assertEqual(decision.reason, 'WRONG_BRANCH')

    def test_no_discount_restricted_brand(self):
        """Discount denied if product has restricted brand tag."""
        ctx = DiscountContext(
            partner_id=1,
            allowed_partner_ids=[1],
            warehouse_id=1,
            allowed_warehouse_ids=[1],
            product_tag_names=['MARCA_RESTRINGIDA_BAYER', 'other_tag'],
            restricted_default_codes=set(),
            product_codes={'PROD001'},
        )
        decision = compute_discount(ctx, 2.0)
        self.assertFalse(decision.apply_discount)
        self.assertEqual(decision.reason, 'RESTRICTED_BRAND')

    def test_no_discount_restricted_sku(self):
        """Discount denied if any product code is in restricted list."""
        ctx = DiscountContext(
            partner_id=1,
            allowed_partner_ids=[1],
            warehouse_id=1,
            allowed_warehouse_ids=[1],
            product_tag_names=[],
            restricted_default_codes={'RESTRICTED_SKU_001', 'RESTRICTED_SKU_002'},
            product_codes={'RESTRICTED_SKU_001'},
        )
        decision = compute_discount(ctx, 2.0)
        self.assertFalse(decision.apply_discount)
        self.assertEqual(decision.reason, 'RESTRICTED_SKU')

    def test_allowed_warehouse_empty_means_all_allowed(self):
        """When allowed_warehouse_ids is empty, all warehouses are OK."""
        ctx = DiscountContext(
            partner_id=1,
            allowed_partner_ids=[1],
            warehouse_id=999,
            allowed_warehouse_ids=[],
            product_tag_names=[],
            restricted_default_codes=set(),
            product_codes={'PROD001'},
        )
        decision = compute_discount(ctx, 2.0)
        self.assertTrue(decision.apply_discount)
        self.assertEqual(decision.reason, 'APPLIED')

    def test_multiple_tags_none_restricted(self):
        """Multiple tags without restricted prefix should allow discount."""
        ctx = DiscountContext(
            partner_id=1,
            allowed_partner_ids=[1],
            warehouse_id=1,
            allowed_warehouse_ids=[1],
            product_tag_names=['tag1', 'tag2', 'generic'],
            restricted_default_codes=set(),
            product_codes={'PROD001'},
        )
        decision = compute_discount(ctx, 2.0)
        self.assertTrue(decision.apply_discount)

    def test_none_product_code_with_empty_restrictions(self):
        """Product with no codes should pass SKU check if list is empty."""
        ctx = DiscountContext(
            partner_id=1,
            allowed_partner_ids=[1],
            warehouse_id=1,
            allowed_warehouse_ids=[1],
            product_tag_names=[],
            restricted_default_codes=set(),
            product_codes=set(),
        )
        decision = compute_discount(ctx, 2.0)
        self.assertTrue(decision.apply_discount)

    def test_restricted_sku_with_multiple_product_codes(self):
        """Discount blocked if any product code (barcode OR default_code) is restricted."""
        ctx = DiscountContext(
            partner_id=1,
            allowed_partner_ids=[1],
            warehouse_id=1,
            allowed_warehouse_ids=[1],
            product_tag_names=[],
            restricted_default_codes={'BARCODE_RESTRICTED'},
            product_codes={'BARCODE_RESTRICTED', 'DEFAULT_CODE_001'},
        )
        decision = compute_discount(ctx, 2.0)
        self.assertFalse(decision.apply_discount)
        self.assertEqual(decision.reason, 'RESTRICTED_SKU')

        ctx2 = DiscountContext(
            partner_id=1,
            allowed_partner_ids=[1],
            warehouse_id=1,
            allowed_warehouse_ids=[1],
            product_tag_names=[],
            restricted_default_codes={'DEFAULT_CODE_RESTRICTED'},
            product_codes={'BARCODE_001', 'DEFAULT_CODE_RESTRICTED'},
        )
        decision2 = compute_discount(ctx2, 2.0)
        self.assertFalse(decision2.apply_discount)
        self.assertEqual(decision2.reason, 'RESTRICTED_SKU')
