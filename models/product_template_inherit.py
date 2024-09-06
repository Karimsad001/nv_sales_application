from odoo import models, api
from logging import getLogger

_logger = getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def get_all_products(self):
        #this function used to return list of products ..
        #How to use:
        #result = models.execute_kw(db, uid, password, 'product.template', 'get_products', [])
        #return array of products. and each of them is a dictionary.
        products = self.search([]).read(['id','name','detailed_type','sale_ok', 'purchase_ok', 'list_price', 'standard_price', 'barcode', 'taxes_id'])
        return products

    @api.model
    def get_products_from_query(self, params=None):
        #this function used to return list of products ..
        #How to use:
        #result = models.execute_kw(db, uid, password, 'product.template', 'get_products_from_query', [])
        #return array of products. and each of them is a dictionary.
        try:
            query = """
                SELECT pt.id,
                pt.name, 
                pt.detailed_type, 
                pt.sale_ok, 
                pt.purchase_ok, 
                pt.list_price, 
                pr.barcode, 
                STRING_AGG(ptr.tax_id::TEXT, ',') AS tax_ids
                FROM
                    product_template as pt
                JOIN
                    product_product as pr
                ON
                    pt.id = pr.product_tmpl_id
                LEFT JOIN
                    product_taxes_rel as ptr
                ON 
                    pt.id = ptr.prod_id
                GROUP BY pt.id, pt.name, pt.detailed_type, pt.sale_ok, pt.purchase_ok, pt.list_price, pr.barcode
            """
            self.env.cr.execute(query, params or [])
            rows = self.env.cr.dictfetchall()
            for res in rows:
                for key in res:
                    if res[key] is None:
                        res[key] = ""
                    if key == "name":
                        name = res["name"]["en_US"]
                        res["name"] = name
                    if key == "tax_ids":
                        res["tax_ids"] = res["tax_ids"].split(',')
            return rows
        except Exception as e:
            _logger.error("An error occurred while executing the query: %s", e)
            return []