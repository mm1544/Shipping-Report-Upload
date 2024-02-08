from odoo import models, fields
from odoo.exceptions import UserError
from io import StringIO
import base64
import csv

# Extend 'sale.order' model for custom shipping report functionality
class SaleOrderFields(models.Model):
    _inherit = 'sale.order'

    # Text fields for detailed shipping information
    shipping_report_carrier = fields.Text(string="Carrier")
    shipping_report_consignment_parcel_no = fields.Text(string="Consignment/Parcel No")
    shipping_report_serial_no = fields.Text(string="Serial No")
    shipping_report_imei_no = fields.Text(string="IMEI No")
    shipping_report_source = fields.Many2one(comodel_name="res.partner", string="Shipping Report Document Added On")

# Extend 'res.partner' for uploading shipping reports
class ContactsFields(models.Model):
    _inherit = 'res.partner'
    shipping_report_to_upload = fields.Binary(string="Shipping Report To Upload", help="Add Shipping Report file here and press dropdown action to upload data to Sales Orders")

# Extend 'res.partner' for importing shipping report data
class ShippingReportUpload(models.Model):
    _inherit = 'res.partner'

    def import_shipping_report_csv_data(self):
        if not self.shipping_report_to_upload:
            raise UserError("No shipping report to upload.")

        csv_data = self.decode_csv_data()
        res_list = self.parse_csv_data(csv_data)
        formatted_data_dict = self.format_data(res_list)

        self.update_sales_orders(formatted_data_dict)

    def decode_csv_data(self):
        return base64.b64decode(self.shipping_report_to_upload).decode('utf-8')

    def parse_csv_data(self, csv_data):
        csv_file = StringIO(csv_data)
        csv_reader = csv.reader(csv_file)
        return [row for row in csv_reader]

    def format_data(self, res_list):
        formatted_data = {}
        for line in res_list[1:]:
            if not line or not line[2]:
                continue

            po_name = line[2]
            if not formatted_data.get(po_name):
                formatted_data[po_name] = [[line[16]], [line[17]], [line[29]], [line[30]]]
            else:
                self.append_unique_values(formatted_data[po_name], line)

        return formatted_data

    def append_unique_values(self, data_list, line):
        for idx, col in enumerate([16, 17, 29, 30]):
            if line[col] not in data_list[idx]:
                data_list[idx].append(line[col])

    def update_sales_orders(self, formatted_data_dict):
        for po_string, data_list in formatted_data_dict.items():
            shipping_report_values = self.get_shipping_report_values(data_list)
            purchase_order = self.env['purchase.order'].search([('name', '=', po_string)])
            if purchase_order:
                sales_order = purchase_order.x_sale_id
                if sales_order:
                    sales_order.write(shipping_report_values)
                    self.log_shipping_report_operation(sales_order, shipping_report_values)

    def get_shipping_report_values(self, data_list):
        return {
            'shipping_report_carrier': '\n'.join(filter(None, data_list[0])),
            'shipping_report_consignment_parcel_no': '\n'.join(filter(None, data_list[1])),
            'shipping_report_serial_no': '\n'.join(filter(None, data_list[2])),
            'shipping_report_imei_no': '\n'.join(filter(None, data_list[3])),
            'shipping_report_source': self.id
        }


    def log_shipping_report_operation(self, sales_order, values):
        # Format the message for logging
        message = "Updated Sales Order {} with Shipping Report Data: {}".format(sales_order.name, values)

        # Create a log entry in ir.logging
        self.env['ir.logging'].create({
            'name': 'Shipping Report Update',  # Name of the log
            'type': 'server',  # Indicates that this log is from the server-side
            'dbname': self.env.cr.dbname,  # Current database name
            'level': 'info',  # Log level (info, warning, error)
            'message': message,  # The main log message
            'path': 'models.res.partner',  # Path indicates the module/class path
            'line': 'ShippingReportUpload.log_shipping_report_operation',  # Method name or line number
            'func': '__import_shipping_report_csv_data__',  # Function name
        })
        





# from odoo import models, fields
# from io import StringIO
# import base64
# import csv
# import datetime
# import logging

# # Inheriting from 'sale.order' to extend its functionality
# class SaleOrderFields(models.Model):
#     _inherit = 'sale.order'

#     # Changed fields from Char to Text for longer text support
#     shipping_report_carrier = fields.Text(string="Carrier")
#     shipping_report_consignment_parcel_no = fields.Text(string="Consignment/Parcel No")
#     shipping_report_serial_no = fields.Text(string="Serial No")
#     shipping_report_imei_no = fields.Text(string="IMEI No")
    
#     # Linking to a 'res.partner' model with a Many2one relationship
#     shipping_report_source = fields.Many2one(comodel_name="res.partner", string="Shipping Report Document Added On")

# # Inheriting from 'res.partner' to add a new field for uploading shipping reports
# class ContactsFields(models.Model):
#     _inherit = 'res.partner'

#     # Binary field to hold the uploaded file
#     shipping_report_to_upload = fields.Binary(string="Shipping Report To Upload", help="Add Shipping Report file here and press dropdown action to upload data to Sales Orders")

