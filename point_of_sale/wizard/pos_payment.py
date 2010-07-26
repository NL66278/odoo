# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import netsvc
from osv import osv,fields
from tools.translate import _
import pos_box_entries
import time
from decimal import Decimal
from tools.translate import _
import pos_receipt

class pos_make_payment(osv.osv_memory):
    _name = 'pos.make.payment'
    _description = 'Point of Sale Payment'

    def default_get(self, cr, uid, fields, context):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        res = super(pos_make_payment, self).default_get(cr, uid, fields, context=context)

        active_id = context and context.get('active_id',False)
        if active_id:
            j_obj = self.pool.get('account.journal')
            company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
            journal = j_obj.search(cr, uid, [('type', '=', 'cash'), ('company_id', '=', company_id)])

            if journal:
                journal = journal[0]
            else:
                journal = None
            wf_service = netsvc.LocalService("workflow")

            order_obj=self.pool.get('pos.order')
            order = order_obj.browse(cr, uid, active_id, context)
            #get amount to pay
            amount = order.amount_total - order.amount_paid
            if amount <= 0.0:
                context.update({'flag': True})
                order_obj.action_paid(cr, uid, [active_id], context)
            elif order.amount_paid > 0.0:
                order_obj.write(cr, uid, [active_id], {'state': 'advance'})
            invoice_wanted_checked = False

            current_date = time.strftime('%Y-%m-%d')

            if 'journal' in fields:
                res.update({'journal':journal})
            if 'amount' in fields:
                res.update({'amount':amount})
            if 'invoice_wanted' in fields:
                res.update({'invoice_wanted':invoice_wanted_checked})
            if 'payment_date' in fields:
                res.update({'payment_date':current_date})
            if 'payment_name'  in fields:
                res.update({'payment_name':'Payment'})
        return res

    def view_init(self, cr, uid, fields_list, context=None):
        res = super(pos_make_payment, self).view_init(cr, uid, fields_list, context=context)
        active_id = context and context.get('active_id', False) or False
        if active_id:
            order = self.pool.get('pos.order').browse(cr, uid, active_id)
            if not order.lines:
                raise osv.except_osv('Error!','No order lines defined for this sale ')
        return True

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
             Changes the view dynamically

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary

             @return: New arch of view.

        """


        result = super(pos_make_payment, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        active_model = context.get('active_model')
        active_id = context.get('active_id', False)
        if not active_id or (active_model and active_model != 'pos.order'):
            return result

        order = self.pool.get('pos.order').browse(cr, uid, active_id)
        if order.amount_total == order.amount_paid:
            result['arch'] = """ <form string="Make Payment" colspan="4">
                            <group col="2" colspan="2">
                                <label string="Do you want to print the Receipt?" colspan="4"/>
                                <separator colspan="4"/>
                                <button icon="gtk-cancel" special="cancel" string="No" readonly="0"/>
                                <button name="print_report" string="Print Receipt" type="object" icon="gtk-print"/>
                            </group>
                        </form>
                    """
        return result

    def check(self, cr, uid, ids, context):

        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print invoice (if wanted) or ticket.
        """
        active_id = context and context.get('active_id',False)
        order_obj = self.pool.get('pos.order')
        jrnl_obj = self.pool.get('account.journal')
        order = order_obj.browse(cr, uid, active_id, context)
        order_name = order.name
        amount = order.amount_total - order.amount_paid
        data =  self.read(cr, uid, ids)[0]

        # Todo need to check ...
        if amount !=0.0:
            invoice_wanted = data['invoice_wanted']
            jrnl_used=False
            if data.get('journal',False):
                jrnl_used=jrnl_obj.browse(cr, uid, data['journal'])
            order_obj.write(cr, uid, [active_id], {'invoice_wanted': invoice_wanted})
            order_obj.add_payment(cr, uid, active_id, data, context=context)

        res_obj = self.pool.get('res.company')
        inv_ref = self.pool.get('account.invoice')
        inv_line_ref = self.pool.get('account.invoice.line')
        product_obj= self.pool.get('product.product')
        inv_ids = []
        for order in self.pool.get('pos.order').browse(cr, uid, ids, context):
#            curr_c = order.user_salesman_id.company_id
            make_obj = self.pool.get('pos.make.payment').browse(cr, uid, uid)
        if invoice_wanted:
            if order.invoice_id:
                inv_ids.append(order.invoice_id.id)
