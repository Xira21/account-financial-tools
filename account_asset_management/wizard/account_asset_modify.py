# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


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

    @api.depends("asset_id", "date")
    def _compute_current_value(self):
        for wiz in self:
            asset = wiz.asset_id
            wiz.current_value = asset.purchase_value - asset.value_depreciated

    @api.depends("asset_id")
    def _compute_new_value(self):
        for wiz in self:
            wiz.new_value = wiz.current_value

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

    def modify(self):
        self.ensure_one()
        self._check_modify()
        # TODO: depreciate until the day before, then decrease or increase
        return {"type": "ir.actions.act_window_close"}
