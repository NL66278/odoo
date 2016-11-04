# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _


class AccountPayInvoiceWizard(models.TransientModel):
    _name = 'account.pay.invoice.wizard'
    _description = 'Register payment for invoice'

    @api.model
    def default_get(self, vals):
        """Fill defaults from invoice info."""
        res = super(AccountPayInvoiceWizard, self).default_get(vals)
        invoice_id = self.env.context.get('invoice_id')
        invoice = self.env['account.invoice'].browse(invoice_id)
        res.update({
            'invoice_id': invoice_id,
            'payment_expected_currency_id': invoice.currency_id.id,
            'currency_id': invoice.currency_id.id,
            'partner_id': self.env['res.partner']._find_accounting_partner(
                invoice.partner_id).id,
            'amount': (
                invoice.type in ('out_refund', 'in_refund') and
                -invoice.residual or
                invoice.residual
            ),
            'reference': invoice.name,
            'close_after_process': True,
            'invoice_type': invoice.type,
            'type': (
                invoice.type in ('out_invoice', 'out_refund') and
                'receipt' or
                'payment'
            ),
        })
        return res

    @api.multi
    def _get_journal_currency(self):
        """Determine currency from journal."""
        for rec in self:
            rec.currency_id = (
                rec.journal_id.currency_id or
                rec.company_id.currency_id or
                False
            )

    state = fields.Selection(
        selection=[('start','start'),('finish','finish')],
        string='State',
        readonly=True,
    )
    invoice_id = fields.Many2one(
        comodel_name='account_invoice',
        string='Invoice',
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        readonly=True,
        help="Customer for invoice."
    )
    amount = fields.Float(
        string='Amount',
        help="Actual amount paid"
    )
    amount_original = fields.Float(
        string='Amount',
        help="Total amount to pay"
    )
    amount_unreconciled = fields.Float(
        string='Amount',
        help="Amount still to pay"
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Account to be reconciled',
        readonly=True,
        help="Debit account for invoice."
    )
    writeoff_amount = fields.Float(
        string='Amount to write off',
        help="Actual amount paid"
    )
    writeoff_acc_id = fields.Many2one(
        comodel_name='account.account',
        string='Account for write off',
        help="Account to register write off amounts"
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        required=True,
        help="Journal for bank or cash payments"
    )
    date = fields.Date(
        string='Date',
    )
    period_id = fields.Many2one(
        comodel_name='account.period',
        string='Period',
    )
    max_amount = fields.Float(
        string='Maximum write-off amount',
    )
    allow_write_off = fields.Boolean(
        string='Allow write off',
    )
    name = fields.Char(
        string='Memo',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_get_journal_currency',
        string='Currency',
        readonly=True,
        required=True,
    )
    payment_expected_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Invoice currency',
        readonly=True,
    )
    reference = fields.Char(
        string='Ref #',
        help="Transaction reference number.",
    )
    pre_line = fields.Boolean(
        string='Previous Payments ?'
    )
    type = fields.Selection(
        selection=[
            ('payment', 'Payment'),
            ('receipt', 'Receipt'),
        ],
        string='Type',
        required=True,
        readonly=True,
    )
    payment_option = fields.Selection(
        selection=[
            ('without_writeoff', 'Keep Open'),
            ('with_writeoff', 'Reconcile Payment Balance'),
        ],
        string='Payment Difference',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="This field helps you to choose what you want to do with the"
             " eventual difference between the paid amount and the sum of"
             " allocated amounts.\n"
             "You can either choose to keep open this difference on the"
             " partner's account, or reconcile it with the payment(s)"
    )
    comment = fields.Char(
        string='Counterpart Comment',
    )
    analytic_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Write-Off Analytic Account',
    )

    @api.multi
    def register_payment(self):
        """Fire action to actually register payment."""
        voucher_model = self.env['account.voucher']
        # Need to create payment voucher object first
        rec = self[0]
        vals = {
            'type': rec.type,
            'state': 'draft',
            'journal_id': rec.journal_id.id,
            'partner_id': rec.partner_id.id,
            'writeoff_acc_id': rec.writeoff_acc_id.id,
            'payment_option': rec.payment_option,
            'account_id': rec.account_id.id,
            'analytic_id': rec.analytic_id.id,
            'period_id': rec.period_id.id,
            'date': rec.date,
            'amount': rec.amount,
        }
        payment_voucher = voucher_model.create(vals)
        # Then call workflow
        payment_voucher.button_proforma_voucher()
        # close window
        return []
