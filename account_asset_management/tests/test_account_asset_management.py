# Copyright (c) 2014 ACSONE SA/NV (acsone.eu).
# Copyright 2009-2018 Noviat
# Copyright 2021 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import calendar
import time
from datetime import date, datetime

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAssetManagement(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # ENVIRONMENTS
        cls.asset_model = cls.env["account.asset"]
        cls.asset_profile_model = cls.env["account.asset.profile"]
        cls.dl_model = cls.env["account.asset.line"]
        cls.remove_model = cls.env["account.asset.remove"]
        # INSTANCES
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.product = cls.env["product.product"].create(
            {"name": "Test", "standard_price": 500.0}
        )

        cls.invoice = (
            cls.env["account.move"]
            .with_context(check_move_validity=False)
            .create(
                {
                    "move_type": "in_invoice",
                    "invoice_date": fields.Date.context_today(cls.env.user),
                    "partner_id": cls.partner.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "test",
                                "product_id": cls.product.id,
                                "price_unit": 2000.00,
                                "quantity": 1,
                            }
                        ),
                    ],
                }
            )
        )

        cls.invoice_2 = (
            cls.env["account.move"]
            .with_context(check_move_validity=False)
            .create(
                {
                    "move_type": "in_invoice",
                    "invoice_date": fields.Date.context_today(cls.env.user),
                    "partner_id": cls.partner.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "test 2",
                                "product_id": cls.product.id,
                                "price_unit": 10000.00,
                                "quantity": 1,
                            }
                        ),
                        Command.create(
                            {
                                "name": "test 3",
                                "product_id": cls.product.id,
                                "price_unit": 20000.00,
                                "quantity": 1,
                            }
                        ),
                    ],
                }
            )
        )

        # analytic configuration
        cls.env.user.group_ids += cls.env.ref("analytic.group_analytic_accounting")

        cls.default_plan = cls.env["account.analytic.plan"].create({"name": "Default"})
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {"name": "test_analytic_account", "plan_id": cls.default_plan.id}
        )

        cls.distribution = cls.env["account.analytic.distribution.model"].create(
            {
                "partner_id": cls.partner.id,
                "analytic_distribution": {cls.analytic_account.id: 100},
            }
        )

        # Asset Profile 1
        cls.ict3Y = cls.asset_profile_model.create(
            {
                "account_expense_depreciation_id": cls.company_data[
                    "default_account_expense"
                ].id,
                "account_asset_id": cls.company_data["default_account_assets"].id,
                "account_depreciation_id": cls.company_data[
                    "default_account_assets"
                ].id,
                "journal_id": cls.company_data["default_journal_purchase"].id,
                "name": "Hardware - 3 Years",
                "method_time": "year",
                "method_number": 3,
                "method_period": "year",
            }
        )
        # Asset Profile 2
        cls.car5y = cls.asset_profile_model.create(
            {
                "account_expense_depreciation_id": cls.company_data[
                    "default_account_expense"
                ].id,
                "account_asset_id": cls.company_data["default_account_assets"].id,
                "account_depreciation_id": cls.company_data[
                    "default_account_assets"
                ].id,
                "journal_id": cls.company_data["default_journal_purchase"].id,
                "name": "Cars - 5 Years",
                "method_time": "year",
                "method_number": 5,
                "method_period": "year",
                "analytic_distribution": cls.distribution._get_distribution(
                    {
                        "partner_id": cls.partner.id,
                    }
                ),
                # "account_analytic_id": cls.analytic_account.id,
            }
        )

    def test_invoice_line_without_product(self):
        tax = self.env["account.tax"].create(
            {
                "name": "TAX 15%",
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "amount": 15.0,
            }
        )

        invoice = (
            self.env["account.move"]
            .with_context(check_move_validity=False)
            .create(
                {
                    "move_type": "in_invoice",
                    "invoice_date": fields.Date.context_today(self.env.user),
                    "partner_id": self.partner.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Line 1",
                                "price_unit": 200.0,
                                "quantity": 1,
                                "tax_ids": [tax.id],
                            }
                        ),
                    ],
                }
            )
        )
        self.assertEqual(invoice.partner_id, self.partner)

    def test_00_fiscalyear_lock_date_month(self):
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 1500,
                "date_start": "1901-02-01",
                "method_time": "year",
                "method_number": 3,
                "method_period": "month",
            }
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        self.assertTrue(asset.depreciation_line_ids[0].init_entry)
        for i in range(1, 36):
            self.assertFalse(asset.depreciation_line_ids[i].init_entry)

    def test_00_fiscalyear_lock_date_year(self):
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 1500,
                "date_start": "1901-02-01",
                "method_time": "year",
                "method_number": 3,
                "method_period": "year",
            }
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        self.assertTrue(asset.depreciation_line_ids[0].init_entry)
        for i in range(1, 4):
            self.assertFalse(asset.depreciation_line_ids[i].init_entry)

    def test_01_nonprorata_basic(self):
        """Basic tests of depreciation board computations and postings."""
        # First create demo assets and do some sanity checks
        # Asset Model 1
        ict0 = self.asset_model.create(
            {
                "state": "draft",
                "method_time": "year",
                "method_number": 3,
                "method_period": "year",
                "name": "Laptop",
                "code": "PI00101",
                "purchase_value": 1500.0,
                "profile_id": self.ict3Y.id,
                "date_start": time.strftime("%Y-01-01"),
            }
        )
        # Sanity checks
        self.assertEqual(ict0.state, "draft")
        self.assertEqual(ict0.purchase_value, 1500)
        self.assertEqual(ict0.salvage_value, 0)
        self.assertEqual(ict0.depreciation_base, 1500)
        self.assertEqual(len(ict0.depreciation_line_ids), 1)
        # Asset Model 2
        vehicle0 = self.asset_model.create(
            {
                "state": "draft",
                "method_time": "year",
                "method_number": 5,
                "method_period": "year",
                "name": "CEO's Car",
                "purchase_value": 12000.0,
                "salvage_value": 2000.0,
                "profile_id": self.car5y.id,
                "date_start": time.strftime("%Y-01-01"),
            }
        )
        # Sanity checks
        self.assertEqual(vehicle0.state, "draft")
        self.assertEqual(vehicle0.purchase_value, 12000)
        self.assertEqual(vehicle0.salvage_value, 2000)
        self.assertEqual(vehicle0.depreciation_base, 10000)
        self.assertEqual(len(vehicle0.depreciation_line_ids), 1)
        # Compute the depreciation boards
        ict0.compute_depreciation_board()
        ict0.invalidate_recordset()
        self.assertEqual(len(ict0.depreciation_line_ids), 4)
        self.assertEqual(ict0.depreciation_line_ids[1].amount, 500)
        vehicle0.compute_depreciation_board()
        vehicle0.invalidate_recordset()
        self.assertEqual(len(vehicle0.depreciation_line_ids), 6)
        self.assertEqual(vehicle0.depreciation_line_ids[1].amount, 2000)
        # Post the first depreciation line
        ict0.validate()
        ict0.depreciation_line_ids[1].create_move()
        ict0.invalidate_recordset()
        self.assertEqual(ict0.state, "open")
        self.assertEqual(ict0.value_depreciated, 500)
        self.assertEqual(ict0.value_residual, 1000)
        vehicle0.validate()
        created_move_ids = vehicle0.depreciation_line_ids[1].create_move()
        for move_id in created_move_ids:
            move = self.env["account.move"].browse(move_id)
            expense_line = move.line_ids.filtered(
                lambda line: line.account_id.internal_group == "expense"
            )
            self.assertEqual(
                expense_line.analytic_distribution,
                self.distribution._get_distribution(
                    {
                        "partner_id": self.partner.id,
                    }
                )
                or False,
            )
        vehicle0.invalidate_recordset()
        self.assertEqual(vehicle0.state, "open")
        self.assertEqual(vehicle0.value_depreciated, 2000)
        self.assertEqual(vehicle0.value_residual, 8000)

    def test_02_prorata_basic(self):
        """Prorata temporis depreciation basic test."""
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 3333,
                "salvage_value": 0,
                "date_start": time.strftime("%Y-07-07"),
                "method_time": "year",
                "method_number": 5,
                "method_period": "month",
                "prorata": True,
            }
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        if calendar.isleap(date.today().year):
            self.assertAlmostEqual(
                asset.depreciation_line_ids[1].amount, 46.44, places=2
            )
        else:
            self.assertAlmostEqual(
                asset.depreciation_line_ids[1].amount, 47.33, places=2
            )
        self.assertAlmostEqual(asset.depreciation_line_ids[2].amount, 55.55, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[3].amount, 55.55, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[4].amount, 55.55, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[5].amount, 55.55, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[6].amount, 55.55, places=2)
        if calendar.isleap(date.today().year):
            self.assertAlmostEqual(
                asset.depreciation_line_ids[-1].amount, 9.11, places=2
            )
        else:
            self.assertAlmostEqual(
                asset.depreciation_line_ids[-1].amount, 8.22, places=2
            )

    def test_03_proprata_init_prev_year(self):
        """Prorata temporis depreciation with init value in prev year."""
        # Create an asset in current year
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 3333,
                "salvage_value": 0,
                "date_start": f"{datetime.now().year - 1}-07-07",
                "method_time": "year",
                "method_number": 5,
                "method_period": "month",
                "prorata": True,
            }
        )
        # Create a initial depreciation line in previous year
        self.dl_model.create(
            {
                "asset_id": asset.id,
                "amount": 325.08,
                "line_date": f"{datetime.now().year - 1}-12-31",
                "type": "depreciate",
                "init_entry": True,
            }
        )
        self.assertEqual(len(asset.depreciation_line_ids), 2)
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        # check the depreciated value is the initial value
        self.assertAlmostEqual(asset.value_depreciated, 325.08, places=2)
        # check computed values in the depreciation board
        self.assertAlmostEqual(asset.depreciation_line_ids[3].amount, 55.55, places=2)
        if calendar.isleap(date.today().year - 1):
            # for leap years the first year depreciation amount of 325.08
            # is too high and hence a correction is applied to the next
            # entry of the table
            self.assertAlmostEqual(
                asset.depreciation_line_ids[2].amount, 54.66, places=2
            )
            self.assertAlmostEqual(
                asset.depreciation_line_ids[3].amount, 55.55, places=2
            )
            self.assertAlmostEqual(
                asset.depreciation_line_ids[-1].amount, 9.11, places=2
            )
        else:
            self.assertAlmostEqual(
                asset.depreciation_line_ids[2].amount, 55.55, places=2
            )
            self.assertAlmostEqual(
                asset.depreciation_line_ids[-1].amount, 8.22, places=2
            )

    def test_04_prorata_init_cur_year(self):
        """Prorata temporis depreciation with init value in curent year."""
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 3333,
                "salvage_value": 0,
                "date_start": time.strftime("%Y-07-07"),
                "method_time": "year",
                "method_number": 5,
                "method_period": "month",
                "prorata": True,
            }
        )
        self.dl_model.create(
            {
                "asset_id": asset.id,
                "amount": 279.44,
                "line_date": time.strftime("%Y-11-30"),
                "type": "depreciate",
                "init_entry": True,
            }
        )
        self.assertEqual(len(asset.depreciation_line_ids), 2)
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        # check the depreciated value is the initial value
        self.assertAlmostEqual(asset.value_depreciated, 279.44, places=2)
        # check computed values in the depreciation board
        if calendar.isleap(date.today().year):
            self.assertAlmostEqual(
                asset.depreciation_line_ids[2].amount, 44.75, places=2
            )
        else:
            self.assertAlmostEqual(
                asset.depreciation_line_ids[2].amount, 45.64, places=2
            )
        self.assertAlmostEqual(asset.depreciation_line_ids[3].amount, 55.55, places=2)
        if calendar.isleap(date.today().year):
            self.assertAlmostEqual(
                asset.depreciation_line_ids[-1].amount, 9.11, places=2
            )
        else:
            self.assertAlmostEqual(
                asset.depreciation_line_ids[-1].amount, 8.22, places=2
            )

    def test_05_degressive_linear(self):
        """Degressive-Linear with annual and quarterly depreciation."""
        # annual depreciation
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 1000,
                "salvage_value": 0,
                "date_start": time.strftime("%Y-07-07"),
                "method_time": "year",
                "method": "degr-linear",
                "method_progress_factor": 0.40,
                "method_number": 5,
                "method_period": "year",
                "prorata": False,
            }
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        # check values in the depreciation board
        self.assertEqual(len(asset.depreciation_line_ids), 5)
        self.assertAlmostEqual(asset.depreciation_line_ids[1].amount, 400.00, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[2].amount, 240.00, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[3].amount, 200.00, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[4].amount, 160.00, places=2)
        # quarterly depreciation
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 1000,
                "salvage_value": 0,
                "date_start": time.strftime("%Y-07-07"),
                "method_time": "year",
                "method": "degr-linear",
                "method_progress_factor": 0.40,
                "method_number": 5,
                "method_period": "quarter",
                "prorata": False,
            }
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        # check values in the depreciation board
        self.assertEqual(len(asset.depreciation_line_ids), 15)
        # lines prior to asset start period are grouped in the first entry
        self.assertAlmostEqual(asset.depreciation_line_ids[1].amount, 300.00, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[3].amount, 60.00, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[7].amount, 50.00, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[13].amount, 40.00, places=2)

    def test_06_degressive_limit(self):
        """Degressive with annual depreciation."""
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 1000,
                "salvage_value": 100,
                "date_start": time.strftime("%Y-07-07"),
                "method_time": "year",
                "method": "degr-limit",
                "method_progress_factor": 0.40,
                "method_number": 5,
                "method_period": "year",
                "prorata": False,
            }
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        # check values in the depreciation board
        self.assertEqual(len(asset.depreciation_line_ids), 6)
        self.assertAlmostEqual(asset.depreciation_line_ids[1].amount, 400.00, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[2].amount, 240.00, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[3].amount, 144.00, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[4].amount, 86.40, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[5].amount, 29.60, places=2)

    def test_07_linear_limit(self):
        """Degressive with annual depreciation."""
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 1000,
                "salvage_value": 100,
                "date_start": time.strftime("%Y-07-07"),
                "method_time": "year",
                "method": "linear-limit",
                "method_number": 5,
                "method_period": "year",
                "prorata": False,
            }
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        # check values in the depreciation board
        self.assertEqual(len(asset.depreciation_line_ids), 6)
        self.assertAlmostEqual(asset.depreciation_line_ids[1].amount, 200.00, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[-1].amount, 100.00, places=2)

    @mute_logger("odoo.models.unlink")
    def test_08_asset_removal(self):
        """Asset removal"""
        asset = self.asset_model.create(
            {
                "name": "test asset removal",
                "profile_id": self.car5y.id,
                "purchase_value": 5000,
                "salvage_value": 0,
                "date_start": "2019-01-01",
                "method_time": "year",
                "method_number": 5,
                "method_period": "quarter",
                "prorata": False,
            }
        )
        asset.compute_depreciation_board()
        asset.validate()
        wiz_ctx = {"active_id": asset.id, "early_removal": True}
        wiz = self.remove_model.with_context(**wiz_ctx).create(
            {
                "date_remove": "2019-01-31",
                "sale_value": 0.0,
                "posting_regime": "gain_loss_on_sale",
                "account_plus_value_id": self.company_data[
                    "default_account_revenue"
                ].id,
                "account_min_value_id": self.company_data["default_account_expense"].id,
            }
        )
        wiz.remove()
        asset.invalidate_recordset()
        self.assertEqual(len(asset.depreciation_line_ids), 3)
        self.assertAlmostEqual(asset.depreciation_line_ids[1].amount, 81.46, places=2)
        self.assertAlmostEqual(asset.depreciation_line_ids[2].amount, 4918.54, places=2)

    def test_09_asset_from_invoice(self):
        all_asset = self.env["account.asset"].search([])
        invoice = self.invoice
        asset_profile = self.car5y
        asset_profile.asset_product_item = False
        self.assertTrue(len(invoice.invoice_line_ids) > 0)
        line = invoice.invoice_line_ids[0]
        self.assertTrue(line.price_unit > 0.0)
        invoice.invoice_line_ids[0].write(
            {"quantity": 2, "asset_profile_id": asset_profile.id}
        )
        invoice.action_post()
        # get all asset after invoice validation
        current_asset = self.env["account.asset"].search([])
        # get the new asset
        new_asset = current_asset - all_asset
        # check that a new asset is created
        self.assertEqual(len(new_asset), 1)
        # check that the new asset has the correct purchase value
        self.assertAlmostEqual(
            new_asset.purchase_value, line.price_unit * line.quantity, places=2
        )

    def test_10_asset_from_invoice_product_item(self):
        all_asset = self.env["account.asset"].search([])
        invoice = self.invoice
        asset_profile = self.car5y
        asset_profile.asset_product_item = True
        self.assertTrue(len(invoice.invoice_line_ids) > 0)
        line = invoice.invoice_line_ids[0]
        self.assertTrue(line.price_unit > 0.0)
        line.quantity = 2
        line.asset_profile_id = asset_profile
        self.assertEqual(len(invoice.invoice_line_ids), 2)
        invoice.action_post()
        # get all asset after invoice validation
        current_asset = self.env["account.asset"].search([])
        # get the new asset
        new_asset = current_asset - all_asset
        # check that a new asset is created
        self.assertEqual(len(new_asset), 2)
        for asset in new_asset:
            # check that the new asset has the correct purchase value
            self.assertAlmostEqual(asset.purchase_value, line.price_unit, places=2)

    def test_11_assets_from_invoice(self):
        all_assets = self.env["account.asset"].search([])
        ctx = dict(self.invoice_2.env.context)
        invoice = self.invoice_2.with_context(**ctx)
        asset_profile = self.car5y
        asset_profile.asset_product_item = True
        # Compute depreciation lines on invoice validation
        asset_profile.open_asset = True
        self.assertTrue(len(invoice.invoice_line_ids) == 2)
        invoice.invoice_line_ids.write(
            {"quantity": 1, "asset_profile_id": asset_profile.id}
        )
        invoice.action_post()
        # Retrieve all assets after invoice validation
        current_assets = self.env["account.asset"].search([])
        # What are the new assets?
        new_assets = current_assets - all_assets
        self.assertEqual(len(new_assets), 2)
        for asset in new_assets:
            dlines = asset.depreciation_line_ids.filtered(
                lambda line: line.type == "depreciate"
            )
            dlines = dlines.sorted(key=lambda line: line.line_date)
            self.assertAlmostEqual(dlines[0].depreciated_value, 0.0)
            self.assertAlmostEqual(dlines[-1].remaining_value, 0.0)

    def test_12_prorata_days_calc(self):
        """Prorata temporis depreciation with days calc option."""
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 3333,
                "salvage_value": 0,
                "date_start": "2019-07-07",
                "method_time": "year",
                "method_number": 5,
                "method_period": "month",
                "prorata": True,
                "days_calc": True,
                "use_leap_years": False,
            }
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        day_rate = 3333 / 1827  # 3333 / 1827 depreciation days
        for i in range(1, 10):
            self.assertAlmostEqual(
                asset.depreciation_line_ids[i].amount,
                asset.depreciation_line_ids[i].line_days * day_rate,
                places=2,
            )
        # Last depreciation remaining
        self.assertAlmostEqual(asset.depreciation_line_ids[-1].amount, 11.05, places=2)

    def test_13_use_leap_year(self):
        # When you use the depreciation with years method and using lap years,
        # the depreciation amount is calculated as 10000 / 1826 days * 365 days
        # = yearly depreciation amount of 1998.90.
        # Then 1998.90 / 12 = 166.58
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 10000,
                "salvage_value": 0,
                "date_start": time.strftime("2019-01-01"),
                "method_time": "year",
                "method_number": 5,
                "method_period": "month",
                "prorata": False,
                "days_calc": False,
                "use_leap_years": True,
            }
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        for i in range(2, 11):
            self.assertAlmostEqual(
                asset.depreciation_line_ids[i].amount, 166.58, places=2
            )
        self.assertAlmostEqual(
            asset.depreciation_line_ids[13].depreciated_value, 1998.90, places=2
        )

    def test_14_not_use_leap_year(self):
        # When you run a depreciation with method = 'year' and no not use
        # lap years you divide 1000 / 5 years = 2000, then divided by 12 months
        # to get 166.67 per month, equal for all periods.
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 10000,
                "salvage_value": 0,
                "date_start": time.strftime("2019-01-01"),
                "method_time": "year",
                "method_number": 5,
                "method_period": "month",
                "prorata": False,
                "days_calc": False,
                "use_leap_years": False,
            }
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        for _i in range(1, 11):
            self.assertAlmostEqual(
                asset.depreciation_line_ids[1].amount, 166.67, places=2
            )
        # In the last month of the fiscal year we compensate for the small
        # deviations if that is necessary.
        self.assertAlmostEqual(asset.depreciation_line_ids[12].amount, 166.63, places=2)

    def test_15_account_asset_group(self):
        """Group's name_get behaves differently depending on code and context"""
        group_fa = self.env["account.asset.group"].create(
            {
                "name": "Fixed Assets",
                "code": "FA",
            }
        )
        group_tfa = self.env["account.asset.group"].create(
            {
                "name": "Tangible Fixed Assets",
                "code": "TFA",
            }
        )
        # Groups are displayed by code (if any) plus name
        self.assertEqual(
            self.env["account.asset.group"].name_search("FA")[0],
            (group_fa.id, "FA Fixed Assets"),
        )
        # Groups with code are shown by code in list views
        self.assertEqual(
            self.env["account.asset.group"]
            .with_context(params={"view_type": "list"})
            .name_search("FA")[0],
            (group_fa.id, "FA Fixed Assets"),
        )
        self.assertEqual(
            self.env["account.asset.group"].name_search("TFA"),
            [(group_tfa.id, "TFA Tangible Fixed Assets")],
        )
        group_tfa.code = False
        group_fa.code = False
        self.assertEqual(
            group_fa.name_search(name="Fixed Assets", operator="="),
            [(group_fa.id, "Fixed Assets")],
        )
        # Groups without code are shown by truncated name in lists
        self.assertEqual(
            group_tfa.name_search(name="Tangible Fixed Assets", operator="="),
            [(group_tfa.id, "Tangible Fixed Assets")],
        )
        self.assertFalse(self.env["account.asset.group"].name_search("stessA dexiF"))

    def test_16_use_number_of_depreciations(self):
        # When you run a depreciation with method = 'number'
        profile = self.car5y
        profile.method_time = "number"
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": profile.id,
                "purchase_value": 10000,
                "salvage_value": 0,
                "date_start": time.strftime("2019-01-01"),
                "method_time": "year",
                "method_number": 5,
                "method_period": "month",
                "prorata": False,
                "days_calc": False,
                "use_leap_years": False,
            }
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        for _i in range(1, 11):
            self.assertAlmostEqual(
                asset.depreciation_line_ids[1].amount, 166.67, places=2
            )
        # In the last month of the fiscal year we compensate for the small
        # deviations if that is necessary.
        self.assertAlmostEqual(asset.depreciation_line_ids[12].amount, 166.63, places=2)

    def test_17_carry_forward_missed_depreciations(self):
        """Asset with accumulate missed depreciations."""
        asset_profile = self.car5y
        # Create an asset with carry_forward_missed_depreciations
        # Theoretically, the depreciation would be 5000 / 12 months
        # which is 416.67 per month
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": asset_profile.id,
                "purchase_value": 5000,
                "salvage_value": 0,
                "date_start": time.strftime("2021-01-01"),
                "method_time": "year",
                "method_number": 1,
                "method_period": "month",
                "carry_forward_missed_depreciations": True,
            }
        )
        # Set the fiscalyear lock date for the company
        self.company_data["company"].fiscalyear_lock_date = time.strftime("2021-05-31")
        # Compute the depreciation board
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        d_lines = asset.depreciation_line_ids
        init_lines = d_lines[1:6]
        # Jan to May entries are before the lock date -> marked as init
        self.assertTrue(init_lines.mapped("init_entry"))
        # Depreciation amount for these lines is set to 0
        for line in init_lines:
            self.assertEqual(line.amount, 0.0)
        # The amount to be carried is 416.67 * 5 = 2083.35
        # This amount is accumulated in the first depreciation for the current
        # available period -> 416.67 + 2083.35 = 2500.02
        self.assertAlmostEqual(d_lines[6].amount, 2500.02, places=2)
        # The rest of the lines should have the corresponding amount of 416.67
        # just as usual
        for _i in range(7, 12):
            self.assertAlmostEqual(d_lines[_i].amount, 416.67, places=2)
        # In the last month the small deviations are compensated
        self.assertAlmostEqual(d_lines[12].amount, 416.63, places=2)

    def test_18_reverse_entries(self):
        """Test that cancelling a posted entry creates a reversal."""
        ict0 = self.asset_model.create(
            {
                "state": "draft",
                "method_time": "year",
                "method_number": 3,
                "method_period": "year",
                "name": "Laptop",
                "code": "PI00101",
                "purchase_value": 1500.0,
                "profile_id": self.ict3Y.id,
                "date_start": time.strftime("%Y-01-01"),
            }
        )
        ict0.profile_id.allow_reversal = True
        # compute the depreciation boards
        ict0.compute_depreciation_board()
        ict0.invalidate_recordset()
        # post the first depreciation line
        ict0.validate()
        ict0.depreciation_line_ids[1].create_move()
        original_move = ict0.depreciation_line_ids[1].move_id
        ict0.invalidate_recordset()
        self.assertEqual(ict0.state, "open")
        self.assertEqual(ict0.value_depreciated, 500)
        self.assertEqual(ict0.value_residual, 1000)
        depreciation_line = ict0.depreciation_line_ids[1]
        wiz_res = depreciation_line.unlink_move()
        self.assertTrue(
            "res_model" in wiz_res and wiz_res["res_model"] == "wiz.asset.move.reverse"
        )
        wiz = Form(
            self.env["wiz.asset.move.reverse"].with_context(
                **{
                    "active_model": depreciation_line._name,
                    "active_id": depreciation_line.id,
                    "active_ids": [depreciation_line.id],
                }
            )
        )
        reverse_wizard = wiz.save()
        reverse_wizard.write({"journal_id": depreciation_line.move_id.journal_id.id})
        ict0.invalidate_recordset()
        self.assertEqual(ict0.value_depreciated, 500)
        self.assertEqual(ict0.value_residual, 1000)
        self.assertEqual(len(original_move.reversal_move_ids), 0)

    @mute_logger("odoo.models.unlink")
    def test_19_unlink_entries(self):
        """Test that cancelling a posted entry creates a reversal, if the
        journal entry has the inalterability hash."""
        ict0 = self.asset_model.create(
            {
                "state": "draft",
                "method_time": "year",
                "method_number": 3,
                "method_period": "year",
                "name": "Laptop",
                "code": "PI00101",
                "purchase_value": 1500.0,
                "profile_id": self.ict3Y.id,
                "date_start": time.strftime("%Y-01-01"),
            }
        )
        # compute the depreciation boards
        ict0.compute_depreciation_board()
        ict0.invalidate_recordset()
        # post the first depreciation line
        ict0.validate()
        ict0.depreciation_line_ids[1].create_move()
        original_move_id = ict0.depreciation_line_ids[1].move_id.id
        ict0.invalidate_recordset()
        self.assertEqual(ict0.state, "open")
        self.assertEqual(ict0.value_depreciated, 500)
        self.assertEqual(ict0.value_residual, 1000)
        ict0.depreciation_line_ids[1].unlink_move()
        ict0.invalidate_recordset()
        self.assertEqual(ict0.value_depreciated, 0)
        self.assertEqual(ict0.value_residual, 1500)
        move = self.env["account.move"].search([("id", "=", original_move_id)])
        self.assertFalse(move)

    def test_20_asset_removal_with_value_residual(self):
        """Asset removal with value residual"""
        asset = self.asset_model.create(
            {
                "name": "test asset removal",
                "profile_id": self.car5y.id,
                "purchase_value": 1000,
                "salvage_value": 0,
                "date_start": "2019-01-01",
                "method_time": "number",
                "method_number": 10,
                "method_period": "month",
                "prorata": False,
            }
        )
        asset.compute_depreciation_board()
        asset.validate()
        lines = asset.depreciation_line_ids.filtered(lambda x: not x.init_entry)
        self.assertEqual(len(lines), 10)
        last_line = lines[-1]
        last_line["amount"] = last_line["amount"] - 0.10
        for asset_line in lines:
            asset_line.create_move()
        self.assertEqual(asset.value_residual, 0.10)
        asset.compute_depreciation_board()
        lines = asset.depreciation_line_ids.filtered(lambda x: not x.init_entry)
        self.assertEqual(len(lines), 11)
        last_line = lines[-1]
        self.assertEqual(last_line.amount, 0.10)
        last_line.create_move()
        self.assertEqual(asset.value_residual, 0)
        self.assertEqual(asset.state, "close")

    def test_20_asset_removal_without_value_residual(self):
        """Asset removal without residual value,
        the gain must be equal to the sale value because the asset is fully depreciated.
        """
        self.car5y.account_plus_value_id = self.company_data["default_account_revenue"]
        self.car5y.account_min_value_id = self.company_data["default_account_expense"]
        asset = self.asset_model.create(
            {
                "name": "test asset removal",
                "profile_id": self.car5y.id,
                "purchase_value": 1000,
                "salvage_value": 0,
                "date_start": "2019-01-01",
                "method_time": "number",
                "method_number": 10,
                "method_period": "month",
                "prorata": False,
            }
        )
        asset.compute_depreciation_board()
        asset.validate()
        lines = asset.depreciation_line_ids.filtered(lambda x: not x.init_entry)
        self.assertEqual(len(lines), 10)
        for asset_line in lines:
            asset_line.create_move()
        self.assertEqual(asset.value_residual, 0)
        self.assertEqual(asset.state, "close")
        sale_invoice = self.init_invoice("out_invoice", amounts=[500], post=False)
        sale_invoice_form = Form(sale_invoice)
        with sale_invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.asset_id = asset
        sale_invoice_form.save()
        self.assertEqual(
            sale_invoice.invoice_line_ids[0].account_id, self.car5y.account_asset_id
        )
        action = asset.remove()
        self.assertNotIn("early_removal", action["context"])
        wizard_form = Form(
            self.remove_model.with_context(
                **action["context"],
            )
        )
        wizard_form.posting_regime = "gain_loss_on_sale"
        remove_wizard = wizard_form.save()
        # check the values from the invoice
        self.assertEqual(remove_wizard.sale_value, 500)
        self.assertEqual(remove_wizard.account_sale_id, self.car5y.account_asset_id)
        remove_wizard.date_remove = "2019-01-31"
        with self.assertRaisesRegex(
            UserError, "The removal date must be after the last depreciation date"
        ):
            remove_wizard.remove()
        remove_wizard.date_remove = "2020-01-31"
        remove_wizard.remove()
        line_remove = asset.depreciation_line_ids.filtered(lambda x: x.type == "remove")
        self.assertEqual(len(line_remove), 1)
        self.assertEqual(line_remove.amount, 0)
        account_move_remove = line_remove.move_id
        self.assertEqual(len(account_move_remove.line_ids), 4)
        aml_sale = account_move_remove.line_ids.filtered(
            lambda x: x.account_id == remove_wizard.account_sale_id and x.debit == 500
        )
        self.assertEqual(len(aml_sale), 1)
        aml_depre = account_move_remove.line_ids.filtered(
            lambda x: x.account_id == self.car5y.account_depreciation_id
            and x.debit == 1000
        )
        self.assertEqual(len(aml_depre), 1)
        aml_asset = account_move_remove.line_ids.filtered(
            lambda x: x.account_id == self.car5y.account_asset_id and x.credit == 1000
        )
        self.assertEqual(len(aml_asset), 1)
        aml_gain = account_move_remove.line_ids.filtered(
            lambda x: x.account_id == remove_wizard.account_plus_value_id
        )
        self.assertEqual(len(aml_gain), 1)
        self.assertEqual(aml_gain.credit, 500)

    def test_21_asset_profile_salvage_value(self):
        """Compute salvage value from asset profile."""
        # Case percent
        self.car5y.salvage_type = "percent"
        self.car5y.salvage_value = 5
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 1000,
                "date_start": time.strftime("%Y-07-07"),
            }
        )
        self.assertEqual(asset.salvage_value, 50)
        # Case fixed amount
        self.car5y.salvage_type = "fixed"
        self.car5y.salvage_value = 5
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 1000,
                "date_start": time.strftime("%Y-07-07"),
            }
        )
        self.assertEqual(asset.salvage_value, 5)

    def test_22_recompute_with_posting_in_the_middle_of_a_period(self):
        """Recompute when the last posted depreciation falls in the middle of
        a period of the new table: no period may be lost."""
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.ict3Y.id,
                "purchase_value": 1200,
                "date_start": "2025-01-01",
                "method_time": "year",
                "method_number": 3,
                "method_period": "month",
            }
        )
        asset.validate()
        depreciation_lines = asset.depreciation_line_ids.filtered(
            lambda line: line.type == "depreciate"
        )
        depreciation_lines[0].create_move()
        asset.set_to_draft()
        asset.method_period = "year"
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        depreciation_lines = asset.depreciation_line_ids.filtered(
            lambda line: line.type == "depreciate"
        )
        self.assertEqual(
            depreciation_lines.mapped("line_date"),
            [
                date(2025, 1, 31),
                date(2025, 12, 31),
                date(2026, 12, 31),
                date(2027, 12, 31),
            ],
        )
        for line, amount in zip(
            depreciation_lines, [33.33, 366.67, 400.0, 400.0], strict=True
        ):
            self.assertAlmostEqual(line.amount, amount, places=2)

    def test_23_early_removal_day_after_last_posted_depreciation(self):
        """An early removal on the day after the last posted depreciation must
        not depreciate that day again."""
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.ict3Y.id,
                "purchase_value": 1200,
                "date_start": "2025-01-01",
            }
        )
        asset.validate()
        depreciation_lines = asset.depreciation_line_ids.filtered(
            lambda line: line.type == "depreciate"
        )
        depreciation_lines[0].create_move()
        wiz = self.remove_model.with_context(
            active_id=asset.id, early_removal=True
        ).create(
            {
                "date_remove": "2026-01-01",
                "sale_value": 0.0,
                "posting_regime": "gain_loss_on_sale",
                "account_plus_value_id": self.company_data[
                    "default_account_revenue"
                ].id,
                "account_min_value_id": self.company_data["default_account_expense"].id,
            }
        )
        wiz.remove()
        asset.invalidate_recordset()
        depreciation_lines = asset.depreciation_line_ids.filtered(
            lambda line: line.type == "depreciate"
        )
        self.assertEqual(depreciation_lines.mapped("amount"), [400.0])
        removal_line = asset.depreciation_line_ids.filtered(
            lambda line: line.type == "remove"
        )
        self.assertAlmostEqual(removal_line.amount, 800.0, places=2)

    def _create_monthly_asset_with_posted_lines(self, posted_months):
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.ict3Y.id,
                "purchase_value": 1200,
                "date_start": "2025-01-01",
                "method_time": "number",
                "method_number": 12,
                "method_period": "month",
            }
        )
        asset.validate()
        asset._get_pending_depreciation_lines()[:posted_months].create_move()
        return asset

    def _modify_asset_value(self, asset, change_date, new_value):
        wiz = (
            self.env["account.asset.modify"]
            .with_context(active_id=asset.id)
            .create({"reason": "Test", "date": change_date, "new_value": new_value})
        )
        wiz.modify()
        asset.invalidate_recordset()

    def _assert_pending_amounts(self, asset, amounts):
        pending_lines = asset._get_pending_depreciation_lines()
        for line, amount in zip(pending_lines, amounts, strict=True):
            self.assertAlmostEqual(line.amount, amount, places=2)

    def test_24_decrease_value(self):
        """Decrease the value of a running asset: separate entry for the
        decrease and the new value spread over all the pending lines, also
        after recomputing the depreciation board."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._modify_asset_value(asset, "2025-06-03", 620)
        prorata_line = asset.depreciation_line_ids.filtered(
            lambda line: line.line_date == date(2025, 6, 2)
        )
        decrease_line = asset.depreciation_line_ids.filtered("value_decrease")
        self.assertAlmostEqual(prorata_line.amount, 6.67, places=2)
        self.assertTrue(prorata_line.move_check)
        self.assertEqual(decrease_line.line_date, date(2025, 6, 3))
        self.assertAlmostEqual(decrease_line.amount, 73.33, places=2)
        self.assertTrue(decrease_line.move_id)
        self.assertNotEqual(decrease_line.move_id, prorata_line.move_id)
        expense_line = decrease_line.move_id.line_ids.filtered(
            lambda line: line.account_id == self.ict3Y.account_expense_depreciation_id
        )
        self.assertAlmostEqual(expense_line.debit, 73.33, places=2)
        self.assertAlmostEqual(asset.value_residual, 620, places=2)
        expected = [83.46] + [89.42] * 5 + [89.44]
        self._assert_pending_amounts(asset, expected)
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        self._assert_pending_amounts(asset, expected)
        # the rest of June: from the 3rd to the 30th
        self.assertEqual(asset._get_pending_depreciation_lines()[0].line_days, 28)
        asset._get_pending_depreciation_lines()[:2].create_move()
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        self._assert_pending_amounts(asset, expected[2:])

    def test_25_decrease_value_to_zero(self):
        """Decreasing the value to zero closes the asset."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._modify_asset_value(asset, "2025-06-03", 0)
        self.assertEqual(asset.state, "close")
        self.assertAlmostEqual(asset.value_residual, 0, places=2)
        self.assertFalse(asset._get_pending_depreciation_lines())

    def test_26_two_decreases_in_the_same_period(self):
        """A second change in the same period does not depreciate again the
        days already depreciated."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._modify_asset_value(asset, "2025-06-03", 620)
        self._modify_asset_value(asset, "2025-06-20", 500)
        june_depreciation = sum(
            asset.depreciation_line_ids.filtered(
                lambda line: line.line_date.month == 6
                and line.move_check
                and not line.value_decrease
            ).mapped("amount")
        )
        # 2 days at 100/month + 17 days of the 28 left at 83.46
        self.assertAlmostEqual(june_depreciation, 6.67 + 50.67, places=2)
        self.assertAlmostEqual(asset.value_residual, 500, places=2)
        self.assertAlmostEqual(
            sum(asset._get_pending_depreciation_lines().mapped("amount")),
            500,
            places=2,
        )

    def test_27_spread_residual_value_without_weights(self):
        """When all the planned amounts are zero, the value is spread in equal
        parts, so nothing is left without depreciating."""
        asset = self._create_monthly_asset_with_posted_lines(0)
        table = [
            {
                "lines": [
                    {"date": date(2025, 1, 31), "days": 31, "amount": 0.0},
                    {"date": date(2025, 2, 28), "days": 28, "amount": 0.0},
                ]
            }
        ]
        asset._spread_residual_value(table, 0, 0, False, 200)
        self.assertEqual([line["amount"] for line in table[0]["lines"]], [500, 500])

    def _increase_asset_value(self, asset, change_date, new_value):
        counterpart = self.env["account.account"].search(
            [("code", "=", "523900"), ("company_ids", "in", asset.company_id.ids)]
        ) or self.env["account.account"].create(
            {
                "code": "523900",
                "name": "Fixed asset suppliers",
                "account_type": "liability_current",
            }
        )
        wiz = (
            self.env["account.asset.modify"]
            .with_context(active_id=asset.id)
            .create(
                {
                    "reason": "Test",
                    "date": change_date,
                    "new_value": new_value,
                    "account_counterpart_id": counterpart.id,
                }
            )
        )
        wiz.modify()
        asset.invalidate_recordset()
        return counterpart

    def test_28_increase_value(self):
        """Increase the value of a running asset: the asset keeps its plan and a
        child asset is created for the increase, with its acquisition entry."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        assets_before = self.asset_model.search([])
        counterpart = self._increase_asset_value(asset, "2025-06-03", 800)
        self.assertEqual(self.asset_model.search([]) - assets_before, asset.child_ids)
        self._assert_pending_amounts(asset, [93.33] + [100.0] * 6)
        child = asset.child_ids
        self.assertEqual(child.state, "open")
        self.assertAlmostEqual(child.purchase_value, 106.67, places=2)
        self.assertEqual(child.date_start, date(2025, 6, 3))
        self.assertEqual(child.method, asset.method)
        self.assertEqual(child.method_time, "year")
        self.assertEqual(child.method_end, date(2025, 12, 31))
        self.assertEqual(child._get_depreciation_end_date(), date(2025, 12, 31))
        self.assertAlmostEqual(
            sum(child._get_pending_depreciation_lines().mapped("amount")),
            106.67,
            places=2,
        )
        create_line = child.depreciation_line_ids.filtered(
            lambda line: line.type == "create"
        )
        self.assertEqual(create_line.move_id.state, "posted")
        asset_line = create_line.move_id.line_ids.filtered(
            lambda line: line.account_id == self.ict3Y.account_asset_id
        )
        counterpart_line = create_line.move_id.line_ids.filtered(
            lambda line: line.account_id == counterpart
        )
        self.assertAlmostEqual(asset_line.debit, 106.67, places=2)
        self.assertEqual(asset_line.asset_id, child)
        self.assertAlmostEqual(counterpart_line.credit, 106.67, places=2)
        self.assertEqual(asset.child_count, 1)
        self.assertAlmostEqual(asset.gross_increase_value, 106.67, places=2)
        self.assertAlmostEqual(asset.total_book_value, 800, places=2)
        self.assertEqual(child.action_view_parent()["res_id"], asset.id)

    def test_29_parent_duration_change_moves_child_end_date(self):
        """When the duration of the parent changes, its value increases end with
        it, without changing their posted depreciations."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child = asset.child_ids
        child_posted_line = child._get_pending_depreciation_lines()[:1]
        child_posted_line.create_move()
        posted_amount = child_posted_line.amount
        asset.set_to_draft()
        asset.method_number = 18
        asset.compute_depreciation_board()
        child.invalidate_recordset()
        self.assertEqual(asset._get_depreciation_end_date(), date(2026, 6, 30))
        self.assertEqual(child.method_end, date(2026, 6, 30))
        self.assertEqual(child._get_depreciation_end_date(), date(2026, 6, 30))
        self.assertTrue(child_posted_line.move_check)
        self.assertEqual(child_posted_line.amount, posted_amount)
        self.assertAlmostEqual(child.value_residual, 106.67 - posted_amount, places=2)

    def test_30_increase_value_of_a_child(self):
        """An increase can only be made from the parent asset."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child = asset.child_ids
        child._get_pending_depreciation_lines()[:1].create_move()
        with self.assertRaisesRegex(UserError, "Make the increase from the parent"):
            self._increase_asset_value(child, "2025-07-01", 200)

    def test_31_decrease_value_of_a_child(self):
        """A decrease of a child asset only changes the child."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child = asset.child_ids
        child._get_pending_depreciation_lines()[:1].create_move()
        self._modify_asset_value(child, "2025-07-01", 50)
        self.assertAlmostEqual(child.value_residual, 50, places=2)
        self.assertTrue(child.depreciation_line_ids.filtered("value_decrease"))
        self.assertFalse(asset.depreciation_line_ids.filtered("value_decrease"))
        self._assert_pending_amounts(asset, [93.33] + [100.0] * 6)
        asset.invalidate_recordset()
        self.assertAlmostEqual(asset.total_book_value, 693.33 + 50, places=2)

    def _create_asset_with_posted_lines(
        self, method, salvage_value=0.0, method_time="year", posted=1
    ):
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.ict3Y.id,
                "purchase_value": 10000,
                "salvage_value": salvage_value,
                "date_start": "2025-01-01",
                "method": method,
                "method_progress_factor": 0.3,
                "method_time": method_time,
                "method_number": 5,
                "method_period": "year",
            }
        )
        asset.validate()
        asset._get_pending_depreciation_lines()[:posted].create_move()
        return asset

    def _check_decrease_keeps_plan_shape(self, asset):
        change_date = date(2026, 7, 1)
        prorata_amount = asset._get_prorata_depreciation(change_date)[1]
        planned = asset._get_pending_depreciation_lines().mapped("amount")
        planned[0] -= prorata_amount
        current_value = asset.purchase_value - asset.value_depreciated - prorata_amount
        self._modify_asset_value(asset, change_date, current_value - 1000)
        decrease_line = asset.depreciation_line_ids.filtered("value_decrease")
        self.assertEqual(decrease_line.line_date, change_date)
        self.assertAlmostEqual(decrease_line.amount, 1000, places=2)
        self.assertTrue(decrease_line.move_id)
        pending = asset._get_pending_depreciation_lines().mapped("amount")
        self.assertAlmostEqual(sum(pending), asset.value_residual, places=2)
        factor = sum(pending) / sum(planned)
        for planned_amount, amount in zip(planned[:-1], pending[:-1], strict=True):
            self.assertAlmostEqual(amount, planned_amount * factor, delta=0.01)
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        self.assertEqual(
            asset._get_pending_depreciation_lines().mapped("amount"), pending
        )
        asset._get_pending_depreciation_lines()[:1].create_move()
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        self.assertEqual(
            asset._get_pending_depreciation_lines().mapped("amount"), pending[1:]
        )

    def _check_increase_child_plan(self, asset):
        change_date = date(2026, 7, 1)
        prorata_amount = asset._get_prorata_depreciation(change_date)[1]
        planned = asset._get_pending_depreciation_lines().mapped("amount")
        planned[0] -= prorata_amount
        current_value = asset.purchase_value - asset.value_depreciated - prorata_amount
        self._increase_asset_value(asset, change_date, current_value + 2000)
        self._assert_pending_amounts(asset, planned)
        child = asset.child_ids
        self.assertEqual(child.method, asset.method)
        self.assertEqual(child.method_progress_factor, asset.method_progress_factor)
        self.assertEqual(child.method_time, "year")
        self.assertEqual(child.salvage_value, 0)
        self.assertEqual(
            child._get_depreciation_end_date(), asset._get_depreciation_end_date()
        )
        self.assertAlmostEqual(
            sum(child._get_pending_depreciation_lines().mapped("amount")),
            2000,
            places=2,
        )
        return child

    def test_32_decrease_value_degressive_linear(self):
        """A decrease of a degressive-linear asset keeps the shape of its plan,
        also after recomputing the depreciation board."""
        asset = self._create_asset_with_posted_lines("degr-linear")
        self._check_decrease_keeps_plan_shape(asset)

    def test_33_decrease_value_degressive(self):
        """A decrease of a degressive asset keeps the shape of its plan, also
        the remaining value of the last period."""
        asset = self._create_asset_with_posted_lines("degressive")
        self._check_decrease_keeps_plan_shape(asset)

    def test_34_increase_value_degressive_linear(self):
        """The value increase of a degressive-linear asset is depreciated with
        the same method and degressive factor until the end of the asset."""
        asset = self._create_asset_with_posted_lines("degr-linear")
        self._check_increase_child_plan(asset)

    def test_35_increase_value_degressive_number_of_depreciations(self):
        """The value increase of an asset with a number of depreciations ends
        on the end date of the asset."""
        asset = self._create_asset_with_posted_lines("degressive", method_time="number")
        child = self._check_increase_child_plan(asset)
        self.assertEqual(child.method_end, asset._get_depreciation_end_date())

    def test_36_modify_value_degressive_limit(self):
        """Degressive up to salvage value: the value cannot go below the salvage
        value, a decrease keeps it and the increase has no salvage value."""
        asset = self._create_asset_with_posted_lines("degr-limit", salvage_value=1000)
        with self.assertRaisesRegex(UserError, "salvage value"):
            self._modify_asset_value(asset, "2026-07-01", 900)
        self._modify_asset_value(asset, "2026-07-01", 3000)
        self.assertAlmostEqual(asset.value_residual, 3000, places=2)
        self.assertAlmostEqual(
            sum(asset._get_pending_depreciation_lines().mapped("amount")),
            2000,
            places=2,
        )
        asset = self._create_asset_with_posted_lines("degr-limit", salvage_value=1000)
        self._check_increase_child_plan(asset)

    def _remove_asset(self, asset, remove_date):
        early_removal = not asset.currency_id.is_zero(asset.value_residual)
        wiz = self.remove_model.with_context(
            active_id=asset.id, early_removal=early_removal
        ).create(
            {
                "date_remove": remove_date,
                "sale_value": 0.0,
                "posting_regime": "gain_loss_on_sale",
                "account_plus_value_id": self.company_data[
                    "default_account_revenue"
                ].id,
                "account_min_value_id": self.company_data["default_account_expense"].id,
            }
        )
        wiz.remove()
        asset.invalidate_recordset()

    def test_37_remove_parent_with_running_child(self):
        """A parent asset cannot be removed while a value increase is running."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child = asset.child_ids
        with self.assertRaisesRegex(UserError, "not removed: .*increase"):
            asset.remove()
        with self.assertRaisesRegex(UserError, "Remove them first"):
            self._remove_asset(asset, "2025-06-10")
        self.assertEqual(asset.state, "open")
        self.assertEqual(child.state, "open")

    def test_38_remove_parent_with_closed_child(self):
        """A parent asset cannot be removed while a value increase is closed
        but not removed."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child = asset.child_ids
        child._get_pending_depreciation_lines()[:1].create_move()
        self._modify_asset_value(child, "2025-07-01", 0)
        self.assertEqual(child.state, "close")
        with self.assertRaisesRegex(UserError, "Remove them first"):
            asset.remove()

    def test_39_remove_child_then_parent(self):
        """A value increase is removed alone with the removal wizard, and then
        the parent can be removed."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child = asset.child_ids
        self._remove_asset(child, "2025-06-10")
        self.assertEqual(child.state, "removed")
        self.assertEqual(asset.state, "open")
        self._assert_pending_amounts(asset, [93.33] + [100.0] * 6)
        self.assertTrue(asset.remove())
        asset._get_pending_depreciation_lines()[:1].create_move()
        self._remove_asset(asset, "2025-07-10")
        self.assertEqual(asset.state, "removed")

    def test_40_decrease_parent_to_zero_with_running_child(self):
        """A parent decreased to zero is closed while its value increase keeps
        running, and it can only be removed after the value increase."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child = asset.child_ids
        self._modify_asset_value(asset, "2025-06-04", 0)
        self.assertEqual(asset.state, "close")
        self.assertEqual(child.state, "open")
        self.assertAlmostEqual(child.value_residual, 106.67, places=2)
        with self.assertRaisesRegex(UserError, "Remove them first"):
            asset.remove()
        self._remove_asset(child, "2025-06-10")
        self._remove_asset(asset, "2025-06-10")
        self.assertEqual(asset.state, "removed")

    def test_41_child_cannot_be_set_to_draft(self):
        """A value increase is changed from its parent, not in draft."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        with self.assertRaisesRegex(UserError, "Modify the parent asset"):
            asset.child_ids.set_to_draft()
        self.assertEqual(asset.child_ids.state, "open")

    def test_42_child_method_cannot_be_changed(self):
        """The method and the duration of a value increase are managed from its
        parent, but its other fields can be changed."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child = asset.child_ids
        for vals in (
            {"method": "degressive"},
            {"method_end": "2026-12-31"},
            {"method_period": "year"},
            {"profile_id": self.car5y.id},
        ):
            with self.assertRaisesRegex(UserError, "managed from its parent"):
                child.write(vals)
        child.write({"note": "Engine improvement", "group_ids": [Command.clear()]})
        self.assertEqual(child.note, "Engine improvement")

    def _post_child_lines(self, asset, count):
        child = asset.child_ids
        posted_lines = child._get_pending_depreciation_lines()[:count]
        posted_lines.create_move()
        return child, posted_lines, posted_lines.mapped("amount")

    def _assert_child_board(self, child, posted_lines, posted_amounts):
        child.invalidate_recordset()
        self.assertTrue(all(posted_lines.mapped("move_check")))
        self.assertEqual(posted_lines.mapped("amount"), posted_amounts)
        self.assertAlmostEqual(
            sum(posted_amounts)
            + sum(child._get_pending_depreciation_lines().mapped("amount")),
            child.depreciation_base,
            places=2,
        )

    def test_43_parent_method_and_period_propagate(self):
        """The method, factor and period of a parent asset changed in draft are
        copied by its value increases when the parent is recomputed."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child = asset.child_ids
        asset.set_to_draft()
        asset.write(
            {
                "method": "degressive",
                "method_progress_factor": 0.4,
                "method_period": "quarter",
            }
        )
        asset.compute_depreciation_board()
        child.invalidate_recordset()
        self.assertEqual(child.method, "degressive")
        self.assertEqual(child.method_progress_factor, 0.4)
        self.assertEqual(child.method_period, "quarter")
        self.assertEqual(child.method_end, asset._get_depreciation_end_date())
        self.assertAlmostEqual(
            sum(child._get_pending_depreciation_lines().mapped("amount")),
            child.value_residual,
            places=2,
        )

    def test_44_propagation_keeps_child_posted_lines(self):
        """When the duration or the period of the parent changes, the posted
        depreciations of its value increase do not change and the value of the
        increase is still fully depreciated."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child, posted_lines, posted_amounts = self._post_child_lines(asset, 2)
        asset.set_to_draft()
        asset.method_number = 18
        asset.compute_depreciation_board()
        self.assertEqual(child.method_end, date(2026, 6, 30))
        self._assert_child_board(child, posted_lines, posted_amounts)
        # from monthly to yearly depreciations
        asset.write({"method_period": "year", "method_number": 2})
        asset.compute_depreciation_board()
        self.assertEqual(child.method_period, "year")
        self.assertEqual(child.method_end, date(2026, 12, 31))
        self._assert_child_board(child, posted_lines, posted_amounts)

    def test_45_shorten_parent_before_child_posted_line(self):
        """The parent must end after the last posted depreciation of its value
        increase (31/07/2025)."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child, posted_lines, posted_amounts = self._post_child_lines(asset, 2)
        asset.set_to_draft()
        for method_number in (6, 7):
            asset.method_number = method_number
            # assertRaises rolls back the changes made before the error
            with self.assertRaises(UserError) as error:
                asset.compute_depreciation_board()
            self.assertIn("must be after the last posted", str(error.exception))
            self.assertIn(child.display_name, str(error.exception))
            self.env.invalidate_all()
            self.assertEqual(asset._get_depreciation_end_date(), date(2025, 12, 31))
            self.assertEqual(child.method_end, date(2025, 12, 31))
            self._assert_child_board(child, posted_lines, posted_amounts)

    def test_46_cannot_delete_asset_with_children(self):
        """An asset with value increases cannot be deleted."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        asset.set_to_draft()
        with self.assertRaisesRegex(UserError, "it has value increases: .*increase"):
            asset.unlink()

    def test_47_two_increases(self):
        """Each increase creates its own child and the parent shows their total."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        asset._get_pending_depreciation_lines()[:1].create_move()
        self._increase_asset_value(asset, "2025-07-01", 700)
        children = asset.child_ids
        self.assertEqual(len(children), 2)
        self.assertEqual(
            children.mapped("date_start"), [date(2025, 7, 1), date(2025, 6, 3)]
        )
        self.assertAlmostEqual(asset.gross_increase_value, 206.67, places=2)
        self.assertAlmostEqual(
            asset.total_book_value,
            asset.value_residual + sum(children.mapped("value_residual")),
            places=2,
        )
        self.assertAlmostEqual(asset.total_book_value, 806.67, places=2)

    def test_48_decrease_parent_keeps_child(self):
        """A decrease of the parent does not change its value increase."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child = asset.child_ids
        child_amounts = child._get_pending_depreciation_lines().mapped("amount")
        self._modify_asset_value(asset, "2025-06-04", 600)
        child.invalidate_recordset()
        self.assertAlmostEqual(asset.value_residual, 600, places=2)
        self.assertEqual(
            child._get_pending_depreciation_lines().mapped("amount"), child_amounts
        )
        self.assertFalse(child.depreciation_line_ids.filtered("value_decrease"))
        self.assertAlmostEqual(child.value_residual, 106.67, places=2)

    def test_49_modify_value_lock_date(self):
        """The entries of a change cannot be in a locked period, including the
        prorata posted the day before the change."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        company = asset.company_id
        # the prorata of 02/06 is locked
        company.fiscalyear_lock_date = date(2025, 6, 2)
        with self.assertRaisesRegex(UserError, "locked period"):
            self._modify_asset_value(asset, "2025-06-03", 620)
        # no prorata: 31/05 is posted, but the change of 01/06 is locked
        company.fiscalyear_lock_date = date(2025, 6, 1)
        with self.assertRaisesRegex(UserError, "locked period"):
            self._modify_asset_value(asset, "2025-06-01", 620)
        self.assertFalse(asset.depreciation_line_ids.filtered("value_decrease"))
        company.fiscalyear_lock_date = date(2025, 5, 31)
        self._modify_asset_value(asset, "2025-06-01", 620)
        self.assertAlmostEqual(asset.value_residual, 620, places=2)

    def test_50_modify_value_before_start_date(self):
        """The date of a change cannot be before the start of the asset."""
        asset = self._create_monthly_asset_with_posted_lines(0)
        with self.assertRaisesRegex(UserError, "before the start date"):
            self._modify_asset_value(asset, "2024-12-31", 1000)

    def _get_message(self, asset, text):
        messages = asset.message_ids.filtered(lambda message: text in message.body)
        self.assertEqual(len(messages), 1)
        return messages.body

    def test_51_decrease_value_message(self):
        """A decrease is logged in the chatter of the asset, with the values
        before and after, the reason and the entries."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._modify_asset_value(asset, "2025-06-03", 620)
        body = self._get_message(asset, "Value decrease on")
        self.assertIn("693.33", body)
        self.assertIn("620.00", body)
        self.assertIn("Reason: Test", body)
        prorata_line = asset.depreciation_line_ids.filtered(
            lambda line: line.line_date == date(2025, 6, 2)
        )
        decrease_line = asset.depreciation_line_ids.filtered("value_decrease")
        for move in prorata_line.move_id | decrease_line.move_id:
            self.assertIn(move.display_name, body)

    def test_52_increase_value_messages(self):
        """An increase is logged in the chatter of the parent, with a link to the
        new asset, and in the chatter of the new asset, with a link to the
        parent and to the entry."""
        asset = self._create_monthly_asset_with_posted_lines(5)
        self._increase_asset_value(asset, "2025-06-03", 800)
        child = asset.child_ids
        move = child.account_move_line_ids.move_id
        body = self._get_message(asset, "Value increase on")
        self.assertIn("800.00", body)
        self.assertIn(child.display_name, body)
        self.assertIn(move.display_name, body)
        body = self._get_message(child, "Created as a value increase of")
        self.assertIn(asset.display_name, body)
        self.assertIn("Reason: Test", body)
        self.assertIn(move.display_name, body)
