# -*- coding: utf-8 -*-
import base64
import logging

from odoo import fields, models, api, tools
from odoo.tools.translate import _
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class ProccessMail(models.Model):
    _name = 'mail.message.dte'
    _description = "DTE Recibido"
    _inherit = ['mail.thread']

    name = fields.Char(
        string="Nombre Envío",
        readonly=True,
    )
    mail_id = fields.Many2one(
        'mail.message',
        string="Email",
        readonly=True,
        ondelete='cascade',
    )
    document_ids = fields.One2many(
        'mail.message.dte.document',
        'dte_id',
        string="Documents",
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string="Compañía",
        readonly=True,
    )

    _order = 'create_date DESC'

    def pre_process(self):
        self.process_message(pre=True)

    @api.multi
    def process_message(self, pre=False, option=False):
        created = []
        for r in self:
            mail_id = r.sudo().mail_id or self.env['mail.message'].sudo().search(
                [('model', '=', 'mail.message.dte'), ('res_id', '=', r.id)],
                limit=1,)
            for att in mail_id.attachment_ids:
                if not att.name:
                    continue
                name = att.name.upper()
                if att.mimetype in ['text/plain'] and name.find('.XML') > -1:
                    try:
                        is_dte_valid = True
                        dtes = self.env['sii.dte.upload_xml.wizard']._get_dtes(xml_file=base64.b64decode(att.datas).decode('ISO-8859-1'))
                        for dte in dtes:
                            documento = dte.find("Documento")
                            tipo_dte = documento.find("Encabezado/IdDoc/TipoDTE")
                            if tipo_dte is None:
                                is_dte_valid = False
                        if not is_dte_valid:
                            _logger.warning(f"Archivo {name} no cumple la estructura xml esperada, no se procesara")
                    except Exception as ex:
                        _logger.warning(f"Archivo {name} no cumple la estructura xml esperada, no se procesara. Detalles: {tools.ustr(ex)}")
                        continue
                    vals = {
                        'xml_file': att.datas,
                        'filename': att.name,
                        'pre_process': pre,
                        'dte_id': r.id,
                        'option': option,
                    }
                    val = self.env['sii.dte.upload_xml.wizard'].create(vals)
                    created.extend(val.confirm(ret=True))
        xml_id = 'l10n_cl_fe.action_dte_process'
        result = self.env.ref('%s' % (xml_id)).read()[0]
        if created:
            ctx = self.env.context.copy()
            ctx.update({
                'active_model': result['res_model'],
                'active_ids': created,
                'active_id': created[0],
            })
            result['context'] = ctx
            domain = safe_eval(result.get('domain', '[]'))
            domain.append(('id', 'in', created))
            result['domain'] = domain
        return result
