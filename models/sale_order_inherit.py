from odoo import models, api
from logging import getLogger
from odoo.exceptions import UserError
import base64

_logger = getLogger(__name__)

class SaleInherit(models.Model):
    _inherit = 'sale.order'

    @api.model
    def get_customers(self,salesman_id):
        #this function used to return list of salesman customers ..
        #How to use:
        #result = models.execute_kw(db, uid, password, 'sale.order', 'get_customers', [salesman_id])
        #Params : salesman_id : this is the odoo id of the salesman
        #return array of names
        partners = self.env["res.partner"].search([('user_id','=',int(salesman_id))])
        return partners.read(['id','name','email','phone'])

    @api.model
    def get_sales_orders(self, salesperson_id):
        #this function used to return list of sales_orders created by salesperson_id ..
        #How to use:
        #result = models.execute_kw(db, uid, password, 'sale.order', 'get_sales_orders', [salesperson_id])
        #Params : salesperson_id : this is the odoo id of the salesman
        #return array of sales_orders with its associated product lines. and each of them is a dictionary.
        sales_orders = self.search([('user_id', '=', int(salesperson_id))]).read(['id', 'date_order', 'payment_term_id', 'order_line'])
        result = []
        for order in sales_orders:
            order_lines = self.env['sale.order.line'].browse(order['order_line'] or [])
            lines = []
            for line in order_lines:
                lines.append({
                    'product_id': line.product_id.id or "",
                    'quantity': line.product_uom_qty or "",
                    'unit_price': line.price_unit or ""
                })
            result.append({
                'id': order['id'] or "",
                'date_order': order['date_order'] or "",
                'payment_term_id': order['payment_term_id'] or "",
                'order_lines': lines
            })
        return result

    @api.model
    def execute_raw_sql_query_dict(self, query, params=None):
        # Executes a raw SQL query and returns the results as a list of dictionaries.
        # :param query: SQL query string to be executed
        # :param params: Parameters to be used in the SQL query (optional)
        # :return: List of dictionaries containing the query result
        try:
            self.env.cr.execute(query, params or [])
            rows = self.env.cr.dictfetchall()
            rows = [
                {k: (v if v is not None else '') for k, v in row.items()}
                for row in rows
            ]
            return rows
        except Exception as e:
            _logger.error("An error occurred: %s", e)
            return []

    @api.model
    def get_sales_orders_from_query(self, salesperson_id, limit, offset):
        #this function used to return list of sales_orders created by salesperson_id ..
        # so -> sale order
        # ol -> order line
        #How to use:
        #result = models.execute_kw(db, uid, password, 'sale.order', 'get_sales_orders_from_query', [salesperson_id, limit, offset])
        #Params : salesperson_id : this is the odoo id of the salesman
        #Params : limit : this is the number of sales returned
        #Params : offset : this is the number of sales excluded in the begin
        #return array of sales_orders with its associated order lines. and each of them is a dictionary.
        super_query = """
            SELECT id as id, name as name, partner_id as partner_id, date_order as date_order, payment_term_id as payment_term_id
            FROM sale_order as so
            WHERE user_id = %s
            ORDER BY id
            LIMIT %s
            OFFSET %s
        """
        super_results = self.execute_raw_sql_query_dict(super_query, [salesperson_id, limit, offset])
        so_ids = tuple(result['id'] for result in super_results)
        print("so_ids:", so_ids)
        sub_query = """
            SELECT
                ol.id as id,
                ol.product_id as product_id,
                ol.name as name,
                ol.product_uom_qty as quantity,
                ol.qty_delivered as quantity_delivered,
                ol.qty_invoiced as quantity_invoiced,
                ol.product_uom,
                ol.price_unit as unit_price,
                ol.order_id as order_id,
                STRING_AGG(ats.account_tax_id::TEXT, ',') as account_tax_id,
                ol.price_subtotal as price_subtotal
            FROM
                sale_order_line as ol
            LEFT JOIN
                account_tax_sale_order_line_rel as ats
            ON
                ol.id = ats.sale_order_line_id
            WHERE
                order_id IN %s
            GROUP BY
                ol.id
            """
        sub_results = self.execute_raw_sql_query_dict(sub_query, [so_ids])
        for order in super_results:
            order_lines = []
            order["order_lines"] = order_lines
            for line in sub_results:
                if(line["order_id"] == order["id"]):
                    line["account_tax_id"] = line["account_tax_id"].split(',')
                    order_lines.append(line)
        return super_results

    @api.model
    def create_sale_order(self, data):
        #this function used to create a sale order from mobile app and add it to odoo records ..
        #How to use:
        #result = models.execute_kw(db, uid, password, 'sale.order', 'create_sale_order', [data])
        #Params : data : this is a dictionary holds the data of sale order that we want to create.
        #data -> data = {
        #     'partner_id': 3,
        #     'date_order': '2024-08-05 11:06:39',
        #     'payment_term_id': '1',
        #     'product_lines': [
        #         {
        #             'product_id': 1,
        #             'name': 'Booking Fees',
        #             'quantity': 4.0,
        #             'unit_price': 15.0
        #         },
        #         {
        #             'product_id': 2,
        #             'name': 'book1',
        #             'quantity': 1.0,
        #             'unit_price': 0.0
        #         }
        #     ]
        # }
        #return the id of the sale order created recently.
        try:
            sale_order = self.create({
                'partner_id': data['partner_id'],
                'date_order': data['date_order'],
                'payment_term_id': data['payment_term_id'] or "",
            })
            sale_order_id = sale_order.id
            lines = data.get('product_lines', [])
            for line in lines:
                self.env['sale.order.line'].create({
                    'product_id': line.get('product_id'),
                    'name': line.get('name'),
                    'product_uom_qty': line.get('quantity'),
                    'price_unit': line.get('unit_price'),
                    'order_id': sale_order_id
                })
            return sale_order_id
        except Exception as e:
            _logger.error("An error occurred while creating: %s", e)
            return {'error: ' + str(e)}

    @api.model
    def print_report_attachment(self, sale_id):
        #this function used to create an attachment(pdf)(Quotation/Order) for a sale_order from mobile app and add it to odoo attachments ..
        #How to use:
        #result = models.execute_kw(db, uid, password, 'sale.order', 'print_report_attachment', [sale_id])
        #Params : sale_id : this is the sale_order id that we want to print its quotation .
        try:
            sale_order = self.browse(int(sale_id))
            report_name = 'sale.report_saleorder_raw'
            # report_name = 'sale.report_saleorder'
            report = self.env['ir.actions.report'].sudo()._get_report_from_name(report_name)
            pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(report, [sale_order.id])
            _logger.critical(base64.b64encode(pdf_content))
            _logger.critical("base64")
            attachment = self.env['ir.attachment'].create({
                'name': f'{sale_order.name}_report',
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'mimetype': 'application/pdf',
            })
            return {'attachment_id': attachment.id, 'attachment_name': attachment.name}
        except Exception as e:
            _logger.error("An error occurred while creating the report attachment: %s", e)
            return {'error': "Error occurred: " + str(e)}

    @api.model
    def test(self, inv_id):
        try:
            invoice = self.env["account.move"].browse(int(inv_id))
            report_name = 'account.report_invoice_with_payments'
            report = self.env['ir.actions.report'].sudo()._get_report_from_name(report_name)
            pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(report.report_file, [invoice.id])
            attachment = self.env['ir.attachment'].create({
                'name': '%s_report' % invoice.name,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'mimetype': 'application/pdf'
            })
            return {'attachment_id': attachment.id, 'attachment_name': attachment.name}
        except Exception as e:
            _logger.error("An error occurred while creating the report attachment: %s", e)
            return {'error': "Error occurred: " + str(e)}
    
    # @api.model
    # def test2(self, sale_id):
    #     try:
    #         order_lines = self.env['sale.order.line'].search([('order_id','=',int(sale_id))]).mapped('id')
    #         invoice_lines = self.env['account.move.line'].search([('sale_line_ids', 'in', order_lines)]).read(['move_id'])
    #         invoice_id = invoice_lines[0]['move_id'][0]
    #         invoice_name = invoice_lines[0]['move_id'][1].replace('/', '_')
    #         report_name = 'account.report_invoice_with_payments'
    #         report = self.env['ir.actions.report'].sudo()._get_report_from_name(report_name)
    #         pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(report.report_file, [invoice_id])
    #         attachment = self.env['ir.attachment'].create({
    #             'name': '%s_report' % invoice_name,
    #             'type': 'binary',
    #             'datas': base64.b64encode(pdf_content),
    #             'mimetype': 'application/pdf'
    #         })
    #         return {'attachment_id': attachment.id, 'attachment_name': attachment.name}
    #     except Exception as e:
    #         _logger.error("An error occurred while creating the report attachment: %s", e)
    #         return {'error': "Error occurred: " + str(e)}
    @api.model
    def test3(self, sale_id):
        try:
            order_lines = self.env['sale.order.line'].search([('order_id','=',int(sale_id))]).mapped('id')
            invoice_lines = self.env['account.move.line'].search([('sale_line_ids', 'in', order_lines)]).read(['move_id'])
            invoices = {}
            for line in invoice_lines:
                move_id = line['move_id'][0]
                move_name = line['move_id'][1].replace('/', '_')
                invoices[move_id] = move_name
            attachments = []
            report_name = 'account.report_invoice_with_payments'
            report = self.env['ir.actions.report'].sudo()._get_report_from_name(report_name)
            for invoice_id, invoice_name in invoices.items():
                pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(report.report_file, [invoice_id])
                attachment = self.env['ir.attachment'].create({
                    'name': '%s_report' % invoice_name,
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'mimetype': 'application/pdf'
                })
                attachments.append({
                    'attachment_id': attachment.id,
                    'attachment_name': attachment.name
                })
            return {'attachments': attachments}
        except Exception as e:
            _logger.error("An error occurred while creating the report attachments: %s", e)
            return {'error': "Error occurred: " + str(e)}