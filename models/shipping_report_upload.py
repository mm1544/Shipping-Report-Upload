from odoo import models, fields
from datetime import date
from odoo.exceptions import UserError
from io import StringIO
import base64
import csv

# Extend 'sale.order' model for custom shipping report functionality


class SaleOrderFields(models.Model):
    _inherit = 'sale.order'

    # Text fields for detailed shipping information
    shipping_report_carrier = fields.Text(string="Carrier")
    shipping_report_consignment_parcel_no = fields.Text(
        string="Consignment/Parcel No")
    shipping_report_serial_no = fields.Text(string="Serial No")
    shipping_report_imei_no = fields.Text(string="IMEI No")
    shipping_report_source = fields.Many2one(
        comodel_name="res.partner", string="Shipping Report Document Added On")

# Extend 'res.partner' for uploading shipping reports


class ContactsFields(models.Model):
    _inherit = 'res.partner'
    shipping_report_to_upload = fields.Binary(
        string="Shipping Report To Upload", help="Add Shipping Report file here and press dropdown action to upload data to Sales Orders")
    dont_send_email_after_shipping_report_upload = fields.Boolean(
        string="Don't Send Email After Shipping Report Upload")


# Extend 'res.partner' for importing shipping report data
class ShippingReportUpload(models.Model):
    _inherit = 'res.partner'

    SHIPPING_CARRIER_LINKS = {
        'Parcelforce Worldwide': 'https://www.parcelforce.com/track-trace',
        'DPD(UK)': 'https://www.dpd.co.uk/service/https://www.dpd.co.uk/service/'
    }

    def import_shipping_report_csv_data(self):
        if not self.shipping_report_to_upload:
            raise UserError("No shipping report to upload.")

        csv_data = self.decode_csv_data()
        res_list = self.parse_csv_data(csv_data)
        formatted_data_dict = self.format_data(res_list)

        self.update_sales_orders_and_send_emails(formatted_data_dict)

    def decode_csv_data(self):
        return base64.b64decode(self.shipping_report_to_upload).decode('utf-8')

    def parse_csv_data(self, csv_data):
        csv_file = StringIO(csv_data)
        csv_reader = csv.reader(csv_file)
        return [row for row in csv_reader]

    def format_data(self, res_list):
        formatted_data = {}
        for line in res_list[1:]:
            # Example of line:
            # ['JTR001', '000', 'PO51414', '29/11/2023', 'FGD2822', '1', 'MK2K3B/A', 'MK2K3B/A', 'IPAD 9TH GEN 10.2 WIFI 64GB SG', '1', '255.80', '51.16', 'GBP', 'LN27663', '29/11/2023', 'FGD2822/00', 'Parcelforce Worldwide', 'WM0336870', 'Address1', 'Address2', 'Address3', 'Address4', 'ST. IVES', '', 'PE27 5JL', 'GB', '-  -', 'FAO: qqqqq', '-  -', 'J3Q2VQ67TD', '', "'"]

            if not line or not line[2]:
                continue

            po_name = line[2]
            if not formatted_data.get(po_name):
                formatted_data[po_name] = [[line[16]],
                                           [line[17]], [line[29]], [line[30]]]
            else:
                self.append_unique_values(formatted_data[po_name], line)

        # Example of formatted_data:
        # {'PO51414': [['Parcelforce Worldwide'], ['WM0336870'], ['J3Q2VQ67TD', 'GQ4TQ71VVN', 'R2JRRW7GV7', 'TY26X3QL6R', ''], ['']], 'PO51419': [['Parcelforce Worldwide'], ['WM0337040'], ['KFHFJQLWRR', 'KVDGDXQ4DF', 'QK46TVDHW0', 'DJ4H3KPFGP', 'Y3WR4Q22VJ', 'RWQWYC2QG4', 'FMXF1W26XQ', 'JPQ0TFV9W4', 'R6HYF6YHLG', 'VG4G449N75', 'V3V19QR4H5'], ['']], 'PO51420': [['Parcelforce Worldwide'], ['WM0338592'], ['P52G2X4WT3', 'VJ2492M2G9'], ['']], 'PO51410': [['Parcelforce Worldwide', 'DPD(UK)'], ['WM0339553', '15502667556123'], ['JRMW9KNY7P', ''], ['']]}
        return formatted_data

    def append_unique_values(self, data_list, line):
        for idx, col in enumerate([16, 17, 29, 30]):
            if line[col] not in data_list[idx]:
                data_list[idx].append(line[col])

    def get_formated_data(self, data_dict):
        serial_numbers_list = []
        shipping_carrier_lines = '<strong>Shipping Carriers</strong><ul style="margin-top: 0; padding-top: 3;">'
        serial_numbers_line = '<strong>Serial Numbers</strong><ul style="margin-top: 0; padding-top: 3;">'

        # data_dict:
        # {'shipping_report_carrier': 'Parcelforce Worldwide\nDPD(UK)', 'shipping_report_consignment_parcel_no': 'WM0339553\n15502667556123', 'shipping_report_serial_no': 'JRMW9KNY7P', 'shipping_report_imei_no': '', 'shipping_report_source': 273041, 'Sale Order': sale.order(60129,)}
        customer_reference = data_dict['Sale Order'].client_order_ref
        customer_reference_line = f'<p><strong>Customer Reference</strong>: {customer_reference}</p>'
        all_shipping_carriers = data_dict['shipping_report_carrier'].split(
            '\n')
        all_shipping_report_consignment_parcel_no = data_dict['shipping_report_consignment_parcel_no'].split(
            '\n')
        for index, carrier_str in enumerate(all_shipping_carriers):

            if self.SHIPPING_CARRIER_LINKS.get(carrier_str):
                shipping_carrier_lines += f'<li style="margin-bottom: 6px;"><u>{carrier_str}</u></br>Consignment/Parcel Number: {all_shipping_report_consignment_parcel_no[index]}</br>Tracking Link: <a style="text-decoration: none;" href="{self.SHIPPING_CARRIER_LINKS.get(carrier_str)}">{self.SHIPPING_CARRIER_LINKS.get(carrier_str)}</a></li>'
        shipping_carrier_lines = f'{shipping_carrier_lines}</ul>'

        if data_dict.get('shipping_report_serial_no'):
            serial_numbers_list = data_dict['shipping_report_serial_no'].split(
                '\n')

        for index, serial_number in enumerate(serial_numbers_list):
            serial_numbers_line += f'<li style="margin-bottom: 6px;">{serial_number}</span></li>'

        all_serial_numbers_lines = f'{serial_numbers_line}</ul>'

        res = f'<span>{customer_reference_line + shipping_carrier_lines + all_serial_numbers_lines}</span>'

        return res

        # test = (f'all_shipping_carriers:\n{all_shipping_carriers}')
        # test += (f'\n\nres:\n{res}')
        # raise UserError(test)
        # shipping_carriers = SHIPPING_CARRIER_LINKS[data_dict['Sale Order'].client_order_ref
        # result = f'<p>{customer_reference}</p>'

        # raise UserError(f'data_dict:\n{data_dict}')

    def get_email_body(self, data_dict):
        table_width = 600
        customer_name = (
            ' ' + data_dict['Sale Order'].partner_id.name if data_dict['Sale Order'].partner_id.name else '')

        email_content = {
            'text_line_1': f'Hello{customer_name},',
            'text_line_2': f'{self.get_formated_data(data_dict)}',
            # 'text_line_2': f'TEXT TO ADD.</br><span>{self.get_formated_data(data_dict)}</span>',
            # 'text_line_2': f'Please find attached a {self.HEADER_TEXT}.',
            'text_line_3': 'Kind regards,',
            'text_line_4': 'JTRS LTD',
            'table_width': table_width
        }

        email_html = f"""
        <!--?xml version="1.0"?-->
        <div style="background:#F0F0F0;color:#515166;padding:10px 0px;font-family:Arial,Helvetica,sans-serif;font-size:12px;">
            <table style="background-color:transparent;width:{email_content['table_width']}px;margin:5px auto;">
                <tbody>
                    <tr>
                        <td style="padding:0px;">
                            <a href="/" style="text-decoration-skip:objects;color:rgb(33, 183, 153);">
                                <img src="/web/binary/company_logo" style="border:0px;vertical-align: baseline; max-width: 100px; width: auto; height: auto;" class="o_we_selected_image" data-original-title="" title="" aria-describedby="tooltip935335">
                            </a>
                        </td>
                        <td style="padding:0px;text-align:right;vertical-align:middle;">&nbsp;</td>
                    </tr>
                </tbody>
            </table>
            <table style="background-color:transparent;width:{email_content['table_width']}px;margin:0px auto;background:white;border:1px solid #e1e1e1;">
                <tbody>
                    <tr>
                        <td style="padding:15px 20px 10px 20px;">
                            <p>{email_content['text_line_1']}</p>
                            </br>
                            <p>{email_content['text_line_2']}</p>
                            </br>
                            <p style="padding-top:20px;">{email_content['text_line_3']}</p>
                            <p>{email_content['text_line_4']}</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:15px 20px 10px 20px;">
                            <!--% include_table %-->
                        </td>
                    </tr>
                </tbody>
            </table>
            <table style="background-color:transparent;width:{email_content['table_width']}px;margin:auto;text-align:center;font-size:12px;">
                <tbody>
                    <tr>
                        <td style="padding-top:10px;color:#afafaf;">
                            <!-- Additional content can go here -->
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        """
        return email_html

    def send_email(self, data):
        recipient_email = data['Sale Order'].partner_id.email
        sender_email = 'OdooBot <odoobot@jtrs.co.uk>'
        cc_email = 'martynas.minskis@jtrs.co.uk'
        subject = f"Serial Numbers ({date.today().strftime('%d/%m/%y')})"
        email_body = self.get_email_body(data)
        # test = f'send_email > SHIPPING_CARRIER_LINKS:\n{self.SHIPPING_CARRIER_LINKS}\n\ndata:\n{data}'
        # test = f'\n\nemail_body:\n{email_body}'
        # raise UserError(test)
        mail_mail = self.env['mail.mail'].create({
            'email_to': recipient_email,
            'email_from': sender_email,
            'email_cc': cc_email,
            'subject': subject,
            'body_html': email_body,
        })
        mail_mail.send()
        # return True

    def update_sales_orders_and_send_emails(self, formatted_data_dict):
        for po_string, data_list in formatted_data_dict.items():
            # #  TEST
            # if po_string != 'PO51410':
            #     continue
            shipping_report_values = self.get_shipping_report_values(data_list)
            # Example of shipping_report_values:
            # {'shipping_report_carrier': 'Parcelforce Worldwide\nDPD(UK)', 'shipping_report_consignment_parcel_no': 'WM0339553\n15502667556123', 'shipping_report_serial_no': 'JRMW9KNY7P', 'shipping_report_imei_no': '', 'shipping_report_source': 273041}
            # raise UserError(f'shipping_report_values:\n{shipping_report_values}')
            purchase_order = self.env['purchase.order'].search(
                [('name', '=', po_string)])
            if purchase_order:
                sales_order = purchase_order.x_sale_id
                if sales_order:
                    sales_order.write(shipping_report_values)
                    self.log_shipping_report_operation(
                        sales_order, shipping_report_values, f'Sale Order {sales_order.name} updated')

                    shipping_report_values['Sale Order'] = sales_order
                    self.send_email(shipping_report_values)

    def get_shipping_report_values(self, data_list):
        return {
            'shipping_report_carrier': '\n'.join(filter(None, data_list[0])),
            'shipping_report_consignment_parcel_no': '\n'.join(filter(None, data_list[1])),
            'shipping_report_serial_no': '\n'.join(filter(None, data_list[2])),
            'shipping_report_imei_no': '\n'.join(filter(None, data_list[3])),
            'shipping_report_source': self.id
        }

    def log_shipping_report_operation(self, sales_order, values, message):
        # Format the message for logging
        final_message = f"Shipping Report Data\n\nmessage:\n{message}\n\nvalues:\n{values}"

        # Create a log entry in ir.logging
        self.env['ir.logging'].create({
            'name': 'Shipping Report Update',  # Name of the log
            'type': 'server',  # Indicates that this log is from the server-side
            'dbname': self.env.cr.dbname,  # Current database name
            'level': 'info',  # Log level (info, warning, error)
            'message': final_message,  # The main log message
            'path': 'models.res.partner',  # Path indicates the module/class path
            # Method name or line number
            'line': 'ShippingReportUpload.log_shipping_report_operation',
            'func': '__import_shipping_report_csv_data__',  # Function name
        })
