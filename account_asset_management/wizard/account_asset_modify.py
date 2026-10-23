# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date, formatLang


class AccountAssetModify(models.TransientModel):
    _name = "account.asset.modify"
    _description = "Modify Asset Value"

    asset_id = fields.Many2one(
        comodel_name="account.asset",
        string="Asset",
        required=True,
        readonly=True,
        default=lambda self: self.env.context.get("active_id"),
    )
    company_id = fields.Many2one(related="asset_id.company_id")
    currency_id = fields.Many2one(related="asset_id.currency_id")
    date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        help="Date of the value change. The asset is depreciated with the "
        "current plan until the day before this date.",
    )
    reason = fields.Char(required=True)
    new_value = fields.Monetary(
        string="New Value",
        compute="_compute_new_value",
        store=True,
        readonly=False,
        help="New net book value of the asset at the date of the change.",
    )
    purchase_value = fields.Monetary(related="asset_id.purchase_value")
    prorata_amount = fields.Monetary(compute="_compute_current_value")
    depreciated_value = fields.Monetary(
        compute="_compute_current_value",
        help="Depreciation posted until the day before the date of the change, "
        "including the prorata of the current period.",
    )
    current_value = fields.Monetary(
        compute="_compute_current_value",
        help="Net book value of the asset at the date of the change: "
        "Purchase Value - Depreciated Value.",
    )
    value_difference = fields.Monetary(
        string="Difference",
        compute="_compute_value_difference",
    )
    modification_type = fields.Selection(
        selection=[("increase", "Increase"), ("decrease", "Decrease")],
        string="Type",
        compute="_compute_value_difference",
    )
    info_message = fields.Text(compute="_compute_info_message")

    @api.depends("asset_id", "date")
    def _compute_current_value(self):
        for wiz in self:
            asset = wiz.asset_id
            prorata_amount = 0.0
            pending_lines = asset._get_pending_depreciation_lines()
            if wiz.date and pending_lines and wiz.date <= pending_lines[0].line_date:
                prorata_amount = asset._get_prorata_depreciation(wiz.date)[1]
            wiz.prorata_amount = prorata_amount
            wiz.depreciated_value = asset.value_depreciated + prorata_amount
            wiz.current_value = asset.purchase_value - wiz.depreciated_value

    @api.depends("current_value")
    def _compute_new_value(self):
        for wiz in self:
            wiz.new_value = wiz.current_value

    @api.depends("date", "prorata_amount")
    def _compute_info_message(self):
        for wiz in self:
            messages = []
            if wiz.prorata_amount:
                messages.append(
                    self.env._(
                        "A depreciation entry of %(amount)s will be posted on "
                        "%(date)s, for the depreciation until the day before "
                        "the change.",
                        amount=formatLang(
                            self.env, wiz.prorata_amount, currency_obj=wiz.currency_id
                        ),
                        date=format_date(self.env, wiz.date - relativedelta(days=1)),
                    )
                )
            wiz.info_message = "\n".join(messages)

    @api.depends("new_value", "current_value")
    def _compute_value_difference(self):
        for wiz in self:
            difference = wiz.new_value - wiz.current_value
            comparison = wiz.currency_id.compare_amounts(difference, 0)
            wiz.value_difference = difference
            if comparison > 0:
                wiz.modification_type = "increase"
            elif comparison < 0:
                wiz.modification_type = "decrease"
            else:
                wiz.modification_type = False

    def _check_modify(self):
        self.ensure_one()
        asset = self.asset_id
        currency = self.currency_id
        if asset.state != "open":
            raise UserError(self.env._("Only running assets can be modified."))
        if not self.modification_type:
            raise UserError(
                self.env._("The new value must be different from the current value.")
            )
        if currency.compare_amounts(self.new_value, asset.salvage_value) < 0:
            raise UserError(
                self.env._(
                    "The new value cannot be lower than the salvage value (%s).",
                    asset.salvage_value,
                )
            )
        posted_lines = asset._get_posted_depreciation_lines()
        if posted_lines and self.date <= posted_lines[0].line_date:
            raise UserError(
                self.env._(
                    "The date must be after the last posted depreciation (%s).",
                    posted_lines[0].line_date,
                )
            )
        pending_lines = asset._get_pending_depreciation_lines()
        if pending_lines and self.date > pending_lines[0].line_date:
            raise UserError(
                self.env._(
                    "All the depreciation lines prior to the date of the change "
                    "must be posted (%s).",
                    pending_lines[0].line_date,
                )
            )

    def modify(self):
        self.ensure_one()
        self._check_modify()
        self.asset_id._depreciate_until(self.date)
        # TODO: decrease or increase
        return {"type": "ir.actions.act_window_close"}
