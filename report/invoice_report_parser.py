from collections import OrderedDict

from odoo import models, api, fields, tools
from odoo.tools.misc import formatLang
from odoo import SUPERUSER_ID


class InvoiceReport(models.AbstractModel):    
    _name = 'report.account.report_invoice'
    _description = 'Reporte de Factura' 
    
    def _get_lines_by_template(self, invoice):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        show_discount_on_report = ICPSudo.get_param('show_discount_on_report', default='percentaje')
        data_by_template = OrderedDict()
        colors = []
        line_key = False
        company = invoice.company_id or self.env.user.company_id
        atribute_size = [company.size_calzado_id.id, company.size_vestuario_id.id]
        for line in invoice.invoice_line_ids:
            colors = []
            for atribute in line.product_id.attribute_value_ids.filtered(lambda x: x.attribute_id == company.color_id):
                colors.append(atribute.name)
            colors = ", ".join(colors)
            line_key = invoice._get_invoice_line_key_to_group(line)
            data_by_template.setdefault(line_key, {})
            data_by_template[line_key].setdefault('price_subtotal', 0.0)
            data_by_template[line_key].setdefault('price_tax_included', 0.0)
            data_by_template[line_key].setdefault('quantity', 0.0)
            data_by_template[line_key].setdefault('attributes', [])
            data_by_template[line_key]['quantity'] += line.quantity
            data_by_template[line_key]['default_code'] = line.product_id.default_code
            data_by_template[line_key]['name'] = line.product_id.name or line.name
            data_by_template[line_key]['product_template'] = line.product_id.product_tmpl_id
            data_by_template[line_key]['uom_id'] = line.uom_id.name
            data_by_template[line_key]['discount'] = line.discount if show_discount_on_report == 'percentaje' else line.discount_value
            data_by_template[line_key]['price_subtotal'] += line.price_subtotal
            data_by_template[line_key]['price_tax_included'] += line.price_total
            data_by_template[line_key]['price_unit'] = line.price_unit  
            data_by_template[line_key]['color'] = colors
            for atribute in line.product_id.attribute_value_ids:
                if atribute.attribute_id.id in atribute_size:
                    data_by_template[line_key]['attributes'].append("<b>%s</b>/%s" % (atribute.name, formatLang(invoice.env, line.quantity, dp='Product Unit of Measure')))
        return list(data_by_template.values())

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}
        invoice_model = self.env['account.invoice']
        ICPSudo = self.env['ir.config_parameter'].sudo()
        docargs = {
            'doc_ids': docids,
            'doc_model': invoice_model._name,
            'data': data,
            'docs': invoice_model.sudo().browse(docids),
            'get_lines': self._get_lines_by_template,
            'show_atributes_on_reports': ICPSudo.get_param('show_atributes_on_reports', default='hide_attributes'),
            'show_discount_on_report': ICPSudo.get_param('show_discount_on_report', default='percentaje'),
        }
        #cuando todos los registros a imprimir son boleta electronica
        #pasar el formato de papel ticket
        #para que de ahi se tome el ancho, alto, etc
        invoice_ticket_recs = docargs['docs'].filtered(lambda o: o.document_class_id.sii_code not in [29, 30, 32, 33, 34, 40, 43, 45, 46, 55, 56, 60, 61, 110, 111, 112] or o.ticket)
        if invoice_ticket_recs and len(invoice_ticket_recs) == len(docargs['docs']):
            docargs.update({
                'data_report_paperformat_id': self.env.ref('l10n_cl_fe.paperformat_pos_boleta_ticket').id,
            })  
        return docargs


class InvoiceReportPayment(models.AbstractModel):    
    _inherit = 'report.account.report_invoice'
    _name = 'report.account.report_invoice_with_payments'


class InvoiceReportCedible(models.AbstractModel):    
    _inherit = 'report.account.report_invoice'
    _name = 'report.l10n_cl_fe.invoice_cedible'

    @api.model
    def _get_report_values(self, docids, data=None):
        docargs = super(InvoiceReportCedible, self)._get_report_values(docids, data)
        docargs['cedible'] = True
        return docargs