# # Extending 'res.partner' model to include a method for importing shipping report data
# class ShippingReportUpload(models.Model):
#     _inherit = 'res.partner'

#     def import_shipping_report_csv_data(self):
#         res_list = []
#         formated_data_dict = {}
#         contact = self

#         if not contact.shipping_report_to_upload:
#             return

#         # Decoding the uploaded CSV file
#         csv_data = base64.b64decode(contact.shipping_report_to_upload)
#         csv_string = csv_data.decode('utf-8')
#         csv_file = StringIO(csv_string)
#         csv_reader = csv.reader(csv_file)

#         # Parsing the CSV data
#         for row in csv_reader:
#             res_list.append(row)

#         for index, line in enumerate(res_list[1:]):
#             # Skipping empty lines or lines without a PO name
#             if not line or not line[2]:
#                 continue

#             # Searching for the corresponding purchase order
#             purchase_order = self.env['purchase.order'].search([('name', '=', line[2])])
#             if not purchase_order:
#                 continue

#             # Getting the linked sales order
#             sales_order = purchase_order.x_sale_id
#             if not sales_order:
#                 continue

#             # Formatting and storing data for each PO
#             if not formated_data_dict.get(line[2]):
#                 formated_data_dict[line[2]] = [[line[16]], [line[17]], [line[29]], [line[30]]]
#             else:
#                 # Avoiding duplicate entries
#                 for idx, col in enumerate([16, 17, 29, 30]):
#                     if line[col] not in formated_data_dict[line[2]][idx]:
#                         formated_data_dict[line[2]][idx].append(line[col])

#         # Updating each sales order with the formatted data
#         for po_string, data_list in formated_data_dict.items():
#             shipping_report_carrier_str = '\n'.join(filter(None, data_list[0]))
#             shipping_report_consignment_parcel_no_str = '\n'.join(filter(None, data_list[1]))
#             shipping_report_serial_no_str = '\n'.join(filter(None, data_list[2]))
#             shipping_report_imei_no_str = '\n'.join(filter(None, data_list[3]))

#             purchase_order = self.env['purchase.order'].search([('name', '=', po_string)])
#             if not purchase_order:
#                 continue

#             sales_order = purchase_order.x_sale_id
#             if not sales_order:
#                 continue
            
#             # Writing the formatted data to the sales order
#             sales_order.write({
#                 'shipping_report_carrier': shipping_report_carrier_str,
#                 'shipping_report_consignment_parcel_no': shipping_report_consignment_parcel_no_str,
#                 'shipping_report_serial_no': shipping_report_serial_no_str,
#                 'shipping_report_imei_no': shipping_report_imei_no_str,
#                 'shipping_report_source': self.id
#             })

#         # Logging the operation
#         mess = "shipping_report_carrier: {},\nshipping_report_consignment_parcel_no: {},\nshipping_report_serial_no: {},\nshipping_report_imei_no: {}".format(
#             line[16], line[17], line[29], line[30])
        
#         self.env['ir.logging'].create({
#             'func': self.name,
#             'line': '2228',
#             'name': 'odoo-dev-mm.import_shipping_report_csv_data',
#             'message': mess,
#             'level': 'info',
#             'path': 'action',
#             'type': 'server',
#         })

#         # Exception handling was commented out in the original code. It's a good practice to handle exceptions for robustness.



# # from odoo import models, fields
# # from io import StringIO
# # import base64
# # import csv
# # import datetime
# # import logging

# # class SaleOrderFields(models.Model):
# #     _inherit = 'sale.order'

# #     # shipping_report_carrier = fields.Char(string="Carrier")
# #     shipping_report_carrier = fields.Text(string="Carrier")
# #     # shipping_report_consignment_parcel_no = fields.Char(string="Consignment/Parcel No")
# #     shipping_report_consignment_parcel_no = fields.Text(string="Consignment/Parcel No")
# #     # shipping_report_serial_no = fields.Char(string="Serial No")
# #     shipping_report_serial_no = fields.Text(string="Serial No")
# #     # shipping_report_imei_no = fields.Char(string="IMEI No")
# #     shipping_report_imei_no = fields.Text(string="IMEI No")
    
# #     shipping_report_source = fields.Many2one(comodel_name="res.partner", string="Shipping Report Dockument Adden On")

# # class ContactsFields(models.Model):
# #     _inherit = 'res.partner'

# #     shipping_report_to_upload = fields.Binary(string="Shipping Report To Upload", help="Add Shipping Report file here and press dropdown action to upload data to Sales Orders")


# # class ShippingReportUpload(models.Model):
# #     _inherit = 'res.partner'

    
# #     def import_shipping_report_csv_data(self):
# #         res_list = []
# #         formated_data_dict = {}
# #         csv_reader = False
# #         contact = self

# #         if not contact.shipping_report_to_upload:
# #             return

# #         # Retrieve the binary data from the 'shipping_report_to_upload' field
# #         csv_data = base64.b64decode(contact.shipping_report_to_upload)

# #         # Read the CSV data
# #         csv_string = csv_data.decode('utf-8')
# #         csv_file = StringIO(csv_string)
# #         csv_reader = csv.reader(csv_file)