#                continue
#            if not make_obj.partner_id:
#                raise osv.except_osv(_('Error'), _('Please provide a partner for the sale.'))
            acc= make_obj.partner_id.property_account_receivable.id
            inv = {
                'name': 'Invoice from POS: '+order_name,
                'origin': order_name,
                'account_id':acc,
                'journal_id':order.sale_journal.id or None,
                'type': 'out_invoice',
                'reference': order.name,
                'partner_id': make_obj.partner_id.id,
                'comment': order.note or '',
            }
            inv.update(inv_ref.onchange_partner_id(cr, uid, [], 'out_invoice', make_obj.partner_id.id)['value'])
            if not inv.get('account_id', None):
                inv['account_id'] = acc
            inv_id = inv_ref.create(cr, uid, inv, context)
            self.write(cr, uid, [order.id], {'invoice_id': inv_id, 'state': 'invoiced'})
            inv_ids.append(inv_id)
            for line in order.lines:
                inv_line = {
                    'invoice_id': inv_id,
                    'product_id': line.product_id.id,
                    'quantity': line.qty,
                }
                inv_name = product_obj.name_get(cr, uid, [line.product_id.id], context=context)[0][1]

                inv_line.update(inv_line_ref.product_id_change(cr, uid, [],
                                                               line.product_id.id,
                                                               line.product_id.uom_id.id,
                                                               line.qty, partner_id = make_obj.partner_id.id, fposition_id=make_obj.partner_id.property_account_position.id)['value'])
#                inv_line['price_unit'] = line.price_unit
#                inv_line['discount'] = line.discount
#                inv_line['account_id'] = acc
#                inv_line['name'] = inv_name
                inv_line['price_unit'] = amount
                inv_line['discount'] = line.discount
                inv_line['account_id'] = acc
                inv_line['name'] = inv_name
                inv_line['invoice_line_tax_id'] = ('invoice_line_tax_id' in inv_line)\
                    and [(6, 0, inv_line['invoice_line_tax_id'])] or []
                inv_line_ref.create(cr, uid, inv_line, context)
        for i in inv_ids:
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'account.invoice', i, 'invoice_open', cr)
#        return inv_ids
        # Todo need to check
#        if amount<=0.0:
#            context.update({'flag':True})
#            order_obj.action_paid(cr,uid,[active_id],context)

#    def test_paid(self, cr, uid, ids, context=None):
#        """ Test all amount is paid for this order
#        @return: True
#        """
#        for order in self.browse(cr, uid, ids, context):
#            if order.lines and not order.amount_total:
#                return True
#            if (not order.lines) or (not order.statement_ids) or \
#                Decimal(str(order.amount_total))!=Decimal(str(order.amount_paid)):
#                return False
#        return True
#        if order_obj.test_paid(cr, uid, [active_id]):
        if order_obj.browse(cr, uid, [active_id]):
            if make_obj.partner_id and make_obj.invoice_wanted:
                order_obj.write(cr, uid, [active_id],{'state':'paid'})
                if context.get('return'):
                    order_obj.write(cr, uid, [active_id],{'state':'done'})
                else:
                     order_obj.write(cr, uid, [active_id],{'state':'paid'})
                return self.print_report(cr, uid, ids, context)
#                return self.create_invoice(cr, uid, ids, context)
            else:
                context.update({'flag': True})
                order_obj.action_paid(cr, uid, [active_id], context)
                if context.get('return'):
                    order_obj.write(cr, uid, [active_id],{'state':'done'})
                else:
                     order_obj.write(cr, uid, [active_id],{'state':'paid'})
                return self.print_report(cr, uid, ids, context)
        if order.amount_paid > 0.0:
            context.update({'flag': True})
            # Todo need to check
            order_obj.action_paid(cr, uid, [active_id], context)
            self.pool.get('pos.order').write(cr, uid, [active_id],{'state':'advance'})
            return self.print_report(cr, uid, ids, context)
#        return {}
        return inv_ids


    def create_invoice(self, cr, uid, ids, context):

        """
          Create  a invoice
        """
        wf_service = netsvc.LocalService("workflow")
        active_ids = [context and context.get('active_id',False)]
        for i in active_ids:
            wf_service.trg_validate(uid, 'pos.order', i, 'invoice', cr)
        datas = {'ids' : context.get('active_id', [])}
        return {
                'type' : 'ir.actions.report.xml',
                'report_name':'pos.invoice',
                'datas' : datas,
        }

    def print_report(self, cr, uid, ids, context=None):
        """
         @summary: To get the date and print the report
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return : retrun report
        """
        if not context:
            context={}
        active_id=context.get('active_id',[])
        datas = {'ids' : [active_id]}
        res =  {}
        datas['form'] = res

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos.receipt',
            'datas': datas,
       }

    _columns = {
        'journal':fields.selection(pos_box_entries.get_journal, "Cash Register",required=True),
        'product_id': fields.many2one('product.product', "Acompte"),
        'amount':fields.float('Amount', digits=(16,2) ,required= True),
        'payment_name': fields.char('Payment name', size=32, required=True),
        'payment_date': fields.date('Payment date', required=True),
        'is_acc': fields.boolean('Accompte'),
        'invoice_wanted': fields.boolean('Invoice'),
        'num_sale':fields.char('Num.File', size=32),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'),
        'partner_id': fields.many2one('res.partner', 'Customer'),
        'invoice_id': fields.many2one('account.invoice', 'Invoice'),
        'state': fields.selection([('draft', 'Draft'), ('payment', 'Payment'),
                                    ('advance','Advance'),
                                   ('paid', 'Paid'), ('done', 'Done'), ('invoiced', 'Invoiced'), ('cancel', 'Cancel')],
                                  'State', readonly=True, ),
    }

pos_make_payment()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

