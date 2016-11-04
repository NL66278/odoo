# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, models, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def invoice_pay_customer(self):
        if not self.ids:
            return []
        return {
            'name':_("Pay Invoice"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.pay.invoice.wizard',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {'invoice_id': self.ids[0],}
        }