# #         # Iterate over the CSV lines
# #         for row in csv_reader:
# #             # Process each row of the CSV file
# #             res_list.append(row)

# #         for index, line in enumerate(res_list[1:]):
        
# #             # line[2] is PO name column
# #             if not line or not line[2]:
# #                 continue
# #                 # log
            
# #             purchase_order = self.env['purchase.order'].search([('name', '=', line[2])])

# #             if not purchase_order:
# #                 continue
# #                 # log
                
# #             sales_order = purchase_order.x_sale_id
            
# #             if not sales_order:
# #                 continue
# #                 # log
            
# #             if not formated_data_dict.get(line[2]):
# #                 # "formated_data_dict: {'PO51414': [{'Parcelforce Worldwide'}, {'WM0336870'}, {'J3Q2VQ67TD'}, {''}]}"
# #                 formated_data_dict[line[2]] = [[line[16]],[line[17]],[line[29]],[line[30]]]
# #             else:
# #                 if line[16] not in formated_data_dict[line[2]][0]:
# #                     formated_data_dict[line[2]][0].append(line[16])
# #                 if line[17] not in formated_data_dict[line[2]][1]:
# #                     formated_data_dict[line[2]][1].append(line[17])
# #                 if line[29] not in formated_data_dict[line[2]][2]:
# #                     formated_data_dict[line[2]][2].append(line[29])
# #                 if line[30] not in formated_data_dict[line[2]][3]:
# #                     formated_data_dict[line[2]][3].append(line[30])

# #         # raise Warning('\n\nformated_data_dict:\n{}\n\n'.format(formated_data_dict))
# #         # {'PO51414': [{'Parcelforce Worldwide'}, {'WM0336870'}, {'', 'R2JRRW7GV7', 'J3Q2VQ67TD', 'GQ4TQ71VVN', 'TY26X3QL6R'}, {''}], 'PO51419': [{'Parcelforce Worldwide'}, {'WM0337040'}, {'FMXF1W26XQ', 'QK46TVDHW0', 'RWQWYC2QG4', 'KFHFJQLWRR', 'KVDGDXQ4DF', 'VG4G449N75', 'V3V19QR4H5', 'Y3WR4Q22VJ', 'R6HYF6YHLG', 'DJ4H3KPFGP', 'JPQ0TFV9W4'}, {''}], 'PO51420': [{'Parcelforce Worldwide'}, {'WM0338592'}, {'VJ2492M2G9', 'P52G2X4WT3'}, {''}], 'PO51410': [{'DPD(UK)', 'Parcelforce Worldwide'}, {'WM0339553', '15502667556123'}, {'JRMW9KNY7P', ''}, {''}]}"

        
# #         # Iterating through the dictionary. key=po_string, value=data_list.
# #         for po_string, data_list in formated_data_dict.items():
# #             shipping_report_carrier_str = ''
# #             shipping_report_consignment_parcel_no_str = ''
# #             shipping_report_serial_no_str = ''
# #             shipping_report_imei_no_str = ''
            
# #             # Convert list to string with '\n' separated values, omitting empty values
# #             shipping_report_carrier_str = '\n'.join(item for item in data_list[0] if item != '')
# #             shipping_report_consignment_parcel_no_str = '\n'.join(item for item in data_list[1] if item != '')
# #             shipping_report_serial_no_str = '\n'.join(item for item in data_list[2] if item != '')
# #             shipping_report_imei_no_str = '\n'.join(item for item in data_list[3] if item != '')

# #             purchase_order = self.env['purchase.order'].search([('name', '=', po_string)])

# #             if not purchase_order:
# #                 continue
# #                 # log
                
# #             sales_order = purchase_order.x_sale_id

# #             if not sales_order:
# #                 continue
                
            
# #             sales_order.write({
# #                 'shipping_report_carrier': shipping_report_carrier_str,
# #                 'shipping_report_consignment_parcel_no': shipping_report_consignment_parcel_no_str,
# #                 'shipping_report_serial_no': shipping_report_serial_no_str,
# #                 'shipping_report_imei_no': shipping_report_imei_no_str,
# #                 'shipping_report_source': self.id
# #                               })
        


# #         mess = "shipping_report_carrier: {},\nshipping_report_consignment_parcel_no: {},\nshipping_report_serial_no: {},\nshipping_report_imei_no: {}".format(line[16],line[17],line[29], line[30])
        
# #         self.env['ir.logging'].create({
# #             'func': self.name,
# #             'line': '2228',
# #             'name': 'odoo-dev-mm.import_shipping_report_csv_data',
# #             'message': mess,
# #             'level': 'info',
# #             'path': 'action',
# #             'type': 'server',
# #         })

# #             # except Exception as e:
# #             #     self.env['ir.logging'].create({
# #             #         'func': self.name,
# #             #         # 'line': '2228',
# #             #         'name': 'odoo-dev-mm.import_shipping_report_csv_data',
# #             #         'message': 'Error:\n{}'.format(e),
# #             #         'level': 'error',
# #             #         'path': 'action',
# #             #         'type': 'server',
# #             #     })