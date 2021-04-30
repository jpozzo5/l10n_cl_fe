# -*- coding: utf-8 -*-
from odoo import fields, models, api, tools
from odoo.tools.translate import _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
import odoo.addons.decimal_precision as dp
import logging
from lxml import etree
import pytz
import logging
_logger = logging.getLogger(__name__)

try:
    from facturacion_electronica import facturacion_electronica as fe
except Exception as e:
    _logger.warning("Problema al cargar Facturación electrónica: %s" % str(e))

allowed_docs = [29, 30, 32, 33, 34, 35, 38, 39, 40,
                41, 43, 45, 46, 48, 53, 55, 56, 60,
                61, 101, 102, 103, 104, 105, 106, 108,
                109, 110, 111, 112, 175, 180, 185, 900,
                901, 902, 903, 904, 905, 906, 907, 909,
                910, 911, 914, 918, 919, 920, 921, 922,
                924, 500, 501,
                ]


class Libro(models.Model):
    _name = "account.move.book"
    _description = 'Libro de Compra / Venta DTE'

    sii_xml_request = fields.Many2one(
        'sii.xml.envio',
        string='SII XML Request',
        copy=False)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('NoEnviado', 'No Enviado'),
        ('EnCola', 'En Cola'),
        ('Enviado', 'Enviado'),
        ('Aceptado', 'Aceptado'),
        ('Rechazado', 'Rechazado'),
        ('Reparo', 'Reparo'),
        ('Proceso', 'Proceso'),
        ('Reenviar', 'Reenviar'),
        ('Anulado', 'Anulado')],
        string='Resultado',
        index=True,
        readonly=True,
        default='draft',
        track_visibility='onchange',
        copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user create invoice, an invoice number is generated. Its in open status till user does not pay invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    move_ids = fields.Many2many('account.move',
        readonly=True,
        states={'draft': [('readonly', False)]})

    tipo_libro = fields.Selection([
        ('ESPECIAL','Especial'),
        ('MENSUAL','Mensual'),
        ('RECTIFICA', 'Rectifica'),
        ],
        string="Tipo de Libro",
        default='MENSUAL',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    tipo_operacion = fields.Selection(
        [
            ('COMPRA','Compras'),
            ('VENTA','Ventas'),
            ('BOLETA','Boleta Electrónica'),
        ],
        string="Tipo de operación",
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    tipo_envio = fields.Selection([
        ('AJUSTE','Ajuste'),
        ('TOTAL','Total'),
        ('PARCIAL','Parcial'),
        ('TOTAL','Total'),
        ],
        string="Tipo de Envío",
        default="TOTAL",
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    folio_notificacion = fields.Char(
        string="Folio de Notificación",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    impuestos = fields.One2many(
        'account.move.book.tax',
        'book_id',
        string="Detalle Impuestos",
    )
    resumen_ids = fields.One2many('account.move.book.resume', 'book_id', u'Resumen por Tipo Doc', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True,
        track_visibility='always',
    )
    total_afecto = fields.Monetary(
        string="Total Afecto",
        readonly=True,
        compute="set_resumen",
        store=True,
    )
    total_exento = fields.Monetary(
        string="Total Exento",
        readonly=True,
        compute='set_resumen',
        store=True,
    )
    total_iva = fields.Monetary(
        string="Total IVA",
        readonly=True,
        compute='set_resumen',
        store=True,
    )
    total_otros_imps = fields.Monetary(
        string="Total Otros Impuestos",
        readonly=True,
        compute='set_resumen',
        store=True,
    )
    total = fields.Monetary(
        string="Total Impuestos",
        readonly=True,
        compute='set_resumen',
        store=True,
    )
    periodo_tributario = fields.Char(
        string='Periodo Tributario',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda *a: datetime.now().strftime('%Y-%m'),
    )
    company_id = fields.Many2one(
        'res.company',
        string="Compañía",
        required=True,
        default=lambda self: self.env.user.company_id.id,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    name = fields.Char(
        string="Detalle",
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    fact_prop = fields.Float(
        string="Factor proporcionalidad",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    nro_segmento = fields.Integer(
        string="Número de Segmento",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    date = fields.Date(
        string="Fecha",
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: fields.Date.context_today(self),)
    boletas = fields.One2many('account.move.book.boletas',
        'book_id',
        string="Boletas",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    codigo_rectificacion = fields.Char(
        string="Código de Rectificación",
    )
    sii_result = fields.Selection(
            [
                ('draft', 'Borrador'),
                ('NoEnviado', 'No Enviado'),
                ('Enviado', 'Enviado'),
                ('Aceptado', 'Aceptado'),
                ('Rechazado', 'Rechazado'),
                ('Reparo', 'Reparo'),
                ('Proceso', 'Proceso'),
                ('Reenviar', 'Reenviar'),
                ('Anulado', 'Anulado')
            ],
            related="state",
        )
    
    @api.multi
    def get_all_taxes(self, date_start, date_end):
        # no se consideran las boletas electronicas(39) ya que estas se toman del consumo de folio
        SQL = """
            SELECT DISTINCT t.account_tax_id
            FROM pos_order_line pl
                INNER JOIN pos_order p ON p.id = pl.order_id
                INNER JOIN sii_document_class c ON c.id = p.document_class_id
                INNER JOIN account_tax_pos_order_line_rel t ON t.pos_order_line_id = pl.id
            WHERE c.sii_code IN (35, 38, 41, 70, 71)
                AND p.date_order >= %(date_start)s AND p.date_order <= %(date_end)s
        """
        self.env.cr.execute(SQL, {'date_start': date_start.strftime(DTF), 'date_end': date_end.strftime(DTF)})
        taxes = [x[0] for x in self.env.cr.fetchall()] 
        return taxes
        
    @api.multi
    def find_boletas(self, date_start, date_end, date_start_invoice, date_end_invoice):
        # no se consideran las boletas electronicas(39) ya que estas se toman del consumo de folio
        SQL = """
            SELECT boleta_data.sii_code, 
                SUM(boleta_data.cantidad_boletas) AS cantidad_boletas,
                SUM(boleta_data.neto) AS neto,
                SUM(boleta_data.monto_impuesto) AS monto_impuesto,
                SUM(boleta_data.monto_total) AS monto_total
            FROM 
                (SELECT c.sii_code, COUNT(p.id) AS cantidad_boletas,
                    SUM(p.amount_total - amount_tax) AS neto,
                    SUM(p.amount_tax) AS monto_impuesto,
                    SUM(p.amount_total) AS monto_total
                FROM pos_order p
                    INNER JOIN sii_document_class c ON c.id = p.document_class_id
                    INNER JOIN account_move a ON a.id = p.account_move
                WHERE c.sii_code IN (35, 38, 41, 70, 71)
                    AND p.date_order >= %(date_start)s AND p.date_order <= %(date_end)s
                GROUP BY c.sii_code
                UNION ALL 
                SELECT c.sii_code, COUNT(i.id) AS cantidad_boletas,
                    SUM(i.amount_total - amount_tax) AS neto,
                    SUM(i.amount_tax) AS monto_impuesto,
                    SUM(i.amount_total) AS monto_total
                FROM account_invoice i
                    INNER JOIN sii_document_class c ON c.id = i.document_class_id
                    INNER JOIN account_move a ON a.id = i.move_id
                WHERE c.sii_code IN (35, 38, 41, 70, 71)
                    AND i.date_invoice >= %(date_start_invoice)s AND i.date_invoice <= %(date_end_invoice)s
                GROUP BY c.sii_code
                ) AS boleta_data
            GROUP BY boleta_data.sii_code
        """
        self.env.cr.execute(SQL, {
            'date_start': date_start.strftime(DTF), 
            'date_end': date_end.strftime(DTF),
            'date_start_invoice': date_start_invoice,
            'date_end_invoice': date_end_invoice,
        })
        return self.env.cr.dictfetchall()
    
    @api.model
    def get_boleta_vals(self, line, taxes):
        sii_document_model = self.env['sii.document_class']
        sii_document_recs = sii_document_model.search([('sii_code', '=', line['sii_code'])], limit=1)
        vals_line = line.copy()
        vals_line['currency_id'] = self.env.user.company_id.currency_id.id
        #buscar el impuesto y el tipo de documento sii
        if taxes:
            vals_line['impuesto'] = taxes[0]
        if sii_document_recs:
            vals_line['tipo_boleta'] = sii_document_recs.id
        return vals_line

    @api.onchange('periodo_tributario', 'tipo_operacion', 'company_id')
    def set_movimientos(self):
        if not self.periodo_tributario or not self.tipo_operacion:
            return
        util_model = self.env['odoo.utils']
        date_start = util_model._change_time_zone(fields.Datetime.from_string(self.periodo_tributario + "-01"))
        date_end = util_model._change_time_zone(fields.Datetime.from_string(self.periodo_tributario + "-01 23:59:59") + relativedelta(day=1, days=-1, months=1))
        date_start_invoice = self.periodo_tributario + "-01"
        date_end_invoice = fields.Date.from_string(self.periodo_tributario + "-01") + relativedelta(day=1, days=-1, months=1)
        current = datetime.strptime(self.periodo_tributario + '-01', '%Y-%m-%d' )
        next_month = current + relativedelta(months=1)
        docs = [False, 70, 71]
        operator = 'not in'
        query = [
            ('company_id', '=', self.company_id.id),
            ('sended', '=', False),
            ('date' , '<', next_month.strftime('%Y-%m-%d')),
            ]
        domain = 'sale'
        if self.tipo_operacion == 'COMPRA':
            two_month = current + relativedelta(months=-2)
            query.append(('date' , '>=', two_month.strftime('%Y-%m-%d')))
            domain = 'purchase'
        elif self.tipo_operacion == 'VENTA':
            #en ventas no considerar las boletas
            docs = [35, 38, 39, 41, 70, 71]
            operator = 'not in'
        elif self.tipo_operacion == 'BOLETA':
            docs = [35, 38, 39, 41, 70, 71]
            operator = 'in'
            query.append(('date', '>=', current.strftime('%Y-%m-%d')))
        query.append(('journal_id.type', '=', domain))
        query.append(('document_class_id.sii_code', operator, docs))
        boleta_lines = [[5, ], ]
        impuesto_lines = [[5,],]
        if self.tipo_operacion in [ 'VENTA' ]:
            cfs = self.env['account.move.consumo_folios'].search([
                ('state', 'not in', ['draft', 'Anulado', 'Rechazado']),
                ('fecha_inicio', '>=', current),
                ('fecha_inicio', '<', next_month),
            ])
            if cfs:
                cantidades = {}
                for cf in cfs:
                    for det in cf.detalles:
                        if det.tpo_doc.sii_code in [39, 41]:
                            if not cantidades.get((cf.id, det.tpo_doc)):
                                cantidades[(cf.id, det.tpo_doc)] = 0
                            cantidades[(cf.id, det.tpo_doc)] += det.cantidad
                lineas = {}
                for key, cantidad in cantidades.items():
                    cf = key[0]
                    tpo_doc = key[1]
                    impuesto = self.env['account.move.consumo_folios.impuestos'].search([('cf_id', '=', cf), ('tpo_doc.sii_code', '=', tpo_doc.sii_code)])
                    if not lineas.get(tpo_doc):
                        lineas[tpo_doc] = {'cantidad': 0, 'neto': 0, 'monto_exento': 0, 'monto_impuesto': 0.0, 'monto_total': 0.0}
                    lineas[tpo_doc] = {
                                'cantidad': lineas[tpo_doc]['cantidad'] + cantidad,
                                'neto': lineas[tpo_doc]['neto'] + impuesto.monto_neto,
                                'monto_exento': lineas[tpo_doc]['monto_exento'] + impuesto.monto_exento,
                                'monto_impuesto': lineas[tpo_doc]['monto_impuesto'] + impuesto.monto_iva,
                                'monto_total': lineas[tpo_doc]['monto_total'] + impuesto.monto_total,
                            }
                for tpo_doc, det in lineas.items():
                    tax_id = self.env['account.tax'].search([('sii_code', '=', 14), ('type_tax_use', '=', 'sale'), ('company_id', '=', self.company_id.id)], limit=1) if tpo_doc.sii_code == 39 else self.env['account.tax'].search([('sii_code', '=', 0), ('type_tax_use', '=', 'sale'), ('company_id', '=', self.company_id.id)], limit=1)
                    line = {
                        'currency_id': self.env.user.company_id.currency_id,
                        'tipo_boleta': tpo_doc.id,
                        'cantidad_boletas': det['cantidad'],
                        'neto': det['neto'] or det['monto_exento'],
                        'monto_impuesto': det['monto_impuesto'],
                        'monto_total': det['monto_total'],
                        'impuesto': tax_id.id,
                    }
                    boleta_lines.append([0, 0, line])
            taxes = self.get_all_taxes(date_start, date_end)
            for line in self.find_boletas(date_start, date_end, date_start_invoice, date_end_invoice):
                boleta_lines.append((0, 0, self.get_boleta_vals(line, taxes)))
        elif self.tipo_operacion in ['BOLETA']:
            cfs = self.env['account.move.consumo_folios'].search([
                ('state', 'not in', ['draft', 'Anulado', 'Rechazado']),
                ('fecha_inicio', '>=', current),
                ('fecha_inicio', '<', next_month),
            ])
            monto_iva = 0
            monto_exento = 0
            for cf in cfs:
                for i in cf.impuestos:
                    monto_iva += i.monto_iva
                    monto_exento += i.monto_exento
            impuesto_lines.extend([
                 [0,0, {'tax_id': self.env['account.tax'].search([('sii_code', '=', 14), ('type_tax_use', '=', 'sale'),('company_id', '=', self.company_id.id)], limit=1).id, 'credit': monto_iva, 'currency_id' : self.env.user.company_id.currency_id.id}],
                 [0,0, {'tax_id': self.env['account.tax'].search([('sii_code', '=', 0), ('type_tax_use', '=', 'sale'),('company_id', '=', self.company_id.id)], limit=1).id, 'credit': monto_exento, 'currency_id' : self.env.user.company_id.currency_id.id}]
                 ])
        self.boletas = boleta_lines
        self.impuestos = impuesto_lines
        self.move_ids = self.env['account.move'].search(query)
        self.resumen_ids = self.get_resumen_by_document()
        
    def get_resumen_by_document(self):
        resumen_data = [(5, 0)]
        grupos = {}
        recs = sorted(self._get_moves(), key=lambda r: f"{r.document_class_id.sii_code}_{r.sii_document_number}")
        for r in recs:
            grupos.setdefault(r.document_class_id.sii_code, [])
            grupos[r.document_class_id.sii_code].append(r.with_context(tax_detail=True)._dte(is_for_libro=True))
        for sii_code, documentos in grupos.items():
            document_class = self.env['sii.document_class'].search([
                ('sii_code', '=', sii_code),
            ], limit=1)
            sign_use = 1
            if document_class.sii_code == 61:
                sign_use = -1
            total_afecto = 0
            total_exento = 0
            total_iva = 0
            total = 0
            for document in documentos:
                totales = document.get('Encabezado', {}).get('Totales', {})
                total_afecto += totales.get('MntNeto', 0) * sign_use
                total_exento += totales.get('MntExe', 0) * sign_use
                total_iva += totales.get('IVA', 0) * sign_use
                total += totales.get('MntTotal', 0) * sign_use
            resumen_data.append((0, 0, {
                'document_class_id': document_class.id,
                'total_afecto': total_afecto,
                'total_exento': total_exento,
                'total_iva': total_iva,
                'total': total,
                'documents_count': len(documentos),
            }))
        for boleta in self.boletas:
            total_afecto = boleta.neto
            total_exento = 0
            total_iva = boleta.monto_impuesto
            # boletas exentas
            if boleta.tipo_boleta.sii_code in (38, 41):
                total_afecto = 0
                total_exento = boleta.neto
            resumen_data.append((0, 0, {
                'document_class_id': boleta.tipo_boleta.id,
                'total_afecto': total_afecto,
                'total_exento': total_exento,
                'total_iva': total_iva,
                'total': boleta.monto_total,
                'documents_count': boleta.cantidad_boletas,
            }))
        return resumen_data


    def _get_imps(self):
        imp = {}
        for move in self.move_ids:
            if move.document_class_id.sii_code not in [35, 38, 39, 41, False, 0]:
                move_imps = move._get_move_imps()
                for key, i in move_imps.items():
                    if not key in imp:
                        imp[key] = i
                    else:
                        imp[key]['credit'] += i['credit']
                        imp[key]['debit'] += i['debit']
        return imp

    @api.depends('move_ids')
    def set_resumen(self):
        for book in self:
            book.total_afecto = 0.0
            book.total_exento = 0.0
            book.total_iva = 0.0
            book.total_otros_imps = 0.0
            book.total = 0.0
            for mov in book.move_ids:
                totales = mov.totales_por_movimiento()
                book.total_afecto += totales['neto']
                book.total_exento += totales['exento']
                book.total_iva += totales['iva']
                book.total_otros_imps += totales['otros_imps']
                book.total += mov.amount

    @api.onchange('move_ids')
    def compute_taxes(self):
        if self.tipo_operacion not in [ 'BOLETA' ]:
            imp = self._get_imps()
            if self.boletas:
                for bol in self.boletas:
                    if not imp.get(bol.impuesto.id):
                        imp[bol.impuesto.id] = {'credit': 0}
                    imp[bol.impuesto.id]['credit'] += bol.monto_impuesto
            if self.impuestos and isinstance(self.id, int):
                self._cr.execute("DELETE FROM account_move_book_tax WHERE book_id=%s", (self.id,))
                self.invalidate_cache()
            lines = [[5,],]
            for key, i in imp.items():
                i['currency_id'] = self.env.user.company_id.currency_id.id
                lines.append([0, 0, i])
            self.impuestos = lines

    @api.multi
    def unlink(self):
        for libro in self:
            if libro.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete a Validated book.'))
        return super(Libro, self).unlink()

    @api.multi
    def get_xml_file(self):
        return {
            'type' : 'ir.actions.act_url',
            'url': '/download/xml/libro/%s' % (self.id),
            'target': 'self',
        }

    @api.onchange('periodo_tributario', 'tipo_operacion')
    def _setName(self):
        self.name = self.tipo_operacion or ''
        if self.periodo_tributario:
            self.name += " " + self.periodo_tributario

    @api.multi
    def validar_libro(self):
        self._validar()
        return self.write({'state': 'NoEnviado'})

    def _get_moves(self):
        recs = []
        if self.move_ids:
            query = [
                ('move_id', 'in', self.move_ids.ids),
                ('sii_document_number', 'not in', [False, '0']),
                ('state', 'not in', ['cancel', 'draft']),
            ]
            invoices = self.env['account.invoice'].search(query)
            for invoice in invoices:
                recs.append(invoice)
        return recs

    def _emisor(self):
        Emisor = {}
        Emisor['RUTEmisor'] = self.company_id.partner_id.rut()
        Emisor['RznSoc'] = self.company_id.name
        Emisor["Modo"] = "produccion" if self.company_id.dte_service_provider == 'SII'\
                  else 'certificacion'
        Emisor["NroResol"] = self.company_id.dte_resolution_number
        Emisor["FchResol"] = self.company_id.dte_resolution_date.strftime('%Y-%m-%d')
        Emisor["ValorIva"] = 19
        return Emisor

    def _get_datos_empresa(self, company_id):
        signature_id = self.env.user.get_digital_signature(company_id)
        if not signature_id:
            raise UserError(_('''There are not a Signature Cert Available for this user, please upload your signature or tell to someelse.'''))
        emisor = self._emisor()
        return {
            "Emisor": emisor,
            "firma_electronica": signature_id.parametros_firma(),
        }

    @api.multi
    def check_folios_duplicity(self, date_start, date_end, datetime_start, datetime_end):
        SQL = """
            SELECT count(sii_document_number), sii_document_number, sii_code
            FROM (
                SELECT p.sii_document_number AS sii_document_number, s.sii_code AS sii_code
                FROM pos_order p
                    INNER JOIN sii_document_class s ON s.id=p.document_class_id
                WHERE p.date_order >= %(datetime_start)s AND p.date_order <= %(datetime_end)s
                    AND p.invoice_id IS NULL
                    AND p.company_id = %(company_id)s
                UNION ALL 
                SELECT i.sii_document_number AS sii_document_number, s.sii_code AS sii_code
                FROM account_invoice i
                    INNER JOIN sii_document_class s ON s.id=i.document_class_id
                WHERE sii_document_number IS NOT NULL AND type not in ('in_invoice', 'in_refund')
                    AND i.date_invoice >= %(date_start)s AND i.date_invoice <= %(date_end)s
                    AND i.company_id = %(company_id)s
            ) sub
            GROUP BY sii_document_number, sii_code
            HAVING count(sii_document_number) > 1
            ORDER BY sii_document_number
        """
        self.env.cr.execute(SQL, {
            'datetime_start': datetime_start.strftime(DTF), 'datetime_end': datetime_end.strftime(DTF),
            'date_start': date_start.strftime(DF), 'date_end': date_end.strftime(DF),
            'company_id': self.env.user.company_id.id,
        })
        return self.env.cr.fetchall()

    def _validar(self):
        util_model = self.env['odoo.utils']
        fecha_inicio = fields.Date.to_date(self.periodo_tributario + "-01")
        fecha_fin = fecha_inicio + relativedelta(day=1, days=-1, months=1)
        date_start = util_model._change_time_zone(fields.Datetime.to_datetime(self.periodo_tributario + "-01"))
        date_end = util_model._change_time_zone(fields.Datetime.to_datetime(self.periodo_tributario + "-01 23:59:59") + relativedelta(day=1, days=-1, months=1))
        if self.tipo_operacion != 'COMPRA' and self.check_folios_duplicity(fecha_inicio, fecha_fin, date_start, date_end):
            raise UserError(u"Hay folios repetidos, primero regularice eso, contacte con su administrador")
        datos = self._get_datos_empresa(self.company_id)
        grupos = {}
        boletas = []
        recs = sorted(self._get_moves(), key=lambda r: f"{r.document_class_id.sii_code}_{r.sii_document_number}")
        self.move_ids.write({'sended': True})
        for r in recs:
            grupos.setdefault(r.document_class_id.sii_code, [])
            grupos[r.document_class_id.sii_code].append(r.with_context(tax_detail=True)._dte(is_for_libro=True))
#         for b in self.boletas:
#             boletas.append(b._dte())
        datos['Libro'] = {
            "PeriodoTributario": self.periodo_tributario,
            "TipoOperacion": self.tipo_operacion,
            "TipoLibro": self.tipo_libro,
            "FolioNotificacion": self.folio_notificacion,
            "TipoEnvio": self.tipo_envio,
            "CodigoRectificacion": self.codigo_rectificacion,
            "Documento": [{'TipoDTE': k, 'documentos': v} for k, v in grupos.items()],
            'FctProp': self.fact_prop,
            'boletas': boletas,
        }
        datos['test'] = True
        result = fe.libro(datos)
        envio_dte = result['sii_xml_request']
        doc_id = '%s_%s' % (self.tipo_operacion, self.periodo_tributario)
        self.sii_xml_request = self.env['sii.xml.envio'].create({
            'xml_envio': envio_dte,
            'name': doc_id,
            'company_id': self.company_id.id,
        }).id

    @api.multi
    def do_dte_send_book(self):
        if self.state not in ['draft', 'NoEnviado', 'Rechazado']:
            raise UserError("El Libro ya ha sido enviado")
        if not self.sii_xml_request or self.sii_xml_request.state == "Rechazado":
            if self.sii_xml_request:
                self.sii_xml_request.unlink()
            self._validar()
        self.env['sii.cola_envio'].create(
                    {
                        'company_id': self.company_id.id,
                        'doc_ids': [self.id],
                        'model': 'account.move.book',
                        'user_id': self.env.user.id,
                        'tipo_trabajo': 'envio',
                    })
        self.state = 'EnCola'

    def do_dte_send(self, n_atencion=''):
        if self.sii_xml_request and self.sii_xml_request.state == "Rechazado":
            self.sii_xml_request.unlink()
            self._validar()
            self.sii_xml_request.state = 'NoEnviado'
        if self.state in ['NoEnviado', 'EnCola']:
            envio_id = self.sii_xml_request
            datos = self._get_datos_empresa(self.company_id)
            datos.update({
                'Libro': {
                    "PeriodoTributario": self.periodo_tributario,
                    "TipoOperacion": self.tipo_operacion,
                    "TipoLibro": self.tipo_libro,
                    "TipoEnvio": self.tipo_envio,
                },
                'sii_xml_request': envio_id.xml_envio.replace('''<?xml version="1.0" encoding="ISO-8859-1"?>\n''', ''),
                'ID': envio_id.name,
            })
            result = fe.libro(datos)
            envio = {
                'xml_envio': result['sii_xml_request'],
                'name': result['sii_send_filename'],
                'company_id': self.company_id.id,
                'user_id': self.env.uid,
                'sii_send_ident': result.get('sii_send_ident'),
                'sii_xml_response': result.get('sii_xml_response'),
                'state': result.get('sii_result'),
            }
            if not envio_id:
                envio_id = self.env['sii.xml.envio'].create(envio)
                for i in self:
                    i.sii_xml_request = envio_id.id
                    i.state = 'Enviado'
            else:
                envio_id.write(envio)
        return self.sii_xml_request

    def _get_send_status(self):
        self.sii_xml_request.get_send_status()
        if self.sii_xml_request.state == 'Aceptado':
            self.state = "Proceso"
        else:
            self.state = self.sii_xml_request.state

    @api.multi
    def ask_for_dte_status(self):
        self._get_send_status()

    def get_sii_result(self):
        for r in self:
            if r.sii_xml_request.state == 'NoEnviado':
                r.state = 'EnCola'
                continue
            r.state = r.sii_xml_request.state

    @api.multi
    def action_cancel(self):
        self.write({'state': 'Anulado'})
        return True
        
    @api.multi
    def action_cancel_to_draft(self):
        if self.move_ids:
            self.with_context(lang='es_CL').move_ids.write({'sended': False})
        self.write({'state': 'draft',
                    'move_ids': [(6, 0, [])],
                    'boletas': [(6, 0, [])],
                    'sii_xml_request': "",
                    })
        return True


class Boletas(models.Model):
    _name = 'account.move.book.boletas'
    _description = 'Línea de boletas mensuales para Libro de Ventas'

    currency_id = fields.Many2one('res.currency',
        string='Moneda',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True,
        track_visibility='always')
    tipo_boleta = fields.Many2one('sii.document_class',
        string="Tipo de Boleta",
        required=True,
        domain=[('document_letter_id.name','in',['B','M'])])
    rango_inicial = fields.Integer(
        string="Rango Inicial",
        required=True)
    rango_final = fields.Integer(
        string="Rango Final",
        required=True)
    cantidad_boletas = fields.Integer(
        string="Cantidad Boletas",
        rqquired=True)
    neto = fields.Monetary(
        string="Monto Neto",
        required=True)
    impuesto = fields.Many2one('account.tax',
        string="Impuesto",
        required=True,
        domain=[('type_tax_use','!=','none'), '|', ('active', '=', False), ('active', '=', True)])
    monto_impuesto = fields.Monetary(
        string="Monto Impuesto",
        required=True)
    monto_total = fields.Monetary(
        string="Monto Total",
        required=True)
    book_id = fields.Many2one('account.move.book', ondelete="cascade")

    @api.onchange('rango_inicial', 'rango_final')
    def get_cantidad(self):
        if not self.rango_inicial or not self.rango_final:
            return
        if self.rango_final < self.rango_inicial:
            raise UserError("¡El rango Final no puede ser menor al inicial")
        self.cantidad_boletas = self.rango_final - self.rango_inicial + 1


class ImpuestosLibro(models.Model):
    _name = "account.move.book.tax"
    _description = 'línea de impuesto Libro CV'

    def get_monto(self):
        for t in self:
            t.amount = t.debit - t.credit
            if t.book_id.tipo_operacion in [ 'VENTA' ]:
                t.amount = t.credit - t.debit

    tax_id = fields.Many2one('account.tax', string="Impuesto")
    credit = fields.Monetary(string="Créditos", default=0.00)
    debit = fields.Monetary(string="Débitos", default=0.00)
    amount = fields.Monetary(compute="get_monto", string="Monto")
    currency_id = fields.Many2one('res.currency',
        string='Moneda',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True,
        track_visibility='always')
    book_id = fields.Many2one('account.move.book', string="Libro", ondelete="cascade")


class LibroResumen(models.Model):
    _name="account.move.book.resume"
    _description = 'Resumen de Libro'
    
    
    book_id = fields.Many2one('account.move.book', string="Libro", ondelete="cascade")
    document_class_id = fields.Many2one('sii.document_class', u'Tipo Documento')
    company_id = fields.Many2one('res.company', string="Compañía", related='book_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='book_id.currency_id', store=True)
    total_afecto = fields.Monetary(string="Total Afecto")
    total_exento = fields.Monetary(string="Total Exento")
    total_iva = fields.Monetary(string="Total IVA")
    total_otros_imps = fields.Monetary(string="Total Otros Impuestos")
    total = fields.Monetary(string="Total")
    documents_count = fields.Integer(u'Numero de Documentos')
    