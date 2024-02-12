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

    def handle_multiple_purchase_orders(self, formatted_data_dict):
        for po_string, data_dict in formatted_data_dict.items():
            # Example of data_dict:
            # {'Parcelforce Worldwide': [['WM0339553'], ['JRMW9KNY7P', ''], ['']], 'DPD(UK)': [['15502667556123'], [''], ['']]}

            sales_order = self.get_sale_order(po_string)
            if not sales_order:
                self.log_shipping_report_operation(
                    "", shipping_report_values, f'Sale Order for purchase_order:{po_string} not found')
                continue

            self.update_sales_orders(data_dict, sales_order)
            self.send_email(data_dict, sales_order)

    def import_shipping_report_csv_data(self):
        if not self.shipping_report_to_upload:
            raise UserError("No shipping report to upload.")

        csv_data = self.decode_csv_data()
        res_list = self.parse_csv_data(csv_data)
        # raise UserError(f'res_list:\n{res_list}')

        formatted_data_dict = self.format_data(res_list)

        self.handle_multiple_purchase_orders(formatted_data_dict)

    def decode_csv_data(self):
        return base64.b64decode(self.shipping_report_to_upload).decode('utf-8')

    def parse_csv_data(self, csv_data):
        csv_file = StringIO(csv_data)
        csv_reader = csv.reader(csv_file)
        return [row for row in csv_reader]

    def format_data(self, res_list):
        # Example of res_list:
        # [['Account Code', 'Account Sequence', 'Customer PO', 'Order Date', 'WC Order No', 'Line Number', 'Part Number', 'Customer Product Code', 'Part Description', 'Line Qty', 'Unit Price', 'Unit VAT', 'Currency', 'Invoice No', 'Despatch Date', 'Delivery No', 'Carrier', 'Consignment/Parcel No', 'Delivery Contact', 'Delivery Address 1', 'Delivery Address 2', 'Delivery Address 3', 'Delivery Town', 'Delivery Address 5', 'Delivery Postcode', 'Delivery Country Code', 'Order Text 1', 'Order Text 2', 'Order Text 3', 'Serial No', 'IMEI No', 'SIM No'], ['JTR001', '000', 'PO51414', '29/11/2023', 'FGD2822', '1', 'MK2K3B/A', 'MK2K3B/A', 'IPAD 9TH GEN 10.2 WIFI 64GB SG', '1', '255.80', '51.16', 'GBP', 'LN27663', '29/11/2023', 'FGD2822/00', 'Parcelforce Worldwide', 'WM0336870', 'CAMBRIDGESHIRE COUNTY COUNCIL', 'THE ICT SERVICE SPEKE HOUSE', 'COMPASS POINT BUSINESS PARK', 'STOCKS BRIDGE WAY', 'ST. IVES', '', 'PE27 5JL', 'GB', '-  -', 'FAO: LEISHA JOY', '-  -', 'J3Q2VQ67TD', '', "'"],...]

        formatted_data = {}
        for line in res_list[1:]:

            if not line or not line[2]:
                continue

            po_name = line[2]
            if not formatted_data.get(po_name):
                # 2.Customer PO, 16.Carrier, 17.Consignment/Parcel No, 29.Serial No, 30.IMEI No
                formatted_data[po_name] = {line[16]: [
                    [line[17]], [line[29]], [line[30]]]}
            else:
                self.format_carrier_dictionary(formatted_data[po_name], line)

        # Example of formatted_data:
        # {'PO51414': {'Parcelforce Worldwide': [['WM0336870'], ['J3Q2VQ67TD', 'GQ4TQ71VVN', 'R2JRRW7GV7', 'TY26X3QL6R', ''], ['']]}, 'PO51419': {'Parcelforce Worldwide': [['WM0337040'], ['KFHFJQLWRR', 'KVDGDXQ4DF', 'QK46TVDHW0', 'DJ4H3KPFGP', 'Y3WR4Q22VJ', 'RWQWYC2QG4', 'FMXF1W26XQ', 'JPQ0TFV9W4', 'R6HYF6YHLG', 'VG4G449N75', 'V3V19QR4H5'], ['']]}, 'PO51420': {'Parcelforce Worldwide': [['WM0338592'], ['P52G2X4WT3', 'VJ2492M2G9'], ['']]}, 'PO51410': {'Parcelforce Worldwide': [['WM0339553'], ['JRMW9KNY7P', ''], ['']], 'DPD(UK)': [['15502667556123'], [''], ['']]}}

        return formatted_data

    def append_unique_values(self, data_list, line):
        for idx, col in enumerate([17, 29, 30]):
            if line[col] not in data_list[idx]:
                data_list[idx].append(line[col])

    def format_carrier_dictionary(self, data_dict, line):
        carrier = line[16]
        if not data_dict.get(carrier):
            data_dict[carrier] = [[line[17]], [line[29]], [line[30]]]
        else:
            self.append_unique_values(data_dict[carrier], line)

    def get_formatted_data(self, data_dict, sale_order):
        """
        Formats the data for display in email content.

        Args:
            data_dict (dict): Dictionary containing shipping report data.
            Example: {'Parcelforce Worldwide': [['WM0339553'], ['JRMW9KNY7P', ''], ['']], 'DPD(UK)': [['15502667556123'], [''], ['']]}

        Returns:
            str: Formatted HTML string for email content.
        """

        # Initialize the HTML content with customer reference
        customer_reference_line = f'<p><strong>Customer Reference</strong>: {sale_order.client_order_ref}</p>'
        customer_reference_line += '<strong>Shipping Carriers</strong><ul style="margin-top: 0; padding-top: 3;">'
        customer_reference_line += '<div style="margin-bottom: 15px;"></div>'

        # Iterate through each carrier in the data dictionary
        for carrier_name, carrier_data_list in data_dict.items():
            # Check for a valid tracking link
            tracking_link = self.SHIPPING_CARRIER_LINKS.get(carrier_name)
            if tracking_link:
                parcel_number = ', '.join(filter(None, carrier_data_list[0]))
                # Append carrier and consignment number to the HTML content
                customer_reference_line += (f'<li style="margin-bottom: 6px;">'
                                            f'<u><strong>{carrier_name}</strong></u></br>'
                                            f'Consignment/Parcel Number: {parcel_number}</br>'
                                            f'Tracking Link: <a style="text-decoration: none;" href="{tracking_link}">{tracking_link}</a>'
                                            f'</li>')

                # Process serial numbers if they exist
                if carrier_data_list[1]:
                    customer_reference_line += '<strong>Serial Numbers</strong><ul style="margin-top: 0; padding-top: 3;">'
                    for serial_number in carrier_data_list[1]:
                        display_serial = serial_number if serial_number else '-'
                        customer_reference_line += f'<li style="margin-bottom: 6px;">{display_serial}</li>'
                    customer_reference_line += '</ul>'

                # Process IMEI numbers if they exist
                if carrier_data_list[2]:
                    customer_reference_line += '<strong>IMEI Numbers</strong><ul style="margin-top: 0; padding-top: 3;">'
                    for imei_number in carrier_data_list[2]:
                        display_imei = imei_number if imei_number else '-'
                        customer_reference_line += f'<li style="margin-bottom: 6px;">{display_imei}</li>'
                    customer_reference_line += '</ul>'

        # Close the HTML list and wrap the content
        customer_reference_line += '</ul>'
        formatted_html_content = f'<span>{customer_reference_line}</span>'

        return formatted_html_content

    def get_email_body(self, data_dict, sale_order):
        table_width = 600
        customer_name = (
            ' ' + sale_order.partner_id.name if sale_order.partner_id.name else '')

        email_content = {
            'text_line_1': f'Hello{customer_name},',
            'text_line_2': f'{self.get_formatted_data(data_dict, sale_order)}',
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

    def send_email(self, data, sale_order):

        recipient_email = sale_order.partner_id.email
        sender_email = 'OdooBot <odoobot@jtrs.co.uk>'
        cc_email = 'martynas.minskis@jtrs.co.uk'
        subject = f"Serial Numbers ({date.today().strftime('%d/%m/%y')})"
        email_body = self.get_email_body(data, sale_order)
        mail_mail = self.env['mail.mail'].create({
            'email_to': recipient_email,
            'email_from': sender_email,
            'email_cc': cc_email,
            'subject': subject,
            'body_html': email_body,
        })
        mail_mail.send()
        # return True

    def get_sale_order(self, po_string):
        purchase_order = self.env['purchase.order'].search(
            [('name', '=', po_string)])
        if not purchase_order:
            return None

        return purchase_order.x_sale_id

    def update_sales_orders(self, formatted_data_dict, sales_order):

        shipping_report_values = self.get_shipping_report_values(
            formatted_data_dict)

        sales_order.write(shipping_report_values)

        self.log_shipping_report_operation(
            sales_order, shipping_report_values, f'Sale Order {sales_order.name} updated')

    def get_shipping_report_values(self, data_dict):
        # Example of returned dictionary:
        # {'shipping_report_carrier': ['Parcelforce Worldwide', 'DPD(UK)'], 'shipping_report_consignment_parcel_no': ['WM0339553', '15502667556123'], 'shipping_report_serial_no': ['JRMW9KNY7P', '', ''], 'shipping_report_imei_no': ['', ''], 'shipping_report_source': 273041}
        data_list = [[], [], [], []]
        for carrier_name, carrier_data_list in data_dict.items():

            data_list[0].append(carrier_name)
            for indx in range(1, 4):
                # Check if carrier_data_list has enough elements to avoid IndexError
                if len(carrier_data_list) >= indx:
                    data_list[indx].extend(carrier_data_list[indx-1])
                else:
                    # Handle cases where carrier_data_list is shorter than expected
                    # Extend with an empty list or handle as needed
                    data_list[indx].extend([])

        return {
            'shipping_report_carrier': '\n'.join(filter(None, data_list[0])),
            'shipping_report_consignment_parcel_no': '\n'.join(filter(None, data_list[1])),
            'shipping_report_serial_no': '\n'.join(filter(None, data_list[2])),
            'shipping_report_imei_no': '\n'.join(filter(None, data_list[3])),
            # Partner where Shipping Report Document Added On
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
