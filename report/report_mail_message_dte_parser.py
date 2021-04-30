from odoo import models, api, fields, tools
from odoo.tools.misc import formatLang
from odoo import SUPERUSER_ID


class MailDteMessageReport(models.AbstractModel):    
    _name = 'report.l10n_cl_fe.report_mail_dte_message'
    _description = 'Reporte de factura desde XML' 

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}
        xml_dte_model = self.env['mail.message.dte.document']
        docargs = {
            'doc_ids': docids,
            'doc_model': xml_dte_model._name,
            'data': data,
            'docs': xml_dte_model.sudo().browse(docids),
        }
        return docargs
